"""Canonical eval workspace layout and artifact writing."""

import json
import re
import shutil
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.harness import PreparedScope, RunResult

ARMS = ("with_skill", "without_skill", "old_skill")
WORKSPACE_SUFFIX = "-workspace"

_ITERATION = re.compile(r"^iteration-(\d+)$")
_EVAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def workspace_name(skill_name: str) -> str:
    """Return the default workspace directory name for a skill."""
    return f"{skill_name}{WORKSPACE_SUFFIX}"


def skill_name_from_workspace(workspace: Path) -> str:
    """Return the skill name encoded in a default workspace directory name."""
    name = Path(workspace).name
    if name.endswith(WORKSPACE_SUFFIX) and len(name) > len(WORKSPACE_SUFFIX):
        return name[: -len(WORKSPACE_SUFFIX)]
    return name


def iteration_number(path: Path) -> int | None:
    """Return the number in an ``iteration-<N>`` directory name, if any."""
    match = _ITERATION.fullmatch(Path(path).name)
    return int(match.group(1)) if match is not None else None


@dataclass(frozen=True)
class InputSource:
    """An eval input resolved against the skill root."""

    relative_path: Path
    source_path: Path


@dataclass(frozen=True)
class InputFile:
    """An eval input preserved in the workspace and staged into a scope."""

    relative_path: Path
    preserved_path: Path


@dataclass(frozen=True)
class Timing:
    """Timing and token totals for one arm."""

    total_tokens: int
    duration_ms: int
    total_duration_seconds: float


@dataclass(frozen=True)
class SavedArtifacts:
    """The timing and saved output files for one arm."""

    timing: Timing
    output_files: tuple[Path, ...]


def default_workspace(skill_path: Path) -> Path:
    """Return the default workspace beside the skill directory."""
    skill = Path(skill_path).resolve()
    return skill.parent / workspace_name(skill.name)


def resolve_workspace(skill_path: Path, workspace: Path | None = None) -> Path:
    """Return the explicit workspace override or the default beside the skill."""
    if workspace is not None:
        return Path(workspace).expanduser().resolve()
    return default_workspace(skill_path)


def create_iteration(workspace: Path) -> Path:
    """Create and return the next ``iteration-<N>`` directory."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    number = 0
    for path in workspace.iterdir():
        match = _ITERATION.match(path.name)
        if path.is_dir() and match is not None:
            number = max(number, int(match.group(1)))
    number += 1
    while True:
        iteration = iteration_directory(workspace, number)
        try:
            iteration.mkdir()
        except FileExistsError:
            number += 1
            continue
        return iteration


def iteration_directory(workspace: Path, number: int) -> Path:
    """Return the path of ``iteration-<number>`` under a workspace."""
    if number < 1:
        raise ValueError("iteration numbers start at 1")
    return Path(workspace) / f"iteration-{number}"


def validate_eval_id(eval_id: int | str) -> str:
    """Return ``eval_id`` as a string safe for a directory name."""
    value = str(eval_id)
    if not _EVAL_ID.fullmatch(value):
        raise ValueError(
            f"eval id {eval_id!r} cannot be used in a directory name; "
            "use letters, digits, dots, underscores, or hyphens"
        )
    return value


def eval_directory(iteration_dir: Path, eval_id: int | str) -> Path:
    """Return the eval directory for ``eval_id`` under an iteration."""
    return Path(iteration_dir) / f"eval-{validate_eval_id(eval_id)}"


def eval_id_from_directory(eval_dir: Path) -> str:
    """Return the eval ID encoded in an ``eval-<ID>`` directory name."""
    name = Path(eval_dir).name
    suffix = name.removeprefix("eval-")
    if suffix == name or not suffix:
        raise ValueError(f"{str(eval_dir)!r} is not an eval directory")
    return suffix


def eval_id_sort_key(eval_id: int | str) -> tuple[int, int, str]:
    """Return a stable sort key for an eval identifier."""
    if isinstance(eval_id, int) and not isinstance(eval_id, bool):
        return (0, eval_id, "")
    value = str(eval_id)
    if value.isdigit():
        return (0, int(value), "")
    return (1, 0, value)


def eval_directories(iteration_dir: Path) -> list[Path]:
    """Return the canonical eval directories in stable eval-ID order."""
    return sorted(
        (
            path
            for path in Path(iteration_dir).iterdir()
            if path.is_dir() and path.name.startswith("eval-")
        ),
        key=lambda path: eval_id_sort_key(eval_id_from_directory(path)),
    )


def validate_arm(arm: str) -> str:
    """Return ``arm`` if it is one of the canonical arm names."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; expected one of: {', '.join(ARMS)}")
    return arm


def run_id(eval_id: int | str, arm: str) -> str:
    """Return the stable ``eval-<ID>-<arm>`` run identity."""
    return f"eval-{validate_eval_id(eval_id)}-{validate_arm(arm)}"


def write_eval_metadata(
    eval_dir: Path,
    *,
    eval_id: int | str,
    prompt: str,
    expected_output: str = "",
) -> Path:
    """Write the initial eval metadata unless it already exists."""
    eval_dir = Path(eval_dir)
    eval_dir.mkdir(parents=True, exist_ok=True)
    path = eval_dir / "eval_metadata.json"
    if path.exists():
        return path
    _write_json(
        path,
        {
            "eval_id": eval_id,
            "eval_name": f"eval-{validate_eval_id(eval_id)}",
            "prompt": prompt,
            "expected_output": expected_output,
            "expectations": [],
        },
    )
    return path


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_error_artifact(
    eval_dir: Path,
    *,
    run_identity: str,
    eval_id: int | str,
    arm: str,
    error: Exception,
    traceback_text: str,
) -> Path:
    """Write a diagnostic sidecar for a run that could not start."""
    arm_dir = Path(eval_dir) / arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    path = arm_dir / "error.json"
    _write_json(
        path,
        {
            "run_id": run_identity,
            "eval_id": eval_id,
            "arm": arm,
            "error": {"type": type(error).__name__, "message": str(error)},
            "traceback": traceback_text,
        },
    )
    return path


def resolve_inputs(skill_path: Path, files: Sequence[str]) -> tuple[InputSource, ...]:
    """Resolve eval input paths against the skill root and validate them."""
    skill_root = Path(skill_path).resolve()
    resolved: list[InputSource] = []
    for value in files:
        source = (skill_root / value).resolve()
        try:
            relative = source.relative_to(skill_root)
        except ValueError as error:
            raise ValueError(
                f"eval input {value!r} must be inside the skill directory"
            ) from error
        if not source.is_file():
            raise FileNotFoundError(
                f"eval input {value!r} does not exist under {str(skill_root)!r}"
            )
        resolved.append(InputSource(relative_path=relative, source_path=source))
    return tuple(resolved)


def preserve_inputs(
    eval_dir: Path, inputs: Sequence[InputSource]
) -> tuple[InputFile, ...]:
    """Copy inputs under ``eval_dir/inputs`` once per eval directory."""
    preserved: list[InputFile] = []
    for input_source in inputs:
        destination = Path(eval_dir) / "inputs" / input_source.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(input_source.source_path, destination)
        preserved.append(
            InputFile(
                relative_path=input_source.relative_path,
                preserved_path=destination,
            )
        )
    return tuple(preserved)


def stage_inputs(scope: PreparedScope, inputs: Sequence[InputFile]) -> tuple[Path, ...]:
    """Copy preserved inputs into the scope and return their staged paths."""
    staged: list[Path] = []
    for input_file in inputs:
        destination = scope.path / input_file.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_file.preserved_path, destination)
        staged.append(destination)
    return tuple(staged)


def write_run_artifacts(
    arm_dir: Path,
    result: RunResult,
    scope_path: Path,
    *,
    run_identity: str,
) -> SavedArtifacts:
    """Write the canonical arm artifacts and return the saved paths."""
    arm_dir = Path(arm_dir)
    arm_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = arm_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    scope_root = Path(scope_path).resolve()

    saved_outputs: list[Path] = []
    for output in result.output_files:
        relative = Path(_relative_path(output, scope_root))
        source = scope_root / relative
        destination = outputs_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        saved_outputs.append(destination)

    _write_json(outputs_dir / "metrics.json", asdict(result.metrics))
    (arm_dir / "transcript.jsonl").write_text(result.transcript_jsonl, encoding="utf-8")
    (arm_dir / "transcript.md").write_text(result.transcript_markdown, encoding="utf-8")

    timing = Timing(
        total_tokens=result.tokens.total,
        duration_ms=result.duration_ms,
        total_duration_seconds=round(result.duration_ms / 1000, 3),
    )
    _write_json(arm_dir / "timing.json", asdict(timing))
    _write_json(
        arm_dir / "run.json",
        _run_document(result, scope_root, run_identity=run_identity),
    )
    return SavedArtifacts(timing=timing, output_files=tuple(saved_outputs))


def _run_document(
    result: RunResult, scope_root: Path, *, run_identity: str
) -> dict[str, object]:
    tokens = asdict(result.tokens)
    tokens["total"] = result.tokens.total
    return {
        "run_id": run_identity,
        "assistant_text": result.assistant_text,
        "tokens": tokens,
        "duration_ms": result.duration_ms,
        "loaded_skill_ids": list(result.loaded_skill_ids),
        "output_files": [
            _relative_path(path, scope_root) for path in result.output_files
        ],
        "exit_code": result.exit_code,
        "stderr": result.stderr,
        "metrics": asdict(result.metrics),
        "timed_out": result.timed_out,
    }


def _relative_path(path: Path, root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve().relative_to(root).as_posix()
