"""Interpret OpenCode JSON transcripts for target-skill trigger detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

CURRENT_SKILL_FIELD = "id"
LEGACY_SKILL_FIELD = "name"


@dataclass(frozen=True)
class TranscriptResult:
    """The decided trigger outcome, or None when the run is undecidable."""

    actual: bool | None
    note: str | None = None
    error: str | None = None
    diagnostics: tuple[str, ...] = ()


def interpret_transcript(
    text: str,
    returncode: int,
    skill_id: str,
    *,
    timed_out: bool = False,
) -> TranscriptResult:
    """Decide whether the target skill was loaded by a completed call.

    Errors are decisive: a run-level error or a target-call error is ERROR even
    when another target call completed. Pending and running updates only count
    when no target call reaches a terminal status. A timeout after a completed
    target call still triggers; a timeout before one is an error.
    """
    completed_target = False
    target_error: str | None = None
    incomplete_target = False
    run_errors: list[str] = []
    other_skills: dict[str, str] = {}
    malformed = False

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed = True
            continue
        if not isinstance(event, dict):
            malformed = True
            continue

        event_type = event.get("type")
        if not isinstance(event_type, str) or not event_type:
            malformed = True
            continue
        if event_type == "error":
            run_errors.append(_error_message(event))
            continue
        if event_type != "tool_use":
            continue

        part = event.get("part")
        if not isinstance(part, dict):
            malformed = True
            continue
        part_type = part.get("type")
        if not isinstance(part_type, str) or part_type != "tool":
            malformed = True
            continue
        tool = part.get("tool")
        if not isinstance(tool, str) or not tool:
            malformed = True
            continue
        if tool != "skill":
            continue

        state = part.get("state")
        if not isinstance(state, dict):
            malformed = True
            continue
        identifiers = _skill_identifiers(state.get("input"))
        if not identifiers:
            malformed = True
            continue
        status = state.get("status")
        status_text = status if isinstance(status, str) else "unknown"
        if skill_id not in identifiers:
            other_skills[identifiers[0]] = status_text
            continue
        if status == "completed":
            completed_target = True
        elif status == "error":
            target_error = _tool_error_message(state)
        else:
            incomplete_target = True

    other_diagnostics = [
        _other_skill_diagnostic(skill, status) for skill, status in other_skills.items()
    ]
    diagnostics = tuple(other_diagnostics + run_errors)

    if run_errors:
        return TranscriptResult(
            actual=None,
            error="; ".join(run_errors),
            diagnostics=diagnostics,
        )
    if target_error is not None:
        return TranscriptResult(
            actual=None,
            error=f"target skill call failed: {target_error}",
            diagnostics=diagnostics,
        )
    if completed_target:
        if timed_out:
            note = "OpenCode timed out after the target skill call"
        elif returncode != 0:
            note = f"OpenCode exited with {returncode} after the target skill call"
        else:
            note = None
        return TranscriptResult(
            actual=True,
            note=note,
            diagnostics=diagnostics,
        )

    if incomplete_target:
        error = (
            "OpenCode timed out before the target skill call completed"
            if timed_out
            else "target skill call did not reach a terminal status"
        )
        return TranscriptResult(
            actual=None,
            error=error,
            diagnostics=diagnostics,
        )
    if timed_out:
        return TranscriptResult(
            actual=None,
            error=f"OpenCode timed out before loading {skill_id}",
            diagnostics=diagnostics,
        )
    if returncode != 0:
        return TranscriptResult(
            actual=None,
            error=f"OpenCode exited with {returncode} without loading {skill_id}",
            diagnostics=diagnostics,
        )
    if malformed:
        return TranscriptResult(
            actual=None,
            error="transcript contained a malformed line",
            diagnostics=diagnostics,
        )
    return TranscriptResult(actual=False, diagnostics=diagnostics)


def _other_skill_diagnostic(skill: str, status: str) -> str:
    if status == "completed":
        return f"other skill loaded: {skill}"
    if status == "error":
        return f"other skill call failed: {skill}"
    return f"other skill call: {skill} ({status})"


def _skill_identifiers(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ()
    return tuple(
        candidate
        for field in (CURRENT_SKILL_FIELD, LEGACY_SKILL_FIELD)
        if isinstance(candidate := value.get(field), str) and candidate
    )


def _message(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str) and message:
            return message
    return fallback


def _error_message(event: dict[str, Any]) -> str:
    return _message(event.get("error"), "OpenCode reported an error")


def _tool_error_message(state: dict[str, Any]) -> str:
    return _message(state.get("error"), "skill call did not complete")
