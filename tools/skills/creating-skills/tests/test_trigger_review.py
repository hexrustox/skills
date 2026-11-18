import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.trigger_review import main, write_trigger_review

from tests.support import embedded_data, write_skill

_TRIGGER_MARKER = "const TRIGGER_DATA = "


def write_queries(skill: Path) -> Path:
    path = skill / "evals" / "trigger_evals.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {"query": "Summarize the invoice.", "should_trigger": True},
                {"query": "Write a poem.", "should_trigger": False},
            ]
        ),
        encoding="utf-8",
    )
    return path


class TriggerReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        self.eval_set = write_queries(self.skill)

    def test_page_embeds_the_skill_and_query_set(self) -> None:
        page = write_trigger_review(self.skill, self.eval_set)
        html = page.read_text(encoding="utf-8")
        data = embedded_data(html, _TRIGGER_MARKER)

        self.assertEqual(
            page,
            self.root / "skills" / "example-skill-workspace" / "trigger-review.html",
        )
        self.assertEqual(data["skill_name"], "example-skill")
        self.assertEqual(data["description"], "Does example-skill work.")
        self.assertEqual(
            data["queries"],
            [
                {"query": "Summarize the invoice.", "should_trigger": True},
                {"query": "Write a poem.", "should_trigger": False},
            ],
        )

    def test_page_offers_editing_and_json_transport_controls(self) -> None:
        html = write_trigger_review(self.skill, self.eval_set).read_text(
            encoding="utf-8"
        )

        self.assertIn('id="add-query"', html)
        self.assertIn('id="query-list"', html)
        self.assertIn('id="download-queries"', html)
        self.assertIn('id="copy-queries"', html)
        self.assertIn("Download trigger_evals.json", html)
        self.assertIn("Copy trigger_evals.json", html)

    def test_query_text_cannot_break_the_embedded_data(self) -> None:
        self.eval_set.write_text(
            json.dumps(
                [
                    {
                        "query": "</script><script>alert('boom')</script>",
                        "should_trigger": True,
                    }
                ]
            ),
            encoding="utf-8",
        )

        html = write_trigger_review(self.skill, self.eval_set).read_text(
            encoding="utf-8"
        )
        data = embedded_data(html, _TRIGGER_MARKER)

        self.assertEqual(
            data["queries"][0]["query"],
            "</script><script>alert('boom')</script>",
        )
        self.assertEqual(html.count("</script>"), 1)

    def test_page_needs_no_server_and_no_network(self) -> None:
        html = write_trigger_review(self.skill, self.eval_set).read_text(
            encoding="utf-8"
        )

        self.assertNotIn("fetch(", html)
        self.assertNotIn("XMLHttpRequest", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn('href="http', html)
        self.assertIsNone(re.search(r"\bsrc=\"http", html))

    def test_output_path_can_be_overridden(self) -> None:
        output = self.root / "review" / "queries.html"

        page = write_trigger_review(self.skill, self.eval_set, output_path=output)

        self.assertEqual(page, output)
        self.assertTrue(output.is_file())

    def test_command_writes_the_page_and_reports_its_path(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--eval-set",
                    str(self.eval_set),
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn("trigger-review.html", output.getvalue())


class TriggerReviewFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")

    def test_missing_eval_set_is_an_error(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = main(["--skill", str(self.skill)])

        self.assertEqual(status, 2)
        self.assertIn("error:", stderr.getvalue())

    def test_invalid_eval_set_is_an_error(self) -> None:
        eval_set = self.skill / "evals" / "trigger_evals.json"
        eval_set.parent.mkdir()
        eval_set.write_text(
            json.dumps([{"query": "Missing polarity."}]), encoding="utf-8"
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--eval-set",
                    str(eval_set),
                ]
            )

        self.assertEqual(status, 2)
        self.assertIn("should_trigger", stderr.getvalue())
