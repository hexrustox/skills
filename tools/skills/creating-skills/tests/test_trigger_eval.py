import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.adapters.opencode import OpenCodeHarness
from scripts.trigger_eval import (
    TriggerQuery,
    evaluate_trigger,
    load_trigger_queries,
    main,
)

from tests.support import (
    BarrierTriggerHarness,
    CannedTriggerHarness,
    FakeOpenCode,
    write_skill,
)


class TriggerQueryLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.path = self.root / "trigger_evals.json"

    def write(self, data: object) -> None:
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_loads_both_polarities_in_order(self) -> None:
        self.write(
            [
                {"query": "Summarize this invoice.", "should_trigger": True},
                {"query": "Write a poem about summer.", "should_trigger": False},
            ]
        )

        queries = load_trigger_queries(self.path)

        self.assertEqual(
            queries,
            (
                TriggerQuery("Summarize this invoice.", True),
                TriggerQuery("Write a poem about summer.", False),
            ),
        )

    def test_rejects_an_empty_set(self) -> None:
        self.write([])

        with self.assertRaisesRegex(ValueError, "no queries"):
            load_trigger_queries(self.path)

    def test_rejects_a_non_list_document(self) -> None:
        self.write({"queries": []})

        with self.assertRaisesRegex(TypeError, "JSON array"):
            load_trigger_queries(self.path)

    def test_rejects_a_missing_query(self) -> None:
        self.write([{"should_trigger": True}])

        with self.assertRaisesRegex(ValueError, "non-empty 'query'"):
            load_trigger_queries(self.path)

    def test_rejects_a_non_boolean_polarity(self) -> None:
        self.write([{"query": "Do the thing", "should_trigger": "yes"}])

        with self.assertRaisesRegex(TypeError, "'should_trigger'"):
            load_trigger_queries(self.path)

    def test_rejects_duplicate_queries(self) -> None:
        self.write(
            [
                {"query": "Do the thing", "should_trigger": True},
                {"query": "Do the thing", "should_trigger": False},
            ]
        )

        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_trigger_queries(self.path)


class TriggerEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.queries = (
            TriggerQuery("Summarize this invoice.", True),
            TriggerQuery("Write a poem about summer.", False),
            TriggerQuery("Extract the tables.", True),
            TriggerQuery("Explain this PDF watermark.", False),
        )
        self.harness = CannedTriggerHarness(
            self.root,
            {
                "Summarize this invoice.": [True, True, False],
                "Write a poem about summer.": [False, True, False],
                "Extract the tables.": [True, False, False],
                "Explain this PDF watermark.": [True, False, True],
            },
        )

    def test_reports_trigger_rates_and_pass_fail_per_query(self) -> None:
        evaluation = evaluate_trigger(
            self.harness,
            "example-skill",
            "Does example work.",
            self.queries,
        )

        results = evaluation.results
        self.assertEqual(
            [result.query for result in results],
            [query.query for query in self.queries],
        )
        self.assertEqual(
            [result.should_trigger for result in results], [True, False, True, False]
        )
        self.assertEqual([result.triggers for result in results], [2, 1, 1, 2])
        self.assertEqual([result.runs for result in results], [3, 3, 3, 3])
        self.assertEqual([result.errors for result in results], [0, 0, 0, 0])
        self.assertAlmostEqual(results[0].trigger_rate, 2 / 3)
        self.assertAlmostEqual(results[1].trigger_rate, 1 / 3)
        self.assertEqual(
            [result.passed for result in results], [True, True, False, False]
        )
        self.assertEqual(evaluation.summary.total, 4)
        self.assertEqual(evaluation.summary.passed, 2)
        self.assertEqual(evaluation.summary.failed, 2)

    def test_runs_every_query_multiple_times(self) -> None:
        evaluate_trigger(
            self.harness,
            "example-skill",
            "Does example work.",
            self.queries,
            runs_per_query=4,
        )

        counts = {
            query: sum(1 for call in self.harness.probe_calls if call["query"] == query)
            for query in (item.query for item in self.queries)
        }
        self.assertEqual(set(counts.values()), {4})
        self.assertTrue(
            all(
                call["skill_name"] == "example-skill"
                and call["description"] == "Does example work."
                for call in self.harness.probe_calls
            )
        )

    def test_probes_run_in_parallel(self) -> None:
        harness = BarrierTriggerHarness(self.root, parties=6)

        evaluate_trigger(
            harness,
            "example-skill",
            "Does example work.",
            self.queries[:2],
            runs_per_query=3,
            workers=6,
        )

        self.assertEqual(len(harness.thread_ids), 6)

    def test_a_failed_probe_counts_as_no_trigger_and_fails_the_query(self) -> None:
        harness = CannedTriggerHarness(
            self.root,
            {"Summarize this invoice.": [None, True, True]},
        )
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            evaluation = evaluate_trigger(
                harness,
                "example-skill",
                "Does example work.",
                (TriggerQuery("Summarize this invoice.", True),),
            )

        result = evaluation.results[0]
        self.assertEqual(result.triggers, 2)
        self.assertEqual(result.errors, 1)
        self.assertFalse(result.passed)
        self.assertEqual(evaluation.summary.failed, 1)
        self.assertIn("probe failed", stderr.getvalue())

    def test_a_failed_probe_cannot_pass_a_should_not_trigger_query(self) -> None:
        harness = CannedTriggerHarness(
            self.root,
            {"Explain this PDF watermark.": [None, None, None]},
        )

        with contextlib.redirect_stderr(io.StringIO()):
            evaluation = evaluate_trigger(
                harness,
                "example-skill",
                "Does example work.",
                (TriggerQuery("Explain this PDF watermark.", False),),
            )

        result = evaluation.results[0]
        self.assertEqual(result.triggers, 0)
        self.assertEqual(result.errors, 3)
        self.assertFalse(result.passed)

    def test_threshold_decides_pass_for_a_partial_rate(self) -> None:
        outcomes = {"Summarize this invoice.": [True, True, False]}

        strict = evaluate_trigger(
            CannedTriggerHarness(self.root, outcomes),
            "example-skill",
            "Does example work.",
            (TriggerQuery("Summarize this invoice.", True),),
            trigger_threshold=0.9,
        )
        lenient = evaluate_trigger(
            CannedTriggerHarness(self.root, outcomes),
            "example-skill",
            "Does example work.",
            (TriggerQuery("Summarize this invoice.", True),),
            trigger_threshold=0.5,
        )

        self.assertFalse(strict.results[0].passed)
        self.assertTrue(lenient.results[0].passed)

    def test_rejects_an_empty_query_set(self) -> None:
        with self.assertRaisesRegex(ValueError, "no queries"):
            evaluate_trigger(self.harness, "example-skill", "Does example work.", ())

    def test_rejects_a_non_positive_run_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "runs_per_query"):
            evaluate_trigger(
                self.harness,
                "example-skill",
                "Does example work.",
                self.queries,
                runs_per_query=0,
            )

    def test_rejects_an_out_of_range_threshold(self) -> None:
        with self.assertRaisesRegex(ValueError, "trigger_threshold"):
            evaluate_trigger(
                self.harness,
                "example-skill",
                "Does example work.",
                self.queries,
                trigger_threshold=1.5,
            )

    def test_document_uses_the_stable_json_contract(self) -> None:
        evaluation = evaluate_trigger(
            self.harness,
            "example-skill",
            "Does example work.",
            self.queries,
        )

        document = evaluation.as_dict()

        self.assertEqual(document["skill_name"], "example-skill")
        self.assertEqual(document["description"], "Does example work.")
        self.assertEqual(
            document["results"][0],
            {
                "query": "Summarize this invoice.",
                "should_trigger": True,
                "trigger_rate": 2 / 3,
                "triggers": 2,
                "runs": 3,
                "errors": 0,
                "pass": True,
            },
        )
        self.assertEqual(document["summary"], {"total": 4, "passed": 2, "failed": 2})


class TriggerEvaluationAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.fake = FakeOpenCode(self.root)
        self.harness = OpenCodeHarness(command=self.fake.command(), temp_root=self.root)
        environment = mock.patch.dict(os.environ, self.fake.environment())
        environment.start()
        self.addCleanup(environment.stop)

    def test_evaluation_uses_canned_probe_streams_from_the_adapter(self) -> None:
        self.fake.configure(trigger="skill")

        evaluation = evaluate_trigger(
            self.harness,
            "example-skill",
            "Does example work.",
            (
                TriggerQuery("Summarize this invoice.", True),
                TriggerQuery("Write a poem about summer.", False),
            ),
            runs_per_query=2,
            workers=1,
        )

        self.assertEqual([result.triggers for result in evaluation.results], [2, 2])
        self.assertEqual([result.errors for result in evaluation.results], [0, 0])
        self.assertEqual(
            [result.passed for result in evaluation.results], [True, False]
        )


class TriggerEvaluationCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        self.eval_set = self.root / "trigger_evals.json"
        self.eval_set.write_text(
            json.dumps(
                [
                    {"query": "Summarize this invoice.", "should_trigger": True},
                    {"query": "Write a poem about summer.", "should_trigger": False},
                ]
            ),
            encoding="utf-8",
        )
        self.harness = CannedTriggerHarness(
            self.root,
            {
                "Summarize this invoice.": [True, True, True],
                "Write a poem about summer.": [False, False, False],
            },
        )

    def run_cli(
        self, *arguments: str, harness: CannedTriggerHarness | None = None
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch(
                "scripts.trigger_eval.get_harness",
                return_value=harness or self.harness,
            ),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(list(arguments))
        return status, stdout.getvalue(), stderr.getvalue()

    def test_cli_prints_the_evaluation_document(self) -> None:
        status, stdout, stderr = self.run_cli(
            "--skill", str(self.skill), "--eval-set", str(self.eval_set)
        )

        document = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(document["summary"], {"total": 2, "passed": 2, "failed": 0})
        self.assertIn("PASS\t3/3\tSummarize this invoice.", stderr)
        self.assertIn("PASS\t0/3\tWrite a poem about summer.", stderr)
        self.assertTrue(
            all(
                call["description"] == "Does example-skill work."
                for call in self.harness.probe_calls
            )
        )

    def test_cli_returns_one_when_a_query_fails(self) -> None:
        harness = CannedTriggerHarness(
            self.root,
            {"Summarize this invoice.": [False, False, False]},
        )

        status, stdout, stderr = self.run_cli(
            "--skill",
            str(self.skill),
            "--eval-set",
            str(self.eval_set),
            harness=harness,
        )

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["summary"]["failed"], 1)
        self.assertIn("FAIL\t0/3\tSummarize this invoice.", stderr)

    def test_cli_writes_the_document_to_an_output_file(self) -> None:
        output = self.root / "results" / "trigger_eval.json"

        status, stdout, _stderr = self.run_cli(
            "--skill",
            str(self.skill),
            "--eval-set",
            str(self.eval_set),
            "--output",
            str(output),
        )

        self.assertEqual(status, 0)
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8")), json.loads(stdout)
        )

    def test_cli_accepts_a_description_override(self) -> None:
        status, _stdout, _stderr = self.run_cli(
            "--skill",
            str(self.skill),
            "--eval-set",
            str(self.eval_set),
            "--description",
            "Custom trigger.",
        )

        self.assertEqual(status, 0)
        self.assertTrue(
            all(
                call["description"] == "Custom trigger."
                for call in self.harness.probe_calls
            )
        )

    def test_cli_rejects_a_bad_eval_set(self) -> None:
        self.eval_set.write_text(
            json.dumps([{"query": "Do the thing"}]), encoding="utf-8"
        )

        status, _stdout, stderr = self.run_cli(
            "--skill", str(self.skill), "--eval-set", str(self.eval_set)
        )

        self.assertEqual(status, 2)
        self.assertIn("should_trigger", stderr)

    def test_cli_rejects_a_missing_skill(self) -> None:
        status, _stdout, stderr = self.run_cli(
            "--skill", str(self.root / "missing"), "--eval-set", str(self.eval_set)
        )

        self.assertEqual(status, 2)
        self.assertIn("error:", stderr)
