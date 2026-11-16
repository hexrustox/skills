import contextlib
import io
import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from scripts.description_loop import (
    run_description_loop,
    split_trigger_queries,
)
from scripts.harness import TriggerResult
from scripts.trigger_eval import TriggerQuery

from tests.support import (
    RecordingHarness,
    ScriptedCompletionHarness,
    canned_run_result,
    write_skill,
)


class DescriptionLoopHarness(ScriptedCompletionHarness):
    """Return probe outcomes per description and scripted optimizer responses."""

    def __init__(
        self,
        root: Path,
        outcome: Callable[[str, str], bool],
        responses: list[str],
    ) -> None:
        super().__init__(root, responses)
        self.outcome = outcome
        self.probe_calls: list[dict[str, object]] = []

    def probe_trigger(self, skill_name, description, query, **options):
        self.probe_calls.append(
            {
                "skill_name": skill_name,
                "description": description,
                "query": query,
                "model": options.get("model"),
            }
        )
        run = canned_run_result(
            self.root / "probe",
            output_name=f"probe-{len(self.probe_calls)}.md",
            loaded_skill_ids=("candidate",) if self.outcome(description, query) else (),
        )
        return TriggerResult(
            triggered=self.outcome(description, query),
            candidate_skill_id="candidate",
            run=run,
        )


class LiveReadingHarness(DescriptionLoopHarness):
    """Capture the live report as it exists when an optimizer run starts."""

    def __init__(
        self,
        root: Path,
        outcome: Callable[[str, str], bool],
        responses: list[str],
        live_report_path: Path,
    ) -> None:
        super().__init__(root, outcome, responses)
        self.live_report_path = live_report_path
        self.live_snapshots: list[str] = []

    def run(self, scope, prompt, **options):
        self.live_snapshots.append(self.live_report_path.read_text(encoding="utf-8"))
        return super().run(scope, prompt, **options)


def make_queries() -> tuple[TriggerQuery, ...]:
    positives = [
        TriggerQuery(f"Summarize invoice {index}.", True) for index in range(4)
    ]
    negatives = [TriggerQuery(f"Write poem {index}.", False) for index in range(4)]
    return tuple(positives + negatives)


def tagged(response: str) -> str:
    return f"<new_description>{response}</new_description>"


class SplitTests(unittest.TestCase):
    def test_split_is_stratified_deterministic_and_complete(self) -> None:
        queries = make_queries()

        first = split_trigger_queries(queries, holdout=0.5, seed=7)
        second = split_trigger_queries(queries, holdout=0.5, seed=7)

        self.assertEqual(first, second)
        self.assertEqual(
            [query.should_trigger for query in first.test], [True, True, False, False]
        )
        self.assertEqual(
            [query.should_trigger for query in first.train], [True, True, False, False]
        )
        self.assertEqual(
            {query.query for query in first.train}
            | {query.query for query in first.test},
            {query.query for query in queries},
        )
        self.assertFalse(
            {query.query for query in first.train}
            & {query.query for query in first.test}
        )

    def test_holdout_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than 0"):
            split_trigger_queries(make_queries(), holdout=0.0)

    def test_holdout_requires_two_queries_of_each_polarity(self) -> None:
        queries = (
            TriggerQuery("Only positive.", True),
            TriggerQuery("One negative.", False),
        )

        with self.assertRaisesRegex(ValueError, "at least 2"):
            split_trigger_queries(queries, holdout=0.4)

    def test_holdout_must_be_below_one(self) -> None:
        with self.assertRaisesRegex(ValueError, "holdout"):
            split_trigger_queries(make_queries(), holdout=1.0)


class DescriptionLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.queries = make_queries()
        self.split = split_trigger_queries(self.queries, holdout=0.5, seed=7)
        self.train_queries = {query.query for query in self.split.train}
        self.test_queries = {query.query for query in self.split.test}

    def outcome(self, description: str, query: str) -> bool:
        should_trigger = next(
            item.should_trigger for item in self.queries if item.query == query
        )
        if description == "Original description.":
            return not should_trigger
        if description == "Mid description.":
            return should_trigger if query in self.test_queries else not should_trigger
        if description == "Final description.":
            return should_trigger if query in self.train_queries else not should_trigger
        raise AssertionError(f"unexpected description {description!r}")

    def run_loop(self, harness: RecordingHarness, **options):
        return run_description_loop(
            harness,
            skill_name="example-skill",
            skill_content="# Example\n\nUse the example.",
            description="Original description.",
            queries=self.queries,
            model="test/model",
            max_iterations=options.pop("max_iterations", 5),
            runs_per_query=1,
            holdout=0.5,
            seed=7,
            workers=1,
            **options,
        )

    def test_best_description_is_chosen_by_test_score(self) -> None:
        harness = DescriptionLoopHarness(
            self.root,
            self.outcome,
            [tagged("Mid description."), tagged("Final description.")],
        )

        result = self.run_loop(harness)

        self.assertEqual(result["exit_reason"], "all_passed (iteration 3)")
        self.assertEqual(result["iterations_run"], 3)
        self.assertEqual(result["best_description"], "Mid description.")
        self.assertEqual(result["best_iteration"], 2)
        self.assertEqual(result["best_test_score"], "4/4")
        self.assertEqual(result["final_description"], "Final description.")
        self.assertEqual(len(result["history"]), 3)
        self.assertEqual(result["history"][1]["test_passed"], 4)
        self.assertEqual(result["history"][2]["test_passed"], 0)

    def test_improvement_prompts_receive_only_train_results(self) -> None:
        harness = DescriptionLoopHarness(
            self.root,
            self.outcome,
            [tagged("Mid description."), tagged("Final description.")],
        )

        self.run_loop(harness)

        self.assertEqual(len(harness.run_calls), 2)
        for call in harness.run_calls:
            prompt = call["prompt"]
            for query in self.test_queries:
                self.assertNotIn(query, prompt)
            self.assertIn("train", prompt.lower())
            self.assertNotIn("test_passed", prompt)
            self.assertNotIn("test_results", prompt)

    def test_optimizer_runs_have_no_tools_and_no_skills(self) -> None:
        harness = DescriptionLoopHarness(
            self.root,
            self.outcome,
            [tagged("Mid description."), tagged("Final description.")],
        )

        self.run_loop(harness)

        self.assertEqual(harness.prepare_calls, [(), ()])
        self.assertEqual(len(harness.run_calls), 2)
        for call in harness.run_calls:
            self.assertTrue(call["no_tools"])
            self.assertEqual(call["model"], "test/model")
            self.assertEqual(call["skill_ids"], ())
        self.assertTrue(all(call["description"] != "" for call in harness.probe_calls))

    def test_live_and_final_reports_are_static_html(self) -> None:
        live = self.root / "live.html"
        final = self.root / "report.html"
        harness = LiveReadingHarness(
            self.root,
            self.outcome,
            [tagged("Mid description."), tagged("Final description.")],
            live,
        )

        self.run_loop(harness, live_report_path=live, report_path=final)

        live_html = live.read_text(encoding="utf-8")
        final_html = final.read_text(encoding="utf-8")
        self.assertNotIn('http-equiv="refresh"', live_html)
        self.assertNotIn('http-equiv="refresh"', final_html)
        self.assertIn("Mid description.", live_html)
        self.assertIn("Mid description.", final_html)
        self.assertNotIn("fetch(", final_html)
        self.assertEqual(len(harness.live_snapshots), 2)
        first_snapshot = harness.live_snapshots[0]
        self.assertIn('http-equiv="refresh"', first_snapshot)
        self.assertIn("Original description.", first_snapshot)
        self.assertNotIn("Mid description.", first_snapshot)

    def test_live_report_keeps_the_best_attempt_when_the_current_is_worse(self) -> None:
        def outcome(description: str, query: str) -> bool:
            should_trigger = next(
                item.should_trigger for item in self.queries if item.query == query
            )
            if description == "Original description.":
                return not should_trigger
            return should_trigger if query in self.test_queries else not should_trigger

        live = self.root / "live.html"
        harness = LiveReadingHarness(
            self.root,
            outcome,
            [
                tagged("Mid description."),
                tagged("Final description."),
                tagged("Third description."),
            ],
            live,
        )

        result = self.run_loop(harness, live_report_path=live, max_iterations=4)

        snapshot = harness.live_snapshots[2]
        self.assertIn("<strong>Best:</strong> Mid description.", snapshot)
        self.assertIn("<strong>Last attempt:</strong> Final description.", snapshot)
        self.assertEqual(result["best_description"], "Mid description.")
        self.assertEqual(result["exit_reason"], "max_iterations (4)")

    def test_improvement_logs_are_saved(self) -> None:
        log_dir = self.root / "logs"
        harness = DescriptionLoopHarness(
            self.root,
            self.outcome,
            [tagged("Mid description."), tagged("Final description.")],
        )

        self.run_loop(harness, log_dir=log_dir)

        self.assertTrue((log_dir / "improve_iter_1.json").is_file())
        self.assertTrue((log_dir / "improve_iter_2.json").is_file())

    def test_a_failed_optimizer_keeps_the_best_attempt_and_saves_reports(self) -> None:
        live = self.root / "live.html"
        final = self.root / "report.html"
        log_dir = self.root / "logs"
        long_description = "x" * 1100
        harness = DescriptionLoopHarness(
            self.root,
            self.outcome,
            [
                tagged(long_description),
                tagged(long_description),
            ],
        )

        result = self.run_loop(
            harness,
            live_report_path=live,
            report_path=final,
            log_dir=log_dir,
        )

        self.assertTrue(result["exit_reason"].startswith("optimizer_error"))
        self.assertEqual(result["best_description"], "Original description.")
        self.assertEqual(result["iterations_run"], 1)
        self.assertTrue((log_dir / "improve_iter_1.json").is_file())
        self.assertTrue(live.is_file())
        self.assertTrue(final.is_file())
        log = json.loads((log_dir / "improve_iter_1.json").read_text(encoding="utf-8"))
        self.assertEqual(log["rewrite_description"], long_description)

    def test_an_over_long_starting_description_is_rejected(self) -> None:
        harness = DescriptionLoopHarness(self.root, self.outcome, [])

        with self.assertRaisesRegex(ValueError, "1024"):
            run_description_loop(
                harness,
                skill_name="example-skill",
                skill_content="# Example",
                description="x" * 1100,
                queries=self.queries,
                model="test/model",
                runs_per_query=1,
            )

    def test_model_is_required_for_the_loop(self) -> None:
        harness = DescriptionLoopHarness(self.root, self.outcome, [])

        with self.assertRaisesRegex(ValueError, "model"):
            run_description_loop(
                harness,
                skill_name="example-skill",
                skill_content="# Example",
                description="Original description.",
                queries=self.queries,
                model="",
                runs_per_query=1,
            )


class DescriptionLoopCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        evals = self.skill / "evals"
        evals.mkdir()
        self.eval_set = evals / "trigger_evals.json"
        self.queries = make_queries()
        self.eval_set.write_text(
            json.dumps(
                [
                    {"query": query.query, "should_trigger": query.should_trigger}
                    for query in self.queries
                ]
            ),
            encoding="utf-8",
        )
        self.split = split_trigger_queries(self.queries, holdout=0.4, seed=42)
        self.train_queries = {query.query for query in self.split.train}

    def outcome(self, description: str, query: str) -> bool:
        should_trigger = next(
            item.should_trigger for item in self.queries if item.query == query
        )
        return should_trigger if query not in self.train_queries else not should_trigger

    def test_cli_saves_results_reports_and_logs(self) -> None:
        from scripts.description_loop import main

        harness = DescriptionLoopHarness(self.root, self.outcome, [])
        results_dir = self.root / "results"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch("scripts.description_loop.get_harness", return_value=harness),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(
                [
                    "--skill-path",
                    str(self.skill),
                    "--eval-set",
                    str(self.eval_set),
                    "--model",
                    "test/model",
                    "--max-iterations",
                    "1",
                    "--runs-per-query",
                    "1",
                    "--workers",
                    "1",
                    "--results-dir",
                    str(results_dir),
                ]
            )

        self.assertEqual(status, 0)
        run_dir = next(path for path in results_dir.iterdir() if path.is_dir())
        self.assertTrue((run_dir / "results.json").is_file())
        self.assertTrue((run_dir / "report.html").is_file())
        self.assertTrue((run_dir / "live.html").is_file())
        self.assertTrue((run_dir / "logs" / "loop.log").is_file())
        document = json.loads(stdout.getvalue())
        self.assertEqual(document["model"], "test/model")
        self.assertEqual(document["iterations_run"], 1)
        self.assertEqual(
            json.loads((run_dir / "results.json").read_text(encoding="utf-8")),
            document,
        )
        self.assertIn("report:", stderr.getvalue().lower())

    def test_cli_requires_a_model(self) -> None:
        from scripts.description_loop import main

        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            main(
                [
                    "--skill-path",
                    str(self.skill),
                    "--eval-set",
                    str(self.eval_set),
                ]
            )

        self.assertEqual(raised.exception.code, 2)

    def test_cli_rejects_a_missing_skill(self) -> None:
        from scripts.description_loop import main

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = main(
                [
                    "--skill-path",
                    str(self.root / "missing"),
                    "--eval-set",
                    str(self.eval_set),
                    "--model",
                    "test/model",
                ]
            )

        self.assertEqual(status, 2)
        self.assertIn("error:", stderr.getvalue())
