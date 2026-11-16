import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts.adapters.opencode import OpenCodeHarness
from scripts.frontmatter import parse_skill_md
from scripts.harness import PreparedScope, TokenTotals

from tests.support import FakeOpenCode, fixture, write_skill


class OpenCodeScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.harness = OpenCodeHarness()

    def prepare(self, *skills: Path):
        scope = self.harness.prepare_scope(skills)
        self.addCleanup(scope.cleanup)
        return scope

    def read_config(self, scope) -> dict:
        return json.loads((scope.path / "opencode.json").read_text(encoding="utf-8"))

    def test_scope_contains_exactly_the_requested_skill(self) -> None:
        skill = write_skill(self.root, "example-skill")
        (skill / "references").mkdir()
        (skill / "references" / "notes.md").write_text("Notes.\n", encoding="utf-8")

        scope = self.prepare(skill)

        copied = scope.path / ".opencode" / "skills" / "example-skill"
        self.assertEqual(scope.skill_ids, ("example-skill",))
        self.assertEqual(
            (copied / "SKILL.md").read_text(encoding="utf-8"),
            (skill / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertTrue((copied / "references" / "notes.md").is_file())
        self.assertEqual(
            [path.name for path in (scope.path / ".opencode" / "skills").iterdir()],
            ["example-skill"],
        )

    def test_scope_config_denies_every_other_skill(self) -> None:
        first = write_skill(self.root, "first-skill")
        second = write_skill(self.root, "second-skill")

        scope = self.prepare(first, second)

        self.assertEqual(
            self.read_config(scope)["permissions"],
            [
                {"action": "skill", "resource": "*", "effect": "deny"},
                {"action": "skill", "resource": "first-skill", "effect": "allow"},
                {"action": "skill", "resource": "second-skill", "effect": "allow"},
            ],
        )

    def test_scope_with_no_skills_denies_every_skill(self) -> None:
        scope = self.prepare()

        skills_dir = scope.path / ".opencode" / "skills"
        self.assertEqual(scope.skill_ids, ())
        self.assertEqual(list(skills_dir.iterdir()), [])
        self.assertEqual(
            self.read_config(scope)["permissions"],
            [{"action": "skill", "resource": "*", "effect": "deny"}],
        )

    def test_scope_defines_a_no_tools_agent(self) -> None:
        scope = self.prepare()

        agent = self.read_config(scope)["agents"]["creating-skills-no-tools"]
        self.assertEqual(agent["mode"], "primary")
        self.assertEqual(
            agent["permissions"], [{"action": "*", "resource": "*", "effect": "deny"}]
        )

    def test_scope_is_created_outside_the_repository(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]

        scope = self.prepare()

        self.assertFalse(scope.path.is_relative_to(repo_root))

    def test_cleanup_removes_the_project(self) -> None:
        scope = self.harness.prepare_scope(())

        scope.cleanup()

        self.assertFalse(scope.path.exists())

    def test_scope_rejects_a_skill_without_skill_md(self) -> None:
        skill = self.root / "skills" / "incomplete"
        skill.mkdir(parents=True)

        with self.assertRaisesRegex(ValueError, "SKILL.md"):
            self.harness.prepare_scope([skill])

    def test_scope_rejects_duplicate_skill_ids(self) -> None:
        first = write_skill(self.root, "example-skill")
        second = write_skill(self.root / "other", "example-skill")

        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.harness.prepare_scope([first, second])


class OpenCodeRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.fake = FakeOpenCode(self.root)
        self.harness = OpenCodeHarness(command=self.fake.command())
        self.skill = write_skill(self.root, "example-skill")
        self.scope = self.harness.prepare_scope([self.skill])
        self.addCleanup(self.scope.cleanup)
        environment = mock.patch.dict(os.environ, self.fake.environment())
        environment.start()
        self.addCleanup(environment.stop)

    def test_run_normalizes_a_canned_stream(self) -> None:
        self.fake.configure(
            stdout_file=str(fixture("normalized.jsonl")),
            stderr="warning\n",
            touch=["answer.md"],
            touch_content="The answer.\n",
        )

        result = self.harness.run(self.scope, "Do the thing")

        self.assertEqual(result.assistant_text, "I will load the skill.")
        self.assertEqual(result.loaded_skill_ids, ("example-skill",))
        self.assertEqual(
            result.tokens,
            TokenTotals(input=100, output=20, reasoning=5, cache_read=7, cache_write=3),
        )
        self.assertEqual(result.tokens.total, 135)
        self.assertGreaterEqual(result.duration_ms, 0)
        self.assertEqual(result.output_files, (self.scope.path / "answer.md",))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stderr, "warning\n")
        self.assertFalse(result.timed_out)
        self.assertEqual(
            result.transcript_jsonl,
            fixture("normalized.jsonl").read_text(encoding="utf-8"),
        )
        self.assertIn("I will load the skill.", result.transcript_markdown)
        self.assertIn("example-skill", result.transcript_markdown)
        self.assertEqual(result.metrics.tool_calls, {"skill": 1})
        self.assertEqual(result.metrics.total_tool_calls, 1)
        self.assertEqual(result.metrics.total_steps, 1)
        self.assertEqual(result.metrics.files_created, ("answer.md",))
        self.assertEqual(result.metrics.errors_encountered, 0)
        self.assertEqual(result.metrics.output_chars, len("The answer.\n"))
        self.assertGreater(result.metrics.transcript_chars, 0)

    def test_run_ignores_a_failed_skill_load(self) -> None:
        event = {
            "type": "tool_use",
            "timestamp": 3,
            "sessionID": "ses_test",
            "part": {
                "type": "tool",
                "tool": "skill",
                "state": {
                    "status": "error",
                    "input": {"id": "example-skill"},
                    "error": "Unable to load skill example-skill",
                },
            },
        }
        self.fake.configure(stdout=json.dumps(event) + "\n")

        result = self.harness.run(self.scope, "Do the thing")

        self.assertEqual(result.loaded_skill_ids, ())
        self.assertEqual(result.metrics.tool_calls, {"skill": 1})
        self.assertEqual(result.metrics.errors_encountered, 1)

    def test_run_preserves_errors_and_nonzero_exit(self) -> None:
        self.fake.configure(
            stdout_file=str(fixture("error.jsonl")),
            stderr="boom\n",
            exit_code=2,
        )

        result = self.harness.run(self.scope, "Do the thing")

        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.stderr, "boom\n")
        self.assertEqual(result.assistant_text, "")
        self.assertEqual(result.metrics.errors_encountered, 2)
        self.assertEqual(result.metrics.total_steps, 1)
        self.assertIn("the run failed", result.transcript_markdown)

    def test_run_writes_artifacts_when_asked(self) -> None:
        self.fake.configure(stdout_file=str(fixture("normalized.jsonl")))
        artifacts = self.root / "artifacts"

        result = self.harness.run(self.scope, "Do the thing", artifacts_dir=artifacts)

        self.assertEqual(
            (artifacts / "transcript.jsonl").read_text(encoding="utf-8"),
            fixture("normalized.jsonl").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (artifacts / "transcript.md").read_text(encoding="utf-8"),
            result.transcript_markdown,
        )
        metrics = json.loads(
            (artifacts / "outputs" / "metrics.json").read_text(encoding="utf-8")
        )
        self.assertEqual(metrics["tool_calls"], {"skill": 1})
        self.assertEqual(metrics["total_steps"], 1)
        self.assertEqual(metrics["transcript_chars"], len(result.transcript_markdown))

    def test_run_builds_the_documented_command(self) -> None:
        self.fake.configure(stdout_file=str(fixture("normalized.jsonl")))
        input_file = self.root / "input.txt"
        input_file.write_text("Input.\n", encoding="utf-8")
        harness = OpenCodeHarness(command=self.fake.command(), standalone=True)

        with mock.patch.dict(
            os.environ,
            {
                "PWD": str(self.root),
                "OPENCODE_CONFIG_CONTENT": '{"skills": ["/somewhere"]}',
            },
        ):
            harness.run(
                self.scope,
                "Do the thing",
                model="provider/model",
                input_files=[input_file],
            )

        invocation = self.fake.invocation()
        self.assertEqual(
            invocation["argv"],
            [
                "--standalone",
                "run",
                "--format",
                "json",
                "--agent",
                "build",
                "--auto",
                "--model",
                "provider/model",
                "--file",
                str(input_file.resolve()),
            ],
        )
        self.assertEqual(invocation["stdin"], "Do the thing")
        self.assertEqual(Path(invocation["cwd"]).resolve(), self.scope.path.resolve())
        self.assertEqual(Path(invocation["pwd"]).resolve(), self.scope.path.resolve())
        self.assertIsNone(invocation["config_content"])
        self.assertEqual(invocation["skills"], ["example-skill"])

    def test_no_tools_uses_the_no_tools_agent(self) -> None:
        self.fake.configure(stdout_file=str(fixture("normalized.jsonl")))

        self.harness.run(self.scope, "Do the thing", no_tools=True)

        argv = self.fake.invocation()["argv"]
        self.assertEqual(argv[argv.index("--agent") + 1], "creating-skills-no-tools")

    def test_run_times_out(self) -> None:
        self.fake.configure(sleep=5)

        started = time.monotonic()
        result = self.harness.run(self.scope, "Do the thing", timeout_seconds=0.2)
        elapsed = time.monotonic() - started

        self.assertTrue(result.timed_out)
        self.assertLess(elapsed, 3)
        self.assertLess(result.duration_ms, 3000)
        self.assertNotEqual(result.exit_code, 0)

    def test_run_reports_a_missing_command(self) -> None:
        harness = OpenCodeHarness(command=("/nonexistent/opencode",))

        with self.assertRaisesRegex(RuntimeError, "opencode"):
            harness.run(self.scope, "Do the thing")

    def test_run_rejects_a_missing_scope(self) -> None:
        missing = PreparedScope(path=self.root / "missing")

        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.harness.run(missing, "Do the thing")


class OpenCodeTriggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.fake = FakeOpenCode(self.root)
        self.harness = OpenCodeHarness(command=self.fake.command(), temp_root=self.root)
        environment = mock.patch.dict(os.environ, self.fake.environment())
        environment.start()
        self.addCleanup(environment.stop)

    def test_probe_detects_the_candidate_skill_event(self) -> None:
        self.fake.configure(trigger="skill")

        result = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertTrue(result.triggered)
        self.assertTrue(result.candidate_skill_id.startswith("example-skill-probe-"))
        self.assertEqual(result.run.loaded_skill_ids, (result.candidate_skill_id,))
        invocation = self.fake.invocation()
        self.assertEqual(invocation["skills"], [result.candidate_skill_id])
        self.assertEqual(
            invocation["permissions"],
            [
                {"action": "skill", "resource": "*", "effect": "deny"},
                {
                    "action": "skill",
                    "resource": result.candidate_skill_id,
                    "effect": "allow",
                },
            ],
        )

    def test_probe_accepts_a_read_of_the_candidate_skill(self) -> None:
        self.fake.configure(trigger="read")

        result = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertTrue(result.triggered)

    def test_probe_stops_the_run_once_triggering_is_observed(self) -> None:
        for trigger in ("skill", "read"):
            with self.subTest(trigger=trigger):
                self.fake.configure(trigger=trigger, trigger_sleep=5)

                started = time.monotonic()
                result = self.harness.probe_trigger(
                    "example-skill", "Does example work.", "Do the thing"
                )
                elapsed = time.monotonic() - started

                self.assertTrue(result.triggered)
                self.assertLess(elapsed, 3)

    def test_probe_ignores_a_different_skill_event(self) -> None:
        self.fake.configure(trigger="skill", trigger_id="other-skill")

        result = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertFalse(result.triggered)

    def test_probe_ignores_a_failed_skill_load(self) -> None:
        for trigger in ("skill", "read"):
            with self.subTest(trigger=trigger):
                self.fake.configure(trigger=trigger, trigger_status="error")

                result = self.harness.probe_trigger(
                    "example-skill", "Does example work.", "Do the thing"
                )

                self.assertFalse(result.triggered)
                self.assertEqual(result.run.loaded_skill_ids, ())

    def test_probe_reports_no_trigger_when_only_text_appears(self) -> None:
        self.fake.configure(
            stdout=(
                '{"type":"text","timestamp":1,"sessionID":"ses_fake",'
                '"part":{"type":"text","text":"No skill here."}}\n'
            )
        )

        result = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertFalse(result.triggered)
        self.assertEqual(result.run.assistant_text, "No skill here.")

    def test_probe_ignores_a_read_outside_the_candidate_directory(self) -> None:
        self.fake.configure(trigger="read", read_path="notes/{candidate}.txt")

        result = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertFalse(result.triggered)

    def test_probe_ignores_a_sibling_directory_with_the_candidate_prefix(self) -> None:
        self.fake.configure(
            trigger="read",
            read_path=".opencode/skills/{candidate}-other/SKILL.md",
        )

        result = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertFalse(result.triggered)

    def test_probe_uses_a_unique_candidate_name(self) -> None:
        self.fake.configure(trigger="skill")

        first = self.harness.probe_trigger(
            "example-skill", "Does example work.", "First query"
        )
        second = self.harness.probe_trigger(
            "example-skill", "Does example work.", "Second query"
        )

        self.assertNotEqual(first.candidate_skill_id, second.candidate_skill_id)

    def test_probe_writes_the_description_into_the_candidate_skill(self) -> None:
        description = 'Use when: the user says "review this".'
        self.fake.configure(trigger="skill")

        self.harness.probe_trigger("example-skill", description, "Do the thing")

        skill_dir = self.root / "probe-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            self.fake.invocation()["skill_md"], encoding="utf-8"
        )
        document = parse_skill_md(skill_dir)
        self.assertEqual(document.name, "example-skill")
        self.assertEqual(document.description, description)

    def test_probe_cleans_up_its_temporary_projects(self) -> None:
        self.fake.configure(trigger="skill")

        self.harness.probe_trigger(
            "example-skill", "Does example work.", "Do the thing"
        )

        self.assertEqual(list(self.root.glob("creating-skills-*")), [])
