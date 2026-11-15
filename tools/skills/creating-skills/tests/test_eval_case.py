import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.adapters.opencode import OpenCodeHarness
from scripts.eval_case import (
    EvalCase,
    find_eval,
    load_evals,
    main,
    run_case,
)
from scripts.workspace import create_iteration

from tests.support import (
    FakeOpenCode,
    RecordingHarness,
    fixture,
    write_evals,
    write_skill,
)


class LoadEvalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")

    def test_reads_every_eval_definition(self) -> None:
        write_evals(
            self.skill,
            [
                {
                    "id": 1,
                    "prompt": "Do the first thing",
                    "expected_output": "The first answer",
                    "files": ["evals/files/input.txt"],
                    "expectations": ["The answer is correct."],
                },
                {"id": "ocean", "prompt": "Do the second thing"},
            ],
        )

        cases = load_evals(self.skill)

        self.assertEqual(
            cases,
            (
                EvalCase(
                    eval_id=1,
                    prompt="Do the first thing",
                    expected_output="The first answer",
                    files=("evals/files/input.txt",),
                    expectations=("The answer is correct.",),
                ),
                EvalCase(eval_id="ocean", prompt="Do the second thing"),
            ),
        )

    def test_rejects_a_missing_definition(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "eval definition"):
            load_evals(self.skill)

    def test_rejects_duplicate_ids(self) -> None:
        write_evals(
            self.skill,
            [
                {"id": 1, "prompt": "First"},
                {"id": 1, "prompt": "Second"},
            ],
        )

        with self.assertRaisesRegex(ValueError, "duplicate eval id"):
            load_evals(self.skill)

    def test_rejects_a_missing_prompt(self) -> None:
        write_evals(self.skill, [{"id": 1}])

        with self.assertRaisesRegex(ValueError, "prompt"):
            load_evals(self.skill)


class FindEvalTests(unittest.TestCase):
    def test_matches_a_numeric_id_from_a_string(self) -> None:
        cases = (
            EvalCase(eval_id=1, prompt="First"),
            EvalCase(eval_id=2, prompt="Second"),
        )

        self.assertEqual(find_eval(cases, "2"), cases[1])

    def test_reports_the_available_ids(self) -> None:
        cases = (EvalCase(eval_id=1, prompt="First"),)

        with self.assertRaisesRegex(ValueError, "available: 1"):
            find_eval(cases, 9)


class RunCaseSetup(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        write_evals(
            self.skill,
            [
                {
                    "id": 1,
                    "prompt": "Do the thing",
                    "expected_output": "The thing is done",
                }
            ],
        )
        self.case = load_evals(self.skill)[0]
        self.harness = RecordingHarness(self.root)


class RunCaseLayoutTests(RunCaseSetup):
    def test_one_case_creates_the_canonical_layout(self) -> None:
        run = run_case(self.harness, self.skill, self.case, "with_skill")

        workspace = self.skill.parent / "example-skill-workspace"
        self.assertEqual(run.run_id, "eval-1-with_skill")
        self.assertEqual(run.iteration_dir, workspace / "iteration-1")
        self.assertEqual(run.eval_dir, workspace / "iteration-1" / "eval-1")
        self.assertEqual(run.arm_dir, run.eval_dir / "with_skill")
        self.assertEqual(
            {path.name for path in run.eval_dir.iterdir()},
            {"eval_metadata.json", "with_skill"},
        )
        self.assertEqual(
            {path.name for path in run.arm_dir.iterdir()},
            {
                "outputs",
                "transcript.jsonl",
                "transcript.md",
                "timing.json",
                "run.json",
            },
        )
        self.assertEqual(
            json.loads(
                (run.eval_dir / "eval_metadata.json").read_text(encoding="utf-8")
            ),
            {
                "eval_id": 1,
                "eval_name": "eval-1",
                "prompt": "Do the thing",
                "expected_output": "The thing is done",
                "expectations": [],
            },
        )
        self.assertEqual(
            json.loads((run.arm_dir / "timing.json").read_text(encoding="utf-8")),
            {
                "total_tokens": 135,
                "duration_ms": 1500,
                "total_duration_seconds": 1.5,
            },
        )
        run_document = json.loads(
            (run.arm_dir / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(run_document["run_id"], "eval-1-with_skill")
        self.assertEqual(run_document["loaded_skill_ids"], ["example-skill"])
        self.assertEqual(run_document["output_files"], ["answer.md"])
        self.assertEqual(
            (run.arm_dir / "outputs" / "answer.md").read_text(encoding="utf-8"),
            "The answer.\n",
        )
        self.assertEqual(
            run.result.output_files,
            (run.arm_dir / "outputs" / "answer.md",),
        )
        self.assertTrue((run.arm_dir / "outputs" / "metrics.json").is_file())

    def test_workspace_override_relocates_the_run(self) -> None:
        override = self.root / "elsewhere"

        run = run_case(
            self.harness,
            self.skill,
            self.case,
            "with_skill",
            workspace=override,
        )

        self.assertEqual(run.iteration_dir, override / "iteration-1")
        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())

    def test_new_invocations_get_a_new_iteration(self) -> None:
        first = run_case(self.harness, self.skill, self.case, "with_skill")
        second = run_case(self.harness, self.skill, self.case, "with_skill")

        self.assertEqual(first.iteration_dir.name, "iteration-1")
        self.assertEqual(second.iteration_dir.name, "iteration-2")
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.run_id, "eval-1-with_skill")

    def test_explicit_iteration_runs_both_arms_in_one_eval_directory(
        self,
    ) -> None:
        workspace = self.root / "workspace"
        iteration = create_iteration(workspace)

        with_skill = run_case(
            self.harness,
            self.skill,
            self.case,
            "with_skill",
            iteration_dir=iteration,
        )
        without_skill = run_case(
            self.harness,
            self.skill,
            self.case,
            "without_skill",
            iteration_dir=iteration,
        )

        self.assertEqual(with_skill.eval_dir, without_skill.eval_dir)
        self.assertEqual(
            {path.name for path in with_skill.eval_dir.iterdir()},
            {"eval_metadata.json", "with_skill", "without_skill"},
        )
        self.assertEqual(with_skill.run_id, "eval-1-with_skill")
        self.assertEqual(without_skill.run_id, "eval-1-without_skill")

    def test_without_skill_uses_an_empty_scope(self) -> None:
        run = run_case(self.harness, self.skill, self.case, "without_skill")

        self.assertEqual(self.harness.prepare_calls[-1], ())
        document = json.loads((run.arm_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(document["loaded_skill_ids"], [])

    def test_old_skill_uses_the_baseline_scope(self) -> None:
        baseline = write_skill(self.root / "snapshots", "old-skill")

        run = run_case(
            self.harness,
            self.skill,
            self.case,
            "old_skill",
            baseline_skill=baseline,
        )

        self.assertEqual(self.harness.prepare_calls[-1], (baseline.resolve(),))
        self.assertEqual(run.run_id, "eval-1-old_skill")

    def test_old_skill_requires_a_baseline(self) -> None:
        with self.assertRaisesRegex(ValueError, "baseline skill"):
            run_case(self.harness, self.skill, self.case, "old_skill")

    def test_unknown_arm_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown arm"):
            run_case(self.harness, self.skill, self.case, "both")

    def test_inputs_are_staged_and_preserved(self) -> None:
        source = self.skill / "evals" / "files" / "input.txt"
        source.parent.mkdir(parents=True)
        source.write_text("Input.\n", encoding="utf-8")
        case = EvalCase(
            eval_id=1,
            prompt="Do the thing",
            files=("evals/files/input.txt",),
        )

        run = run_case(self.harness, self.skill, case, "with_skill")

        preserved = run.eval_dir / "inputs" / "evals" / "files" / "input.txt"
        self.assertEqual(preserved.read_text(encoding="utf-8"), "Input.\n")
        call = self.harness.run_calls[-1]
        staged = call["input_files"]
        self.assertEqual(len(staged), 1)
        self.assertEqual(staged[0].name, "input.txt")
        self.assertEqual(self.harness.scope_files["evals/files/input.txt"], "Input.\n")

    def test_preserved_inputs_are_not_replaced_by_a_later_arm(self) -> None:
        source = self.skill / "evals" / "files" / "input.txt"
        source.parent.mkdir(parents=True)
        source.write_text("First.\n", encoding="utf-8")
        case = EvalCase(
            eval_id=1,
            prompt="Do the thing",
            files=("evals/files/input.txt",),
        )
        first = run_case(self.harness, self.skill, case, "with_skill")

        source.write_text("Changed.\n", encoding="utf-8")
        run_case(
            self.harness,
            self.skill,
            case,
            "without_skill",
            iteration_dir=first.iteration_dir,
        )

        preserved = first.eval_dir / "inputs" / "evals" / "files" / "input.txt"
        self.assertEqual(preserved.read_text(encoding="utf-8"), "First.\n")
        self.assertEqual(self.harness.scope_files["evals/files/input.txt"], "First.\n")

    def test_invalid_input_does_not_consume_an_iteration(self) -> None:
        case = EvalCase(
            eval_id=1,
            prompt="Do the thing",
            files=("evals/files/missing.txt",),
        )

        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            run_case(self.harness, self.skill, case, "with_skill")

        workspace = self.skill.parent / "example-skill-workspace"
        self.assertFalse(workspace.exists())

    def test_failed_run_still_saves_artifacts(self) -> None:
        harness = RecordingHarness(
            self.root, exit_code=2, stderr="boom\n", timed_out=True
        )

        run = run_case(harness, self.skill, self.case, "with_skill")

        document = json.loads((run.arm_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(document["exit_code"], 2)
        self.assertEqual(document["stderr"], "boom\n")
        self.assertTrue(document["timed_out"])
        self.assertTrue((run.arm_dir / "timing.json").is_file())

    def test_metadata_edits_survive_a_rerun(self) -> None:
        run = run_case(self.harness, self.skill, self.case, "with_skill")
        metadata_path = run.eval_dir / "eval_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["expectations"] = ["The answer is correct."]
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        run_case(
            self.harness,
            self.skill,
            self.case,
            "without_skill",
            iteration_dir=run.iteration_dir,
        )

        self.assertEqual(
            json.loads(metadata_path.read_text(encoding="utf-8"))["expectations"],
            ["The answer is correct."],
        )


class CliTests(RunCaseSetup):
    def test_cli_runs_one_case(self) -> None:
        stdout = io.StringIO()
        with (
            mock.patch("scripts.eval_case.get_harness", return_value=self.harness),
            contextlib.redirect_stdout(stdout),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--eval-id",
                    "1",
                    "--arm",
                    "with_skill",
                    "--workspace",
                    str(self.root / "cli-workspace"),
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn("eval-1-with_skill", stdout.getvalue())
        self.assertTrue(
            (
                self.root
                / "cli-workspace"
                / "iteration-1"
                / "eval-1"
                / "with_skill"
                / "run.json"
            ).is_file()
        )

    def test_cli_reports_a_missing_eval(self) -> None:
        stderr = io.StringIO()
        with (
            mock.patch("scripts.eval_case.get_harness", return_value=self.harness),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--eval-id",
                    "9",
                    "--arm",
                    "with_skill",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn("available: 1", stderr.getvalue())

    def test_cli_reuses_an_existing_iteration(self) -> None:
        workspace = self.root / "cli-workspace"
        create_iteration(workspace)

        with (
            mock.patch("scripts.eval_case.get_harness", return_value=self.harness),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--eval-id",
                    "1",
                    "--arm",
                    "without_skill",
                    "--workspace",
                    str(workspace),
                    "--iteration",
                    "1",
                ]
            )

        self.assertEqual(status, 0)
        self.assertTrue(
            (
                workspace / "iteration-1" / "eval-1" / "without_skill" / "run.json"
            ).is_file()
        )

    def test_cli_rejects_a_missing_iteration(self) -> None:
        stderr = io.StringIO()
        with (
            mock.patch("scripts.eval_case.get_harness", return_value=self.harness),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--eval-id",
                    "1",
                    "--arm",
                    "with_skill",
                    "--workspace",
                    str(self.root / "cli-workspace"),
                    "--iteration",
                    "2",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn("does not exist", stderr.getvalue())


class OpenCodeRunCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.fake = FakeOpenCode(self.root)
        self.harness = OpenCodeHarness(command=self.fake.command(), temp_root=self.root)
        self.skill = write_skill(self.root, "example-skill")
        write_evals(
            self.skill,
            [
                {
                    "id": 1,
                    "prompt": "Do the thing",
                    "expected_output": "The thing is done",
                    "files": ["evals/files/input.txt"],
                }
            ],
        )
        input_file = self.skill / "evals" / "files" / "input.txt"
        input_file.parent.mkdir(parents=True)
        input_file.write_text("Input.\n", encoding="utf-8")
        self.case = load_evals(self.skill)[0]
        environment = mock.patch.dict(os.environ, self.fake.environment())
        environment.start()
        self.addCleanup(environment.stop)

    def test_run_case_saves_the_adapter_artifacts(self) -> None:
        self.fake.configure(
            stdout_file=str(fixture("normalized.jsonl")),
            touch=["answer.md"],
            touch_content="The answer.\n",
        )

        run = run_case(self.harness, self.skill, self.case, "with_skill")

        self.assertEqual(run.run_id, "eval-1-with_skill")
        self.assertEqual(
            (run.arm_dir / "transcript.jsonl").read_text(encoding="utf-8"),
            fixture("normalized.jsonl").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "I will load the skill.",
            (run.arm_dir / "transcript.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            json.loads((run.arm_dir / "timing.json").read_text(encoding="utf-8")),
            {
                "total_tokens": 135,
                "duration_ms": run.timing.duration_ms,
                "total_duration_seconds": round(run.timing.duration_ms / 1000, 3),
            },
        )
        document = json.loads((run.arm_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(document["loaded_skill_ids"], ["example-skill"])
        self.assertEqual(document["output_files"], ["answer.md"])
        self.assertEqual(document["metrics"]["tool_calls"], {"skill": 1})
        self.assertEqual(
            (run.arm_dir / "outputs" / "answer.md").read_text(encoding="utf-8"),
            "The answer.\n",
        )
        self.assertEqual(
            (run.eval_dir / "inputs" / "evals" / "files" / "input.txt").read_text(
                encoding="utf-8"
            ),
            "Input.\n",
        )

        invocation = self.fake.invocation()
        self.assertEqual(invocation["skills"], ["example-skill"])
        attached = invocation["files"]
        self.assertEqual(len(attached), 1)
        path, content = next(iter(attached.items()))
        self.assertTrue(path.endswith("evals/files/input.txt"))
        self.assertEqual(content, "Input.\n")
        self.assertEqual(list(self.root.glob("creating-skills-scope-*")), [])

    def test_without_skill_denies_every_skill(self) -> None:
        self.fake.configure(stdout_file=str(fixture("normalized.jsonl")))

        run_case(self.harness, self.skill, self.case, "without_skill")

        invocation = self.fake.invocation()
        self.assertEqual(invocation["skills"], [])
        self.assertEqual(
            invocation["permissions"],
            [{"action": "skill", "resource": "*", "effect": "deny"}],
        )

    def test_old_skill_denies_every_other_skill(self) -> None:
        baseline = self.root / "snapshots" / "example-skill"
        baseline.parent.mkdir(parents=True)
        shutil.copytree(self.skill, baseline)
        self.fake.configure(stdout_file=str(fixture("normalized.jsonl")))

        run_case(
            self.harness,
            self.skill,
            self.case,
            "old_skill",
            baseline_skill=baseline,
        )

        invocation = self.fake.invocation()
        self.assertEqual(invocation["skills"], ["example-skill"])
        self.assertEqual(
            invocation["permissions"],
            [
                {"action": "skill", "resource": "*", "effect": "deny"},
                {"action": "skill", "resource": "example-skill", "effect": "allow"},
            ],
        )
