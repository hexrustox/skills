import json
import os
import posixpath
import re
from pathlib import Path

import yaml

from validate_skill.model import Finding, SkillResult

_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
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
    return Finding(rule=rule, severity="error", message=message, location=location)


def _warning(rule: str, message: str, location: str) -> Finding:
    return Finding(rule=rule, severity="warning", message=message, location=location)


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


def _check_name(frontmatter: dict[str, object], directory_name: str) -> list[Finding]:
    findings = _non_empty_string(frontmatter, "name")
    value = frontmatter.get("name")
    if not isinstance(value, str) or not value.strip():
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
    findings = _non_empty_string(frontmatter, "description")
    value = frontmatter.get("description")
    if not isinstance(value, str) or not value.strip():
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


def _check_metadata(frontmatter: dict[str, object]) -> list[Finding]:
    findings: list[Finding] = []

    if "metadata" not in frontmatter:
        return [_error("metadata.version.missing", "metadata.version is required", "metadata.version")]

    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        return [_error("metadata.type", "metadata must be a mapping of strings to strings", "metadata")]

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

    if "version" not in metadata:
        findings.append(_error("metadata.version.missing", "metadata.version is required", "metadata.version"))
    else:
        version = metadata.get("version")
        if not isinstance(version, str):
            findings.append(
                _error("metadata.version.type", "metadata.version must be a string", "metadata.version")
            )
        elif not version.strip():
            findings.append(
                _error("metadata.version.empty", "metadata.version must not be empty", "metadata.version")
            )

    for key in metadata:
        if isinstance(key, str) and key != "version":
            findings.append(
                _warning(
                    "metadata.extra-key",
                    f"metadata.{key} is not part of the repo convention; only version is expected",
                    f"metadata.{key}",
                )
            )

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


def _check_body(body: str) -> list[Finding]:
    if not body.strip():
        return [_error("body.empty", "SKILL.md body must not be empty", "body")]
    return []


def _directory_name(path: Path) -> str:
    return path.parent.name or path.resolve().parent.name


def _find_plugin_manifest(skill_dir: Path) -> Path | None:
    for parent in (skill_dir, *skill_dir.parents):
        candidate = parent / ".claude-plugin" / "plugin.json"
        if candidate.exists():
            return candidate
    return None


def _normalize_manifest_entry(entry: str) -> str:
    return posixpath.normpath(entry.replace("\\", "/"))


def _load_manifest(manifest: Path) -> tuple[list[str] | None, Finding | None]:
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return (
            None,
            _error(
                "plugin.manifest-invalid",
                f"could not parse {manifest}: {error}",
                str(manifest),
            ),
        )
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("skills"), list)
        or not all(isinstance(entry, str) for entry in data["skills"])
    ):
        return (
            None,
            _error(
                "plugin.manifest-invalid",
                f"{manifest} must contain a 'skills' array of strings",
                str(manifest),
            ),
        )
    return data["skills"], None


def _check_plugin_registration(skill_file: Path) -> list[Finding]:
    skill_dir = Path(os.path.abspath(skill_file)).parent
    manifest = _find_plugin_manifest(skill_dir)
    if manifest is None:
        return [
            _error(
                "plugin.manifest-missing",
                f"no .claude-plugin/plugin.json found above {skill_dir}",
                "plugin",
            )
        ]

    entries, error = _load_manifest(manifest)
    if error is not None:
        return [error]

    plugin_root = manifest.parent.parent
    relative = skill_dir.relative_to(plugin_root).as_posix()
    registered = {_normalize_manifest_entry(entry) for entry in entries or []}
    if relative not in registered:
        return [
            _error(
                "plugin.unregistered",
                f"skill directory '{relative}' is not registered in {manifest}",
                "plugin",
            )
        ]
    return []


def validate_skill(path: Path) -> SkillResult:
    result = SkillResult(path=path)
    text = path.read_text(encoding="utf-8")

    frontmatter, body, findings = _parse_frontmatter(text)
    result.findings.extend(findings)
    result.findings.extend(_check_plugin_registration(path))
    if frontmatter is None:
        return result

    result.findings.extend(_check_name(frontmatter, _directory_name(path)))
    result.findings.extend(_check_description(frontmatter))
    result.findings.extend(_check_optional_fields(frontmatter))
    result.findings.extend(_check_metadata(frontmatter))
    result.findings.extend(_check_unknown_keys(frontmatter))
    result.findings.extend(_check_body(body))
    return result
