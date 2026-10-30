import json
from collections.abc import Sequence

from validate_skill.model import Finding, Run, SkillResult, TargetFailure


def _finding_text(finding: Finding) -> str:
    return (
        f"  {finding.severity.value} {finding.rule}: {finding.message} "
        f"[{finding.location}]"
    )


def _finding_dict(finding: Finding) -> dict[str, str]:
    return {
        "severity": finding.severity.value,
        "rule": finding.rule,
        "message": finding.message,
        "location": finding.location,
    }


def _failure_dict(failure: TargetFailure) -> dict[str, str]:
    return {
        "path": str(failure.path),
        "message": failure.message,
    }


def _summary_counts(results: Sequence[SkillResult]) -> dict[str, int]:
    return {
        "skills": len(results),
        "errors": sum(result.error_count for result in results),
        "warnings": sum(result.warning_count for result in results),
    }


def _summary_text(results: Sequence[SkillResult]) -> str:
    counts = _summary_counts(results)
    skills = counts["skills"]
    errors = counts["errors"]
    warnings = counts["warnings"]
    return (
        f"{skills} skill{'s' if skills != 1 else ''} checked, "
        f"{errors} error{'s' if errors != 1 else ''}, "
        f"{warnings} warning{'s' if warnings != 1 else ''}"
    )


def render_text(run: Run, *, verbose: bool = False) -> str:
    lines: list[str] = []
    for result in run.results:
        if not verbose and not result.findings:
            continue
        lines.append(f"skill: {result.path}")
        lines.extend(_finding_text(finding) for finding in result.findings)

    if verbose or any(result.findings for result in run.results):
        lines.append(_summary_text(run.results))
    return "\n".join(lines)


def render_json(run: Run) -> str:
    payload = {
        "skills": [
            {
                "path": str(result.path),
                "findings": [_finding_dict(finding) for finding in result.findings],
            }
            for result in run.results
        ],
        "failures": [_failure_dict(failure) for failure in run.failures],
        "summary": _summary_counts(run.results),
    }
    return json.dumps(payload, indent=2)
