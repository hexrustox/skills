import tempfile
import unittest
from pathlib import Path

from scripts.description_report import generate_report, write_report


def history_entry(
    iteration: int,
    description: str,
    *,
    train_passed: int,
    test_passed: int,
) -> dict[str, object]:
    train = [
        {
            "query": "Summarize the invoice.",
            "should_trigger": True,
            "triggers": 1 if train_passed else 0,
            "runs": 1,
            "pass": bool(train_passed),
        },
        {
            "query": "Write a poem.",
            "should_trigger": False,
            "triggers": 0 if train_passed else 1,
            "runs": 1,
            "pass": bool(train_passed),
        },
    ]
    test = [
        {
            "query": "Extract the invoice total.",
            "should_trigger": True,
            "triggers": 1 if test_passed else 0,
            "runs": 1,
            "pass": bool(test_passed),
        }
    ]
    return {
        "iteration": iteration,
        "description": description,
        "train_passed": train_passed,
        "train_failed": 2 - train_passed,
        "train_total": 2,
        "train_results": train,
        "test_passed": test_passed,
        "test_failed": 1 - test_passed,
        "test_total": 1,
        "test_results": test,
    }


def report_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "skill_name": "example-skill",
        "original_description": "Original description.",
        "best_description": "Best description.",
        "best_score": "1/1",
        "best_test_score": "1/1",
        "best_train_score": "2/2",
        "best_iteration": 2,
        "final_description": "Final description.",
        "exit_reason": "all_passed (iteration 2)",
        "iterations_run": 2,
        "holdout": 0.4,
        "train_size": 2,
        "test_size": 1,
        "model": "test/model",
        "history": [
            history_entry(1, "Original description.", train_passed=0, test_passed=0),
            history_entry(2, "Best description.", train_passed=2, test_passed=1),
        ],
    }
    data.update(overrides)
    return data


class DescriptionReportTests(unittest.TestCase):
    def test_report_shows_train_and_test_scores_and_queries(self) -> None:
        html = generate_report(report_data(), skill_name="example-skill")

        self.assertIn("example-skill", html)
        self.assertIn("Original description.", html)
        self.assertIn("Best description.", html)
        self.assertIn("Final description.", html)
        self.assertIn("Summarize the invoice.", html)
        self.assertIn("Extract the invoice total.", html)
        self.assertIn("Train", html)
        self.assertIn("Test", html)
        self.assertIn("Best score", html)
        self.assertIn("1/1", html)
        self.assertIn("test/model", html)

    def test_report_escapes_untrusted_text(self) -> None:
        data = report_data(best_description="<script>alert('boom')</script>")

        html = generate_report(data)

        self.assertNotIn("<script>alert('boom')</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_live_report_refreshes_and_final_report_does_not(self) -> None:
        live = generate_report(report_data(), auto_refresh=True)
        final = generate_report(report_data(), auto_refresh=False)

        self.assertIn('http-equiv="refresh"', live)
        self.assertNotIn('http-equiv="refresh"', final)

    def test_report_is_static(self) -> None:
        html = generate_report(report_data())

        self.assertNotIn("fetch(", html)
        self.assertNotIn("XMLHttpRequest", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn('href="http', html)

    def test_write_report_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.html"

            written = write_report(path, report_data(), skill_name="example-skill")

            self.assertEqual(written, path)
            self.assertIn("Best description.", path.read_text(encoding="utf-8"))
