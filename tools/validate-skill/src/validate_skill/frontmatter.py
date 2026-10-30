import re
from collections.abc import Callable

import yaml

from validate_skill.model import Finding

_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

Frontmatter = dict[str, object]


def _required_string(
    frontmatter: Frontmatter, field: str
) -> tuple[str | None, list[Finding]]:
    if field not in frontmatter:
        return None, [Finding.error(f"{field}.missing", f"{field} is required", field)]
    value = frontmatter[field]
    if not isinstance(value, str):
        return None, [Finding.error(f"{field}.type", f"{field} must be a string", field)]
    if not value.strip():
        return None, [Finding.error(f"{field}.empty", f"{field} must not be empty", field)]
    return value, []


def _check_name(frontmatter: Frontmatter, directory_name: str) -> list[Finding]:
    value, findings = _required_string(frontmatter, "name")
    if value is None:
        return findings
    if not 1 <= len(value) <= 64:
        findings.append(Finding.error("name.length", "name must be 1-64 characters", "name"))
    if _NAME_PATTERN.fullmatch(value) is None:
        findings.append(
            Finding.error(
                "name.grammar",
                "name must use lowercase letters, digits, and single hyphens, "
                "with no leading or trailing hyphen",
                "name",
            )
        )
    if value != directory_name:
        findings.append(
            Finding.error(
                "name.directory",
                f"name must match the skill directory name '{directory_name}'",
                "name",
            )
        )
    return findings


def _check_description(frontmatter: Frontmatter) -> list[Finding]:
    value, findings = _required_string(frontmatter, "description")
    if value is None:
        return findings
    if len(value) > 1024:
        findings.append(
            Finding.error(
                "description.length", "description must be 1-1024 characters", "description"
            )
        )
    return findings


def _check_string(
    frontmatter: Frontmatter,
    field: str,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
) -> list[Finding]:
    value = frontmatter[field]
    if not isinstance(value, str):
        return [Finding.error(f"frontmatter.{field}.type", f"{field} must be a string", field)]
    if (min_length is not None and len(value) < min_length) or (
        max_length is not None and len(value) > max_length
    ):
        return [
            Finding.error(
                f"frontmatter.{field}.length",
                f"{field} must be {min_length}-{max_length} characters",
                field,
            )
        ]
    return []


def _check_disable_model_invocation(frontmatter: Frontmatter) -> list[Finding]:
    if isinstance(frontmatter["disable-model-invocation"], bool):
        return []
    return [
        Finding.error(
            "frontmatter.disable-model-invocation.type",
            "disable-model-invocation must be a boolean",
            "disable-model-invocation",
        )
    ]


def _check_license(frontmatter: Frontmatter) -> list[Finding]:
    return _check_string(frontmatter, "license")


def _check_compatibility(frontmatter: Frontmatter) -> list[Finding]:
    return _check_string(frontmatter, "compatibility", min_length=1, max_length=500)


def _warn_allowed_tools(_frontmatter: Frontmatter) -> list[Finding]:
    return [
        Finding.warning(
            "frontmatter.allowed-tools.experimental",
            "allowed-tools is experimental and implementation-dependent; "
            "its value is not validated",
            "allowed-tools",
        )
    ]


FieldCheck = Callable[[Frontmatter], list[Finding]]

_OPTIONAL_FIELDS: tuple[tuple[str, FieldCheck], ...] = (
    ("disable-model-invocation", _check_disable_model_invocation),
    ("license", _check_license),
    ("compatibility", _check_compatibility),
    ("allowed-tools", _warn_allowed_tools),
)

_KNOWN_FIELDS = frozenset(
    {"name", "description", "metadata"} | {name for name, _ in _OPTIONAL_FIELDS}
)


def parse_frontmatter(text: str) -> tuple[Frontmatter | None, str, list[Finding]]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return (
            None,
            "",
            [
                Finding.error(
                    "frontmatter.missing", "SKILL.md has no frontmatter block", "frontmatter"
                )
            ],
        )

    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        return (
            None,
            "",
            [
                Finding.error(
                    "frontmatter.malformed",
                    "frontmatter block is not closed with ---",
                    "frontmatter",
                )
            ],
        )

    raw = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        return (
            None,
            body,
            [
                Finding.error(
                    "frontmatter.malformed",
                    f"frontmatter is not valid YAML: {error}",
                    "frontmatter",
                )
            ],
        )

    if not isinstance(data, dict):
        return (
            None,
            body,
            [
                Finding.error(
                    "frontmatter.not-mapping",
                    "frontmatter must be a YAML mapping",
                    "frontmatter",
                )
            ],
        )

    return data, body, []


def check_frontmatter_fields(
    frontmatter: Frontmatter, directory_name: str
) -> list[Finding]:
    findings = _check_name(frontmatter, directory_name)
    findings.extend(_check_description(frontmatter))
    for name, check in _OPTIONAL_FIELDS:
        if name in frontmatter:
            findings.extend(check(frontmatter))
    return findings


def check_unknown_keys(frontmatter: Frontmatter) -> list[Finding]:
    return [
        Finding.warning(
            "frontmatter.unknown-key",
            f"unknown frontmatter key '{key}'",
            str(key),
        )
        for key in frontmatter
        if key not in _KNOWN_FIELDS
    ]
