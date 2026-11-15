"""Generate a standalone HTML review page from canonical eval run artifacts."""

import argparse
import base64
import json
import mimetypes
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scripts.workspace import ARMS, run_id

_ITERATION = re.compile(r"^iteration-(\d+)$")
_EXCLUDED_OUTPUTS = frozenset({"metrics.json", "user_notes.md"})
_TEXT_EXTENSIONS = frozenset(
    {
        ".c",
        ".cpp",
        ".css",
        ".csv",
        ".go",
        ".h",
        ".hpp",
        ".html",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".py",
        ".rb",
        ".r",
        ".rs",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
_IMAGE_EXTENSIONS = frozenset({".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
_MIME_OVERRIDES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".svg": "image/svg+xml",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "review.html"


def write_review(
    iteration_dir: Path,
    *,
    output_path: Path | None = None,
    previous_iteration: Path | None = None,
    benchmark_path: Path | None = None,
    include_previous: bool = True,
    skill_name: str | None = None,
) -> Path:
    """Write the standalone review page for ``iteration_dir`` and return its path."""
    iteration = Path(iteration_dir)
    data = collect_review(
        iteration,
        previous_iteration=previous_iteration,
        benchmark_path=benchmark_path,
        include_previous=include_previous,
        skill_name=skill_name,
    )
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    marker = "/*__EMBEDDED_DATA__*/"
    if marker not in template:
        raise ValueError(f"review template {str(_TEMPLATE_PATH)!r} has no data marker")
    embedded = (
        json.dumps(data, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    html = template.replace(marker, f"const EMBEDDED_DATA = {embedded};")
    destination = (
        Path(output_path)
        if output_path is not None
        else iteration.resolve() / "review.html"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return destination


def collect_review(
    iteration_dir: Path,
    *,
    previous_iteration: Path | None = None,
    benchmark_path: Path | None = None,
    include_previous: bool = True,
    skill_name: str | None = None,
) -> dict[str, Any]:
    """Build the review document embedded in the page."""
    iteration = Path(iteration_dir).resolve()
    if not iteration.is_dir():
        raise ValueError(f"iteration directory {str(iteration)!r} does not exist")

    runs = collect_runs(iteration)
    if not runs:
        raise ValueError(f"no runs found in {str(iteration)!r}")

    if previous_iteration is not None:
        previous_dir: Path | None = Path(previous_iteration).resolve()
    elif include_previous:
        previous_dir = find_previous_iteration(iteration)
    else:
        previous_dir = None
    if previous_dir is not None and not previous_dir.is_dir():
        raise ValueError(
            f"previous iteration directory {str(previous_dir)!r} does not exist"
        )

    benchmark = _load_benchmark(iteration, benchmark_path)
    return {
        "skill_name": skill_name or _skill_name(iteration, benchmark),
        "iteration": iteration.name,
        "runs": runs,
        "feedback": load_feedback(iteration),
        "previous": _previous_document(previous_dir) if previous_dir else None,
        "benchmark": benchmark,
    }


def collect_runs(iteration_dir: Path) -> list[dict[str, Any]]:
    """Return one review entry per arm directory in ``iteration_dir``."""
    runs: list[dict[str, Any]] = []
    for eval_dir in _eval_directories(Path(iteration_dir)):
        metadata = _load_json(eval_dir / "eval_metadata.json") or {}
        eval_id = metadata.get("eval_id", _eval_id_from_directory(eval_dir))
        for arm in ARMS:
            arm_dir = eval_dir / arm
            if arm_dir.is_dir():
                runs.append(_build_run(eval_dir, arm, metadata, eval_id))
    return runs


def find_previous_iteration(iteration_dir: Path) -> Path | None:
    """Return the nearest earlier ``iteration-<N>`` beside ``iteration_dir``."""
    iteration = Path(iteration_dir).resolve()
    number = _iteration_number(iteration)
    if number is None:
        return None
    candidates: list[tuple[int, Path]] = []
    for path in iteration.parent.iterdir():
        if not path.is_dir():
            continue
        other = _iteration_number(path)
        if other is not None and other < number:
            candidates.append((other, path))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def load_feedback(iteration_dir: Path) -> dict[str, Any]:
    """Load reviewer feedback saved beside an iteration."""
    document = _load_json(Path(iteration_dir) / "feedback.json") or {}
    reviews: dict[str, str] = {}
    raw_reviews = document.get("reviews")
    if isinstance(raw_reviews, list):
        for entry in raw_reviews:
            if not isinstance(entry, dict):
                continue
            run_identity = entry.get("run_id")
            feedback = entry.get("feedback")
            if isinstance(run_identity, str) and isinstance(feedback, str):
                reviews[run_identity] = feedback
    return {"reviews": reviews, "notes": _text(document.get("notes"))}


def _build_run(
    eval_dir: Path,
    arm: str,
    metadata: dict[str, Any],
    eval_id: object,
) -> dict[str, Any]:
    arm_dir = eval_dir / arm
    run_document = _load_json(arm_dir / "run.json") or {}
    error_document = _load_json(arm_dir / "error.json")
    metrics = _load_json(arm_dir / "outputs" / "metrics.json")
    if metrics is None:
        raw_metrics = run_document.get("metrics")
        metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
    return {
        "run_id": run_id(_eval_key(eval_id), arm),
        "eval_id": eval_id,
        "eval_name": _text(metadata.get("eval_name")) or f"eval-{eval_id}",
        "arm": arm,
        "prompt": _text(metadata.get("prompt")),
        "expected_output": _text(metadata.get("expected_output")),
        "status": _status(run_document, error_document),
        "error": _error_message(error_document),
        "assistant_text": _text(run_document.get("assistant_text")),
        "timing": _load_json(arm_dir / "timing.json") or {},
        "metrics": metrics,
        "outputs": _embed_outputs(arm_dir / "outputs"),
        "user_notes": _read_optional_text(arm_dir / "outputs" / "user_notes.md"),
        "grading": _load_json(arm_dir / "grading.json"),
    }


def _status(run_document: dict[str, Any], error_document: dict[str, Any] | None) -> str:
    if error_document is not None:
        return "error"
    if not run_document:
        return "unknown"
    if bool(run_document.get("timed_out")):
        return "timed_out"
    exit_code = run_document.get("exit_code")
    if (
        isinstance(exit_code, int)
        and not isinstance(exit_code, bool)
        and exit_code != 0
    ):
        return "failed"
    return "ok"


def _error_message(error_document: dict[str, Any] | None) -> str:
    if error_document is None:
        return ""
    detail = error_document.get("error")
    if isinstance(detail, dict):
        return _text(detail.get("message")) or _text(detail.get("type"))
    return _text(detail)


def _previous_document(previous_dir: Path) -> dict[str, Any]:
    runs = collect_runs(previous_dir)
    feedback = load_feedback(previous_dir)
    return {
        "iteration": previous_dir.name,
        "runs": {
            run["run_id"]: {
                "status": run["status"],
                "outputs": run["outputs"],
                "grading": run["grading"],
            }
            for run in runs
        },
        "feedback": feedback["reviews"],
        "notes": feedback["notes"],
    }


def _load_benchmark(
    iteration_dir: Path, benchmark_path: Path | None
) -> dict[str, Any] | None:
    path = (
        Path(benchmark_path)
        if benchmark_path is not None
        else Path(iteration_dir) / "benchmark.json"
    )
    if not path.is_file():
        if benchmark_path is not None:
            raise ValueError(f"benchmark file {str(path)!r} does not exist")
        return None
    return _load_json(path)


def _skill_name(iteration_dir: Path, benchmark: dict[str, Any] | None) -> str:
    if benchmark is not None:
        metadata = benchmark.get("metadata")
        if isinstance(metadata, dict):
            name = _text(metadata.get("skill_name"))
            if name:
                return name
    workspace_name = iteration_dir.parent.name
    suffix = "-workspace"
    if workspace_name.endswith(suffix) and len(workspace_name) > len(suffix):
        return workspace_name[: -len(suffix)]
    return workspace_name or "skill"


def _eval_directories(iteration_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in iteration_dir.iterdir()
            if path.is_dir() and path.name.startswith("eval-")
        ),
        key=_eval_directory_key,
    )


def _eval_directory_key(path: Path) -> tuple[int, int, str]:
    suffix = path.name.removeprefix("eval-")
    if suffix.isdigit():
        return (0, int(suffix), "")
    return (1, 0, suffix)


def _eval_id_from_directory(eval_dir: Path) -> str:
    suffix = eval_dir.name.removeprefix("eval-")
    return suffix or "unknown"


def _eval_key(eval_id: object) -> int | str:
    if isinstance(eval_id, (int, str)) and not isinstance(eval_id, bool):
        return eval_id
    return str(eval_id)


def _iteration_number(path: Path) -> int | None:
    match = _ITERATION.fullmatch(path.name)
    return int(match.group(1)) if match is not None else None


def _embed_outputs(outputs_dir: Path) -> list[dict[str, Any]]:
    if not outputs_dir.is_dir():
        return []
    files = sorted(
        (
            path
            for path in outputs_dir.rglob("*")
            if path.is_file()
            and path.name not in _EXCLUDED_OUTPUTS
            and not path.is_symlink()
        ),
        key=lambda path: path.relative_to(outputs_dir).as_posix(),
    )
    return [
        _embed_file(path, path.relative_to(outputs_dir).as_posix()) for path in files
    ]


def _embed_file(path: Path, name: str) -> dict[str, Any]:
    suffix = path.suffix.lower()
    mime = _mime_type(path)
    if suffix in _TEXT_EXTENSIONS:
        return {
            "name": name,
            "type": "text",
            "content": path.read_text(encoding="utf-8", errors="replace"),
        }
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    data_uri = f"data:{mime};base64,{encoded}"
    if suffix in _IMAGE_EXTENSIONS:
        return {
            "name": name,
            "type": "image",
            "mime": mime,
            "data_uri": data_uri,
        }
    if suffix == ".pdf":
        return {"name": name, "type": "pdf", "mime": mime, "data_uri": data_uri}
    return {"name": name, "type": "binary", "mime": mime, "data_uri": data_uri}


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[suffix]
    mime, _encoding = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _read_optional_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{str(path)!r} is not valid JSON: {error}") from error
    if not isinstance(document, dict):
        raise TypeError(f"{str(path)!r} must contain a JSON object")
    return document


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def main(argv: Sequence[str] | None = None) -> int:
    """Generate a review page from the command line."""
    parser = argparse.ArgumentParser(
        description="Write a standalone HTML review page for one eval iteration."
    )
    parser.add_argument("--iteration", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--no-previous", action="store_true")
    parser.add_argument("--skill-name")
    args = parser.parse_args(argv)

    try:
        path = write_review(
            args.iteration,
            output_path=args.output,
            previous_iteration=args.previous,
            benchmark_path=args.benchmark,
            include_previous=not args.no_previous,
            skill_name=args.skill_name,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"review: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
