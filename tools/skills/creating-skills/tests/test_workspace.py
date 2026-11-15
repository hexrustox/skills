import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness import PreparedScope
from scripts.workspace import (
    create_iteration,
    default_workspace,
    eval_directory,
    preserve_inputs,
    resolve_inputs,
    resolve_workspace,
    run_id,
    stage_inputs,
    write_eval_metadata,
    write_run_artifacts,
)

from tests.support import canned_run_result, write_skill


class WorkspacePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)

    def test_default_workspace_is_a_sibling_of_the_skill(self) -> None:
        skill = write_skill(self.root, "example-skill")

        workspace = default_workspace(skill)

        self.assertEqual(workspace, skill.parent / "example-skill-workspace")

    def test_resolve_workspace_uses_an_explicit_override(self) -> None:
        skill = write_skill(self.root, "example-skill")
        override = self.root / "elsewhere"

        workspace = resolve_workspace(skill, override)

        self.assertEqual(workspace, override.resolve())

    def test_resolve_workspace_defaults_beside_the_skill(self) -> None:
        skill = write_skill(self.root, "example-skill")

        workspace = resolve_workspace(skill)

        self.assertEqual(workspace, default_workspace(skill))


class WorkspaceLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.workspace = self.root / "example-skill-workspace"

    def test_first_iteration_is_number_one(self) -> None:
        iteration = create_iteration(self.workspace)

        self.assertEqual(iteration, self.workspace / "iteration-1")
        self.assertTrue(iteration.is_dir())

    def test_iterations_increment_from_the_highest_existing_number(self) -> None:
        (self.workspace / "iteration-1").mkdir(parents=True)
        (self.workspace / "iteration-3").mkdir()
        (self.workspace / "iteration-notes").mkdir()

        iteration = create_iteration(self.workspace)

        self.assertEqual(iteration, self.workspace / "iteration-4")

    def test_eval_directory_uses_the_eval_id(self) -> None:
        iteration = self.workspace / "iteration-1"

        self.assertEqual(eval_directory(iteration, 1), iteration / "eval-1")
        self.assertEqual(eval_directory(iteration, "ocean"), iteration / "eval-ocean")

    def test_eval_directory_rejects_an_unsafe_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "directory name"):
            eval_directory(self.root, "../escape")

    def test_run_id_combines_the_eval_and_arm(self) -> None:
        self.assertEqual(run_id(1, "with_skill"), "eval-1-with_skill")
        self.assertEqual(run_id("ocean", "without_skill"), "eval-ocean-without_skill")

    def test_run_id_rejects_an_unknown_arm(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown arm"):
            run_id(1, "both")


class EvalMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.eval_dir = self.root / "iteration-1" / "eval-1"

    def test_metadata_starts_with_empty_expectations(self) -> None:
        path = write_eval_metadata(
            self.eval_dir,
            eval_id=1,
            prompt="Do the thing",
            expected_output="A thing",
        )

        self.assertEqual(path, self.eval_dir / "eval_metadata.json")
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8")),
            {
                "eval_id": 1,
                "eval_name": "eval-1",
                "prompt": "Do the thing",
                "expected_output": "A thing",
                "expectations": [],
            },
        )

    def test_metadata_is_not_overwritten(self) -> None:
        path = write_eval_metadata(self.eval_dir, eval_id=1, prompt="First")
        path.write_text(
            json.dumps({"expectations": ["The answer is correct."]}),
            encoding="utf-8",
        )

        write_eval_metadata(self.eval_dir, eval_id=1, prompt="Changed")

        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8")),
            {"expectations": ["The answer is correct."]},
        )


class InputFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        self.eval_dir = self.root / "workspace" / "iteration-1" / "eval-1"

    def test_inputs_are_preserved_relative_to_the_skill(self) -> None:
        source = self.skill / "evals" / "files" / "input.txt"
        source.parent.mkdir(parents=True)
        source.write_text("Input.\n", encoding="utf-8")

        inputs = preserve_inputs(
            self.eval_dir, resolve_inputs(self.skill, ["evals/files/input.txt"])
        )

        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].relative_path, Path("evals/files/input.txt"))
        self.assertEqual(
            inputs[0].preserved_path,
            self.eval_dir / "inputs" / "evals" / "files" / "input.txt",
        )
        self.assertEqual(inputs[0].preserved_path.read_text(), "Input.\n")

    def test_preserved_inputs_are_not_overwritten(self) -> None:
        source = self.skill / "evals" / "files" / "input.txt"
        source.parent.mkdir(parents=True)
        source.write_text("First.\n", encoding="utf-8")
        preserve_inputs(
            self.eval_dir, resolve_inputs(self.skill, ["evals/files/input.txt"])
        )
        source.write_text("Changed.\n", encoding="utf-8")

        inputs = preserve_inputs(
            self.eval_dir, resolve_inputs(self.skill, ["evals/files/input.txt"])
        )

        self.assertEqual(inputs[0].preserved_path.read_text(), "First.\n")

    def test_inputs_outside_the_skill_are_rejected(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("Outside.\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "inside the skill directory"):
            resolve_inputs(self.skill, ["../outside.txt"])

    def test_missing_inputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            resolve_inputs(self.skill, ["evals/files/missing.txt"])

    def test_inputs_are_staged_into_the_scope(self) -> None:
        source = self.skill / "evals" / "files" / "input.txt"
        source.parent.mkdir(parents=True)
        source.write_text("Input.\n", encoding="utf-8")
        inputs = preserve_inputs(
            self.eval_dir, resolve_inputs(self.skill, ["evals/files/input.txt"])
        )
        scope_dir = self.root / "scope"
        scope_dir.mkdir()
        scope = PreparedScope(path=scope_dir)

        staged = stage_inputs(scope, inputs)

        self.assertEqual(staged, (scope_dir / "evals" / "files" / "input.txt",))
        self.assertEqual(staged[0].read_text(), "Input.\n")


class RunArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.scope_path = self.root / "scope"
        self.scope_path.mkdir()
        self.arm_dir = self.root / "iteration-1" / "eval-1" / "with_skill"

    def test_writes_the_canonical_arm_artifacts(self) -> None:
        result = canned_run_result(self.scope_path, loaded_skill_ids=("example-skill",))

        saved = write_run_artifacts(
            self.arm_dir,
            result,
            self.scope_path,
            run_identity="eval-1-with_skill",
        )

        self.assertEqual(
            {path.name for path in self.arm_dir.iterdir()},
            {
                "outputs",
                "transcript.jsonl",
                "transcript.md",
                "timing.json",
                "run.json",
            },
        )
        self.assertEqual(
            (self.arm_dir / "transcript.jsonl").read_text(encoding="utf-8"),
            result.transcript_jsonl,
        )
        self.assertEqual(
            (self.arm_dir / "transcript.md").read_text(encoding="utf-8"),
            result.transcript_markdown,
        )
        self.assertEqual(
            (self.arm_dir / "outputs" / "answer.md").read_text(encoding="utf-8"),
            "The answer.\n",
        )
        self.assertEqual(
            json.loads(
                (self.arm_dir / "outputs" / "metrics.json").read_text(encoding="utf-8")
            ),
            {
                "tool_calls": {"write": 1},
                "total_tool_calls": 1,
                "total_steps": 1,
                "files_created": ["answer.md"],
                "errors_encountered": 0,
                "output_chars": len("The answer.\n"),
                "transcript_chars": len("# Transcript\n\nDone.\n"),
            },
        )
        self.assertEqual(
            json.loads((self.arm_dir / "timing.json").read_text(encoding="utf-8")),
            {
                "total_tokens": 135,
                "duration_ms": 1500,
                "total_duration_seconds": 1.5,
            },
        )
        self.assertEqual(
            saved.timing.__dict__,
            {
                "total_tokens": 135,
                "duration_ms": 1500,
                "total_duration_seconds": 1.5,
            },
        )
        self.assertEqual(
            saved.output_files,
            (self.arm_dir / "outputs" / "answer.md",),
        )

    def test_writes_normalized_run_metadata(self) -> None:
        result = canned_run_result(self.scope_path, loaded_skill_ids=("example-skill",))

        write_run_artifacts(
            self.arm_dir,
            result,
            self.scope_path,
            run_identity="eval-1-with_skill",
        )

        self.assertEqual(
            json.loads((self.arm_dir / "run.json").read_text(encoding="utf-8")),
            {
                "run_id": "eval-1-with_skill",
                "assistant_text": "Done.",
                "tokens": {
                    "input": 100,
                    "output": 20,
                    "reasoning": 5,
                    "cache_read": 7,
                    "cache_write": 3,
                    "total": 135,
                },
                "duration_ms": 1500,
                "loaded_skill_ids": ["example-skill"],
                "output_files": ["answer.md"],
                "exit_code": 0,
                "stderr": "",
                "metrics": {
                    "tool_calls": {"write": 1},
                    "total_tool_calls": 1,
                    "total_steps": 1,
                    "files_created": ["answer.md"],
                    "errors_encountered": 0,
                    "output_chars": len("The answer.\n"),
                    "transcript_chars": len("# Transcript\n\nDone.\n"),
                },
                "timed_out": False,
            },
        )

    def test_preserves_a_failed_run(self) -> None:
        result = canned_run_result(
            self.scope_path,
            loaded_skill_ids=("example-skill",),
            exit_code=2,
            stderr="boom\n",
            timed_out=True,
        )

        write_run_artifacts(
            self.arm_dir,
            result,
            self.scope_path,
            run_identity="eval-1-with_skill",
        )

        document = json.loads((self.arm_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(document["exit_code"], 2)
        self.assertEqual(document["stderr"], "boom\n")
        self.assertTrue(document["timed_out"])

    def test_copies_nested_outputs(self) -> None:
        result = canned_run_result(
            self.scope_path,
            loaded_skill_ids=("example-skill",),
            output_name="reports/answer.md",
        )

        write_run_artifacts(
            self.arm_dir,
            result,
            self.scope_path,
            run_identity="eval-1-with_skill",
        )

        self.assertEqual(
            (self.arm_dir / "outputs" / "reports" / "answer.md").read_text(
                encoding="utf-8"
            ),
            "The answer.\n",
        )
