"""Measure whether a skill description triggers for a set of queries."""

import argparse
import json
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.adapters import available_harnesses, get_harness
from scripts.frontmatter import parse_skill_md
from scripts.harness import Harness


@dataclass(frozen=True)
class TriggerQuery:
    """One query in a trigger eval set."""

    query: str
    should_trigger: bool


@dataclass(frozen=True)
class TriggerQueryResult:
    """The measured trigger rate for one query."""

    query: str
    should_trigger: bool
    triggers: int
    runs: int
    errors: int
    trigger_rate: float
    passed: bool


@dataclass(frozen=True)
class TriggerSummary:
    """Pass and fail counts across a trigger eval set."""

    total: int
    passed: int
    failed: int


@dataclass(frozen=True)
class TriggerEvaluation:
    """The measured trigger rates for one description."""

    skill_name: str
    description: str
    results: tuple[TriggerQueryResult, ...]
    summary: TriggerSummary

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON document for this evaluation."""
        return {
            "skill_name": self.skill_name,
            "description": self.description,
            "results": [
                {
                    "query": result.query,
                    "should_trigger": result.should_trigger,
                    "trigger_rate": result.trigger_rate,
                    "triggers": result.triggers,
                    "runs": result.runs,
                    "errors": result.errors,
                    "pass": result.passed,
                }
                for result in self.results
            ],
            "summary": {
                "total": self.summary.total,
                "passed": self.summary.passed,
                "failed": self.summary.failed,
            },
        }

    def restrict(self, queries: Sequence["TriggerQuery"]) -> "TriggerEvaluation":
        """Return this evaluation restricted to ``queries``, in their order."""
        by_query = {result.query: result for result in self.results}
        results = tuple(by_query[query.query] for query in queries)
        passed = sum(1 for result in results if result.passed)
        return TriggerEvaluation(
            skill_name=self.skill_name,
            description=self.description,
            results=results,
            summary=TriggerSummary(
                total=len(results),
                passed=passed,
                failed=len(results) - passed,
            ),
        )


def load_trigger_queries(path: Path) -> tuple[TriggerQuery, ...]:
    """Load and validate a trigger eval set.

    The file is a JSON array of ``{"query": str, "should_trigger": bool}``
    objects.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError("a trigger eval set must be a JSON array")

    queries: list[TriggerQuery] = []
    seen: set[str] = set()
    for index, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise TypeError(f"trigger query at index {index} must be a JSON object")

        query = raw.get("query")
        if query is None:
            raise ValueError(
                f"trigger query at index {index} is missing a non-empty 'query'"
            )
        if not isinstance(query, str):
            raise TypeError(f"trigger query at index {index} has a non-string 'query'")
        if not query.strip():
            raise ValueError(
                f"trigger query at index {index} is missing a non-empty 'query'"
            )
        if query in seen:
            raise ValueError(f"duplicate trigger query {query!r}")
        seen.add(query)

        should_trigger = raw.get("should_trigger")
        if not isinstance(should_trigger, bool):
            raise TypeError(
                f"trigger query {query!r} is missing a boolean 'should_trigger'"
            )

        queries.append(TriggerQuery(query=query, should_trigger=should_trigger))

    if not queries:
        raise ValueError("trigger eval set contains no queries")
    return tuple(queries)


def evaluate_trigger(
    harness: Harness,
    skill_name: str,
    description: str,
    queries: Sequence[TriggerQuery],
    *,
    runs_per_query: int = 3,
    trigger_threshold: float = 0.5,
    workers: int | None = None,
    model: str | None = None,
    timeout_seconds: float = 120.0,
) -> TriggerEvaluation:
    """Run every query several times in parallel and measure the trigger rate.

    A should-trigger query passes when its rate is at least
    ``trigger_threshold``. A should-not-trigger query passes when its rate is
    below the threshold. A failed probe counts as no trigger and fails its
    query.
    """
    queries = tuple(queries)
    if not queries:
        raise ValueError("trigger evaluation contains no queries")
    if runs_per_query < 1:
        raise ValueError("runs_per_query must be at least 1")
    if not 0 <= trigger_threshold <= 1:
        raise ValueError("trigger_threshold must be between 0 and 1")
    if workers is not None and workers < 1:
        raise ValueError("workers must be at least 1")

    total_runs = len(queries) * runs_per_query
    worker_count = workers if workers is not None else min(10, total_runs)
    triggered: dict[int, list[bool]] = {index: [] for index in range(len(queries))}
    errors: dict[int, int] = {index: 0 for index in range(len(queries))}

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(
                harness.probe_trigger,
                skill_name,
                description,
                query.query,
                model=model,
                timeout_seconds=timeout_seconds,
            ): index
            for index, query in enumerate(queries)
            for _run in range(runs_per_query)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                triggered[index].append(future.result().triggered)
            except Exception as error:  # noqa: BLE001 - one probe must not stop the set
                print(f"warning: {error}", file=sys.stderr)
                errors[index] += 1
                triggered[index].append(False)

    results: list[TriggerQueryResult] = []
    for index, query in enumerate(queries):
        outcomes = triggered[index]
        triggers = sum(outcomes)
        rate = triggers / len(outcomes)
        passed = errors[index] == 0 and (
            rate >= trigger_threshold
            if query.should_trigger
            else rate < trigger_threshold
        )
        results.append(
            TriggerQueryResult(
                query=query.query,
                should_trigger=query.should_trigger,
                triggers=triggers,
                runs=len(outcomes),
                errors=errors[index],
                trigger_rate=rate,
                passed=passed,
            )
        )

    passed_count = sum(1 for result in results if result.passed)
    return TriggerEvaluation(
        skill_name=skill_name,
        description=description,
        results=tuple(results),
        summary=TriggerSummary(
            total=len(results),
            passed=passed_count,
            failed=len(results) - passed_count,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the trigger evaluation command line interface."""
    parser = argparse.ArgumentParser(
        description="Measure whether a skill description triggers for a set of queries."
    )
    parser.add_argument("--skill", required=True, type=Path)
    parser.add_argument("--eval-set", required=True, type=Path)
    parser.add_argument("--description")
    parser.add_argument("--runs-per-query", type=int, default=3)
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--harness", default=available_harnesses()[0])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        document = parse_skill_md(Path(args.skill).resolve())
        queries = load_trigger_queries(args.eval_set)
        harness = get_harness(args.harness)
        evaluation = evaluate_trigger(
            harness,
            document.name,
            args.description or document.description,
            queries,
            runs_per_query=args.runs_per_query,
            trigger_threshold=args.trigger_threshold,
            workers=args.workers,
            model=args.model,
            timeout_seconds=args.timeout,
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    text = json.dumps(evaluation.as_dict(), indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")

    print(text, end="")
    for result in evaluation.results:
        status = "PASS" if result.passed else "FAIL"
        detail = f"{result.triggers}/{result.runs}"
        if result.errors:
            detail += f", {result.errors} errors"
        print(f"{status}\t{detail}\t{result.query}", file=sys.stderr)
    return 0 if evaluation.summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
