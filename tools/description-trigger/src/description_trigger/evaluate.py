"""Run every case as an isolated probe and summarize the results."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from description_trigger.cases import Case, CaseSet
from description_trigger.probe import Probe, ProbeError, create_probe, run_probe
from description_trigger.transcript import TranscriptResult, interpret_transcript


class ResultState(StrEnum):
    """The user-visible outcome of one case."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CaseResult:
    """One case's expected outcome and the probe's interpretation."""

    case_id: str
    expected: bool
    state: ResultState
    duration: float
    probe: Probe | None
    outcome: TranscriptResult


@dataclass(frozen=True)
class EvaluationReport:
    """The complete outcome of one evaluation invocation."""

    skill_id: str
    case_path: Path
    model: str
    opencode_version: str
    results: tuple[CaseResult, ...]

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
    def total_duration(self) -> float:
        return sum(result.duration for result in self.results)

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
) -> EvaluationReport:
    """Run one isolated probe for every case and collect the results."""
    skill = skill_dir.expanduser().resolve()
    results = tuple(
        _evaluate_case(skill, case_set.skill_id, case, model) for case in case_set.cases
    )
    return EvaluationReport(
        skill_id=case_set.skill_id,
        case_path=case_set.path,
        model=model,
        opencode_version=opencode_version,
        results=results,
    )


def _evaluate_case(
    skill_dir: Path,
    skill_id: str,
    case: Case,
    model: str,
) -> CaseResult:
    started = time.monotonic()
    probe: Probe | None = None
    outcome = TranscriptResult(actual=None)

    try:
        probe = create_probe(skill_dir, case.identifier, skill_id)
        run = run_probe(probe, case.prompt, model)
        outcome = interpret_transcript(run.stdout, run.returncode, skill_id)
    except ProbeError as probe_error:
        probe = probe_error.probe or probe
        outcome = TranscriptResult(actual=None, error=str(probe_error))

    duration = time.monotonic() - started
    if outcome.actual is None:
        state = ResultState.ERROR
    elif outcome.actual == case.expected_trigger:
        state = ResultState.PASS
    else:
        state = ResultState.FAIL

    return CaseResult(
        case_id=case.identifier,
        expected=case.expected_trigger,
        state=state,
        duration=duration,
        probe=probe,
        outcome=outcome,
    )


def format_report(report: EvaluationReport) -> str:
    """Render the per-case results and run metadata."""
    lines: list[str] = []
    for result in report.results:
        lines.append(
            f"{result.state} {result.case_id} "
            f"expected={_format_trigger(result.expected)} "
            f"actual={_format_actual(result.outcome.actual)} "
            f"duration={result.duration:.2f}s"
        )
        if result.outcome.note:
            lines.append(f"  Note: {result.outcome.note}")
        if result.outcome.error:
            lines.append(f"  Error: {result.outcome.error}")
        for diagnostic in result.outcome.diagnostics:
            lines.append(f"  Diagnostic: {diagnostic}")
        if result.probe is not None:
            lines.append(f"  Probe directory: {result.probe.directory}")

    lines.extend(
        [
            "",
            "Summary:",
            f"  Passed: {report.passed}",
            f"  Failed: {report.failed}",
            f"  Error: {report.errored}",
            f"  Cases: {len(report.results)}",
            f"  Runs: {len(report.results)}",
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
