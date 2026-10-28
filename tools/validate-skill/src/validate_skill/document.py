import math
import posixpath
import re
from collections.abc import Callable, Mapping

import yaml

from validate_skill.model import Finding, Severity

ReferenceExists = Callable[[str], bool]

_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(((?:[^()\n]|\([^()\n]*\))*)\)")
_MARKDOWN_REFERENCE_PATTERN = re.compile(
    r"^[ \t]{0,3}\[[^\]]+\]:[ \t]*(<[^>]*>|\S+)", re.MULTILINE
)
_INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
_REFERENCE_DIRECTORIES = frozenset({"scripts", "references", "assets"})
_URL_SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_MAX_BODY_LINES = 500
_MAX_BODY_TOKENS = 5_000
_CHARS_PER_TOKEN = 4
_KNOWN_FIELDS = frozenset(
    {
        "name",
        "description",
        "disable-model-invocation",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
)


def _error(rule: str, message: str, location: str) -> Finding:
    return Finding(rule=rule, severity=Severity.ERROR, message=message, location=location)


def _warning(rule: str, message: str, location: str) -> Finding:
    return Finding(rule=rule, severity=Severity.WARNING, message=message, location=location)


def _missing_version() -> Finding:
    return _error(
        "metadata.version.missing",
        "metadata.version is required",
        "metadata.version",
    )


def _parse_frontmatter(
    text: str,
) -> tuple[dict[str, object] | None, str, list[Finding]]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return (
            None,
            "",
            [_error("frontmatter.missing", "SKILL.md has no frontmatter block", "frontmatter")],
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
                _error(
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
            [_error("frontmatter.malformed", f"frontmatter is not valid YAML: {error}", "frontmatter")],
        )

    if not isinstance(data, dict):
        return (
            None,
            body,
            [
                _error(
                    "frontmatter.not-mapping",
                    "frontmatter must be a YAML mapping",
                    "frontmatter",
                )
            ],
        )

    return data, body, []


def _required_string(
    frontmatter: dict[str, object], field: str
) -> tuple[str | None, list[Finding]]:
    if field not in frontmatter:
        return None, [_error(f"{field}.missing", f"{field} is required", field)]
    value = frontmatter[field]
    if not isinstance(value, str):
        return None, [_error(f"{field}.type", f"{field} must be a string", field)]
    if not value.strip():
        return None, [_error(f"{field}.empty", f"{field} must not be empty", field)]
    return value, []


def _check_name(frontmatter: dict[str, object], directory_name: str) -> list[Finding]:
    value, findings = _required_string(frontmatter, "name")
    if value is None:
        return findings
    if not 1 <= len(value) <= 64:
        findings.append(_error("name.length", "name must be 1-64 characters", "name"))
    if _NAME_PATTERN.fullmatch(value) is None:
        findings.append(
            _error(
                "name.grammar",
                "name must use lowercase letters, digits, and single hyphens, "
                "with no leading or trailing hyphen",
                "name",
            )
        )
    if value != directory_name:
        findings.append(
            _error(
                "name.directory",
                f"name must match the skill directory name '{directory_name}'",
                "name",
            )
        )
    return findings


def _check_description(frontmatter: dict[str, object]) -> list[Finding]:
    value, findings = _required_string(frontmatter, "description")
    if value is None:
        return findings
    if len(value) > 1024:
        findings.append(
            _error("description.length", "description must be 1-1024 characters", "description")
        )
    return findings


def _check_string_field(
    frontmatter: dict[str, object],
    field: str,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
) -> list[Finding]:
    if field not in frontmatter:
        return []
    value = frontmatter[field]
    if not isinstance(value, str):
        return [_error(f"frontmatter.{field}.type", f"{field} must be a string", field)]
    if (min_length is not None and len(value) < min_length) or (
        max_length is not None and len(value) > max_length
    ):
        return [
            _error(
                f"frontmatter.{field}.length",
                f"{field} must be {min_length}-{max_length} characters",
                field,
            )
        ]
    return []


def _check_optional_fields(frontmatter: dict[str, object]) -> list[Finding]:
    findings: list[Finding] = []

    if "disable-model-invocation" in frontmatter and not isinstance(
        frontmatter["disable-model-invocation"], bool
    ):
        findings.append(
            _error(
                "frontmatter.disable-model-invocation.type",
                "disable-model-invocation must be a boolean",
                "disable-model-invocation",
            )
        )

    findings.extend(_check_string_field(frontmatter, "license"))
    findings.extend(_check_string_field(frontmatter, "compatibility", min_length=1, max_length=500))

    if "allowed-tools" in frontmatter:
        allowed_tools = frontmatter["allowed-tools"]
        if not isinstance(allowed_tools, str):
            findings.append(
                _error(
                    "frontmatter.allowed-tools.type",
                    "allowed-tools must be a space-separated string",
                    "allowed-tools",
                )
            )
        elif not allowed_tools.strip() or "\n" in allowed_tools:
            findings.append(
                _error(
                    "frontmatter.allowed-tools.shape",
                    "allowed-tools must be a non-empty space-separated string",
                    "allowed-tools",
                )
            )

    return findings


def _metadata_mapping(
    frontmatter: dict[str, object],
) -> tuple[Mapping[object, object] | None, list[Finding]]:
    if "metadata" not in frontmatter:
        return None, [_missing_version()]
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        return None, [
            _error("metadata.type", "metadata must be a mapping of strings to strings", "metadata")
        ]
    return metadata, []


def _check_metadata_entries(metadata: Mapping[object, object]) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in metadata.items():
        if not isinstance(key, str):
            findings.append(_error("metadata.key-type", "metadata keys must be strings", "metadata"))
            continue
        if key != "version" and not isinstance(value, str):
            findings.append(
                _error(
                    "metadata.value-type",
                    f"metadata.{key} must be a string",
                    f"metadata.{key}",
                )
            )
    return findings


def _check_metadata_version(metadata: Mapping[object, object]) -> list[Finding]:
    if "version" not in metadata:
        return [_missing_version()]
    version = metadata.get("version")
    if not isinstance(version, str):
        return [
            _error("metadata.version.type", "metadata.version must be a string", "metadata.version")
        ]
    if not version.strip():
        return [
            _error("metadata.version.empty", "metadata.version must not be empty", "metadata.version")
        ]
    return []


def _check_metadata_extra_keys(metadata: Mapping[object, object]) -> list[Finding]:
    return [
        _warning(
            "metadata.extra-key",
            f"metadata.{key} is not part of the repo convention; only version is expected",
            f"metadata.{key}",
        )
        for key in metadata
        if isinstance(key, str) and key != "version"
    ]


def _check_metadata(frontmatter: dict[str, object]) -> list[Finding]:
    metadata, findings = _metadata_mapping(frontmatter)
    if metadata is None:
        return findings
    findings.extend(_check_metadata_entries(metadata))
    findings.extend(_check_metadata_version(metadata))
    findings.extend(_check_metadata_extra_keys(metadata))
    return findings


def _check_unknown_keys(frontmatter: dict[str, object]) -> list[Finding]:
    return [
        _warning(
            "frontmatter.unknown-key",
            f"unknown frontmatter key '{key}'",
            str(key),
        )
        for key in frontmatter
        if key not in _KNOWN_FIELDS
    ]


def _normalize_path(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))


def _strip_fenced_code(body: str) -> str:
    lines = body.splitlines(keepends=True)
    kept: list[str] = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            kept.append("\n" if line.endswith("\n") else "")
            continue
        kept.append(("\n" if line.endswith("\n") else "") if in_fence else line)
    return "".join(kept)


def _check_body(body: str) -> list[Finding]:
    if not body.strip():
        return [_error("body.empty", "SKILL.md body must not be empty", "body")]

    findings: list[Finding] = []
    line_count = len(body.splitlines())
    if line_count > _MAX_BODY_LINES:
        findings.append(
            _warning(
                "body.lines",
                f"SKILL.md body has {line_count} lines; keep it to {_MAX_BODY_LINES} or fewer",
                "body",
            )
        )

    token_estimate = math.ceil(len(body) / _CHARS_PER_TOKEN)
    if token_estimate > _MAX_BODY_TOKENS:
        findings.append(
            _warning(
                "body.tokens",
                f"SKILL.md body is estimated at {token_estimate} tokens "
                f"(characters / {_CHARS_PER_TOKEN}); keep it to {_MAX_BODY_TOKENS} or fewer",
                "body",
            )
        )
    return findings


def _reference_path(target: str) -> str | None:
    candidate = target.strip()
    if not candidate:
        return None
    if candidate.startswith("<") and candidate.endswith(">"):
        candidate = candidate[1:-1].strip()
    else:
        parts = candidate.split()
        if not parts:
            return None
        candidate = parts[0]

    candidate = candidate.split("#", 1)[0].split("?", 1)[0].strip()
    if not candidate:
        return None
    if candidate.startswith(("#", "/", "~", "\\")):
        return None
    if _URL_SCHEME_PATTERN.match(candidate):
        return None

    normalized = _normalize_path(candidate)
    first_part = normalized.split("/", 1)[0]
    if first_part not in _REFERENCE_DIRECTORIES:
        return None
    return normalized


def _line_number(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def _iter_references(body: str) -> list[tuple[str, int]]:
    references: list[tuple[str, int]] = []
    scannable = _strip_fenced_code(body)

    for pattern in (_MARKDOWN_LINK_PATTERN, _MARKDOWN_REFERENCE_PATTERN):
        for match in pattern.finditer(scannable):
            normalized = _reference_path(match.group(1))
            if normalized is not None:
                references.append(
                    (normalized, _line_number(body, match.start()))
                )

    for match in _INLINE_CODE_PATTERN.finditer(scannable):
        for token in match.group(1).split():
            normalized = _reference_path(token)
            if normalized is not None:
                references.append(
                    (normalized, _line_number(body, match.start()))
                )

    return references


def _check_references(body: str, reference_exists: ReferenceExists) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()

    for normalized, line_number in _iter_references(body):
        if normalized in seen:
            continue
        seen.add(normalized)
        location = f"body:{line_number}"
        if len(normalized.split("/")) > 2:
            findings.append(
                _warning(
                    "reference.too-deep",
                    f"reference '{normalized}' is more than one level below the skill root",
                    location,
                )
            )
        if not reference_exists(normalized):
            findings.append(
                _warning(
                    "reference.missing",
                    f"referenced path '{normalized}' does not exist",
                    location,
                )
            )

    return findings


def validate_document(
    text: str,
    directory_name: str,
    reference_exists: ReferenceExists,
) -> list[Finding]:
    frontmatter, body, findings = _parse_frontmatter(text)
    if frontmatter is None:
        return findings

    findings.extend(_check_name(frontmatter, directory_name))
    findings.extend(_check_description(frontmatter))
    findings.extend(_check_optional_fields(frontmatter))
    findings.extend(_check_metadata(frontmatter))
    findings.extend(_check_unknown_keys(frontmatter))
    findings.extend(_check_body(body))
    findings.extend(_check_references(body, reference_exists))
    return findings
