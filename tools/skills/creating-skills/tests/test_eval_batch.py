import contextlib
import io
import json
import shutil
import tempfile
import threading
import unittest
from collections.abc import Sequence
from pathlib import Path
from unittest import mock

from scripts.eval_batch import main, run_batch
from scripts.harness import PreparedScope, RunResult
from scripts.workspace import write_eval_metadata

from tests.support import RecordingHarness, write_evals, write_skill


class MetadataProbeHarness(RecordingHarness):
    """Record whether eval metadata exists when a run starts."""

    def __init__(self, root: Path, workspace: Path) -> None:
        super().__init__(root)
        self.workspace = workspace
        self.metadata_seen: list[bool] = []

    def run(
        self,
        scope: PreparedScope,
        prompt: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        input_files: Sequence[Path] = (),
        no_tools: bool = False,
        artifacts_dir: Path | None = None,
    ) -> RunResult:
        eval_id = {"Do the first thing": 1, "Do the second thing": 2}[prompt]
        metadata = self.workspace / "iteration-1" / f"eval-{eval_id}"
        self.metadata_seen.append((metadata / "eval_metadata.json").is_file())
        return super().run(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=input_files,
            no_tools=no_tools,
            artifacts_dir=artifacts_dir,
        )


class BarrierHarness(RecordingHarness):
    """Block every run until all runs have started."""

    def __init__(self, root: Path, parties: int) -> None:
        super().__init__(root)
        self.barrier = threading.Barrier(parties, timeout=5)
        self.thread_ids: set[int] = set()
        self._lock = threading.Lock()

    def run(
        self,
        scope: PreparedScope,
        prompt: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        input_files: Sequence[Path] = (),
        no_tools: bool = False,
        artifacts_dir: Path | None = None,
    ) -> RunResult:
        with self._lock:
            self.thread_ids.add(threading.get_ident())
        self.barrier.wait()
        return super().run(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=input_files,
            no_tools=no_tools,
            artifacts_dir=artifacts_dir,
        )


class FailingHarness(RecordingHarness):
    """Fail one baseline run with a setup error."""

    def run(
        self,
        scope: PreparedScope,
        prompt: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        input_files: Sequence[Path] = (),
        no_tools: bool = False,
        artifacts_dir: Path | None = None,
    ) -> RunResult:
        if not scope.skill_ids and prompt == "Do the second thing":
            raise RuntimeError("baseline exploded")
        return super().run(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=input_files,
            no_tools=no_tools,
            artifacts_dir=artifacts_dir,
        )


class MetadataEditingHarness(RecordingHarness):
    """Simulate the agent drafting assertions while runs are in progress."""

    def __init__(self, root: Path, workspace: Path) -> None:
        super().__init__(root)
        self.workspace = workspace

    def run(
        self,
        scope: PreparedScope,
        prompt: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        input_files: Sequence[Path] = (),
        no_tools: bool = False,
        artifacts_dir: Path | None = None,
    ) -> RunResult:
        path = self.workspace / "iteration-1" / "eval-1" / "eval_metadata.json"
        if path.is_file():
            metadata = json.loads(path.read_text(encoding="utf-8"))
            if not metadata["expectations"]:
                metadata["expectations"] = ["The first thing is done."]
                path.write_text(json.dumps(metadata), encoding="utf-8")
        return super().run(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=input_files,
            no_tools=no_tools,
            artifacts_dir=artifacts_dir,
        )


class BatchLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        write_evals(
            self.skill,
            [
                {"id": 1, "prompt": "Do the first thing"},
                {"id": 2, "prompt": "Do the second thing"},
            ],
        )
        self.harness = RecordingHarness(self.root)

    def test_one_batch_creates_one_iteration_with_both_arms_per_case(self) -> None:
        result = run_batch(self.harness, self.skill)

        workspace = self.skill.parent / "example-skill-workspace"
        self.assertEqual(result.iteration_dir, workspace / "iteration-1")
        self.assertEqual(result.baseline_arm, "without_skill")
        self.assertEqual(
            [outcome.run_id for outcome in result.outcomes],
            [
                "eval-1-with_skill",
                "eval-1-without_skill",
                "eval-2-with_skill",
                "eval-2-without_skill",
            ],
        )
        self.assertEqual({outcome.status for outcome in result.outcomes}, {"ok"})
        for eval_name in ("eval-1", "eval-2"):
            eval_dir = result.iteration_dir / eval_name
            metadata = json.loads(
                (eval_dir / "eval_metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["expectations"], [])
            self.assertTrue((eval_dir / "with_skill" / "run.json").is_file())
            self.assertTrue((eval_dir / "without_skill" / "run.json").is_file())
        self.assertEqual(
            [path.name for path in workspace.iterdir()],
            ["iteration-1"],
        )

    def test_metadata_exists_before_every_run_starts(self) -> None:
        workspace = self.skill.parent / "example-skill-workspace"
        harness = MetadataProbeHarness(self.root, workspace)

        run_batch(harness, self.skill)

        self.assertEqual(harness.metadata_seen, [True, True, True, True])

    def test_assertion_drafts_survive_the_remaining_arms(self) -> None:
        workspace = self.skill.parent / "example-skill-workspace"
        harness = MetadataEditingHarness(self.root, workspace)

        result = run_batch(harness, self.skill)

        metadata = json.loads(
            (result.iteration_dir / "eval-1" / "eval_metadata.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(metadata["expectations"], ["The first thing is done."])

    def test_all_arms_start_together(self) -> None:
        harness = BarrierHarness(self.root, parties=4)

        result = run_batch(harness, self.skill)

        self.assertEqual({outcome.status for outcome in result.outcomes}, {"ok"})
        self.assertEqual(len(harness.thread_ids), 4)

    def test_one_failed_run_does_not_stop_the_rest(self) -> None:
        harness = FailingHarness(self.root)

        result = run_batch(harness, self.skill)

        statuses = {outcome.run_id: outcome.status for outcome in result.outcomes}
        self.assertEqual(statuses["eval-2-without_skill"], "error")
        self.assertEqual(
            {
                status
                for run_id, status in statuses.items()
                if run_id != "eval-2-without_skill"
            },
            {"ok"},
        )
        eval_1 = result.iteration_dir / "eval-1"
        self.assertTrue((eval_1 / "with_skill" / "run.json").is_file())
        self.assertTrue((eval_1 / "without_skill" / "run.json").is_file())
        eval_2 = result.iteration_dir / "eval-2"
        self.assertTrue((eval_2 / "with_skill" / "run.json").is_file())
        error = json.loads(
            (eval_2 / "without_skill" / "error.json").read_text(encoding="utf-8")
        )
        self.assertEqual(error["run_id"], "eval-2-without_skill")
        self.assertEqual(error["error"]["type"], "RuntimeError")
        self.assertEqual(error["error"]["message"], "baseline exploded")

    def test_adapter_failure_is_saved_as_a_failed_run(self) -> None:
        harness = RecordingHarness(
            self.root, exit_code=2, stderr="boom\n", timed_out=True
        )

        result = run_batch(harness, self.skill)

        self.assertEqual({outcome.status for outcome in result.outcomes}, {"failed"})
        for outcome in result.outcomes:
            self.assertIsNotNone(outcome.case_run)
            assert outcome.case_run is not None
            self.assertTrue((outcome.case_run.arm_dir / "run.json").is_file())
            self.assertTrue((outcome.case_run.arm_dir / "timing.json").is_file())
            document = json.loads(
                (outcome.case_run.arm_dir / "run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(document["exit_code"], 2)
            self.assertTrue(document["timed_out"])

    def test_baseline_snapshot_runs_as_old_skill_with_the_same_id(self) -> None:
        snapshot = self.root / "snapshots" / "skill-snapshot"
        shutil.copytree(self.skill, snapshot)

        result = run_batch(self.harness, self.skill, baseline_skill=snapshot)

        self.assertEqual(result.baseline_arm, "old_skill")
        for eval_name in ("eval-1", "eval-2"):
            eval_dir = result.iteration_dir / eval_name
            self.assertTrue((eval_dir / "old_skill" / "run.json").is_file())
            self.assertFalse((eval_dir / "without_skill").exists())
        for outcome in result.outcomes:
            self.assertIsNotNone(outcome.case_run)
            assert outcome.case_run is not None
            document = json.loads(
                (outcome.case_run.arm_dir / "run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(document["loaded_skill_ids"], ["example-skill"])

        baseline_paths = {
            path
            for call in self.harness.prepare_calls
            for path in call
            if path != self.skill.resolve()
        }
        self.assertEqual(len(baseline_paths), 1)
        baseline_path = baseline_paths.pop()
        self.assertEqual(baseline_path.name, "example-skill")
        self.assertFalse(baseline_path.exists())

    def test_baseline_cannot_be_the_live_skill(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be the live skill"):
            run_batch(self.harness, self.skill, baseline_skill=self.skill)

        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())

    def test_baseline_requires_a_skill_document(self) -> None:
        empty = self.root / "snapshots" / "empty"
        empty.mkdir(parents=True)

        with self.assertRaisesRegex(ValueError, "SKILL.md"):
            run_batch(self.harness, self.skill, baseline_skill=empty)

        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())

    def test_case_filter_runs_only_the_selected_case_in_both_arms(self) -> None:
        result = run_batch(self.harness, self.skill, eval_ids=["2"])

        self.assertEqual(
            [outcome.run_id for outcome in result.outcomes],
            ["eval-2-with_skill", "eval-2-without_skill"],
        )
        self.assertFalse((result.iteration_dir / "eval-1").exists())
        self.assertTrue((result.iteration_dir / "eval-2" / "with_skill").is_dir())
        self.assertTrue((result.iteration_dir / "eval-2" / "without_skill").is_dir())

    def test_case_filter_reports_unknown_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "available: 1, 2"):
            run_batch(self.harness, self.skill, eval_ids=["9"])

    def test_case_filter_deduplicates_ids(self) -> None:
        result = run_batch(self.harness, self.skill, eval_ids=["2", "2"])

        self.assertEqual(len(result.outcomes), 2)

    def test_retry_cannot_mix_baseline_arms_in_one_iteration(self) -> None:
        iteration = self.root / "existing-workspace" / "iteration-1"
        (iteration / "eval-1" / "old_skill").mkdir(parents=True)

        with self.assertRaisesRegex(ValueError, "already contains old_skill"):
            run_batch(self.harness, self.skill, iteration_dir=iteration)

    def test_workspace_override_relocates_the_batch(self) -> None:
        override = self.root / "elsewhere"

        result = run_batch(self.harness, self.skill, workspace=override)

        self.assertEqual(result.iteration_dir, override / "iteration-1")
        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())

    def test_batch_adds_runs_to_an_existing_iteration(self) -> None:
        workspace = self.root / "existing-workspace"
        iteration = workspace / "iteration-1"
        iteration.mkdir(parents=True)

        result = run_batch(self.harness, self.skill, iteration_dir=iteration)

        self.assertEqual(result.iteration_dir, iteration.resolve())
        self.assertTrue((iteration / "eval-1" / "with_skill" / "run.json").is_file())

    def test_unsafe_eval_id_does_not_create_a_workspace(self) -> None:
        write_evals(
            self.skill,
            [{"id": "../escape", "prompt": "Do something unsafe"}],
        )

        with self.assertRaisesRegex(ValueError, "directory name"):
            run_batch(self.harness, self.skill)

        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())

    def test_empty_eval_definition_is_rejected_before_creating_a_workspace(
        self,
    ) -> None:
        write_evals(self.skill, [])

        with self.assertRaisesRegex(ValueError, "no eval cases"):
            run_batch(self.harness, self.skill)

        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())

    def test_bad_inputs_do_not_stop_the_other_cases(self) -> None:
        write_evals(
            self.skill,
            [
                {"id": 1, "prompt": "Do the first thing"},
                {
                    "id": 2,
                    "prompt": "Do the second thing",
                    "files": ["evals/files/missing.txt"],
                },
            ],
        )

        result = run_batch(self.harness, self.skill)

        statuses = {outcome.run_id: outcome.status for outcome in result.outcomes}
        self.assertEqual(
            statuses,
            {
                "eval-1-with_skill": "ok",
                "eval-1-without_skill": "ok",
                "eval-2-with_skill": "error",
                "eval-2-without_skill": "error",
            },
        )
        self.assertTrue(
            (result.iteration_dir / "eval-1" / "with_skill" / "run.json").is_file()
        )
        for arm in ("with_skill", "without_skill"):
            error_path = result.iteration_dir / "eval-2" / arm / "error.json"
            error = json.loads(error_path.read_text(encoding="utf-8"))
            self.assertEqual(error["run_id"], f"eval-2-{arm}")
            self.assertEqual(error["error"]["type"], "FileNotFoundError")

    def test_metadata_write_failure_does_not_stop_the_rest(self) -> None:
        def write_metadata(
            eval_dir: Path,
            *,
            eval_id: int | str,
            prompt: str,
            expected_output: str = "",
        ) -> Path:
            if str(eval_id) == "2":
                raise OSError("disk full")
            return write_eval_metadata(
                eval_dir,
                eval_id=eval_id,
                prompt=prompt,
                expected_output=expected_output,
            )

        with mock.patch(
            "scripts.eval_batch.write_eval_metadata", side_effect=write_metadata
        ):
            result = run_batch(self.harness, self.skill)

        statuses = {outcome.run_id: outcome.status for outcome in result.outcomes}
        self.assertEqual(statuses["eval-1-with_skill"], "ok")
        self.assertEqual(statuses["eval-1-without_skill"], "ok")
        self.assertEqual(statuses["eval-2-with_skill"], "error")
        self.assertEqual(statuses["eval-2-without_skill"], "error")
        error = json.loads(
            (result.iteration_dir / "eval-2" / "with_skill" / "error.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(error["error"]["type"], "OSError")

    def test_all_bad_inputs_are_rejected_before_creating_a_workspace(self) -> None:
        write_evals(
            self.skill,
            [
                {
                    "id": 1,
                    "prompt": "Do the first thing",
                    "files": ["evals/files/missing.txt"],
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "no runnable eval cases"):
            run_batch(self.harness, self.skill)

        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())


class BatchCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self.skill = write_skill(self.root, "example-skill")
        write_evals(
            self.skill,
            [
                {"id": 1, "prompt": "Do the first thing"},
                {"id": 2, "prompt": "Do the second thing"},
            ],
        )
        self.harness = RecordingHarness(self.root)

    def test_cli_runs_the_batch_and_reports_success(self) -> None:
        workspace = self.root / "cli-workspace"
        stdout = io.StringIO()
        with (
            mock.patch("scripts.eval_batch.get_harness", return_value=self.harness),
            contextlib.redirect_stdout(stdout),
        ):
            status = main(["--skill", str(self.skill), "--workspace", str(workspace)])

        self.assertEqual(status, 0)
        output = stdout.getvalue()
        self.assertIn(f"iteration: {workspace / 'iteration-1'}", output)
        self.assertIn("4 runs: 4 ok, 0 failed, 0 error", output)
        for run_id in (
            "eval-1-with_skill",
            "eval-1-without_skill",
            "eval-2-with_skill",
            "eval-2-without_skill",
        ):
            self.assertIn(run_id, output)
        self.assertTrue(
            (workspace / "iteration-1" / "eval-2" / "with_skill" / "run.json").is_file()
        )

    def test_cli_returns_one_when_a_run_fails(self) -> None:
        stdout = io.StringIO()
        with (
            mock.patch(
                "scripts.eval_batch.get_harness", return_value=FailingHarness(self.root)
            ),
            contextlib.redirect_stdout(stdout),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--workspace",
                    str(self.root / "cli-workspace"),
                ]
            )

        self.assertEqual(status, 1)
        output = stdout.getvalue()
        self.assertIn("4 runs: 3 ok, 0 failed, 1 error", output)
        self.assertIn("error: eval-2-without_skill (baseline exploded)", output)

    def test_cli_returns_two_for_an_unknown_case(self) -> None:
        stderr = io.StringIO()
        with (
            mock.patch("scripts.eval_batch.get_harness", return_value=self.harness),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(["--skill", str(self.skill), "--case", "9"])

        self.assertEqual(status, 2)
        self.assertIn("available: 1, 2", stderr.getvalue())

    def test_cli_accepts_a_baseline_and_case_filter(self) -> None:
        snapshot = self.root / "snapshots" / "skill-snapshot"
        shutil.copytree(self.skill, snapshot)
        workspace = self.root / "cli-workspace"
        with (
            mock.patch("scripts.eval_batch.get_harness", return_value=self.harness),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--case",
                    "1",
                    "--baseline-skill",
                    str(snapshot),
                    "--workspace",
                    str(workspace),
                ]
            )

        self.assertEqual(status, 0)
        iteration = workspace / "iteration-1"
        self.assertTrue((iteration / "eval-1" / "with_skill" / "run.json").is_file())
        self.assertTrue((iteration / "eval-1" / "old_skill" / "run.json").is_file())
        self.assertFalse((iteration / "eval-2").exists())

    def test_cli_warns_when_a_snapshot_exists_but_was_not_passed(self) -> None:
        snapshot = self.skill.parent / "example-skill-workspace" / "skill-snapshot"
        snapshot.parent.mkdir(parents=True)
        shutil.copytree(self.skill, snapshot)
        stderr = io.StringIO()
        with (
            mock.patch("scripts.eval_batch.get_harness", return_value=self.harness),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(["--skill", str(self.skill)])

        self.assertEqual(status, 0)
        self.assertIn("pass --baseline-skill", stderr.getvalue())
        iteration = self.skill.parent / "example-skill-workspace" / "iteration-1"
        self.assertTrue((iteration / "eval-1" / "without_skill").is_dir())
        self.assertFalse((iteration / "eval-1" / "old_skill").exists())

    def test_cli_rejects_a_missing_iteration(self) -> None:
        stderr = io.StringIO()
        with (
            mock.patch("scripts.eval_batch.get_harness", return_value=self.harness),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(
                [
                    "--skill",
                    str(self.skill),
                    "--workspace",
                    str(self.root / "cli-workspace"),
                    "--iteration",
                    "1",
                ]
            )

        self.assertEqual(status, 2)
        self.assertIn("does not exist", stderr.getvalue())

    def test_baseline_name_must_match_the_live_skill(self) -> None:
        other = self.root / "snapshots" / "other-skill"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text(
            "---\nname: other-skill\ndescription: Other.\n---\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "name must match"):
            run_batch(self.harness, self.skill, baseline_skill=other)

        self.assertFalse((self.skill.parent / "example-skill-workspace").exists())
