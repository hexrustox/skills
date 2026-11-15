"""Run every eval case in both arms into one canonical iteration."""

import argparse
import shutil
import sys
import tempfile
import traceback
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from scripts.adapters import available_harnesses, get_harness
from scripts.eval_case import (
    CaseRun,
    EvalCase,
    find_eval,
    load_evals,
    run_case,
    validate_skill,
)
from scripts.frontmatter import parse_skill_md
from scripts.harness import Harness
from scripts.workspace import (
    ARMS,
    InputSource,
    create_iteration,
    eval_directory,
    iteration_directory,
    preserve_inputs,
    resolve_inputs,
    resolve_workspace,
    run_id,
    validate_eval_id,
    write_error_artifact,
    write_eval_metadata,
)

WITH_SKILL, WITHOUT_SKILL, OLD_SKILL = ARMS
RunStatus = Literal["ok", "failed", "error"]


@dataclass(frozen=True)
class RunOutcome:
    """The result of one eval case in one arm."""

    run_id: str
    eval_id: int | str
    arm: str
    status: RunStatus
    case_run: CaseRun | None = None
    error: str | None = None


@dataclass(frozen=True)
class BatchResult:
    """Every run produced by one batch invocation."""

    iteration_dir: Path
    baseline_arm: str
    outcomes: tuple[RunOutcome, ...]


@dataclass(frozen=True)
class _Failure:
    """An exception raised before or during a run."""

    error: Exception
    traceback: str


def run_batch(
    harness: Harness,
    skill_path: Path,
    *,
    eval_ids: Sequence[int | str] = (),
    workspace: Path | None = None,
    iteration_dir: Path | None = None,
    baseline_skill: Path | None = None,
    model: str | None = None,
    timeout_seconds: float = 600.0,
    progress: Callable[[str], None] | None = None,
) -> BatchResult:
    """Run every selected eval case in both arms and save the artifacts."""
    skill_path = validate_skill(skill_path)
    cases = _select_cases(load_evals(skill_path), eval_ids)
    if not cases:
        raise ValueError("eval definition contains no eval cases")
    for case in cases:
        validate_eval_id(case.eval_id)

    baseline_arm = OLD_SKILL if baseline_skill is not None else WITHOUT_SKILL
    arms = (WITH_SKILL, baseline_arm)
    resolved_inputs, input_failures = _resolve_case_inputs(skill_path, cases)
    if len(input_failures) == len(cases):
        details = "; ".join(
            f"eval {case.eval_id}: {failure.error}"
            for index, case in enumerate(cases)
            if (failure := input_failures.get(index)) is not None
        )
        raise ValueError(f"no runnable eval cases: {details}")

    notify = progress or (lambda _message: None)
    with tempfile.TemporaryDirectory(prefix="creating-skills-baseline-") as temp_dir:
        baseline = _prepare_baseline(skill_path, baseline_skill, Path(temp_dir))
        if iteration_dir is None:
            iteration_dir = create_iteration(resolve_workspace(skill_path, workspace))
        else:
            iteration_dir = Path(iteration_dir).resolve()
        _ensure_consistent_baseline(iteration_dir, baseline_arm)

        outcomes: dict[tuple[int, str], RunOutcome] = {}
        tasks: list[tuple[int, EvalCase, str]] = []
        for index, case in enumerate(cases):
            eval_dir = eval_directory(iteration_dir, case.eval_id)
            try:
                eval_dir.mkdir(parents=True, exist_ok=True)
                write_eval_metadata(
                    eval_dir,
                    eval_id=case.eval_id,
                    prompt=case.prompt,
                    expected_output=case.expected_output,
                )
            except OSError as error:
                _record_case_error(
                    eval_dir, case, arms, index, _failure(error), outcomes
                )
                continue

            failure = input_failures.get(index)
            if failure is not None:
                _record_case_error(eval_dir, case, arms, index, failure, outcomes)
                continue

            try:
                preserve_inputs(eval_dir, resolved_inputs[index])
            except OSError as error:
                _record_case_error(
                    eval_dir, case, arms, index, _failure(error), outcomes
                )
                continue

            tasks.extend((index, case, arm) for arm in arms)

        notify(f"iteration: {iteration_dir}")
        notify(f"baseline: {baseline_arm}")
        notify(f"runs: {len(tasks)}")
        if tasks:
            with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
                futures = {
                    executor.submit(
                        _run_one,
                        harness,
                        skill_path,
                        case,
                        arm,
                        iteration_dir,
                        baseline,
                        model,
                        timeout_seconds,
                    ): (index, case, arm)
                    for index, case, arm in tasks
                }
                for future in as_completed(futures):
                    index, _case, arm = futures[future]
                    outcome = future.result()
                    outcomes[(index, arm)] = outcome
                    notify(_progress_line(outcome))

    ordered = tuple(
        outcomes[(index, arm)] for index, _case in enumerate(cases) for arm in arms
    )
    return BatchResult(
        iteration_dir=iteration_dir,
        baseline_arm=baseline_arm,
        outcomes=ordered,
    )


def _resolve_case_inputs(
    skill_path: Path, cases: Sequence[EvalCase]
) -> tuple[dict[int, tuple[InputSource, ...]], dict[int, _Failure]]:
    resolved: dict[int, tuple[InputSource, ...]] = {}
    failures: dict[int, _Failure] = {}
    for index, case in enumerate(cases):
        try:
            resolved[index] = resolve_inputs(skill_path, case.files)
        except (OSError, ValueError) as error:
            failures[index] = _failure(error)
    return resolved, failures


def _prepare_baseline(
    skill_path: Path, baseline_skill: Path | None, temp_dir: Path
) -> Path | None:
    """Validate and alias a baseline snapshot under the live skill's name."""
    if baseline_skill is None:
        return None
    baseline = validate_skill(baseline_skill)
    if baseline == skill_path:
        raise ValueError("the baseline skill must not be the live skill")
    if parse_skill_md(baseline).name != parse_skill_md(skill_path).name:
        raise ValueError("the baseline skill name must match the live skill name")
    alias = temp_dir / skill_path.name
    shutil.copytree(baseline, alias)
    return alias


def _select_cases(
    cases: Sequence[EvalCase], eval_ids: Sequence[int | str]
) -> tuple[EvalCase, ...]:
    if not eval_ids:
        return tuple(cases)
    selected = {str(eval_id) for eval_id in eval_ids}
    for eval_id in selected:
        find_eval(cases, eval_id)
    return tuple(case for case in cases if str(case.eval_id) in selected)


def _ensure_consistent_baseline(iteration_dir: Path, baseline_arm: str) -> None:
    """Reject adding the other baseline form to an existing iteration."""
    if not iteration_dir.is_dir():
        return
    other = OLD_SKILL if baseline_arm == WITHOUT_SKILL else WITHOUT_SKILL
    if any((path / other).is_dir() for path in iteration_dir.glob("eval-*")):
        raise ValueError(
            f"iteration {str(iteration_dir)!r} already contains {other} runs; "
            "start a new iteration or use the same baseline"
        )


def _record_case_error(
    eval_dir: Path,
    case: EvalCase,
    arms: Sequence[str],
    index: int,
    failure: _Failure,
    outcomes: dict[tuple[int, str], RunOutcome],
) -> None:
    for arm in arms:
        identity = run_id(case.eval_id, arm)
        _write_error(eval_dir, case, arm, identity, failure)
        outcomes[(index, arm)] = _error_outcome(case, arm, failure.error)


def _error_outcome(case: EvalCase, arm: str, error: Exception) -> RunOutcome:
    return RunOutcome(
        run_id=run_id(case.eval_id, arm),
        eval_id=case.eval_id,
        arm=arm,
        status="error",
        error=str(error),
    )


def _run_one(
    harness: Harness,
    skill_path: Path,
    case: EvalCase,
    arm: str,
    iteration_dir: Path,
    baseline_alias: Path | None,
    model: str | None,
    timeout_seconds: float,
) -> RunOutcome:
    identity = run_id(case.eval_id, arm)
    eval_dir = eval_directory(iteration_dir, case.eval_id)
    try:
        run = run_case(
            harness,
            skill_path,
            case,
            arm,
            iteration_dir=iteration_dir,
            baseline_skill=baseline_alias,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    except Exception as error:  # noqa: BLE001 - one run must not stop the batch
        failure = _failure(error)
        _write_error(eval_dir, case, arm, identity, failure)
        return _error_outcome(case, arm, error)

    status: RunStatus = (
        "ok" if run.result.exit_code == 0 and not run.result.timed_out else "failed"
    )
    return RunOutcome(
        run_id=identity,
        eval_id=case.eval_id,
        arm=arm,
        status=status,
        case_run=run,
    )


def _progress_line(outcome: RunOutcome) -> str:
    run = outcome.case_run
    if run is None:
        return f"{outcome.status}\t{outcome.run_id}\t{outcome.error}"
    timing = run.timing
    return (
        f"{outcome.status}\t{outcome.run_id}\t"
        f"{timing.total_duration_seconds:.1f}s\t{timing.total_tokens} tokens"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the batch command line interface."""
    parser = argparse.ArgumentParser(
        description="Run every eval case in both arms into one iteration."
    )
    parser.add_argument("--skill", required=True, type=Path)
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        dest="eval_ids",
        metavar="ID",
        help="run only this eval ID; repeat to select several",
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--iteration", type=int)
    parser.add_argument("--baseline-skill", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--harness", default=available_harnesses()[0])
    args = parser.parse_args(argv)

    try:
        skill_path = validate_skill(args.skill)
        iteration_dir = None
        if args.iteration is not None:
            workspace = resolve_workspace(skill_path, args.workspace)
            iteration_dir = iteration_directory(workspace, args.iteration)
            if not iteration_dir.is_dir():
                raise ValueError(
                    f"iteration {args.iteration} does not exist in {str(workspace)!r}"
                )
        if args.baseline_skill is None:
            snapshot = resolve_workspace(skill_path, args.workspace) / "skill-snapshot"
            if snapshot.is_dir():
                print(
                    f"warning: {snapshot} exists; pass --baseline-skill to use it",
                    file=sys.stderr,
                )
        harness = get_harness(args.harness)
        result = run_batch(
            harness,
            skill_path,
            eval_ids=args.eval_ids,
            workspace=None if iteration_dir else args.workspace,
            iteration_dir=iteration_dir,
            baseline_skill=args.baseline_skill,
            model=args.model,
            timeout_seconds=args.timeout,
            progress=lambda message: print(message, flush=True),
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    _print_summary(result)
    return 0 if all(outcome.status == "ok" for outcome in result.outcomes) else 1


def _print_summary(result: BatchResult) -> None:
    counts = Counter(outcome.status for outcome in result.outcomes)
    print(f"iteration: {result.iteration_dir}")
    print(
        f"{len(result.outcomes)} runs: "
        f"{counts['ok']} ok, {counts['failed']} failed, {counts['error']} error"
    )
    for outcome in result.outcomes:
        if outcome.status == "ok":
            continue
        detail = outcome.error or "exit code or timeout"
        print(f"{outcome.status}: {outcome.run_id} ({detail})")


def _failure(error: Exception) -> _Failure:
    return _Failure(error=error, traceback=traceback.format_exc())


def _write_error(
    eval_dir: Path,
    case: EvalCase,
    arm: str,
    identity: str,
    failure: _Failure,
) -> None:
    try:
        write_error_artifact(
            eval_dir,
            run_identity=identity,
            eval_id=case.eval_id,
            arm=arm,
            error=failure.error,
            traceback_text=failure.traceback,
        )
    except OSError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
