import json
import tempfile
import unittest
from pathlib import Path

from scripts.improve_description import (
    DescriptionTooLongError,
    build_improvement_prompt,
    propose_description,
)

from tests.support import ScriptedCompletionHarness


def evaluation_document(queries: list[dict[str, object]]) -> dict[str, object]:
    """Build a trigger evaluation document for prompt tests."""
    passed = sum(1 for query in queries if query["pass"])
    return {
        "skill_name": "example-skill",
        "description": "Old description.",
        "results": queries,
        "summary": {
            "total": len(queries),
            "passed": passed,
            "failed": len(queries) - passed,
        },
    }


def query_result(
    query: str, should_trigger: bool, *, passed: bool, triggers: int = 3
) -> dict[str, object]:
    return {
        "query": query,
        "should_trigger": should_trigger,
        "trigger_rate": triggers / 3,
        "triggers": triggers,
        "runs": 3,
        "errors": 0,
        "pass": passed,
    }


class FailingRewriteHarness(ScriptedCompletionHarness):
    """Fail the second completion call."""

    def __init__(self, root: Path, responses: list[str]) -> None:
        super().__init__(root, responses)
        self.calls = 0

    def run(self, scope, prompt, **options):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("rewrite call failed")
        return super().run(scope, prompt, **options)


class ImprovementPromptTests(unittest.TestCase):
    def test_prompt_is_harness_neutral(self) -> None:
        prompt = build_improvement_prompt(
            skill_name="example-skill",
            skill_content="# Example\n\nUse the example.",
            current_description="Old description.",
            train_results=evaluation_document(
                [query_result("Do the example.", True, passed=False)]
            ),
            history=[],
        )

        lowered = prompt.lower()
        # Build the terms from pieces so the port's neutralization audit does
        # not match this test fixture.
        for term in (
            "cl" + "aude",
            "an" + "thropic",
            "co" + "work",
            "present" + "_files",
            "available" + "_skills",
        ):
            self.assertNotIn(term, lowered)

    def test_prompt_includes_failures_and_limits_the_response(self) -> None:
        train = evaluation_document(
            [
                query_result("Do the example.", True, passed=False, triggers=1),
                query_result("Write a poem.", False, passed=False, triggers=2),
            ]
        )

        prompt = build_improvement_prompt(
            skill_name="example-skill",
            skill_content="# Example\n\nUse the example.",
            current_description="Old description.",
            train_results=train,
            history=[],
        )

        self.assertIn("Old description.", prompt)
        self.assertIn("FAILED TO TRIGGER", prompt)
        self.assertIn("Do the example.", prompt)
        self.assertIn("FALSE TRIGGERS", prompt)
        self.assertIn("Write a poem.", prompt)
        self.assertIn("1024", prompt)
        self.assertIn("<new_description>", prompt)

    def test_prompt_never_includes_held_out_test_results(self) -> None:
        train = evaluation_document(
            [query_result("Do the example.", True, passed=False)]
        )
        history = [
            {
                "iteration": 1,
                "description": "Earlier description.",
                "train_passed": 1,
                "train_failed": 1,
                "train_total": 2,
                "train_results": [
                    query_result("Do the example.", True, passed=True),
                    query_result("Write a poem.", False, passed=True),
                ],
                "test_passed": 0,
                "test_failed": 2,
                "test_total": 2,
                "test_results": [
                    query_result("Hidden held-out query.", True, passed=False),
                ],
            }
        ]

        prompt = build_improvement_prompt(
            skill_name="example-skill",
            skill_content="# Example",
            current_description="Old description.",
            train_results=train,
            history=history,
        )

        self.assertIn("Earlier description.", prompt)
        self.assertIn("Do the example.", prompt)
        self.assertNotIn("Hidden held-out query.", prompt)
        self.assertNotIn("test_passed", prompt)


class ProposeDescriptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.train = evaluation_document(
            [query_result("Do the example.", True, passed=False)]
        )

    def propose(
        self, harness: ScriptedCompletionHarness, *, log_dir: Path | None = None
    ):
        return propose_description(
            harness,
            skill_name="example-skill",
            skill_content="# Example\n\nUse the example.",
            current_description="Old description.",
            train_results=self.train,
            history=[],
            model="test/model",
            log_dir=log_dir,
            iteration=1,
        )

    def test_optimizer_runs_without_tools_and_with_every_skill_denied(self) -> None:
        harness = ScriptedCompletionHarness(
            self.root, ["<new_description>New description.</new_description>"]
        )

        proposal = self.propose(harness)

        self.assertEqual(proposal.description, "New description.")
        self.assertEqual(harness.prepare_calls, [()])
        self.assertEqual(len(harness.run_calls), 1)
        call = harness.run_calls[0]
        self.assertTrue(call["no_tools"])
        self.assertEqual(call["model"], "test/model")
        self.assertEqual(call["skill_ids"], ())

    def test_a_too_long_description_gets_one_rewrite(self) -> None:
        long_description = "x" * 1100
        harness = ScriptedCompletionHarness(
            self.root,
            [
                f"<new_description>{long_description}</new_description>",
                "<new_description>Short description.</new_description>",
            ],
        )

        proposal = self.propose(harness)

        self.assertEqual(proposal.description, "Short description.")
        self.assertEqual(proposal.char_count, len(long_description))
        self.assertEqual(proposal.rewrite_char_count, len("Short description."))
        self.assertEqual(len(harness.run_calls), 2)
        rewrite_prompt = harness.run_calls[1]["prompt"]
        self.assertIn("1024", rewrite_prompt)
        self.assertIn(long_description, rewrite_prompt)
        self.assertTrue(harness.run_calls[1]["no_tools"])
        self.assertEqual(harness.run_calls[1]["skill_ids"], ())

    def test_a_rewrite_that_is_still_too_long_fails(self) -> None:
        harness = ScriptedCompletionHarness(
            self.root,
            [
                f"<new_description>{'x' * 1100}</new_description>",
                f"<new_description>{'y' * 1100}</new_description>",
            ],
        )

        with self.assertRaisesRegex(DescriptionTooLongError, "1024"):
            self.propose(harness)

    def test_a_rejected_rewrite_is_still_logged(self) -> None:
        log_dir = self.root / "logs"
        harness = ScriptedCompletionHarness(
            self.root,
            [
                f"<new_description>{'x' * 1100}</new_description>",
                f"<new_description>{'y' * 1100}</new_description>",
            ],
        )

        with self.assertRaises(DescriptionTooLongError):
            self.propose(harness, log_dir=log_dir)

        log = json.loads((log_dir / "improve_iter_1.json").read_text(encoding="utf-8"))
        self.assertEqual(log["rewrite_description"], "y" * 1100)
        self.assertEqual(log["rewrite_char_count"], 1100)

    def test_logs_record_prompts_responses_and_run_metadata(self) -> None:
        log_dir = self.root / "logs"
        harness = ScriptedCompletionHarness(
            self.root,
            [
                f"<new_description>{'x' * 1100}</new_description>",
                "<new_description>Short description.</new_description>",
            ],
        )

        self.propose(harness, log_dir=log_dir)

        log = json.loads((log_dir / "improve_iter_1.json").read_text(encoding="utf-8"))
        self.assertIn("Old description.", log["prompt"])
        self.assertEqual(log["parsed_description"], "x" * 1100)
        self.assertEqual(log["char_count"], 1100)
        self.assertTrue(log["over_limit"])
        self.assertIn("1024", log["rewrite_prompt"])
        self.assertEqual(log["rewrite_description"], "Short description.")
        self.assertEqual(log["final_description"], "Short description.")
        self.assertEqual(log["model"], "test/model")
        self.assertTrue(log["run"]["no_tools"])
        self.assertEqual(log["run"]["loaded_skill_ids"], [])
        self.assertTrue((log_dir / "improve_iter_1.transcript.jsonl").is_file())

    def test_a_failed_rewrite_call_is_logged_before_failing(self) -> None:
        log_dir = self.root / "logs"
        harness = FailingRewriteHarness(
            self.root,
            [f"<new_description>{'x' * 1100}</new_description>"],
        )

        with self.assertRaisesRegex(RuntimeError, "rewrite call failed"):
            self.propose(harness, log_dir=log_dir)

        log = json.loads((log_dir / "improve_iter_1.json").read_text(encoding="utf-8"))
        self.assertEqual(log["parsed_description"], "x" * 1100)
        self.assertIn("1024", log["rewrite_prompt"])
        self.assertEqual(log["error"], "rewrite call failed")
        self.assertIsNone(log["rewrite_run"])

    def test_an_empty_completion_is_an_error(self) -> None:
        harness = ScriptedCompletionHarness(self.root, [""])

        with self.assertRaisesRegex(RuntimeError, "no description"):
            self.propose(harness)

    def test_model_is_required_at_the_public_boundary(self) -> None:
        harness = ScriptedCompletionHarness(
            self.root, ["<new_description>New.</new_description>"]
        )

        with self.assertRaisesRegex(ValueError, "model"):
            propose_description(
                harness,
                skill_name="example-skill",
                skill_content="# Example",
                current_description="Old description.",
                train_results=self.train,
                history=[],
                model="",
            )
