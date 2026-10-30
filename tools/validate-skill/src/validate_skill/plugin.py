import json
from pathlib import Path

from validate_skill.model import Finding
from validate_skill.references import normalize_path


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
            Finding.error(
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
            Finding.error(
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
                Finding.error(
                    "plugin.manifest-missing",
                    f"no .claude-plugin/plugin.json found above {skill_dir}",
                    "plugin",
                )
            ]

        entries, error = self._load(manifest)
        if error is not None:
            return [error]

        relative = skill_dir.relative_to(_plugin_root(manifest)).as_posix()
        registered = {normalize_path(entry) for entry in entries or []}
        if relative not in registered:
            return [
                Finding.error(
                    "plugin.unregistered",
                    f"skill directory '{relative}' is not registered in {manifest}",
                    "plugin",
                )
            ]
        return []
