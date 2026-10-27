from pathlib import Path

import yaml

from validate_skill.model import Finding, SkillResult


def _error(rule: str, message: str, location: str) -> Finding:
    return Finding(rule=rule, severity="error", message=message, location=location)


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


def _non_empty_string(frontmatter: dict[str, object], field: str) -> list[Finding]:
    value = frontmatter.get(field)
    if field not in frontmatter:
        return [_error(f"{field}.missing", f"{field} is required", field)]
    if not isinstance(value, str):
        return [_error(f"{field}.type", f"{field} must be a string", field)]
    if not value.strip():
        return [_error(f"{field}.empty", f"{field} must not be empty", field)]
    return []


def validate_skill(path: Path) -> SkillResult:
    result = SkillResult(path=path)
    text = path.read_text(encoding="utf-8")

    frontmatter, _body, findings = _parse_frontmatter(text)
    result.findings.extend(findings)
    if frontmatter is None:
        return result

    result.findings.extend(_non_empty_string(frontmatter, "name"))
    result.findings.extend(_non_empty_string(frontmatter, "description"))
    return result
