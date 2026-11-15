"""Parse the frontmatter of a skill's SKILL.md without third-party dependencies."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

_BLOCK_SCALAR_INDICATORS = frozenset({">", ">-", ">+", "|", "|-", "|+"})
_TOP_LEVEL_ENTRY = re.compile(r"([A-Za-z0-9_-]+):(?:[ \t]*(.*))?")
_UNQUOTED_COMMENT = re.compile(r"[ \t]+#")


class FrontmatterError(ValueError):
    """Raised when a SKILL.md frontmatter block cannot be parsed."""


@dataclass(frozen=True)
class SkillDocument:
    """The name, description, and full content of a SKILL.md file."""

    name: str
    description: str
    content: str


def parse_skill_md(skill_path: Path) -> SkillDocument:
    """Parse the SKILL.md in ``skill_path``.

    Returns the skill's name, description, and full file content.
    """
    skill_md = skill_path / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    lines = content.splitlines()

    if not lines or lines[0].removeprefix("\ufeff").strip() != "---":
        raise FrontmatterError("SKILL.md must start with a '---' frontmatter delimiter")

    closing = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        ),
        None,
    )
    if closing is None:
        raise FrontmatterError(
            "SKILL.md frontmatter is missing a closing '---' delimiter"
        )

    fields = _parse_frontmatter(lines[1:closing])

    if "name" not in fields:
        raise FrontmatterError("SKILL.md frontmatter is missing required 'name'")
    if "description" not in fields:
        raise FrontmatterError("SKILL.md frontmatter is missing required 'description'")

    name = fields["name"]
    description = fields["description"]
    if not name.strip():
        raise FrontmatterError("SKILL.md frontmatter field 'name' must not be empty")
    if not description.strip():
        raise FrontmatterError(
            "SKILL.md frontmatter field 'description' must not be empty"
        )

    return SkillDocument(name=name, description=description, content=content)


def _parse_frontmatter(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    seen: set[str] = set()
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        line_number = index + 2
        if line[0].isspace():
            raise FrontmatterError(
                f"SKILL.md frontmatter line {line_number} is indented "
                "without a parent key"
            )

        match = _TOP_LEVEL_ENTRY.fullmatch(line)
        if match is None:
            raise FrontmatterError(
                f"SKILL.md frontmatter line {line_number} is not a 'key: value' entry"
            )

        key = match.group(1)
        if key in seen:
            raise FrontmatterError(
                f"SKILL.md frontmatter line {line_number} repeats key '{key}'"
            )
        seen.add(key)

        value, index = _parse_value(lines, index + 1, match.group(2) or "", line_number)
        if key in ("name", "description"):
            fields[key] = value

    return fields


def _parse_value(
    lines: list[str], index: int, raw_value: str, line_number: int
) -> tuple[str, int]:
    indicator = _UNQUOTED_COMMENT.split(raw_value.strip(), maxsplit=1)[0].strip()
    if indicator in _BLOCK_SCALAR_INDICATORS:
        block_lines, index = _collect_indented(lines, index)
        return " ".join(part.strip() for part in block_lines if part.strip()), index

    if indicator.startswith((">", "|")):
        raise FrontmatterError(
            f"SKILL.md frontmatter line {line_number} uses unsupported "
            f"block scalar indicator {indicator!r}"
        )

    if not indicator:
        continuation, index = _collect_indented(lines, index)
        return " ".join(part.strip() for part in continuation if part.strip()), index

    value = _parse_inline_value(indicator, line_number)
    continuation, index = _collect_indented(lines, index)
    if continuation:
        joined = " ".join(part.strip() for part in continuation if part.strip())
        if joined:
            value = f"{value} {joined}"
    return value, index


def _collect_indented(lines: list[str], index: int) -> tuple[list[str], int]:
    collected: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line and not line[0].isspace():
            break
        collected.append(line)
        index += 1
    return collected, index


def _parse_inline_value(value: str, line_number: int) -> str:
    if value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise FrontmatterError(
                f"SKILL.md frontmatter line {line_number} has an invalid "
                f"double-quoted value: {error.msg}"
            ) from error

    if value.startswith("'"):
        if not value.endswith("'") or len(value) == 1:
            raise FrontmatterError(
                f"SKILL.md frontmatter line {line_number} has an unterminated "
                "single-quoted value"
            )
        return value[1:-1].replace("''", "'")

    if value.startswith(("[", "{", "&", "*", "!", "- ", "? ")):
        raise FrontmatterError(
            f"SKILL.md frontmatter line {line_number} uses unsupported "
            f"inline value {value!r}"
        )

    return _UNQUOTED_COMMENT.split(value, maxsplit=1)[0].strip()
