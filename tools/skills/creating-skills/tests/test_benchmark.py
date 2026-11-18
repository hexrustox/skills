import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.benchmark import build_benchmark, main, write_benchmark


class BenchmarkAggregationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.iteration = self.root / "example-skill-workspace" / "iteration-1"
        self.iteration.mkdir(parents=True)

    def write_graded_run(
        self,
        eval_id: int | str,
        arm: str,
        *,
        eval_name: str | None = None,
        metadata_eval_id: int | str | None = None,
        pass_rate: float = 1.0,
        passed: int = 1,
        failed: int = 0,
        total: int = 1,
        time_seconds: float = 1.0,
        tokens: int = 100,
        output_chars: int = 100,
        grading_timing: dict[str, Any] | None = None,
        expectations: list[dict[str, Any]] | None = None,
        tool_calls: int = 2,
        errors: int = 0,
        user_notes_summary: dict[str, Any] | None = None,
    ) -> Path:
        eval_dir = self.iteration / f"eval-{eval_id}"
        eval_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "eval_id": metadata_eval_id if metadata_eval_id is not None else eval_id,
            "eval_name": eval_name or f"eval-{eval_id}",
            "prompt": "Do the task.",
            "expected_output": "A good answer.",
            "expectations": [],
        }
        (eval_dir / "eval_metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        arm_dir = eval_dir / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        grading: dict[str, Any] = {
            "expectations": expectations or [],
            "summary": {
                "passed": passed,
                "failed": failed,
                "total": total,
                "pass_rate": pass_rate,
            },
            "execution_metrics": {
                "total_tool_calls": tool_calls,
                "output_chars": output_chars,
                "errors_encountered": errors,
            },
        }
        if user_notes_summary is not None:
            grading["user_notes_summary"] = user_notes_summary
        if grading_timing is not None:
            grading["timing"] = grading_timing
        (arm_dir / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
        (arm_dir / "timing.json").write_text(
            json.dumps(
                {
                    "total_tokens": tokens,
                    "duration_ms": round(time_seconds * 1000),
                    "total_duration_seconds": time_seconds,
                }
            ),
            encoding="utf-8",
        )
        return arm_dir

    def test_each_graded_arm_directory_is_one_run(self) -> None:
        self.write_graded_run(1, "with_skill")
        self.write_graded_run(1, "without_skill")
        self.write_graded_run(2, "with_skill")
        ungraded = self.iteration / "eval-2" / "without_skill"
        ungraded.mkdir(parents=True)
        (ungraded / "error.json").write_text("{}", encoding="utf-8")

        benchmark = build_benchmark(self.iteration)

        self.assertEqual(
            [run["configuration"] for run in benchmark["runs"]],
            ["with_skill", "without_skill", "with_skill"],
        )
        self.assertEqual([run["eval_id"] for run in benchmark["runs"]], [1, 1, 2])
        self.assertEqual(benchmark["metadata"]["evals_run"], [1, 2])

    def test_summary_reports_mean_stddev_min_and_max_for_each_metric(self) -> None:
        self.write_graded_run(
            1, "with_skill", pass_rate=1.0, time_seconds=10.0, tokens=100
        )
        self.write_graded_run(
            2, "with_skill", pass_rate=0.5, time_seconds=20.0, tokens=300
        )
        self.write_graded_run(
            1, "without_skill", pass_rate=0.0, time_seconds=5.0, tokens=50
        )

        summary = build_benchmark(self.iteration)["run_summary"]

        self.assertEqual(
            summary["with_skill"]["pass_rate"],
            {"mean": 0.75, "stddev": 0.3536, "min": 0.5, "max": 1.0},
        )
        self.assertEqual(
            summary["with_skill"]["time_seconds"],
            {"mean": 15.0, "stddev": 7.0711, "min": 10.0, "max": 20.0},
        )
        self.assertEqual(
            summary["with_skill"]["tokens"],
            {"mean": 200.0, "stddev": 141.4214, "min": 100.0, "max": 300.0},
        )
        self.assertEqual(
            summary["without_skill"]["pass_rate"],
            {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
        )

    def test_delta_comes_from_arm_names_not_directory_order(self) -> None:
        self.write_graded_run(
            1, "without_skill", pass_rate=0.75, time_seconds=20.0, tokens=50
        )
        self.write_graded_run(
            1, "with_skill", pass_rate=0.25, time_seconds=10.0, tokens=100
        )

        summary = build_benchmark(self.iteration)["run_summary"]

        self.assertEqual(
            summary["delta"],
            {"pass_rate": "-0.50", "time_seconds": "-10.0", "tokens": "+50"},
        )

    def test_old_skill_is_the_baseline_when_present(self) -> None:
        self.write_graded_run(
            1, "old_skill", pass_rate=0.30, time_seconds=12.0, tokens=120
        )
        self.write_graded_run(
            1, "with_skill", pass_rate=0.80, time_seconds=10.0, tokens=100
        )

        summary = build_benchmark(self.iteration)["run_summary"]

        self.assertEqual(
            summary["delta"],
            {"pass_rate": "+0.50", "time_seconds": "-2.0", "tokens": "-20"},
        )

    def test_eval_names_come_from_metadata_and_run_count_comes_from_data(self) -> None:
        self.write_graded_run(
            "directory-name",
            "with_skill",
            eval_name="invoice-totals",
            metadata_eval_id="actual-id",
        )
        self.write_graded_run(2, "with_skill", eval_name="poem")

        benchmark = build_benchmark(self.iteration)
        named_run = next(
            run for run in benchmark["runs"] if run["eval_id"] == "actual-id"
        )

        self.assertEqual(named_run["eval_name"], "invoice-totals")
        self.assertEqual(named_run["eval_id"], "actual-id")
        self.assertEqual(benchmark["metadata"]["evals_run"], [2, "actual-id"])
        self.assertEqual(benchmark["metadata"]["runs_per_configuration"], 1)

    def test_tokens_come_from_timing_not_output_characters(self) -> None:
        self.write_graded_run(
            1,
            "with_skill",
            time_seconds=0.0,
            tokens=84852,
            output_chars=999999,
            grading_timing={"total_tokens": 111, "total_duration_seconds": 99.0},
        )

        benchmark = build_benchmark(self.iteration)
        result = benchmark["runs"][0]["result"]

        self.assertEqual(result["tokens"], 84852)
        self.assertEqual(result["time_seconds"], 0.0)
        self.assertEqual(
            benchmark["run_summary"]["with_skill"]["tokens"]["mean"], 84852
        )

    def test_run_copies_expectations_notes_and_execution_metrics(self) -> None:
        expectations = [
            {
                "text": "The output includes a title",
                "passed": True,
                "evidence": "Title found on the first line.",
            }
        ]
        self.write_graded_run(
            1,
            "with_skill",
            expectations=expectations,
            tool_calls=7,
            errors=2,
            user_notes_summary={
                "uncertainties": ["Used 2023 data."],
                "needs_review": ["Check the table totals."],
                "workarounds": [],
            },
        )

        run = build_benchmark(self.iteration)["runs"][0]

        self.assertEqual(run["expectations"], expectations)
        self.assertEqual(run["notes"], ["Used 2023 data.", "Check the table totals."])
        self.assertEqual(run["result"]["tool_calls"], 7)
        self.assertEqual(run["result"]["errors"], 2)

    def test_writes_benchmark_json_and_markdown(self) -> None:
        self.write_graded_run(
            1, "with_skill", pass_rate=0.75, time_seconds=10.0, tokens=100
        )
        self.write_graded_run(
            1, "without_skill", pass_rate=0.25, time_seconds=20.0, tokens=50
        )

        path = write_benchmark(
            self.iteration,
            skill_name="example-skill",
            skill_path="/skills/example-skill",
            timestamp="2026-01-15T10:30:00Z",
        )

        self.assertEqual(path, self.iteration / "benchmark.json")
        benchmark = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(benchmark["metadata"]["skill_name"], "example-skill")
        self.assertEqual(benchmark["metadata"]["skill_path"], "/skills/example-skill")
        self.assertEqual(benchmark["metadata"]["timestamp"], "2026-01-15T10:30:00Z")
        self.assertEqual(benchmark["metadata"]["runs_per_configuration"], 1)
        self.assertEqual(
            benchmark["run_summary"]["delta"],
            {"pass_rate": "+0.50", "time_seconds": "-10.0", "tokens": "+50"},
        )
        markdown = (self.iteration / "benchmark.md").read_text(encoding="utf-8")
        self.assertIn("# Skill Benchmark: example-skill", markdown)
        self.assertIn("| Pass rate |", markdown)
        self.assertIn("75.0% ± 0.0%", markdown)
        self.assertIn("+0.50", markdown)

    def test_command_writes_the_benchmark_and_reports_its_path(self) -> None:
        self.write_graded_run(1, "with_skill")
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            code = main(["--iteration", str(self.iteration)])

        self.assertEqual(code, 0)
        self.assertTrue((self.iteration / "benchmark.json").is_file())
        self.assertTrue((self.iteration / "benchmark.md").is_file())
        self.assertIn(str(self.iteration / "benchmark.json"), output.getvalue())

    def test_command_fails_when_no_runs_are_graded(self) -> None:
        error = io.StringIO()

        with contextlib.redirect_stderr(error):
            code = main(["--iteration", str(self.iteration)])

        self.assertEqual(code, 2)
        self.assertIn("no graded runs", error.getvalue())
