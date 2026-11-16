import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.benchmark import write_benchmark
from scripts.review import main, write_review
from scripts.workspace import run_id, write_eval_metadata, write_run_artifacts

from tests.support import canned_run_result, embedded_data

_SKILL_NAME = "example-skill"
_GRADING = {
    "expectations": [
        {
            "text": "The output includes a title",
            "passed": True,
            "evidence": "Title found on the first line.",
        },
        {
            "text": "The output is a poem",
            "passed": False,
            "evidence": "The output is prose.",
        },
    ],
    "summary": {"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5},
}


class ReviewPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.workspace = self.root / f"{_SKILL_NAME}-workspace"

    def write_run(
        self,
        iteration: Path,
        *,
        eval_id: int | str,
        arm: str = "with_skill",
        eval_name: str = "poem",
        prompt: str = "Write a short poem.",
        output_text: str = "Roses are red.\n",
        grading: dict[str, Any] | None = None,
    ) -> Path:
        eval_dir = iteration / f"eval-{eval_id}"
        metadata_path = write_eval_metadata(
            eval_dir,
            eval_id=eval_id,
            prompt=prompt,
            expected_output="A short poem.",
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["eval_name"] = eval_name
        metadata["expectations"] = [
            expectation["text"]
            for expectation in (grading or {}).get("expectations", [])
        ]
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        scope = self.root / "scopes" / f"{iteration.name}-{eval_id}-{arm}"
        scope.mkdir(parents=True)
        result = canned_run_result(
            scope,
            loaded_skill_ids=(_SKILL_NAME,),
            output_text=output_text,
        )
        arm_dir = eval_dir / arm
        write_run_artifacts(
            arm_dir,
            result,
            scope,
            run_identity=run_id(eval_id, arm),
        )
        if grading is not None:
            (arm_dir / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
        return arm_dir

    def write_feedback(
        self,
        iteration: Path,
        reviews: dict[str, str],
        *,
        notes: str = "",
        iteration_name: str | None = None,
        skill_name: str | None = None,
    ) -> Path:
        path = iteration / "feedback.json"
        path.write_text(
            json.dumps(
                {
                    "skill_name": skill_name or _SKILL_NAME,
                    "iteration": iteration_name or iteration.name,
                    "reviews": [
                        {"run_id": run_id, "feedback": feedback, "reviewed": True}
                        for run_id, feedback in reviews.items()
                    ],
                    "notes": notes,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_page_embeds_prompt_outputs_grades_and_feedback_controls(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1, grading=_GRADING)

        page = write_review(iteration)
        html = page.read_text(encoding="utf-8")
        data = embedded_data(html)

        self.assertEqual(page, iteration / "review.html")
        self.assertEqual(data["skill_name"], _SKILL_NAME)
        run = data["runs"][0]
        self.assertEqual(run["run_id"], "eval-1-with_skill")
        self.assertEqual(run["prompt"], "Write a short poem.")
        self.assertEqual(run["outputs"][0]["name"], "answer.md")
        self.assertEqual(run["outputs"][0]["content"], "Roses are red.\n")
        self.assertEqual(run["grading"], _GRADING)
        self.assertIn('id="download-feedback"', html)
        self.assertIn('id="copy-feedback"', html)
        self.assertIn("Download feedback JSON", html)
        self.assertIn("Copy feedback JSON", html)

    def test_output_with_a_script_tag_cannot_break_the_page(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(
            iteration,
            eval_id=1,
            output_text="<script>alert('boom')</script>\n",
        )

        html = write_review(iteration).read_text(encoding="utf-8")
        data = embedded_data(html)

        self.assertEqual(
            data["runs"][0]["outputs"][0]["content"],
            "<script>alert('boom')</script>\n",
        )
        self.assertEqual(html.count("</script>"), 1)

    def test_previous_iteration_is_matched_by_stable_run_identity(self) -> None:
        previous = self.workspace / "iteration-1"
        current = self.workspace / "iteration-2"
        self.write_run(
            previous,
            eval_id="ocean",
            eval_name="ocean",
            prompt="Describe the ocean.",
            output_text="The old ocean description.\n",
        )
        self.write_run(
            current,
            eval_id="ocean",
            eval_name="ocean",
            prompt="Describe the ocean.",
            output_text="The new ocean description.\n",
        )
        self.write_feedback(
            previous,
            {"eval-ocean-with_skill": "Mention the tides."},
        )

        data = embedded_data(write_review(current).read_text(encoding="utf-8"))

        self.assertEqual(data["previous"]["iteration"], "iteration-1")
        self.assertEqual(
            data["previous"]["feedback"]["eval-ocean-with_skill"],
            "Mention the tides.",
        )
        previous_run = data["previous"]["runs"]["eval-ocean-with_skill"]
        self.assertEqual(
            previous_run["outputs"][0]["content"], "The old ocean description.\n"
        )
        self.assertEqual(
            data["runs"][0]["outputs"][0]["content"],
            "The new ocean description.\n",
        )

    def test_existing_feedback_for_the_current_iteration_is_embedded(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        self.write_feedback(
            iteration,
            {"eval-1-with_skill": "This looks right."},
            notes="The baseline needs work.",
        )

        data = embedded_data(write_review(iteration).read_text(encoding="utf-8"))

        self.assertEqual(
            data["feedback"]["reviews"]["eval-1-with_skill"], "This looks right."
        )
        self.assertEqual(data["feedback"]["reviewed"], ["eval-1-with_skill"])
        self.assertEqual(data["feedback"]["notes"], "The baseline needs work.")

    def test_empty_reviewed_feedback_is_kept_as_reviewed(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        self.write_feedback(iteration, {"eval-1-with_skill": ""})

        data = embedded_data(write_review(iteration).read_text(encoding="utf-8"))

        self.assertEqual(data["feedback"]["reviews"]["eval-1-with_skill"], "")
        self.assertEqual(data["feedback"]["reviewed"], ["eval-1-with_skill"])

    def test_feedback_for_a_different_iteration_is_rejected(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        self.write_feedback(
            iteration,
            {"eval-1-with_skill": "Wrong iteration."},
            iteration_name="iteration-1",
        )

        with self.assertRaisesRegex(ValueError, "iteration-1"):
            write_review(iteration)

    def test_feedback_for_a_different_skill_is_rejected(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        self.write_feedback(
            iteration,
            {"eval-1-with_skill": "Wrong skill."},
            skill_name="other-skill",
        )

        with self.assertRaisesRegex(ValueError, "other-skill"):
            write_review(iteration)

    def test_stable_identity_comes_from_the_eval_directory(self) -> None:
        previous = self.workspace / "iteration-1"
        current = self.workspace / "iteration-2"
        self.write_run(previous, eval_id="ocean", output_text="Old ocean.\n")
        self.write_run(current, eval_id="ocean", output_text="New ocean.\n")
        metadata_path = current / "eval-ocean" / "eval_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["eval_id"] = "edited"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        data = embedded_data(write_review(current).read_text(encoding="utf-8"))

        self.assertEqual(data["runs"][0]["run_id"], "eval-ocean-with_skill")
        self.assertEqual(
            data["previous"]["runs"]["eval-ocean-with_skill"]["outputs"][0]["content"],
            "Old ocean.\n",
        )

    def test_nested_output_named_metrics_is_not_filtered(self) -> None:
        iteration = self.workspace / "iteration-2"
        arm_dir = self.write_run(iteration, eval_id=1)
        nested = arm_dir / "outputs" / "reports" / "metrics.json"
        nested.parent.mkdir(parents=True)
        nested.write_text("{}\n", encoding="utf-8")

        data = embedded_data(write_review(iteration).read_text(encoding="utf-8"))

        names = [output["name"] for output in data["runs"][0]["outputs"]]
        self.assertIn("reports/metrics.json", names)
        self.assertNotIn("metrics.json", names)

    def test_benchmark_tab_renders_supplied_benchmark_data(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        benchmark = {
            "metadata": {
                "skill_name": _SKILL_NAME,
                "timestamp": "2026-01-15T10:30:00Z",
                "evals_run": [1],
                "runs_per_configuration": 1,
            },
            "runs": [],
            "run_summary": {
                "with_skill": {
                    "pass_rate": {"mean": 1.0, "stddev": 0.0, "min": 1.0, "max": 1.0},
                    "time_seconds": {
                        "mean": 1.2,
                        "stddev": 0.0,
                        "min": 1.2,
                        "max": 1.2,
                    },
                    "tokens": {"mean": 15, "stddev": 0, "min": 15, "max": 15},
                },
                "delta": {"pass_rate": "+1.00"},
            },
            "notes": ["The skill passed every expectation."],
        }
        (iteration / "benchmark.json").write_text(
            json.dumps(benchmark), encoding="utf-8"
        )

        page = write_review(iteration)
        html = page.read_text(encoding="utf-8")
        data = embedded_data(html)

        self.assertEqual(data["benchmark"], benchmark)
        self.assertIn('id="benchmark-tab"', html)
        self.assertIn('id="benchmark-content"', html)

    def test_review_page_displays_the_generated_benchmark(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1, grading=_GRADING)
        baseline_grading = {
            "expectations": _GRADING["expectations"],
            "summary": {"passed": 0, "failed": 2, "total": 2, "pass_rate": 0.0},
        }
        self.write_run(
            iteration, eval_id=1, arm="without_skill", grading=baseline_grading
        )

        write_benchmark(
            iteration,
            skill_name=_SKILL_NAME,
            timestamp="2026-01-15T10:30:00Z",
        )
        page = write_review(iteration)
        html = page.read_text(encoding="utf-8")
        data = embedded_data(html)

        self.assertEqual(data["benchmark"]["metadata"]["skill_name"], _SKILL_NAME)
        self.assertEqual(
            [run["configuration"] for run in data["benchmark"]["runs"]],
            ["with_skill", "without_skill"],
        )
        self.assertEqual(
            data["benchmark"]["run_summary"]["delta"]["pass_rate"], "+0.50"
        )
        self.assertIn('id="benchmark-tab"', html)
        self.assertIn('id="benchmark-content"', html)

    def test_benchmark_can_be_supplied_from_another_path(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        benchmark = {
            "metadata": {"skill_name": _SKILL_NAME},
            "runs": [],
            "run_summary": {},
            "notes": ["Supplied from a separate file."],
        }
        supplied = self.root / "benchmark-results.json"
        supplied.write_text(json.dumps(benchmark), encoding="utf-8")

        data = embedded_data(
            write_review(iteration, benchmark_path=supplied).read_text(encoding="utf-8")
        )

        self.assertEqual(data["benchmark"], benchmark)

    def test_command_writes_the_page_and_reports_its_path(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            code = main(["--iteration", str(iteration)])

        self.assertEqual(code, 0)
        self.assertTrue((iteration / "review.html").is_file())
        self.assertIn(str(iteration / "review.html"), output.getvalue())

    def test_previous_context_can_be_omitted(self) -> None:
        previous = self.workspace / "iteration-1"
        current = self.workspace / "iteration-2"
        self.write_run(previous, eval_id=1, output_text="Old.\n")
        self.write_run(current, eval_id=1, output_text="New.\n")

        data = embedded_data(
            write_review(current, include_previous=False).read_text(encoding="utf-8")
        )

        self.assertIsNone(data["previous"])

    def test_page_needs_no_server_and_no_network(self) -> None:
        iteration = self.workspace / "iteration-2"
        self.write_run(iteration, eval_id=1)

        html = write_review(iteration).read_text(encoding="utf-8")

        self.assertNotIn("fetch(", html)
        self.assertNotIn("XMLHttpRequest", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn('href="http', html)
        self.assertIsNone(re.search(r"\bsrc=\"http", html))
