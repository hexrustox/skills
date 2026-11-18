"""Run the train/test description optimization loop."""

import argparse
import json
import random
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.adapters import available_harnesses, get_harness
from scripts.description_report import write_report
from scripts.frontmatter import parse_skill_md
from scripts.harness import Harness
from scripts.improve_description import MAX_DESCRIPTION_CHARS, propose_description
from scripts.trigger_eval import (
    TriggerEvaluation,
    TriggerQuery,
    evaluate_trigger,
    load_trigger_queries,
)
from scripts.workspace import default_workspace


@dataclass(frozen=True)
class TriggerSplit:
    """The train and held-out test portions of a trigger eval set."""

    train: tuple[TriggerQuery, ...]
    test: tuple[TriggerQuery, ...]


def split_trigger_queries(
    queries: Sequence[TriggerQuery],
    *,
    holdout: float = 0.4,
    seed: int = 42,
) -> TriggerSplit:
    """Split queries into train and test sets, stratified by polarity.

    Each polarity needs at least two queries so both sides of the split have
    something to measure. The shuffle is seeded so repeated runs compare the
    same train and test sets.
    """
    queries = tuple(queries)
    if not queries:
        raise ValueError("trigger eval set contains no queries")
    if not 0 < holdout < 1:
        raise ValueError("holdout must be greater than 0 and less than 1")

    should_trigger = [query for query in queries if query.should_trigger]
    should_not_trigger = [query for query in queries if not query.should_trigger]
    for label, group in (
        ("should-trigger", should_trigger),
        ("should-not-trigger", should_not_trigger),
    ):
        if len(group) < 2:
            raise ValueError(
                f"holdout splitting needs at least 2 {label} queries, "
                f"but the set has {len(group)}"
            )

    rng = random.Random(seed)
    rng.shuffle(should_trigger)
    rng.shuffle(should_not_trigger)

    def test_count(group: list[TriggerQuery]) -> int:
        return min(max(1, int(len(group) * holdout)), len(group) - 1)

    positive_test = test_count(should_trigger)
    negative_test = test_count(should_not_trigger)
    test = tuple(should_trigger[:positive_test] + should_not_trigger[:negative_test])
    train = tuple(should_trigger[positive_test:] + should_not_trigger[negative_test:])
    return TriggerSplit(train=train, test=test)


def run_description_loop(
    harness: Harness,
    *,
    skill_name: str,
    skill_content: str,
    description: str,
    queries: Sequence[TriggerQuery],
    model: str,
    max_iterations: int = 5,
    runs_per_query: int = 3,
    trigger_threshold: float = 0.5,
    holdout: float = 0.4,
    seed: int = 42,
    workers: int | None = None,
    timeout_seconds: float = 120.0,
    optimizer_timeout_seconds: float = 300.0,
    live_report_path: Path | None = None,
    report_path: Path | None = None,
    log_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Evaluate and improve a description until every train query passes.

    The optimizer receives train failures only. Test results are evaluated with
    the train set in one batch for parallelism, then partitioned and kept out of
    every improvement prompt. The returned best description is selected by test
    score.
    """
    if not model.strip():
        raise ValueError("a non-empty model is required for description optimization")
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    if not description.strip():
        raise ValueError("the starting description must not be empty")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise ValueError(
            f"the starting description is {len(description)} characters, over the "
            f"{MAX_DESCRIPTION_CHARS}-character limit"
        )

    split = split_trigger_queries(queries, holdout=holdout, seed=seed)
    original_description = description
    current_description = description
    history: list[dict[str, Any]] = []
    exit_reason = "unknown"
    _emit(
        log,
        f"Split: {len(split.train)} train, {len(split.test)} test (holdout={holdout})",
    )

    for iteration in range(1, max_iterations + 1):
        _emit(
            log,
            f"\nIteration {iteration}/{max_iterations}\n"
            f"Description: {current_description}",
        )
        evaluation = evaluate_trigger(
            harness,
            skill_name,
            current_description,
            split.train + split.test,
            runs_per_query=runs_per_query,
            trigger_threshold=trigger_threshold,
            workers=workers,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        train = evaluation.restrict(split.train)
        test = evaluation.restrict(split.test)
        entry = _history_entry(iteration, current_description, train, test)
        history.append(entry)
        _emit(log, _evaluation_line("Train", train))
        _emit(log, _evaluation_line("Test ", test))

        if live_report_path is not None:
            write_report(
                live_report_path,
                _result_document(
                    skill_name=skill_name,
                    original_description=original_description,
                    current_description=current_description,
                    best=_best_entry(history),
                    history=history,
                    split=split,
                    model=model,
                    holdout=holdout,
                    exit_reason="in progress",
                ),
                auto_refresh=True,
                skill_name=skill_name,
            )

        if train.summary.failed == 0:
            exit_reason = f"all_passed (iteration {iteration})"
            _emit(log, f"\nAll train queries passed on iteration {iteration}.")
            break
        if iteration == max_iterations:
            exit_reason = f"max_iterations ({max_iterations})"
            _emit(log, f"\nMax iterations reached ({max_iterations}).")
            break

        _emit(log, "\nImproving description from train failures...")
        try:
            proposal = propose_description(
                harness,
                skill_name=skill_name,
                skill_content=skill_content,
                current_description=current_description,
                train_results=train.as_dict(),
                history=_blinded_history(history),
                model=model,
                timeout_seconds=optimizer_timeout_seconds,
                log_dir=log_dir,
                iteration=iteration,
            )
        except (OSError, RuntimeError) as error:
            exit_reason = f"optimizer_error ({error})"
            _emit(log, f"\nOptimizer failed: {error}")
            break
        _emit(
            log,
            f"Proposed description ({len(proposal.description)} characters): "
            f"{proposal.description}",
        )
        current_description = proposal.description

    best = _best_entry(history)
    result = _result_document(
        skill_name=skill_name,
        original_description=original_description,
        current_description=current_description,
        best=best,
        history=history,
        split=split,
        model=model,
        holdout=holdout,
        exit_reason=exit_reason,
    )
    for path in (live_report_path, report_path):
        if path is not None:
            write_report(
                path,
                result,
                auto_refresh=False,
                skill_name=skill_name,
            )
    _emit(log, f"\nExit reason: {exit_reason}")
    _emit(log, f"Best score: {result['best_score']} (iteration {best['iteration']})")
    return result


def _history_entry(
    iteration: int,
    description: str,
    train: TriggerEvaluation,
    test: TriggerEvaluation,
) -> dict[str, Any]:
    return {
        "iteration": iteration,
        "description": description,
        "train_passed": train.summary.passed,
        "train_failed": train.summary.failed,
        "train_total": train.summary.total,
        "train_results": train.as_dict()["results"],
        "test_passed": test.summary.passed,
        "test_failed": test.summary.failed,
        "test_total": test.summary.total,
        "test_results": test.as_dict()["results"],
    }


def _blinded_history(
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only the train view of history for the improvement prompt."""
    return [
        {
            "iteration": entry.get("iteration"),
            "description": entry.get("description", ""),
            "train_passed": entry.get("train_passed", 0),
            "train_failed": entry.get("train_failed", 0),
            "train_total": entry.get("train_total", 0),
            "train_results": entry.get("train_results", []),
        }
        for entry in history
    ]


def _result_document(
    *,
    skill_name: str,
    original_description: str,
    current_description: str,
    best: Mapping[str, Any],
    history: list[dict[str, Any]],
    split: TriggerSplit,
    model: str,
    holdout: float,
    exit_reason: str,
) -> dict[str, Any]:
    return {
        "skill_name": skill_name,
        "original_description": original_description,
        "best_description": best["description"],
        "best_score": f"{best['test_passed']}/{best['test_total']}",
        "best_train_score": f"{best['train_passed']}/{best['train_total']}",
        "best_test_score": f"{best['test_passed']}/{best['test_total']}",
        "best_iteration": best["iteration"],
        "final_description": current_description,
        "exit_reason": exit_reason,
        "iterations_run": len(history),
        "holdout": holdout,
        "train_size": len(split.train),
        "test_size": len(split.test),
        "model": model,
        "history": history,
    }


def _best_entry(history: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(history, key=lambda entry: _as_int(entry.get("test_passed")))


def _evaluation_line(label: str, evaluation: TriggerEvaluation) -> str:
    return (
        f"{label}: {evaluation.summary.passed}/{evaluation.summary.total} "
        f"queries passed"
    )


def _emit(log: Callable[[str], None] | None, message: str) -> None:
    if log is not None:
        log(message)


def _as_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _results_directory(base: Path) -> Path:
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H%M%S")
    for suffix in range(1, 1000):
        name = timestamp if suffix == 1 else f"{timestamp}-{suffix}"
        candidate = base / name
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(
        f"could not create a unique results directory under {str(base)!r}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the description optimization loop from the command line."""
    parser = argparse.ArgumentParser(
        description="Optimize a skill description with a train/test trigger split."
    )
    parser.add_argument("--skill-path", required=True, type=Path)
    parser.add_argument("--eval-set", required=True, type=Path)
    parser.add_argument("--description")
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--runs-per-query", type=int, default=3)
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    parser.add_argument("--holdout", type=float, default=0.4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--optimizer-timeout", type=float, default=300.0)
    parser.add_argument("--harness", default=available_harnesses()[0])
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        skill = parse_skill_md(Path(args.skill_path).resolve())
        queries = load_trigger_queries(args.eval_set)
        harness = get_harness(args.harness)
        base = (
            args.results_dir
            if args.results_dir is not None
            else default_workspace(Path(args.skill_path).resolve())
            / "description-optimization"
        )
        run_dir = _results_directory(base)
        log_dir = run_dir / "logs"
        log_dir.mkdir()
        log_path = log_dir / "loop.log"
        log_stream = log_path.open("w", encoding="utf-8")

        def log(message: str) -> None:
            log_stream.write(message + "\n")
            log_stream.flush()
            if args.verbose:
                print(message, file=sys.stderr)

        try:
            output = run_description_loop(
                harness,
                skill_name=skill.name,
                skill_content=skill.content,
                description=args.description or skill.description,
                queries=queries,
                model=args.model,
                max_iterations=args.max_iterations,
                runs_per_query=args.runs_per_query,
                trigger_threshold=args.trigger_threshold,
                holdout=args.holdout,
                seed=args.seed,
                workers=args.workers,
                timeout_seconds=args.timeout,
                optimizer_timeout_seconds=args.optimizer_timeout,
                live_report_path=run_dir / "live.html",
                report_path=run_dir / "report.html",
                log_dir=log_dir,
                log=log,
            )
        finally:
            log_stream.close()
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    text = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    (run_dir / "results.json").write_text(text, encoding="utf-8")
    print(text, end="")
    print(f"results: {run_dir / 'results.json'}", file=sys.stderr)
    print(f"report: {run_dir / 'report.html'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
