"""Tests for the evaluate command, driven through the CLI."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

from support import install_fake_opencode, run_cli, skill_call_stdout

JsonPayload = str | dict[str, Any] | list[Any]


def valid_cases() -> dict[str, Any]:
    return {
        "direct-request": {
            "prompt": "Summarize this document for me.",
            "expect": True,
        },
        "indirect-request": {
            "prompt": "I have a pile of notes and need the key points pulled out.",
            "expect": True,
        },
        "near-miss-phrasing": {
            "prompt": "Turn these paragraphs into a short overview.",
            "expect": True,
        },
        "adjacent-task": {
            "prompt": "Translate this document into French.",
            "expect": False,
        },
        "out-of-scope-keyword": {
            "prompt": "Summarize why the build failed.",
            "expect": False,
        },
        "too-vague": {
            "prompt": "Can you help me with this?",
            "expect": False,
        },
    }


class EvaluateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.temp = Path(directory.name)
        self.repo = self.temp / "repo"
        self.skill = self.repo / "skills" / "my-skill"
        self.default_cases = (
            self.repo / "tests" / "my-skill" / "description-trigger.json"
        )
        self.tmp = self.temp / "tmp"
        self.tmp.mkdir()
        self.marker = self.temp / "opencode-launched"
        self.spec_path = self.temp / "spec.json"
        self.cases = valid_cases()
        self.write_skill()
        self.write_cases(self.cases)
        self.write_spec(default={"stdout": "", "exit": 0})
        self.env = install_fake_opencode(self.temp)
        self.env["FAKE_OPENCODE_MARKER"] = str(self.marker)
        self.env["FAKE_OPENCODE_SPEC"] = str(self.spec_path)
        self.env["TMPDIR"] = str(self.tmp)

    def write_skill(
        self,
        frontmatter: str | None = None,
        body: str = "# My Skill\n",
        directory: Path | None = None,
    ) -> Path:
        target = directory or self.skill
        target.mkdir(parents=True, exist_ok=True)
        if frontmatter is None:
            frontmatter = (
                "name: my-skill\n"
                "description: Summarize documents and pull out the key points."
            )
        (target / "SKILL.md").write_text(
            f"---\n{frontmatter}\n---\n{body}",
            encoding="utf-8",
        )
        return target

    def write_cases(
        self,
        payload: JsonPayload,
        path: Path | None = None,
    ) -> Path:
        path = path or self.default_cases
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_spec(
        self,
        *,
        prompts: dict[str, dict[str, Any]] | None = None,
        default: dict[str, Any] | None = None,
    ) -> Path:
        self.spec_path.write_text(
            json.dumps({"prompts": prompts or {}, "default": default or {}}),
            encoding="utf-8",
        )
        return self.spec_path

    def trigger_expected_cases(self, *, field: str = "id") -> None:
        self.write_spec(
            prompts={
                case["prompt"]: {
                    "stdout": skill_call_stdout("my-skill", field=field),
                }
                for case in self.cases.values()
                if case["expect"]
            },
            default={"stdout": "", "exit": 0},
        )

    def run_cli(
        self,
        *arguments: str | Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return run_cli(*arguments, cwd=self.temp, env=env or self.env)

    def probe_directories(self) -> list[Path]:
        return sorted(path for path in self.tmp.iterdir() if path.is_dir())

    def probe_config(self, probe: Path) -> dict[str, Any]:
        return json.loads(
            (probe / ".opencode" / "opencode.json").read_text(encoding="utf-8")
        )

    def evaluate(self, *arguments: str | Path) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "evaluate",
            self.skill,
            "--model",
            "test/model",
            *arguments,
        )


class EvaluateInvocationTest(EvaluateTestCase):
    def test_model_is_required(self) -> None:
        result = self.run_cli("evaluate", self.skill)

        self.assertEqual(result.returncode, 2)
        self.assertIn("--model", result.stderr)
        self.assertFalse(self.marker.exists(), "missing model launched OpenCode")

    def test_invalid_case_file_exits_2_without_launching_opencode(self) -> None:
        self.write_cases("{ not json")

        result = self.evaluate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid JSON", result.stderr)
        self.assertFalse(self.marker.exists(), "preflight launched OpenCode")
        self.assertEqual(self.probe_directories(), [])

    def test_ineligible_skill_exits_2_without_launching_opencode(self) -> None:
        (self.skill / "SKILL.md").unlink()

        result = self.evaluate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("SKILL.md", result.stderr)
        self.assertFalse(self.marker.exists(), "preflight launched OpenCode")
        self.assertEqual(self.probe_directories(), [])

    def test_explicit_case_path_is_used(self) -> None:
        cases = self.write_cases(self.cases, self.temp / "outside" / "cases.json")
        self.trigger_expected_cases()

        result = self.evaluate("--cases", cases)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Case file: {cases}", result.stdout)


class EvaluateResultTest(EvaluateTestCase):
    def test_completed_target_skill_call_passes(self) -> None:
        self.trigger_expected_cases()

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("expected=true", result.stdout)
        self.assertIn("actual=true", result.stdout)
        self.assertRegex(result.stdout, r"duration=\d+\.\d{2}s")
        self.assertIn("Passed: 6", result.stdout)
        self.assertIn("Failed: 0", result.stdout)
        self.assertIn("Error: 0", result.stdout)

    def test_clean_run_without_target_call_fails_positive_cases(self) -> None:
        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("FAIL direct-request", result.stdout)
        self.assertIn("expected=true", result.stdout)
        self.assertIn("actual=false", result.stdout)
        self.assertIn("PASS adjacent-task", result.stdout)
        self.assertIn("Passed: 3", result.stdout)
        self.assertIn("Failed: 3", result.stdout)
        self.assertIn("Error: 0", result.stdout)

    def test_nonzero_exit_without_target_call_is_error(self) -> None:
        self.write_spec(default={"stdout": "", "exit": 1})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("expected=true", result.stdout)
        self.assertIn("actual=ERROR", result.stdout)
        self.assertIn("Error: 6", result.stdout)

    def test_target_error_status_is_error(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill", status="error"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("actual=ERROR", result.stdout)
        self.assertIn("Error: target skill call failed: denied", result.stdout)
        self.assertIn("Error: 6", result.stdout)

    def test_target_error_after_completed_target_call_is_error(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill")
                + skill_call_stdout("my-skill", status="error"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("actual=ERROR", result.stdout)
        self.assertIn("Error: target skill call failed: denied", result.stdout)

    def test_completed_target_call_after_target_error_is_error(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill", status="error")
                + skill_call_stdout("my-skill"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("actual=ERROR", result.stdout)
        self.assertIn("Error: target skill call failed: denied", result.stdout)

    def test_target_error_is_reported_before_nonzero_exit(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill", status="error"),
                "exit": 1,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: target skill call failed: denied", result.stdout)
        self.assertNotIn("without loading my-skill", result.stdout)

    def test_running_target_call_then_completed_target_call_triggers(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill", status="running")
                + skill_call_stdout("my-skill"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("FAIL adjacent-task", result.stdout)
        self.assertIn("actual=true", result.stdout)
        self.assertIn("Error: 0", result.stdout)

    def test_running_target_call_without_completion_is_error(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill", status="running"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn(
            "Error: target skill call did not reach a terminal status",
            result.stdout,
        )

    def test_failed_other_skill_call_is_not_reported_as_loaded(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("another-skill", status="error"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL direct-request", result.stdout)
        self.assertIn("actual=false", result.stdout)
        self.assertIn(
            "Diagnostic: other skill call failed: another-skill", result.stdout
        )
        self.assertNotIn("other skill loaded: another-skill", result.stdout)

    def test_other_skill_call_does_not_trigger(self) -> None:
        self.write_spec(
            default={"stdout": skill_call_stdout("another-skill"), "exit": 0}
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL direct-request", result.stdout)
        self.assertIn("actual=false", result.stdout)
        self.assertIn("PASS adjacent-task", result.stdout)
        self.assertIn("Diagnostic: other skill loaded: another-skill", result.stdout)

    def test_other_skill_call_does_not_change_completed_target_result(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("another-skill")
                + skill_call_stdout("my-skill"),
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("FAIL adjacent-task", result.stdout)
        self.assertIn("actual=true", result.stdout)
        self.assertIn("Diagnostic: other skill loaded: another-skill", result.stdout)

    def test_legacy_name_field_is_recognized(self) -> None:
        self.trigger_expected_cases(field="name")

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("actual=true", result.stdout)

    def test_target_match_in_either_skill_input_field_is_recognized(self) -> None:
        self.write_spec(
            prompts={
                case["prompt"]: {
                    "stdout": skill_call_stdout(
                        "my-skill",
                        field="name",
                        additional_input={"id": "another-skill"},
                    ),
                }
                for case in self.cases.values()
                if case["expect"]
            },
            default={"stdout": "", "exit": 0},
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("actual=true", result.stdout)

    def test_skill_id_match_is_exact(self) -> None:
        self.write_spec(
            default={"stdout": skill_call_stdout("my-skill-extra"), "exit": 0}
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL direct-request", result.stdout)
        self.assertIn("actual=false", result.stdout)
        self.assertIn("Diagnostic: other skill loaded: my-skill-extra", result.stdout)

    def test_skill_id_match_is_case_sensitive(self) -> None:
        self.write_spec(default={"stdout": skill_call_stdout("My-Skill"), "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAIL direct-request", result.stdout)
        self.assertIn("actual=false", result.stdout)
        self.assertIn("Diagnostic: other skill loaded: My-Skill", result.stdout)

    def test_malformed_transcript_is_error(self) -> None:
        self.write_spec(default={"stdout": "{ not json\n", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)
        self.assertIn("Error: 6", result.stdout)

    def test_json_line_without_event_type_is_error(self) -> None:
        self.write_spec(default={"stdout": '{"unexpected": true}\n', "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_tool_use_line_without_part_type_is_error(self) -> None:
        event = {"type": "tool_use", "part": {"sessionID": "ses_probe"}}
        self.write_spec(default={"stdout": json.dumps(event) + "\n", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_tool_use_line_without_tool_name_is_error(self) -> None:
        event = {"type": "tool_use", "part": {"type": "tool"}}
        self.write_spec(default={"stdout": json.dumps(event) + "\n", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_tool_use_line_with_empty_tool_name_is_error(self) -> None:
        event = {"type": "tool_use", "part": {"type": "tool", "tool": ""}}
        self.write_spec(default={"stdout": json.dumps(event) + "\n", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_tool_use_line_with_unexpected_part_type_is_error(self) -> None:
        event = {"type": "tool_use", "part": {"type": "text"}}
        self.write_spec(default={"stdout": json.dumps(event) + "\n", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_empty_event_type_is_error(self) -> None:
        self.write_spec(default={"stdout": '{"type": ""}\n', "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_empty_skill_identifier_is_error(self) -> None:
        self.write_spec(default={"stdout": skill_call_stdout(""), "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: transcript contained a malformed line", result.stdout)

    def test_malformed_line_after_completed_target_call_is_not_error(self) -> None:
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill") + "{ not json\n",
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("FAIL adjacent-task", result.stdout)
        self.assertIn("actual=true", result.stdout)
        self.assertIn("Error: 0", result.stdout)

    def test_run_level_error_event_alone_is_error(self) -> None:
        error_event = json.dumps(
            {
                "type": "error",
                "timestamp": 2,
                "sessionID": "ses_probe",
                "error": {"type": "unknown", "message": "probe failed"},
            }
        )
        self.write_spec(default={"stdout": error_event + "\n", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("Error: probe failed", result.stdout)
        self.assertIn("Error: 6", result.stdout)

    def test_run_level_error_event_is_error_not_a_trigger(self) -> None:
        error_event = json.dumps(
            {
                "type": "error",
                "timestamp": 2,
                "sessionID": "ses_probe",
                "error": {"type": "unknown", "message": "probe failed"},
            }
        )
        self.write_spec(
            default={
                "stdout": skill_call_stdout("my-skill") + error_event + "\n",
                "exit": 0,
            }
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("probe failed", result.stdout)

    def test_nonzero_exit_after_completed_target_call_still_triggers(self) -> None:
        self.write_spec(default={"stdout": skill_call_stdout("my-skill"), "exit": 1})

        result = self.evaluate()

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("FAIL adjacent-task", result.stdout)
        self.assertIn("actual=true", result.stdout)
        self.assertIn(
            "Note: OpenCode exited with 1 after the target skill call",
            result.stdout,
        )

    def test_error_takes_precedence_over_failure_in_report_and_exit_code(
        self,
    ) -> None:
        prompts = {}
        for case in self.cases.values():
            # Expected positives error out; expected negatives trigger and fail.
            status = "error" if case["expect"] else "completed"
            prompts[case["prompt"]] = {
                "stdout": skill_call_stdout("my-skill", status=status),
            }
        self.write_spec(prompts=prompts, default={"stdout": "", "exit": 0})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("FAIL adjacent-task", result.stdout)
        self.assertIn("Passed: 0", result.stdout)
        self.assertIn("Failed: 3", result.stdout)
        self.assertIn("Error: 3", result.stdout)


class EvaluateProbeTest(EvaluateTestCase):
    def test_each_case_gets_a_fresh_project_with_only_the_target_skill(self) -> None:
        self.trigger_expected_cases()

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        probes = self.probe_directories()
        self.assertEqual(len(probes), len(self.cases))
        self.assertEqual(len(set(probes)), len(probes))
        agent_names = set()
        for probe in probes:
            config = self.probe_config(probe)
            self.assertEqual(len(config["agents"]), 1)
            agent_name, definition = next(iter(config["agents"].items()))
            agent_names.add(agent_name)
            self.assertEqual(definition["mode"], "primary")
            self.assertEqual(
                definition["permissions"],
                [
                    {"action": "*", "resource": "*", "effect": "deny"},
                    {"action": "skill", "resource": "my-skill", "effect": "allow"},
                ],
            )
            skills = probe / ".opencode" / "skills"
            self.assertEqual(
                sorted(path.name for path in skills.iterdir() if path.is_dir()),
                ["my-skill"],
            )
            self.assertEqual(
                (skills / "my-skill" / "SKILL.md").read_text(encoding="utf-8"),
                (self.skill / "SKILL.md").read_text(encoding="utf-8"),
            )
        self.assertEqual(len(agent_names), len(probes))

    def test_probe_command_uses_json_agent_model_archived_and_stdin(self) -> None:
        self.trigger_expected_cases()

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        for probe in self.probe_directories():
            invocation = json.loads(
                (probe / "fake-opencode.json").read_text(encoding="utf-8")
            )
            agent_name = next(iter(self.probe_config(probe)["agents"]))
            self.assertEqual(
                invocation["arguments"],
                [
                    "run",
                    "--format",
                    "json",
                    "--agent",
                    agent_name,
                    "--model",
                    "test/model",
                    "--archived",
                ],
            )
            self.assertEqual(invocation["cwd"], str(probe))
            self.assertEqual(invocation["pwd"], str(probe))
            prompt = (probe / "fake-prompt.txt").read_text(encoding="utf-8")
            self.assertIn(prompt, {case["prompt"] for case in self.cases.values()})

    def test_probe_directories_keep_config_transcript_and_stderr(self) -> None:
        self.trigger_expected_cases()

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        for probe in self.probe_directories():
            self.assertTrue((probe / ".opencode" / "opencode.json").is_file())
            self.assertTrue((probe / "transcript.jsonl").is_file())
            self.assertTrue((probe / "stderr.txt").is_file())
            self.assertIn("Probe directory:", result.stdout)

    def test_error_probe_directories_keep_transcript_and_stderr(self) -> None:
        self.write_spec(default={"stdout": "", "stderr": "probe failed\n", "exit": 1})

        result = self.evaluate()

        self.assertEqual(result.returncode, 2, result.stdout)
        probes = self.probe_directories()
        self.assertEqual(len(probes), len(self.cases))
        for probe in probes:
            self.assertTrue((probe / ".opencode" / "opencode.json").is_file())
            self.assertTrue((probe / "transcript.jsonl").is_file())
            self.assertEqual(
                (probe / "stderr.txt").read_text(encoding="utf-8"),
                "probe failed\n",
            )
            self.assertIn(str(probe), result.stdout)

    def test_report_records_run_metadata(self) -> None:
        self.trigger_expected_cases()

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Cases: 6", result.stdout)
        self.assertIn("Runs: 6", result.stdout)
        self.assertRegex(result.stdout, r"Total duration: \d+\.\d{2}s")
        self.assertIn("Skill: my-skill", result.stdout)
        self.assertIn(f"Case file: {self.default_cases}", result.stdout)
        self.assertIn("Model: test/model", result.stdout)
        self.assertIn("OpenCode version: fake-opencode 9.9.9", result.stdout)


class EvaluateTimeoutTest(EvaluateTestCase):
    def hang(
        self,
        prompt: str,
        *,
        stdout: str = "",
        ignore_sigterm: bool = False,
    ) -> None:
        self.write_spec(
            prompts={
                prompt: {
                    "stdout": stdout,
                    "sleep": 60,
                    "ignore_sigterm": ignore_sigterm,
                }
            },
            default={"stdout": "", "exit": 0},
        )

    def timed_probe(self, case_id: str) -> Path:
        probes = [
            probe for probe in self.probe_directories() if f"-{case_id}-" in probe.name
        ]
        self.assertEqual(len(probes), 1)
        return probes[0]

    def assert_process_stopped(self, probe: Path) -> None:
        invocation = json.loads(
            (probe / "fake-opencode.json").read_text(encoding="utf-8")
        )
        with self.assertRaises(ProcessLookupError):
            os.kill(invocation["pid"], 0)

    def test_timeout_option_defaults_to_300_seconds(self) -> None:
        result = self.run_cli("evaluate", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--timeout", result.stdout)
        self.assertIn("default: 300)", result.stdout)

    def test_non_positive_timeout_is_rejected(self) -> None:
        result = self.evaluate("--timeout", "0")

        self.assertEqual(result.returncode, 2)
        self.assertIn("timeout must be greater than zero", result.stderr)
        self.assertFalse(self.marker.exists(), "invalid timeout launched OpenCode")

    def test_non_finite_timeout_is_rejected(self) -> None:
        for value in ("nan", "inf"):
            with self.subTest(value=value):
                result = self.evaluate("--timeout", value)

                self.assertEqual(result.returncode, 2)
                self.assertIn("timeout must be finite", result.stderr)
                self.assertFalse(
                    self.marker.exists(), "invalid timeout launched OpenCode"
                )

    def test_timeout_before_target_call_is_error(self) -> None:
        self.hang(self.cases["direct-request"]["prompt"])

        started = time.monotonic()
        result = self.evaluate("--timeout", "0.5")
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 10)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertIn("expected=true", result.stdout)
        self.assertIn("actual=ERROR", result.stdout)
        self.assertIn(
            "Error: OpenCode timed out before loading my-skill", result.stdout
        )
        self.assertIn(
            "Diagnostic: probe timed out after 0.5s; sent SIGTERM", result.stdout
        )
        probe = self.timed_probe("direct-request")
        self.assertTrue((probe / "transcript.jsonl").is_file())
        self.assert_process_stopped(probe)

    def test_timeout_after_completed_target_call_triggers_with_note(self) -> None:
        self.hang(
            self.cases["direct-request"]["prompt"],
            stdout=skill_call_stdout("my-skill"),
        )

        started = time.monotonic()
        result = self.evaluate("--timeout", "0.5")
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 10)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("expected=true", result.stdout)
        self.assertIn("actual=true", result.stdout)
        self.assertIn(
            "Note: OpenCode timed out after the target skill call", result.stdout
        )
        self.assertIn(
            "Diagnostic: probe timed out after 0.5s; sent SIGTERM", result.stdout
        )
        probe = self.timed_probe("direct-request")
        self.assertTrue((probe / "transcript.jsonl").is_file())
        self.assert_process_stopped(probe)

    def test_hung_probe_gets_sigkill_after_grace_period(self) -> None:
        marker = self.temp / "sigterm-received"
        self.env["FAKE_OPENCODE_SIGTERM_MARKER"] = str(marker)
        self.hang(self.cases["direct-request"]["prompt"], ignore_sigterm=True)

        started = time.monotonic()
        result = self.evaluate("--timeout", "0.5")
        elapsed = time.monotonic() - started

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ERROR direct-request", result.stdout)
        self.assertTrue(marker.is_file(), "SIGTERM was not delivered")
        self.assertIn("sent SIGTERM, then SIGKILL after 1s", result.stdout)
        self.assertGreaterEqual(elapsed, 1.4)
        self.assertLess(elapsed, 10)
        self.assert_process_stopped(self.timed_probe("direct-request"))


class EvaluateSmokeTest(EvaluateTestCase):
    def test_synthetic_probe_loads_target_skill_under_deny_all(self) -> None:
        self.write_spec(
            prompts={
                case["prompt"]: {"verify_probe": True}
                for case in self.cases.values()
                if case["expect"]
            },
            default={"stdout": "", "exit": 0},
        )

        result = self.evaluate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS direct-request", result.stdout)
        self.assertIn("Passed: 6", result.stdout)
