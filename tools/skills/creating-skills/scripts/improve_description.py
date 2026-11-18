"""Ask a fresh no-tools agent to improve a skill description."""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scripts.harness import Harness, RunResult

MAX_DESCRIPTION_CHARS = 1024
_NEW_DESCRIPTION = re.compile(r"<new_description>(.*?)</new_description>", re.DOTALL)


class DescriptionTooLongError(RuntimeError):
    """Raised when a description is still over the limit after a rewrite."""


@dataclass(frozen=True)
class ProposedDescription:
    """One optimizer proposal and the runs behind it."""

    description: str
    prompt: str
    response: str
    char_count: int
    rewrite_prompt: str | None
    rewrite_response: str | None
    rewrite_description: str | None
    rewrite_char_count: int | None
    run: RunResult
    rewrite_run: RunResult | None


def build_improvement_prompt(
    *,
    skill_name: str,
    skill_content: str,
    current_description: str,
    train_results: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> str:
    """Build a harness-neutral prompt from train failures and train history.

    ``train_results`` is a trigger evaluation document. History entries may
    carry test fields, but this function reads only their train fields so held
    out results cannot leak into the improvement prompt.
    """
    results = train_results.get("results")
    summary = train_results.get("summary")
    if not isinstance(results, list) or not isinstance(summary, dict):
        raise TypeError("train results must contain 'results' and 'summary'")

    failed_triggers = [
        result
        for result in results
        if isinstance(result, dict)
        and result.get("should_trigger") is True
        and result.get("pass") is not True
    ]
    false_triggers = [
        result
        for result in results
        if isinstance(result, dict)
        and result.get("should_trigger") is False
        and result.get("pass") is not True
    ]

    passed = summary.get("passed")
    total = summary.get("total")
    prompt = f"""You are optimizing the description of an agent skill named "{skill_name}". A skill is a reusable procedure the agent can load when a task matches it. The skill's name and description are shown to the agent before it decides whether to load the skill. The description is therefore the trigger, not a summary of the implementation.

Write a description that makes the agent load the skill for relevant requests and avoid loading it for nearby requests that need something else.

Here is the current description:
<current_description>
{current_description}
</current_description>

Current train score: {passed}/{total}

"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have loaded the skill but did not):\n"
        for result in failed_triggers:
            prompt += (
                f'  - "{result.get("query", "")}" '
                f"(triggered {result.get('triggers', 0)}/{result.get('runs', 0)} times)\n"
            )
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (loaded the skill but should not have):\n"
        for result in false_triggers:
            prompt += (
                f'  - "{result.get("query", "")}" '
                f"(triggered {result.get('triggers', 0)}/{result.get('runs', 0)} times)\n"
            )
        prompt += "\n"

    train_history = _train_history(history)
    if train_history:
        prompt += (
            "PREVIOUS ATTEMPTS (do not repeat these; try a structurally "
            "different description):\n\n"
        )
        for entry in train_history:
            prompt += (
                f"<attempt train={entry['train_score']}>\n"
                f'Description: "{entry["description"]}"\n'
            )
            if entry["results"]:
                prompt += "Train results:\n"
                for result in entry["results"]:
                    status = "PASS" if result.get("pass") else "FAIL"
                    prompt += (
                        f'  [{status}] "{str(result.get("query", ""))[:80]}" '
                        f"(triggered {result.get('triggers', 0)}/"
                        f"{result.get('runs', 0)})\n"
                    )
            prompt += "</attempt>\n\n"

    prompt += f"""Skill content (for context on what the skill does):
<skill_content>
{skill_content}
</skill_content>

Based on the failures, write a new and improved description that is more likely to trigger correctly. Generalize from the failures to broader categories of user intent; do not build an ever-expanding list of specific queries. A long list overfits the sample and consumes space in every request.

Keep the description to roughly 100-200 words. There is a hard limit of 1024 characters: a description over that limit will be rejected.

Tips that work well for descriptions:
- Phrase the skill as "Use this skill for ..." rather than "This skill does ...".
- Focus on the user's intent and the situations that should invoke the skill, not on the implementation.
- Make the description distinctive so it wins over neighboring skills.
- If repeated attempts fail, change the sentence structure or wording instead of adding more clauses.

Respond with only the new description text inside <new_description> tags, nothing else."""
    return prompt


def parse_description(text: str) -> str:
    """Extract a description from an optimizer response."""
    match = _NEW_DESCRIPTION.search(text)
    description = match.group(1) if match is not None else text
    return description.strip().strip('"').strip()


def propose_description(
    harness: Harness,
    *,
    skill_name: str,
    skill_content: str,
    current_description: str,
    train_results: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    model: str,
    timeout_seconds: float = 300.0,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> ProposedDescription:
    """Run the optimizer in no-tools completion mode with every skill denied."""
    if not model.strip():
        raise ValueError("a non-empty model is required for description improvement")

    prompt = build_improvement_prompt(
        skill_name=skill_name,
        skill_content=skill_content,
        current_description=current_description,
        train_results=train_results,
        history=history,
    )
    run = _complete(harness, prompt, model=model, timeout_seconds=timeout_seconds)
    response = run.assistant_text.strip()
    if not response:
        raise RuntimeError("the optimizer returned no description")
    description = parse_description(response)
    if not description:
        raise RuntimeError("the optimizer returned an empty description")
    proposed_char_count = len(description)

    rewrite_prompt: str | None = None
    rewrite_response: str | None = None
    rewrite_description: str | None = None
    rewrite_run: RunResult | None = None
    too_long: DescriptionTooLongError | None = None

    if len(description) > MAX_DESCRIPTION_CHARS:
        rewrite_prompt = (
            f"{prompt}\n\n"
            f"---\n\n"
            f"A previous attempt produced this description, which at "
            f"{proposed_char_count} characters is over the {MAX_DESCRIPTION_CHARS}-character "
            f"hard limit:\n\n"
            f'"{description}"\n\n'
            f"Rewrite it to be under {MAX_DESCRIPTION_CHARS} characters while keeping "
            f"the most important trigger words and intent coverage. Respond with only "
            f"the new description in <new_description> tags."
        )
        try:
            rewrite_run = _complete(
                harness,
                rewrite_prompt,
                model=model,
                timeout_seconds=timeout_seconds,
            )
            rewrite_response = rewrite_run.assistant_text.strip()
            if not rewrite_response:
                raise RuntimeError("the optimizer returned no rewritten description")
            rewrite_description = parse_description(rewrite_response)
            if not rewrite_description:
                raise RuntimeError(
                    "the optimizer returned an empty rewritten description"
                )
            description = rewrite_description
        except (OSError, RuntimeError) as error:
            _log_failure(
                log_dir,
                ProposedDescription(
                    description=description,
                    prompt=prompt,
                    response=response,
                    char_count=proposed_char_count,
                    rewrite_prompt=rewrite_prompt,
                    rewrite_response=rewrite_response,
                    rewrite_description=rewrite_description,
                    rewrite_char_count=(
                        len(rewrite_description)
                        if rewrite_description is not None
                        else None
                    ),
                    run=run,
                    rewrite_run=rewrite_run,
                ),
                model=model,
                iteration=iteration,
                error=str(error),
            )
            raise
        if len(rewrite_description) > MAX_DESCRIPTION_CHARS:
            too_long = DescriptionTooLongError(
                f"the rewritten description is {len(rewrite_description)} characters, "
                f"over the {MAX_DESCRIPTION_CHARS}-character limit"
            )

    proposal = ProposedDescription(
        description=description,
        prompt=prompt,
        response=response,
        char_count=proposed_char_count,
        rewrite_prompt=rewrite_prompt,
        rewrite_response=rewrite_response,
        rewrite_description=rewrite_description,
        rewrite_char_count=(
            len(rewrite_description) if rewrite_description is not None else None
        ),
        run=run,
        rewrite_run=rewrite_run,
    )
    if log_dir is not None:
        _write_logs(Path(log_dir), proposal, model=model, iteration=iteration)
    if too_long is not None:
        raise too_long
    return proposal


def _complete(
    harness: Harness,
    prompt: str,
    *,
    model: str,
    timeout_seconds: float,
) -> RunResult:
    with harness.prepare_scope() as scope:
        run = harness.run(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            no_tools=True,
        )
    if run.timed_out:
        raise RuntimeError("the optimizer run timed out")
    if run.exit_code != 0:
        detail = run.stderr.strip() or "no stderr"
        raise RuntimeError(
            f"the optimizer run exited with code {run.exit_code}: {detail}"
        )
    return run


def _train_history(
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw in history:
        raw_results = raw.get("train_results")
        description = raw.get("description")
        entries.append(
            {
                "description": description if isinstance(description, str) else "",
                "train_score": (
                    f"{raw.get('train_passed', 0)}/{raw.get('train_total', 0)}"
                ),
                "results": [
                    result for result in raw_results if isinstance(result, dict)
                ]
                if isinstance(raw_results, list)
                else [],
            }
        )
    return entries


def _write_logs(
    log_dir: Path,
    proposal: ProposedDescription,
    *,
    model: str,
    iteration: int | None,
    error: str | None = None,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    stem = f"improve_iter_{iteration if iteration is not None else 'unknown'}"
    _write_transcript(log_dir / f"{stem}.transcript", proposal.run)
    if proposal.rewrite_run is not None:
        _write_transcript(log_dir / f"{stem}.rewrite.transcript", proposal.rewrite_run)

    document: dict[str, Any] = {
        "iteration": iteration,
        "model": model,
        "prompt": proposal.prompt,
        "response": proposal.response,
        "parsed_description": parse_description(proposal.response),
        "char_count": proposal.char_count,
        "over_limit": proposal.char_count > MAX_DESCRIPTION_CHARS,
        "rewrite_prompt": proposal.rewrite_prompt,
        "rewrite_response": proposal.rewrite_response,
        "rewrite_description": proposal.rewrite_description,
        "rewrite_char_count": proposal.rewrite_char_count,
        "final_description": proposal.description,
        "error": error,
        "run": _run_log(proposal.run, model=model),
        "rewrite_run": (
            _run_log(proposal.rewrite_run, model=model)
            if proposal.rewrite_run is not None
            else None
        ),
    }
    (log_dir / f"{stem}.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _log_failure(
    log_dir: Path | None,
    proposal: ProposedDescription,
    *,
    model: str,
    iteration: int | None,
    error: str,
) -> None:
    if log_dir is None:
        return
    _write_logs(
        Path(log_dir),
        proposal,
        model=model,
        iteration=iteration,
        error=error,
    )


def _write_transcript(path: Path, run: RunResult) -> None:
    Path(f"{path}.jsonl").write_text(run.transcript_jsonl, encoding="utf-8")
    Path(f"{path}.md").write_text(run.transcript_markdown, encoding="utf-8")


def _run_log(run: RunResult, *, model: str) -> dict[str, Any]:
    tokens = asdict(run.tokens)
    tokens["total"] = run.tokens.total
    return {
        "model": model,
        "no_tools": True,
        "loaded_skill_ids": list(run.loaded_skill_ids),
        "tokens": tokens,
        "duration_ms": run.duration_ms,
        "exit_code": run.exit_code,
        "stderr": run.stderr,
        "timed_out": run.timed_out,
    }
