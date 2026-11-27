"""Validate that a skill can be advertised for model invocation."""

from __future__ import annotations

import re
from pathlib import Path

MANIFEST_NAME = "SKILL.md"
SKILL_DIRECTORY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_PATTERN = re.compile(
    r"""^(?P<indent> *)(?P<key>"[^"]*"|'[^']*'|[A-Za-z0-9_./-]+):(?:[ \t]+(?P<value>.*))?$"""
)
BLOCK_SCALAR_PATTERN = re.compile(
    r"^(?P<indicator>[|>])(?:[+-][1-9]?|[1-9][+-]?)?\s*(?:#.*)?$"
)
NULL_VALUES = frozenset({"~", "null"})
TRUE_VALUES = frozenset({"true", "yes", "on", "1"})
FALSE_VALUES = frozenset({"false", "no", "off", "0"})
NON_STRING_PATTERNS = (
    re.compile(r"^(?:true|false|yes|no|on|off)$", re.IGNORECASE),
    re.compile(r"^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$"),
)
ESCAPED_CHARACTERS = {
    "0": "\0",
    "a": "\a",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "v": "\v",
    "f": "\f",
    "r": "\r",
    "e": "\x1b",
    " ": " ",
    '"': '"',
    "/": "/",
    "\\": "\\",
}


class SkillError(Exception):
    """Raised when a skill cannot be advertised for model invocation."""


def validate_skill(skill_dir: Path) -> None:
    """Reject skills OpenCode cannot offer to the model."""
    path = skill_dir.expanduser().resolve()
    if not path.is_dir():
        raise SkillError(f"skill directory not found: {path}")
    if not SKILL_DIRECTORY_PATTERN.fullmatch(path.name):
        raise SkillError(
            f"skill directory name {path.name!r} is not lowercase kebab-case"
        )
    manifest = path / MANIFEST_NAME
    if not manifest.is_file():
        raise SkillError(f"skill has no {MANIFEST_NAME}: {path}")

    try:
        text = manifest.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise SkillError(f"{MANIFEST_NAME} is not valid UTF-8: {manifest}") from error
    except OSError as error:
        raise SkillError(
            f"could not read {MANIFEST_NAME} {manifest}: {error}"
        ) from error

    frontmatter = _frontmatter_lines(text, manifest)
    description = _read_description(frontmatter, manifest)
    if not description.strip():
        raise SkillError(
            f"{MANIFEST_NAME} frontmatter description is empty: {manifest}"
        )
    if _boolean_field(frontmatter, "disable-model-invocation") is True:
        raise SkillError(
            f"{MANIFEST_NAME} sets disable-model-invocation to true, "
            f"hiding it from model invocation: {manifest}"
        )
    if _metadata_boolean(frontmatter, "opencode/autoinvoke", manifest) is False:
        raise SkillError(
            f"{MANIFEST_NAME} sets metadata.opencode/autoinvoke to false, "
            f"hiding it from model invocation: {manifest}"
        )


def _frontmatter_lines(text: str, path: Path) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise SkillError(f"{MANIFEST_NAME} has no frontmatter: {path}")
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            return lines[1:index]
    raise SkillError(f"{MANIFEST_NAME} frontmatter is not closed: {path}")


def _read_description(lines: list[str], path: Path) -> str:
    field = _find_field(lines, "description", 0)
    if field is None:
        raise SkillError(f"{MANIFEST_NAME} frontmatter has no description: {path}")
    raw_value, continuation = field
    description = _scalar_value(raw_value, continuation)
    if _is_plain_scalar(raw_value) and _is_non_string_scalar(description):
        raise SkillError(
            f"{MANIFEST_NAME} frontmatter description must be a string: {path}"
        )
    return description


def _boolean_field(lines: list[str], key: str) -> bool | None:
    field = _find_field(lines, key, 0)
    if field is None:
        return None
    return _parse_boolean(_scalar_value(*field))


def _parse_boolean(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def _metadata_boolean(lines: list[str], key: str, path: Path) -> bool | None:
    field = _find_field(lines, "metadata", 0)
    if field is None:
        return None
    raw_value, continuation = field
    value = raw_value.strip()
    if value and not value.startswith("#") and value.lower() not in NULL_VALUES:
        raise SkillError(
            f"{MANIFEST_NAME} frontmatter metadata must use block syntax: {path}"
        )

    child_indent = _first_content_indent(continuation)
    if child_indent is None:
        return None
    child = _find_field(continuation, key, child_indent)
    if child is None:
        return None
    return _parse_boolean(_scalar_value(*child))


def _first_content_indent(lines: list[str]) -> int | None:
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return _indentation(line)
    return None


def _find_field(
    lines: list[str],
    key: str,
    indent: int,
) -> tuple[str, list[str]] | None:
    for index, line in enumerate(lines):
        parsed = _split_field(line)
        if parsed is None:
            continue
        line_indent, field_key, raw_value = parsed
        if line_indent == indent and field_key == key:
            return raw_value, _continuation_lines(lines, index + 1, indent)
    return None


def _continuation_lines(lines: list[str], start: int, indent: int) -> list[str]:
    continuation: list[str] = []
    for line in lines[start:]:
        if line.strip() and _indentation(line) <= indent:
            break
        continuation.append(line)
    return continuation


def _split_field(line: str) -> tuple[int, str, str] | None:
    match = FIELD_PATTERN.fullmatch(line)
    if match is None:
        return None
    return (
        len(match.group("indent")),
        _unquote_key(match.group("key")),
        match.group("value") or "",
    )


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote_key(value: str) -> str:
    if value[0] == '"':
        return _unescape_double(value[1:-1])
    if value[0] == "'":
        return value[1:-1].replace("''", "'")
    return value


def _unescape_double(value: str) -> str:
    return re.sub(
        r"\\(.)",
        lambda match: ESCAPED_CHARACTERS.get(match.group(1), match.group(1)),
        value,
    )


def _scalar_value(raw_value: str, continuation: list[str]) -> str:
    value = raw_value.strip()
    block = BLOCK_SCALAR_PATTERN.fullmatch(value)
    if block:
        return _block_scalar_value(block.group("indicator"), continuation)

    if value.startswith(('"', "'")):
        return _quoted_scalar_value("\n".join([value, *continuation]))

    lines = [value] if value else []
    for line in continuation:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    plain = " ".join(lines)
    return "" if plain.lower() in NULL_VALUES else _strip_plain_comment(plain)


def _is_plain_scalar(raw_value: str) -> bool:
    value = raw_value.strip()
    return bool(
        value
        and not value.startswith(('"', "'"))
        and not BLOCK_SCALAR_PATTERN.fullmatch(value)
    )


def _is_non_string_scalar(value: str) -> bool:
    normalized = value.strip()
    if normalized.startswith(("[", "{")):
        return True
    return any(pattern.fullmatch(normalized) for pattern in NON_STRING_PATTERNS)


def _block_scalar_value(indicator: str, lines: list[str]) -> str:
    content = [line for line in lines if line.strip()]
    if not content:
        return ""
    indent = min(_indentation(line) for line in content)
    dedented = [line[indent:] if line.strip() else "" for line in lines]
    while dedented and not dedented[-1].strip():
        dedented.pop()
    if indicator == ">":
        return " ".join(line.strip() for line in dedented if line.strip())
    return "\n".join(dedented)


def _quoted_scalar_value(value: str) -> str:
    quote = value[0]
    index = 1
    while index < len(value):
        character = value[index]
        if quote == '"' and character == "\\":
            index += 2
            continue
        if character == quote:
            if quote == "'" and value[index + 1 : index + 2] == "'":
                index += 2
                continue
            inner = value[1:index]
            if quote == "'":
                return inner.replace("''", "'")
            return _unescape_double(inner)
        index += 1
    return value[1:]


def _strip_plain_comment(value: str) -> str:
    for index, character in enumerate(value):
        if character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value
