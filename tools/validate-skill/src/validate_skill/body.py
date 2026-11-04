import math
from collections.abc import Callable

from validate_skill.model import Finding
from validate_skill.references import scan_references

ReferenceExists = Callable[[str], bool]

_MAX_BODY_LINES = 500
_MAX_BODY_TOKENS = 5_000
_CHARS_PER_TOKEN = 4


def check_body(body: str) -> list[Finding]:
    if not body.strip():
        return [Finding.error("body.empty", "SKILL.md body must not be empty", "body")]

    findings: list[Finding] = []
    line_count = len(body.splitlines())
    if line_count > _MAX_BODY_LINES:
        findings.append(
            Finding.warning(
                "body.lines",
                f"SKILL.md body has {line_count} lines; keep it to {_MAX_BODY_LINES} or fewer",
                "body",
            )
        )

    token_estimate = math.ceil(len(body) / _CHARS_PER_TOKEN)
    if token_estimate > _MAX_BODY_TOKENS:
        findings.append(
            Finding.warning(
                "body.tokens",
                f"SKILL.md body is estimated at {token_estimate} tokens "
                f"(characters / {_CHARS_PER_TOKEN}); keep it to {_MAX_BODY_TOKENS} or fewer",
                "body",
            )
        )
    return findings


def check_references(body: str, reference_exists: ReferenceExists) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()

    for reference in scan_references(body):
        if reference.path in seen:
            continue
        seen.add(reference.path)
        location = f"body:{reference.line}"
        if len(reference.path.split("/")) > 2:
            findings.append(
                Finding.warning(
                    "reference.too-deep",
                    f"reference '{reference.path}' is more than one level below the skill root",
                    location,
                )
            )
        if not reference_exists(reference.path):
            findings.append(
                Finding.warning(
                    "reference.missing",
                    f"referenced path '{reference.path}' does not exist",
                    location,
                )
            )

    return findings
