"""Run every case as an isolated probe and summarize the results."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import partial
from pathlib import Path

from description_trigger.cases import Case, CaseSet
from description_trigger.probe import (
    Probe,
    ProbeError,
    create_probe,
    remove_probe,
    run_probe,
)
from description_trigger.transcript import TranscriptResult, interpret_transcript


class ResultState(StrEnum):
    """The user-visible outcome of one case."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class RunResult:
    """One probe run and the transcript interpretation it produced."""

    duration: float
    probe: Probe | None
    outcome: TranscriptResult


@dataclass(frozen=True)
class CaseResult:
    """One case's expected outcome and all of its repeat runs."""

    case_id: str
    expected: bool
    state: ResultState
    duration: float
    runs: tuple[RunResult, ...]

    @property
    def actuals(self) -> tuple[bool | None, ...]:
        """The actual trigger of every repeat, in run order."""
        return _actuals(self.runs)

    @property
    def matched(self) -> int:
        """The number of repeats that matched the expectation."""
        return sum(actual == self.expected for actual in self.actuals)


def _actuals(runs: tuple[RunResult, ...]) -> tuple[bool | None, ...]:
    return tuple(run.outcome.actual for run in runs)


@dataclass(frozen=True)
class EvaluationReport:
    """The complete outcome of one evaluation invocation."""

    skill_id: str
    case_path: Path
    model: str
    opencode_version: str
    results: tuple[CaseResult, ...]
    total_duration: float

    @property
    def passed(self) -> int:
        return sum(result.state == ResultState.PASS for result in self.results)

    @property
    def failed(self) -> int:
        return sum(result.state == ResultState.FAIL for result in self.results)

    @property
    def errored(self) -> int:
        return sum(result.state == ResultState.ERROR for result in self.results)

    @property
    def total_runs(self) -> int:
        return sum(len(result.runs) for result in self.results)

    @property
    def exit_code(self) -> int:
        if self.errored:
            return 2
        if self.failed:
            return 1
        return 0


def evaluate_cases(
    skill_dir: Path,
    case_set: CaseSet,
    model: str,
    opencode_version: str,
    timeout: float,
    repeats: int = 1,
    jobs: int = 1,
    keep: bool = False,
    standalone: bool = False,
) -> EvaluationReport:
    """Run every case and repeat as an isolated probe and collect the results."""
    skill = skill_dir.expanduser().resolve()
    started = time.monotonic()
    cases = [case for case in case_set.cases for _ in range(repeats)]
    evaluate_run = partial(
        _evaluate_run, skill, case_set.skill_id, model, timeout, standalone
    )
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(evaluate_run, case) for case in cases]
        runs = [future.result() for future in futures]
    total_duration = time.monotonic() - started

    runs_by_case: dict[str, list[RunResult]] = {
        case.identifier: [] for case in case_set.cases
    }
    for case, run in zip(cases, runs):
        runs_by_case[case.identifier].append(run)

    results = tuple(
        _aggregate_case(case, tuple(runs_by_case[case.identifier]))
        for case in case_set.cases
    )
    if not keep:
        results = tuple(_discard_passing_probes(result) for result in results)
    return EvaluationReport(
        skill_id=case_set.skill_id,
        case_path=case_set.path,
        model=model,
        opencode_version=opencode_version,
        results=results,
        total_duration=total_duration,
    )


def _evaluate_run(
    skill_dir: Path,
    skill_id: str,
    model: str,
    timeout: float,
    standalone: bool,
    case: Case,
) -> RunResult:
    started = time.monotonic()
    probe: Probe | None = None
    outcome = TranscriptResult(actual=None)

    try:
        probe = create_probe(skill_dir, case.identifier, skill_id)
        run = run_probe(probe, case.prompt, model, timeout, standalone=standalone)
        outcome = interpret_transcript(
            run.stdout,
            run.returncode,
            skill_id,
            timed_out=run.timed_out,
        )
        if run.timed_out:
            outcome = replace(
                outcome,
                diagnostics=outcome.diagnostics + (run.timeout_diagnostic(timeout),),
            )
    except ProbeError as probe_error:
        probe = probe_error.probe or probe
        outcome = TranscriptResult(actual=None, error=str(probe_error))

    return RunResult(
        duration=time.monotonic() - started,
        probe=probe,
        outcome=outcome,
    )


def _aggregate_case(case: Case, runs: tuple[RunResult, ...]) -> CaseResult:
    actuals = _actuals(runs)
    if any(actual is None for actual in actuals):
        state = ResultState.ERROR
    elif all(actual == case.expected_trigger for actual in actuals):
        state = ResultState.PASS
    else:
        state = ResultState.FAIL

    return CaseResult(
        case_id=case.identifier,
        expected=case.expected_trigger,
        state=state,
        duration=sum(run.duration for run in runs),
        runs=runs,
    )


def _discard_passing_probes(result: CaseResult) -> CaseResult:
    if result.state is not ResultState.PASS:
        return result
    runs = tuple(_discard_probe(run) for run in result.runs)
    return replace(result, runs=runs)


def _discard_probe(run: RunResult) -> RunResult:
    if run.probe is None or not remove_probe(run.probe):
        return run
    return replace(run, probe=None)


def format_report(report: EvaluationReport) -> str:
    """Render the per-case results and run metadata."""
    lines: list[str] = []
    for result in report.results:
        actuals = ",".join(_format_actual(actual) for actual in result.actuals)
        matched = (
            f" matched={result.matched}/{len(result.runs)}"
            if len(result.runs) > 1
            else ""
        )
        lines.append(
            f"{result.state} {result.case_id} "
            f"expected={_format_trigger(result.expected)} "
            f"actual={actuals}{matched} "
            f"duration={result.duration:.2f}s"
        )
        for index, run in enumerate(result.runs, start=1):
            prefix = f"Run {index}: " if len(result.runs) > 1 else ""
            if run.outcome.note:
                lines.append(f"  {prefix}Note: {run.outcome.note}")
            if run.outcome.error:
                lines.append(f"  {prefix}Error: {run.outcome.error}")
            for diagnostic in run.outcome.diagnostics:
                lines.append(f"  {prefix}Diagnostic: {diagnostic}")
            if run.probe is not None:
                lines.append(f"  {prefix}Probe directory: {run.probe.directory}")
                lines.append(f"  {prefix}Transcript: {run.probe.transcript_path}")
                lines.append(f"  {prefix}Stderr: {run.probe.stderr_path}")

    lines.extend(
        [
            "",
            "Summary:",
            f"  Passed: {report.passed}",
            f"  Failed: {report.failed}",
            f"  Error: {report.errored}",
            f"  Cases: {len(report.results)}",
            f"  Runs: {report.total_runs}",
            f"  Total duration: {report.total_duration:.2f}s",
            f"  Skill: {report.skill_id}",
            f"  Case file: {report.case_path}",
            f"  Model: {report.model}",
            f"  OpenCode version: {report.opencode_version}",
        ]
    )
    return "\n".join(lines)


def _format_trigger(value: bool) -> str:
    return "true" if value else "false"


def _format_actual(value: bool | None) -> str:
    if value is None:
        return ResultState.ERROR.value
    return _format_trigger(value)
