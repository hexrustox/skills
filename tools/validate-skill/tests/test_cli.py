import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "validate_skill", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)

    def write_skill(self, content: str, name: str = "example") -> Path:
        skill_dir = self.root / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(textwrap.dedent(content), encoding="utf-8")
        return skill_dir

    def test_valid_skill_exits_zero_with_summary(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            ---

            # Example

            Follow these steps.
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"skill: {skill_dir}", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 0 warnings", result.stdout)

    def test_missing_frontmatter_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill("# Example\n\nNo frontmatter here.\n")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.missing", result.stdout)
        self.assertIn("1 skill checked, 1 error, 0 warnings", result.stdout)

    def test_malformed_yaml_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: [unclosed
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.malformed", result.stdout)

    def test_non_mapping_frontmatter_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            - one
            - two
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.not-mapping", result.stdout)

    def test_missing_name_exits_one_with_name_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            description: Does an example task.
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.missing", result.stdout)

    def test_missing_description_exits_one_with_description_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error description.missing", result.stdout)

    def test_empty_name_and_description_exit_one_with_relevant_rules(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: "  "
            description: ""
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.empty", result.stdout)
        self.assertIn("error description.empty", result.stdout)

    def test_non_string_name_and_description_exit_one_with_relevant_rules(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: 123
            description: [not, text]
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.type", result.stdout)
        self.assertIn("error description.type", result.stdout)

    def test_skill_file_path_is_accepted(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir / "SKILL.md"), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 errors", result.stdout)

    def test_findings_are_grouped_per_skill_before_summary(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            unknown: value
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], f"skill: {skill_dir}")
        self.assertTrue(lines[1].startswith("  error name.missing:"))
        self.assertTrue(lines[2].startswith("  error description.missing:"))
        self.assertEqual(lines[-1], "1 skill checked, 2 errors, 0 warnings")

    def test_no_arguments_exits_two(self) -> None:
        result = run_cli(cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)

    def test_nonexistent_path_exits_two(self) -> None:
        result = run_cli(str(self.root / "missing"), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)

    def test_directory_without_skill_file_exits_two(self) -> None:
        empty_dir = self.root / "empty"
        empty_dir.mkdir()

        result = run_cli(str(empty_dir), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("not a SKILL.md file or skill directory", result.stderr)

    def test_referenced_scripts_are_not_executed(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            ---

            Run `scripts/mutate.sh`.
            """
        )
        script = skill_dir / "scripts" / "mutate.sh"
        script.parent.mkdir()
        marker = self.root / "executed"
        script.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
        script.chmod(0o755)

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
