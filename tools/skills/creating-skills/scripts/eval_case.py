"""Run one eval case in one arm into the canonical eval workspace."""

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from scripts.adapters import available_harnesses, get_harness
from scripts.harness import Harness, RunResult
from scripts.workspace import (
    ARMS,
    Timing,
    create_iteration,
    eval_directory,
    iteration_directory,
    preserve_inputs,
    resolve_inputs,
    resolve_workspace,
    run_id,
    stage_inputs,
    validate_arm,
    write_eval_metadata,
    write_run_artifacts,
)


@dataclass(frozen=True)
class EvalCase:
    """One test case from a skill's ``evals/evals.json``."""

    eval_id: int | str
    prompt: str
    expected_output: str = ""
    files: tuple[str, ...] = ()
    expectations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CaseRun:
    """The saved artifacts for one eval case in one arm."""

    run_id: str
    iteration_dir: Path
    eval_dir: Path
    arm_dir: Path
    result: RunResult
    timing: Timing


def load_evals(skill_path: Path) -> tuple[EvalCase, ...]:
    """Load and validate the eval definitions for ``skill_path``."""
    skill_path = validate_skill(skill_path)
    path = skill_path / "evals" / "evals.json"
    if not path.is_file():
        raise FileNotFoundError(f"no eval definition at {str(path)!r}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("eval definition must be a JSON object")
    raw_evals = data.get("evals")
    if not isinstance(raw_evals, list):
        raise TypeError("eval definition must contain an 'evals' list")

    cases: list[EvalCase] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_evals):
        if not isinstance(raw, dict):
            raise TypeError(f"eval at index {index} must be a JSON object")
        eval_id = raw.get("id")
        if isinstance(eval_id, bool) or not isinstance(eval_id, (int, str)):
            raise TypeError(f"eval at index {index} is missing a valid 'id'")
        key = str(eval_id)
        if not key:
            raise ValueError(f"eval at index {index} is missing a valid 'id'")
        if key in seen:
            raise ValueError(f"duplicate eval id {key!r}")
        seen.add(key)

        prompt = raw.get("prompt")
        if prompt is None:
            raise ValueError(f"eval {key!r} is missing a non-empty 'prompt'")
        if not isinstance(prompt, str):
            raise TypeError(f"eval {key!r} has a non-string 'prompt'")
        if not prompt.strip():
            raise ValueError(f"eval {key!r} is missing a non-empty 'prompt'")
        expected_output = raw.get("expected_output", "")
        if not isinstance(expected_output, str):
            raise TypeError(f"eval {key!r} has a non-string 'expected_output'")

        files = _string_list(raw.get("files", []), f"eval {key!r} 'files'")
        expectations = _string_list(
            raw.get("expectations", []), f"eval {key!r} 'expectations'"
        )
        cases.append(
            EvalCase(
                eval_id=eval_id,
                prompt=prompt,
                expected_output=expected_output,
                files=files,
                expectations=expectations,
            )
        )
    return tuple(cases)


def find_eval(cases: Sequence[EvalCase], eval_id: int | str) -> EvalCase:
    """Return the case matching ``eval_id`` or raise with the available IDs."""
    value = str(eval_id)
    for case in cases:
        if str(case.eval_id) == value:
            return case
    available = ", ".join(str(case.eval_id) for case in cases) or "none"
    raise ValueError(f"no eval with id {value!r}; available: {available}")


def run_case(
    harness: Harness,
    skill_path: Path,
    case: EvalCase,
    arm: str,
    *,
    workspace: Path | None = None,
    iteration_dir: Path | None = None,
    baseline_skill: Path | None = None,
    model: str | None = None,
    timeout_seconds: float = 600.0,
) -> CaseRun:
    """Run one eval case in one arm and save the canonical artifacts.

    When ``iteration_dir`` is supplied, ``workspace`` is ignored. Inputs are
    validated before the iteration is created, so a bad definition does not
    consume an iteration number.
    """
    validate_arm(arm)
    skill_path = validate_skill(skill_path)
    skills = _scope_skills(arm, skill_path, baseline_skill)
    input_sources = resolve_inputs(skill_path, case.files)
    identity = run_id(case.eval_id, arm)
    if iteration_dir is None:
        iteration_dir = create_iteration(resolve_workspace(skill_path, workspace))
    else:
        iteration_dir = Path(iteration_dir).resolve()
        iteration_dir.mkdir(parents=True, exist_ok=True)

    eval_dir = eval_directory(iteration_dir, case.eval_id)
    eval_dir.mkdir(parents=True, exist_ok=True)
    write_eval_metadata(
        eval_dir,
        eval_id=case.eval_id,
        prompt=case.prompt,
        expected_output=case.expected_output,
    )
    inputs = preserve_inputs(eval_dir, input_sources)

    arm_dir = eval_dir / arm
    if arm_dir.exists():
        shutil.rmtree(arm_dir)
    arm_dir.mkdir(parents=True)

    with harness.prepare_scope(skills) as scope:
        staged = stage_inputs(scope, inputs)
        result = harness.run(
            scope,
            case.prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=staged,
        )
        saved = write_run_artifacts(arm_dir, result, scope.path, run_identity=identity)

    return CaseRun(
        run_id=identity,
        iteration_dir=iteration_dir,
        eval_dir=eval_dir,
        arm_dir=arm_dir,
        result=replace(result, output_files=saved.output_files),
        timing=saved.timing,
    )


def _scope_skills(
    arm: str, skill_path: Path, baseline_skill: Path | None
) -> tuple[Path, ...]:
    if arm == "with_skill":
        return (skill_path,)
    if arm == "without_skill":
        return ()
    if baseline_skill is None:
        raise ValueError("the old_skill arm requires a baseline skill")
    return (validate_skill(baseline_skill),)


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{label} must contain only strings")
        items.append(item)
    return tuple(items)


def validate_skill(skill_path: Path) -> Path:
    path = Path(skill_path).resolve()
    if not (path / "SKILL.md").is_file():
        raise ValueError(f"skill directory {str(path)!r} does not contain SKILL.md")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    """Run the single-case command line interface."""
    parser = argparse.ArgumentParser(description="Run one eval case in one arm.")
    parser.add_argument("--skill", required=True, type=Path)
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--iteration", type=int)
    parser.add_argument("--baseline-skill", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--harness", default=available_harnesses()[0])
    args = parser.parse_args(argv)

    try:
        skill_path = validate_skill(args.skill)
        case = find_eval(load_evals(skill_path), args.eval_id)
        iteration_dir = None
        if args.iteration is not None:
            workspace = resolve_workspace(skill_path, args.workspace)
            iteration_dir = iteration_directory(workspace, args.iteration)
            if not iteration_dir.is_dir():
                raise ValueError(
                    f"iteration {args.iteration} does not exist in {str(workspace)!r}"
                )
        harness = get_harness(args.harness)
        run = run_case(
            harness,
            skill_path,
            case,
            args.arm,
            workspace=None if iteration_dir else args.workspace,
            iteration_dir=iteration_dir,
            baseline_skill=args.baseline_skill,
            model=args.model,
            timeout_seconds=args.timeout,
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"{run.run_id}\t{run.arm_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
