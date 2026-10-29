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


if __name__ == "__main__":
    unittest.main()
