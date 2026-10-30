import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from collections.abc import Iterable
from pathlib import Path

from validate_skill.model import Finding


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "validate_skill", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def valid_frontmatter(*, name: str = "example") -> str:
    return (
        f"name: {name}\n"
        "description: Does an example task.\n"
        "metadata:\n"
        '  version: "1.0.0"\n'
    )


def build_document(
    body: str = "# Example",
    *,
    frontmatter: str | None = None,
    name: str = "example",
) -> str:
    frontmatter_text = (
        valid_frontmatter(name=name)
        if frontmatter is None
        else textwrap.dedent(frontmatter).strip()
    )
    return "---\n" f"{frontmatter_text}\n" "---\n\n" f"{body}\n"


def rules(findings: Iterable[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self._registrations: dict[Path, list[str]] = {}

    def write_manifest(
        self, entries: list[str], *, plugin_root: Path | None = None
    ) -> Path:
        manifest = (plugin_root or self.root) / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"skills": entries}), encoding="utf-8")
        return manifest

    def write_skill(
        self,
        content: str,
        name: str = "example",
        *,
        base: Path | None = None,
        register: bool = True,
    ) -> Path:
        skill_dir = (base or self.root) / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(textwrap.dedent(content), encoding="utf-8")
        if register:
            entries = self._registrations.setdefault(skill_dir.parent, [])
            entries.append(f"./{name}")
            self.write_manifest(entries, plugin_root=skill_dir.parent)
        return skill_dir

    def write_document(
        self,
        body: str = "# Example",
        *,
        frontmatter: str | None = None,
        name: str = "example",
        base: Path | None = None,
        register: bool = True,
    ) -> Path:
        document = build_document(body, frontmatter=frontmatter, name=name)
        return self.write_skill(document, name=name, base=base, register=register)

    def assert_error(
        self, result: subprocess.CompletedProcess[str], rule: str
    ) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"error {rule}", result.stdout)

    def assert_warning(
        self, result: subprocess.CompletedProcess[str], rule: str
    ) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"warning {rule}", result.stdout)
