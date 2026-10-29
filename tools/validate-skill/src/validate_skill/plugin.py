import json
import posixpath
from pathlib import Path

from validate_skill.model import Finding, Severity


def _error(rule: str, message: str, location: str) -> Finding:
    return Finding(rule=rule, severity=Severity.ERROR, message=message, location=location)


def _find_manifest(skill_dir: Path) -> Path | None:
    for parent in (skill_dir, *skill_dir.parents):
        candidate = parent / ".claude-plugin" / "plugin.json"
        if candidate.exists():
            return candidate
    return None


def _plugin_root(manifest: Path) -> Path:
    return manifest.parent.parent


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


class PluginRegistry:
    def __init__(self) -> None:
        self._manifests: dict[Path, tuple[list[str] | None, Finding | None]] = {}

    def _load(self, manifest: Path) -> tuple[list[str] | None, Finding | None]:
        if manifest not in self._manifests:
            self._manifests[manifest] = _load_manifest(manifest)
        return self._manifests[manifest]

    def check(self, skill_dir: Path) -> list[Finding]:
        manifest = _find_manifest(skill_dir)
        if manifest is None:
            return [
                _error(
                    "plugin.manifest-missing",
                    f"no .claude-plugin/plugin.json found above {skill_dir}",
                    "plugin",
                )
            ]

        entries, error = self._load(manifest)
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
