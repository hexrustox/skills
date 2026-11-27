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
) -> TranscriptResult:
    """Decide whether the target skill was loaded by a completed call."""
    completed_target = False
    target_error: str | None = None
    run_errors: list[str] = []
    other_skills: list[str] = []
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
        if event_type == "error":
            run_errors.append(_error_message(event))
            continue
        if event_type != "tool_use":
            continue

        part = event.get("part")
        if not isinstance(part, dict):
            malformed = True
            continue
        if part.get("type") != "tool" or part.get("tool") != "skill":
            continue

        state = part.get("state")
        if not isinstance(state, dict):
            malformed = True
            continue
        identifiers = _skill_identifiers(state.get("input"))
        if not identifiers:
            malformed = True
            continue
        if skill_id not in identifiers:
            other_skills.append(identifiers[0])
            continue
        if state.get("status") == "completed":
            completed_target = True
        else:
            target_error = _tool_error_message(state)

    diagnostics = tuple(
        [f"other skill loaded: {skill}" for skill in other_skills] + run_errors
    )

    if completed_target and not run_errors:
        notes: list[str] = []
        if returncode != 0:
            notes.append(
                f"OpenCode exited with {returncode} after the target skill call"
            )
        if target_error is not None:
            notes.append(f"target skill call also failed: {target_error}")
        return TranscriptResult(
            actual=True,
            note="; ".join(notes) if notes else None,
            diagnostics=diagnostics,
        )

    if run_errors:
        return TranscriptResult(
            actual=None,
            error="; ".join(run_errors),
            diagnostics=diagnostics,
        )
    if returncode != 0:
        return TranscriptResult(
            actual=None,
            error=f"OpenCode exited with {returncode} without loading {skill_id}",
            diagnostics=diagnostics,
        )
    if target_error is not None:
        return TranscriptResult(
            actual=None,
            error=f"target skill call failed: {target_error}",
            diagnostics=diagnostics,
        )
    if malformed:
        return TranscriptResult(
            actual=None,
            error="transcript contained malformed JSON",
            diagnostics=diagnostics,
        )
    return TranscriptResult(actual=False, diagnostics=diagnostics)


def _skill_identifiers(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ()
    return tuple(
        candidate
        for field in (CURRENT_SKILL_FIELD, LEGACY_SKILL_FIELD)
        if isinstance(candidate := value.get(field), str)
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
