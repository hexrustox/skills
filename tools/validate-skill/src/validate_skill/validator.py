import json
import os
import posixpath
from pathlib import Path

from validate_skill.document import validate_document
from validate_skill.model import Finding, Severity, SkillResult


def _error(rule: str, message: str, location: str) -> Finding:
    return Finding(rule=rule, severity=Severity.ERROR, message=message, location=location)


def _find_plugin_manifest(skill_dir: Path) -> Path | None:
    for parent in (skill_dir, *skill_dir.parents):
        candidate = parent / ".claude-plugin" / "plugin.json"
        if candidate.exists():
            return candidate
    return None


def _plugin_root(manifest: Path) -> Path:
    plugin_directory = manifest.parent
    return plugin_directory.parent


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


class ManifestCache:
    def __init__(self) -> None:
        self._loaded: dict[Path, tuple[list[str] | None, Finding | None]] = {}

    def load(self, manifest: Path) -> tuple[list[str] | None, Finding | None]:
        if manifest not in self._loaded:
            self._loaded[manifest] = _load_manifest(manifest)
        return self._loaded[manifest]


def _check_plugin_registration(skill_dir: Path, cache: ManifestCache) -> list[Finding]:
    manifest = _find_plugin_manifest(skill_dir)
    if manifest is None:
        return [
            _error(
                "plugin.manifest-missing",
                f"no .claude-plugin/plugin.json found above {skill_dir}",
                "plugin",
            )
        ]

    entries, error = cache.load(manifest)
    if error is not None:
        return [error]

    relative = skill_dir.relative_to(_plugin_root(manifest)).as_posix()
    registered = {
        posixpath.normpath(entry.replace("\\", "/")) for entry in entries or []
    }
    if relative not in registered:
        return [
            _error(
                "plugin.unregistered",
                f"skill directory '{relative}' is not registered in {manifest}",
                "plugin",
            )
        ]
    return []


def validate_skill(path: Path, cache: ManifestCache | None = None) -> SkillResult:
    skill_file = Path(os.path.abspath(path))
    skill_dir = skill_file.parent
    text = skill_file.read_text(encoding="utf-8")

    result = SkillResult(path=path)
    result.findings.extend(
        validate_document(
            text,
            skill_dir.name,
            lambda candidate: (skill_dir / candidate).exists(),
        )
    )
    result.findings.extend(_check_plugin_registration(skill_dir, cache or ManifestCache()))
    return result
