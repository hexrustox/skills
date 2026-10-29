import unittest
from pathlib import Path

from validate_skill.model import Finding, Run, Severity, SkillResult, TargetFailure


def _finding(severity: Severity) -> Finding:
    return Finding(
        rule="example.rule",
        severity=severity,
        message="example message",
        location="example",
    )


class RunExitCodeTestCase(unittest.TestCase):
    def test_empty_run_exits_zero(self) -> None:
        self.assertEqual(Run().exit_code, 0)

    def test_warnings_only_exit_zero(self) -> None:
        run = Run(
            results=(SkillResult(path=Path("skill"), findings=[_finding(Severity.WARNING)]),)
        )

        self.assertEqual(run.exit_code, 0)

    def test_errors_exit_one(self) -> None:
        run = Run(
            results=(SkillResult(path=Path("skill"), findings=[_finding(Severity.ERROR)]),)
        )

        self.assertEqual(run.exit_code, 1)

    def test_target_failures_exit_two(self) -> None:
        run = Run(failures=(TargetFailure(Path("missing"), "does not exist"),))

        self.assertEqual(run.exit_code, 2)

    def test_target_failures_take_precedence_over_errors(self) -> None:
        run = Run(
            results=(SkillResult(path=Path("skill"), findings=[_finding(Severity.ERROR)]),),
            failures=(TargetFailure(Path("missing"), "does not exist"),),
        )

        self.assertEqual(run.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
