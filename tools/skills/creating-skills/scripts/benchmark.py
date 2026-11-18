"""Aggregate graded eval runs into benchmark JSON and Markdown."""

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.workspace import (
    ARMS,
    eval_directories,
    eval_id_from_directory,
    eval_id_sort_key,
    skill_name_from_workspace,
)

WITH_SKILL = "with_skill"
BASELINES = ("old_skill", "without_skill")


def build_benchmark(
    iteration_dir: Path,
    *,
    skill_name: str | None = None,
    skill_path: str | Path | None = None,
    executor_model: str | None = None,
    analyzer_model: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build the benchmark document for one eval iteration."""
    iteration = Path(iteration_dir).resolve()
    if not iteration.is_dir():
        raise ValueError(f"iteration directory {str(iteration)!r} does not exist")
    runs = _collect_runs(iteration)
    if not runs:
        raise ValueError(f"no graded runs found in {str(iteration)!r}")

    metadata: dict[str, Any] = {
        "skill_name": skill_name or skill_name_from_workspace(iteration.parent),
        "skill_path": str(skill_path) if skill_path is not None else "",
        "timestamp": timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evals_run": _eval_ids(runs),
        "runs_per_configuration": _runs_per_configuration(runs),
    }
    if executor_model is not None:
        metadata["executor_model"] = executor_model
    if analyzer_model is not None:
        metadata["analyzer_model"] = analyzer_model

    return {
        "metadata": metadata,
        "runs": runs,
        "run_summary": _summarize(runs),
        "notes": [],
    }


def _collect_runs(iteration_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    run_numbers: Counter[tuple[str, str]] = Counter()
    for eval_dir in eval_directories(iteration_dir):
        metadata = _load_json(eval_dir / "eval_metadata.json") or {}
        directory_eval_id = eval_id_from_directory(eval_dir)
        eval_id = metadata.get("eval_id", directory_eval_id)
        if isinstance(eval_id, bool) or not isinstance(eval_id, (int, str)):
            eval_id = directory_eval_id
        eval_name = _text(metadata.get("eval_name")) or f"eval-{eval_id}"

        for arm in ARMS:
            arm_dir = eval_dir / arm
            grading_path = arm_dir / "grading.json"
            if not grading_path.is_file():
                continue
            grading = _load_json(grading_path)
            if grading is None:
                continue
            run_key = (str(eval_id), arm)
            run_numbers[run_key] += 1
            runs.append(
                _build_run(
                    arm_dir,
                    grading,
                    eval_id=eval_id,
                    eval_name=eval_name,
                    arm=arm,
                    run_number=run_numbers[run_key],
                )
            )
    return runs


def _build_run(
    arm_dir: Path,
    grading: dict[str, Any],
    *,
    eval_id: int | str,
    eval_name: str,
    arm: str,
    run_number: int,
) -> dict[str, Any]:
    summary = _mapping(grading.get("summary"))
    expectations = _expectations(grading.get("expectations"))
    timing = _timing(arm_dir, grading)
    metrics = _mapping(grading.get("execution_metrics"))
    if not metrics:
        metrics = _load_json(arm_dir / "outputs" / "metrics.json") or {}

    passed = _integer(summary.get("passed"))
    failed = _integer(summary.get("failed"))
    total = _integer(summary.get("total"))
    if total == 0 and expectations:
        total = len(expectations)
        passed = sum(1 for item in expectations if item.get("passed") is True)
        failed = total - passed
    pass_rate = _number(summary.get("pass_rate"))
    if pass_rate is None:
        pass_rate = passed / total if total else 0.0

    return {
        "eval_id": eval_id,
        "eval_name": eval_name,
        "configuration": arm,
        "run_number": run_number,
        "result": {
            "pass_rate": pass_rate,
            "passed": passed,
            "failed": failed,
            "total": total,
            "time_seconds": _time_seconds(timing),
            "tokens": _integer(timing.get("total_tokens")),
            "tool_calls": _integer(metrics.get("total_tool_calls")),
            "errors": _integer(metrics.get("errors_encountered")),
        },
        "expectations": expectations,
        "notes": _notes(grading.get("user_notes_summary")),
    }


def _timing(arm_dir: Path, grading: dict[str, Any]) -> dict[str, Any]:
    timing = _load_json(arm_dir / "timing.json")
    if timing is not None:
        return timing
    return _mapping(grading.get("timing"))


def _time_seconds(timing: dict[str, Any]) -> float:
    seconds = _number(timing.get("total_duration_seconds"))
    if seconds is not None:
        return seconds
    milliseconds = _number(timing.get("duration_ms"))
    return milliseconds / 1000 if milliseconds is not None else 0.0


def _expectations(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _notes(value: object) -> list[str]:
    summary = _mapping(value)
    notes: list[str] = []
    for key in ("uncertainties", "needs_review", "workarounds"):
        items = summary.get(key)
        if isinstance(items, list):
            notes.extend(item for item in items if isinstance(item, str))
    return notes


def _eval_ids(runs: Sequence[dict[str, Any]]) -> list[int | str]:
    unique: dict[str, int | str] = {}
    for run in runs:
        eval_id = run["eval_id"]
        if isinstance(eval_id, (int, str)):
            unique.setdefault(str(eval_id), eval_id)
    return sorted(unique.values(), key=eval_id_sort_key)


def _runs_per_configuration(runs: Sequence[dict[str, Any]]) -> int:
    counts = Counter((str(run["eval_id"]), str(run["configuration"])) for run in runs)
    return max(counts.values(), default=0)


def _summarize(runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        configuration = str(run["configuration"])
        grouped.setdefault(configuration, []).append(run)

    summary: dict[str, Any] = {}
    for arm in ARMS:
        arm_runs = grouped.get(arm)
        if not arm_runs:
            continue
        summary[arm] = {
            "pass_rate": _stats(
                [float(run["result"]["pass_rate"]) for run in arm_runs]
            ),
            "time_seconds": _stats(
                [float(run["result"]["time_seconds"]) for run in arm_runs]
            ),
            "tokens": _stats([float(run["result"]["tokens"]) for run in arm_runs]),
        }

    primary = summary.get(WITH_SKILL)
    baseline_name = next((arm for arm in BASELINES if arm in summary), None)
    if primary is not None and baseline_name is not None:
        baseline = summary[baseline_name]
        summary["delta"] = {
            "pass_rate": f"{_mean(primary, 'pass_rate') - _mean(baseline, 'pass_rate'):+.2f}",
            "time_seconds": (
                f"{_mean(primary, 'time_seconds') - _mean(baseline, 'time_seconds'):+.1f}"
            ),
            "tokens": f"{_mean(primary, 'tokens') - _mean(baseline, 'tokens'):+.0f}",
        }
    return summary


def _mean(summary: dict[str, Any], metric: str) -> float:
    return float(summary[metric]["mean"])


def _stats(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    count = len(values)
    mean = sum(values) / count
    variance = (
        sum((value - mean) ** 2 for value in values) / (count - 1) if count > 1 else 0.0
    )
    return {
        "mean": round(mean, 4),
        "stddev": round(math.sqrt(variance), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


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


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _integer(value: object) -> int:
    number = _number(value)
    return int(number) if number is not None else 0


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def write_benchmark(
    iteration_dir: Path,
    *,
    skill_name: str | None = None,
    skill_path: str | Path | None = None,
    executor_model: str | None = None,
    analyzer_model: str | None = None,
    timestamp: str | None = None,
) -> Path:
    """Write ``benchmark.json`` and ``benchmark.md`` for one iteration."""
    iteration = Path(iteration_dir).resolve()
    benchmark = build_benchmark(
        iteration,
        skill_name=skill_name,
        skill_path=skill_path,
        executor_model=executor_model,
        analyzer_model=analyzer_model,
        timestamp=timestamp,
    )
    path = iteration / "benchmark.json"
    path.write_text(
        json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    path.with_suffix(".md").write_text(_markdown(benchmark), encoding="utf-8")
    return path


def _markdown(benchmark: dict[str, Any]) -> str:
    metadata = benchmark["metadata"]
    summary = benchmark["run_summary"]
    configs = [arm for arm in ARMS if arm in summary]
    delta = summary.get("delta")
    if not isinstance(delta, dict):
        delta = {}

    lines = [f"# Skill Benchmark: {metadata['skill_name']}", ""]
    if metadata.get("skill_path"):
        lines.append(f"**Skill**: {metadata['skill_path']}")
    if metadata.get("executor_model"):
        lines.append(f"**Executor model**: {metadata['executor_model']}")
    if metadata.get("analyzer_model"):
        lines.append(f"**Analyzer model**: {metadata['analyzer_model']}")
    lines.append(f"**Date**: {metadata['timestamp']}")
    runs_per_configuration = metadata["runs_per_configuration"]
    plural = "" if runs_per_configuration == 1 else "s"
    lines.append(
        f"**Evals**: {', '.join(str(eval_id) for eval_id in metadata['evals_run'])} "
        f"({runs_per_configuration} run{plural} per configuration)"
    )

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Metric | "
            + " | ".join(_arm_label(arm) for arm in configs)
            + " | Delta |",
            "| --- | " + " | ".join("---" for _ in configs) + " | --- |",
        ]
    )
    lines.append(
        "| Pass rate | "
        + " | ".join(
            _format_stat(summary[arm]["pass_rate"], percent=True, decimals=1)
            for arm in configs
        )
        + f" | {delta.get('pass_rate', '—')} |"
    )
    lines.append(
        "| Time (s) | "
        + " | ".join(
            _format_stat(summary[arm]["time_seconds"], percent=False, decimals=1)
            for arm in configs
        )
        + f" | {_delta_with_suffix(delta, 'time_seconds', 's')} |"
    )
    lines.append(
        "| Tokens | "
        + " | ".join(
            _format_stat(summary[arm]["tokens"], percent=False, decimals=0)
            for arm in configs
        )
        + f" | {delta.get('tokens', '—')} |"
    )

    notes = benchmark.get("notes")
    if isinstance(notes, list) and notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in notes if isinstance(note, str))
    return "\n".join(lines) + "\n"


def _arm_label(arm: str) -> str:
    return arm.replace("_", " ").title()


def _format_stat(stat: dict[str, Any], *, percent: bool, decimals: int) -> str:
    scale = 100 if percent else 1
    suffix = "%" if percent else ""
    mean = float(stat.get("mean", 0.0)) * scale
    stddev = float(stat.get("stddev", 0.0)) * scale
    return f"{mean:.{decimals}f}{suffix} ± {stddev:.{decimals}f}{suffix}"


def _delta_with_suffix(delta: dict[str, Any], key: str, suffix: str) -> str:
    value = delta.get(key)
    return f"{value}{suffix}" if isinstance(value, str) else "—"


def main(argv: Sequence[str] | None = None) -> int:
    """Write the benchmark from the command line."""
    parser = argparse.ArgumentParser(
        description="Aggregate graded eval runs into benchmark JSON and Markdown."
    )
    parser.add_argument("--iteration", required=True, type=Path)
    parser.add_argument("--skill-name")
    parser.add_argument("--skill-path")
    parser.add_argument("--executor-model")
    parser.add_argument("--analyzer-model")
    args = parser.parse_args(argv)

    try:
        path = write_benchmark(
            args.iteration,
            skill_name=args.skill_name,
            skill_path=args.skill_path,
            executor_model=args.executor_model,
            analyzer_model=args.analyzer_model,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"benchmark: {path}")
    print(f"markdown: {path.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
