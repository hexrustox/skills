import unittest

from support import RepoTestCase, rules
from validate_skill.run import run_validation


class RunTestCase(RepoTestCase):
    def test_results_keep_the_requested_target_as_identity(self) -> None:
        skill_dir = self.write_document("# Example")

        run = run_validation([skill_dir, skill_dir / "SKILL.md"])

        self.assertEqual(run.failures, ())
        self.assertEqual([result.path for result in run.results], [skill_dir, skill_dir / "SKILL.md"])

    def test_validation_continues_after_a_target_fails(self) -> None:
        valid = self.write_document("# Example")

        run = run_validation([self.root / "missing", valid])

        self.assertEqual([failure.path for failure in run.failures], [self.root / "missing"])
        self.assertIn("does not exist", run.failures[0].message)
        self.assertEqual([result.path for result in run.results], [valid])
        self.assertEqual(rules(run.results[0].findings), [])

    def test_directory_without_skill_file_is_a_target_failure(self) -> None:
        empty_dir = self.root / "empty"
        empty_dir.mkdir()

        run = run_validation([empty_dir])

        self.assertEqual(run.results, ())
        self.assertEqual([failure.path for failure in run.failures], [empty_dir])
        self.assertIn("not a SKILL.md file or skill directory", run.failures[0].message)

    def test_batch_run_reports_findings_for_every_valid_target(self) -> None:
        first = self.write_document(
            frontmatter="""\
            name: first
            metadata:
              version: "1.0.0"
            """,
            name="first",
        )
        second = self.write_document("# Second", name="second")

        run = run_validation([first, second])

        self.assertEqual(
            [rules(result.findings) for result in run.results],
            [["description.missing"], []],
        )

    def test_registration_is_reported_when_frontmatter_is_missing(self) -> None:
        skill_file = self.write_skill(
            "# Example\n\nNo frontmatter here.\n", register=False
        ) / "SKILL.md"

        run = run_validation([skill_file])

        self.assertEqual(run.failures, ())
        self.assertEqual(
            rules(run.results[0].findings),
            ["frontmatter.missing", "plugin.manifest-missing"],
        )

    def test_document_and_registration_findings_combine(self) -> None:
        skill_dir = self.write_document(
            frontmatter="""\
            name: example
            metadata:
              version: "1.0.0"
            """,
            register=False,
        )
        self.write_manifest(["./other"])

        run = run_validation([skill_dir / "SKILL.md"])

        self.assertEqual(
            rules(run.results[0].findings),
            ["description.missing", "plugin.unregistered"],
        )

    def test_reference_resolver_checks_the_skill_root(self) -> None:
        skill_dir = self.write_document(
            "Read [the guide](references/guide.md).",
            register=False,
        )
        self.write_manifest(["./example"])
        reference = skill_dir / "references" / "guide.md"
        reference.parent.mkdir()
        reference.write_text("# Guide\n", encoding="utf-8")

        run = run_validation([skill_dir / "SKILL.md"])

        self.assertEqual(run.results[0].findings, [])


if __name__ == "__main__":
    unittest.main()
