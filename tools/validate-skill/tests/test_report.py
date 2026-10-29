import json
import unittest
from pathlib import Path

from validate_skill.model import Finding, Severity, SkillResult
from validate_skill.report import render_json, render_text
from validate_skill.run import Run


def build_run() -> Run:
    return Run(
        results=(
            SkillResult(
                path=Path("first"),
                findings=[
                    Finding(
                        rule="description.missing",
                        severity=Severity.ERROR,
                        message="description is required",
                        location="description",
                    ),
                    Finding(
                        rule="metadata.extra-key",
                        severity=Severity.WARNING,
                        message="metadata.owner is not part of the repo convention",
                        location="metadata.owner",
                    ),
                ],
            ),
            SkillResult(path=Path("second")),
        )
    )


class ReportTestCase(unittest.TestCase):
    def test_text_groups_findings_per_skill_and_summarizes(self) -> None:
        self.assertEqual(
            render_text(build_run()),
            "skill: first\n"
            "  error description.missing: description is required [description]\n"
            "  warning metadata.extra-key: metadata.owner is not part of the repo "
            "convention [metadata.owner]\n"
            "skill: second\n"
            "2 skills checked, 1 error, 1 warning",
        )

    def test_json_contains_skills_findings_and_summary(self) -> None:
        payload = json.loads(render_json(build_run()))

        self.assertEqual(
            payload,
            {
                "skills": [
                    {
                        "path": "first",
                        "findings": [
                            {
                                "severity": "error",
                                "rule": "description.missing",
                                "message": "description is required",
                                "location": "description",
                            },
                            {
                                "severity": "warning",
                                "rule": "metadata.extra-key",
                                "message": "metadata.owner is not part of the repo convention",
                                "location": "metadata.owner",
                            },
                        ],
                    },
                    {"path": "second", "findings": []},
                ],
                "summary": {"skills": 2, "errors": 1, "warnings": 1},
            },
        )

    def test_empty_run_renders_no_text_and_empty_json(self) -> None:
        empty = Run()

        self.assertEqual(render_text(empty), "")
        self.assertEqual(
            json.loads(render_json(empty)),
            {"skills": [], "summary": {"skills": 0, "errors": 0, "warnings": 0}},
        )

    def test_summary_uses_singular_forms(self) -> None:
        self.assertTrue(
            render_text(build_run()).endswith(
                "2 skills checked, 1 error, 1 warning"
            )
        )
        single = Run(results=(SkillResult(path=Path("only")),))
        self.assertEqual(render_text(single), "skill: only\n1 skill checked, 0 errors, 0 warnings")


if __name__ == "__main__":
    unittest.main()
