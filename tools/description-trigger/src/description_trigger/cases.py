"""Load and validate description-trigger case files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CASE_FILE_NAME = "description-trigger.json"
CASE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CASE_FIELDS = frozenset({"prompt", "expect"})
MIN_POSITIVE = 3
MIN_NEGATIVE = 3


class CaseFileError(Exception):
    """Raised when a case file is missing or invalid."""


class _DuplicateKeyError(Exception):
    def __init__(self, key: str) -> None:
        self.key = key


@dataclass(frozen=True)
class Case:
    """One prompt and the trigger outcome it expects."""

    identifier: str
    prompt: str
    expected_trigger: bool


@dataclass(frozen=True)
class CaseSet:
    """The validated cases for one skill."""

    skill_id: str
    path: Path
    cases: tuple[Case, ...]

    @property
    def positive_count(self) -> int:
        return _counts(self.cases)[0]

    @property
    def negative_count(self) -> int:
        return _counts(self.cases)[1]


def resolve_case_path(skill_dir: Path, cases_path: Path | None) -> Path:
    """Return the explicit case path or derive the repository default."""
    if cases_path is not None:
        return cases_path.expanduser().resolve()
    skill = skill_dir.expanduser().resolve()
    return skill.parent.parent / "tests" / skill.name / CASE_FILE_NAME


def load_case_set(skill_dir: Path, cases_path: Path | None) -> CaseSet:
    """Read and validate one skill's case file."""
    skill = skill_dir.expanduser().resolve()
    path = resolve_case_path(skill, cases_path)
    if not path.is_file():
        message = f"case file not found: {path}"
        if cases_path is None:
            message += " (pass --cases PATH to use a different location)"
        raise CaseFileError(message)

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise CaseFileError(f"case file is not valid UTF-8: {path}") from error
    except OSError as error:
        raise CaseFileError(f"could not read case file {path}: {error}") from error

    try:
        document = json.loads(text, object_pairs_hook=_object_without_duplicates)
    except _DuplicateKeyError as error:
        raise CaseFileError(f"duplicate key {error.key!r} in {path}") from error
    except json.JSONDecodeError as error:
        raise CaseFileError(f"invalid JSON in {path}: {error}") from error

    return CaseSet(
        skill_id=skill.name,
        path=path,
        cases=_validate_document(document),
    )


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _validate_document(document: Any) -> tuple[Case, ...]:
    if not isinstance(document, dict):
        raise CaseFileError("case file must contain a JSON object keyed by case ID")

    cases: list[Case] = []
    for identifier, raw_case in document.items():
        if not CASE_ID_PATTERN.fullmatch(identifier):
            raise CaseFileError(f"case ID {identifier!r} is not lowercase kebab-case")
        if not isinstance(raw_case, dict):
            raise CaseFileError(f"case {identifier!r} must be an object")

        missing = CASE_FIELDS - raw_case.keys()
        unknown = raw_case.keys() - CASE_FIELDS
        if missing:
            fields = ", ".join(sorted(missing))
            raise CaseFileError(f"case {identifier!r} is missing field(s): {fields}")
        if unknown:
            fields = ", ".join(sorted(unknown))
            raise CaseFileError(f"case {identifier!r} has unknown field(s): {fields}")

        prompt = raw_case["prompt"]
        if not isinstance(prompt, str):
            raise CaseFileError(f"case {identifier!r} prompt must be a string")
        if not prompt.strip():
            raise CaseFileError(f"case {identifier!r} prompt must not be empty")

        expected_trigger = raw_case["expect"]
        if not isinstance(expected_trigger, bool):
            raise CaseFileError(f"case {identifier!r} expect must be a JSON boolean")

        cases.append(
            Case(
                identifier=identifier,
                prompt=prompt,
                expected_trigger=expected_trigger,
            )
        )

    positive, negative = _counts(tuple(cases))
    _require_minimum(MIN_POSITIVE, positive, "expect: true")
    _require_minimum(MIN_NEGATIVE, negative, "expect: false")
    return tuple(cases)


def _counts(cases: tuple[Case, ...]) -> tuple[int, int]:
    positive = sum(case.expected_trigger for case in cases)
    return positive, len(cases) - positive


def _require_minimum(minimum: int, found: int, expected_trigger: str) -> None:
    if found < minimum:
        raise CaseFileError(
            f"need at least {minimum} cases with {expected_trigger}; found {found}"
        )
