import json
import unittest

from support import RepoTestCase, run_cli


class CliJsonTestCase(RepoTestCase):
    def test_json_output_contains_skills_findings_and_summary(self) -> None:
        warning = self.write_document(
            frontmatter="""\
            name: warning
            description: Does an example task.
            metadata:
              version: "1.0.0"
              owner: team
            """,
            name="warning",
        )
        failing = self.write_document(
            frontmatter="""\
            name: failing
            metadata:
              version: "1.0.0"
            """,
            name="failing",
        )

        result = run_cli("--json", str(warning), str(failing), cwd=self.root)

        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"skills", "summary"})
        self.assertEqual(payload["summary"], {"skills": 2, "errors": 1, "warnings": 1})
        self.assertEqual(
            [skill["path"] for skill in payload["skills"]],
            [str(warning), str(failing)],
        )
        for skill in payload["skills"]:
            for finding in skill["findings"]:
                self.assertEqual(
                    set(finding), {"severity", "rule", "message", "location"}
                )
                self.assertIn(finding["severity"], {"error", "warning"})
                for value in finding.values():
                    self.assertIsInstance(value, str)
                    self.assertTrue(value)
        self.assertEqual(
            payload["skills"][0]["findings"],
            [
                {
                    "severity": "warning",
                    "rule": "metadata.extra-key",
                    "message": "metadata.owner is not part of the repo convention; "
                    "only version is expected",
                    "location": "metadata.owner",
                }
            ],
        )
        self.assertEqual(payload["skills"][1]["findings"][0]["rule"], "description.missing")

    def test_json_findings_match_text_findings(self) -> None:
        warning = self.write_document(
            frontmatter="""\
            name: warning
            description: Does an example task.
            metadata:
              version: "1.0.0"
              owner: team
            """,
            body="Read `references/missing.md`.",
            name="warning",
        )
        failing = self.write_document(
            frontmatter="""\
            name: failing
            description: Does an example task.
            metadata: {}
            """,
            body="# Failing",
            name="failing",
        )

        text_result = run_cli(str(warning), str(failing), cwd=self.root)
        json_result = run_cli("--json", str(warning), str(failing), cwd=self.root)

        self.assertEqual(json_result.returncode, text_result.returncode)
        payload = json.loads(json_result.stdout)
        text_finding_count = sum(
            line.startswith(("  error ", "  warning "))
            for line in text_result.stdout.splitlines()
        )
        json_finding_count = sum(
            len(skill["findings"]) for skill in payload["skills"]
        )
        self.assertEqual(json_finding_count, text_finding_count)
        self.assertIn("metadata.extra-key", text_result.stdout)
        for skill in payload["skills"]:
            for finding in skill["findings"]:
                self.assertIn(
                    f"{finding['severity']} {finding['rule']}: "
                    f"{finding['message']} [{finding['location']}]",
                    text_result.stdout,
                )

    def test_json_output_for_warnings_only_exits_zero(self) -> None:
        skill_dir = self.write_document(
            frontmatter="""\
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            unknown: value
            """
        )

        result = run_cli(str(skill_dir), "--json", cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"], {"skills": 1, "errors": 0, "warnings": 1})
        self.assertEqual(len(payload["skills"][0]["findings"]), 1)

    def test_json_output_with_usage_error_exits_two(self) -> None:
        result = run_cli("--json", str(self.root / "missing"), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["skills"], [])
        self.assertEqual(payload["summary"], {"skills": 0, "errors": 0, "warnings": 0})


if __name__ == "__main__":
    unittest.main()
