import unittest

from support import RepoTestCase, run_cli


class CliTestCase(RepoTestCase):
    def test_valid_skill_exits_zero_with_summary(self) -> None:
        skill_dir = self.write_document("# Example\n\nFollow these steps.")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"skill: {skill_dir}", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 0 warnings", result.stdout)

    def test_missing_frontmatter_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill("# Example\n\nNo frontmatter here.\n")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assert_error(result, "frontmatter.missing")
        self.assertIn("1 skill checked, 1 error, 0 warnings", result.stdout)

    def test_skill_file_path_is_accepted(self) -> None:
        skill_dir = self.write_document("# Example")

        result = run_cli(str(skill_dir / "SKILL.md"), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 errors", result.stdout)

    def test_findings_are_grouped_per_skill_before_summary(self) -> None:
        skill_dir = self.write_document(
            frontmatter="""\
            metadata:
              version: "1.0.0"
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
        skill_dir = self.write_document("Run `scripts/mutate.sh`.")
        script = skill_dir / "scripts" / "mutate.sh"
        script.parent.mkdir()
        marker = self.root / "executed"
        script.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
        script.chmod(0o755)

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_missing_local_references_warn_and_exit_zero(self) -> None:
        skill_dir = self.write_document(
            "See [the guide](references/guide.md), the logo in "
            "[assets](assets/logo.png), and run `scripts/run.sh`."
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assert_warning(result, "reference.missing")
        self.assertIn("1 skill checked, 0 errors, 3 warnings", result.stdout)

    def test_multiple_paths_are_validated_in_one_run(self) -> None:
        first = self.write_document("First skill.", name="first")
        second = self.write_document("Second skill.", name="second")

        result = run_cli(str(first), str(second), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"skill: {first}", result.stdout)
        self.assertIn(f"skill: {second}", result.stdout)
        self.assertIn("2 skills checked, 0 errors, 0 warnings", result.stdout)

    def test_validation_continues_after_an_earlier_path_fails(self) -> None:
        failing = self.write_document(
            frontmatter="""\
            name: failing
            metadata:
              version: "1.0.0"
            """,
            name="failing",
        )
        passing = self.write_document("Passing skill.", name="passing")

        result = run_cli(str(failing), str(passing), cwd=self.root)

        self.assert_error(result, "description.missing")
        self.assertIn(f"skill: {passing}", result.stdout)
        self.assertNotIn("error ", result.stdout.split(f"skill: {passing}", 1)[1])
        self.assertIn("2 skills checked, 1 error, 0 warnings", result.stdout)

    def test_multiple_paths_with_only_warnings_exit_zero(self) -> None:
        first = self.write_document(
            frontmatter="""\
            name: first
            description: Does an example task.
            metadata:
              version: "1.0.0"
            unknown: value
            """,
            name="first",
        )
        second = self.write_document("Second skill.", name="second")

        result = run_cli(str(first), str(second), cwd=self.root)

        self.assert_warning(result, "frontmatter.unknown-key")
        self.assertIn("2 skills checked, 0 errors, 1 warning", result.stdout)

    def test_nonexistent_path_in_a_batch_exits_two(self) -> None:
        valid = self.write_document("Valid skill.")

        result = run_cli(str(self.root / "missing"), str(valid), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)
        self.assertIn(f"skill: {valid}", result.stdout)


if __name__ == "__main__":
    unittest.main()
