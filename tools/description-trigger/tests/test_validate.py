"""Tests for the validate command, driven through the CLI."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from support import run_cli

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


class ValidateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.temp = Path(directory.name)
        self.repo = self.temp / "repo"
        self.skill = self.repo / "skills" / "my-skill"
        self.default_cases = (
            self.repo / "tests" / "my-skill" / "description-trigger.json"
        )
        self.write_skill()

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

    def run_cli(
        self,
        *arguments: str | Path,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return run_cli(*arguments, cwd=cwd or self.temp, env=env)

    def fake_opencode_environment(self) -> tuple[Path, dict[str, str]]:
        marker = self.temp / "opencode-was-launched"
        bin_directory = self.temp / "bin"
        bin_directory.mkdir()
        fake_opencode = bin_directory / "opencode"
        fake_opencode.write_text(
            f"#!/bin/sh\ntouch {marker}\n",
            encoding="utf-8",
        )
        fake_opencode.chmod(0o755)
        env = {
            **os.environ,
            "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
        }
        return marker, env


class ValidateSuccessTest(ValidateTestCase):
    def assert_skill_passes(self) -> None:
        self.write_cases(valid_cases())
        result = self.run_cli("validate", self.skill)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Skill: my-skill", result.stdout)

    def test_literal_block_description_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: |\n"
            "  Summarize documents and pull out the key points.\n"
            "  Use when the user has a pile of notes."
        )

        self.assert_skill_passes()

    def test_folded_block_description_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: >\n"
            "  Summarize documents and pull out the key points.\n"
            "  Use when the user has a pile of notes."
        )

        self.assert_skill_passes()

    def test_quoted_description_is_accepted(self) -> None:
        for quote in ('"', "'"):
            with self.subTest(quote=quote):
                self.write_skill(
                    "name: my-skill\n"
                    f"description: {quote}Summarize documents: pull out the key points.{quote}"
                )

                self.assert_skill_passes()

    def test_plain_multiline_description_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "  Use when the user has a pile of notes."
        )

        self.assert_skill_passes()

    def test_quoted_multiline_description_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            'description: "Summarize documents and pull out the key points.\n'
            '  Use when the user has a pile of notes."'
        )

        self.assert_skill_passes()

    def test_indented_block_description_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: |2\n"
            "  Summarize documents and pull out the key points."
        )

        self.assert_skill_passes()

    def test_disable_model_invocation_false_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "disable-model-invocation: false"
        )

        self.assert_skill_passes()

    def test_metadata_autoinvoke_true_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "metadata:\n"
            "  opencode/autoinvoke: true"
        )

        self.assert_skill_passes()

    def test_unrelated_metadata_is_accepted(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "metadata:\n"
            "  credits:\n"
            "    author: Someone\n"
            "    opencode/autoinvoke: false"
        )

        self.assert_skill_passes()

    def test_valid_case_file_prints_summary(self) -> None:
        cases = self.write_cases(valid_cases(), self.temp / "elsewhere" / "cases.json")

        result = self.run_cli("validate", self.skill, "--cases", cases)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Skill: my-skill", result.stdout)
        self.assertIn(f"Case file: {cases}", result.stdout)
        self.assertIn("Positive: 3", result.stdout)
        self.assertIn("Negative: 3", result.stdout)

    def test_default_case_path_is_derived_from_skill_directory(self) -> None:
        cases = self.write_cases(valid_cases())

        result = self.run_cli("validate", self.skill)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(cases), result.stdout)
        self.assertIn("Positive: 3", result.stdout)
        self.assertIn("Negative: 3", result.stdout)

    def test_explicit_case_path_may_be_outside_the_repository_layout(self) -> None:
        cases = self.write_cases(valid_cases(), self.temp / "nested" / "other.json")

        result = self.run_cli("validate", self.skill, "--cases", cases)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(cases), result.stdout)

    def test_validation_never_launches_opencode(self) -> None:
        self.write_cases(valid_cases())
        marker, env = self.fake_opencode_environment()

        result = self.run_cli("validate", self.skill, env=env)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists(), "validation launched OpenCode")

    def test_rejected_validation_never_launches_opencode(self) -> None:
        self.write_cases("{ not json")
        marker, env = self.fake_opencode_environment()

        result = self.run_cli("validate", self.skill, env=env)

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertFalse(marker.exists(), "validation launched OpenCode")

    def test_ineligible_skill_rejection_never_launches_opencode(self) -> None:
        (self.skill / "SKILL.md").unlink()
        self.write_cases(valid_cases())
        marker, env = self.fake_opencode_environment()

        result = self.run_cli("validate", self.skill, env=env)

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertFalse(marker.exists(), "validation launched OpenCode")


class ValidateRejectionTest(ValidateTestCase):
    def assert_rejected(
        self,
        cases: JsonPayload,
        *message_parts: str,
    ) -> None:
        case_path = self.write_cases(cases)
        result = self.run_cli("validate", self.skill, "--cases", case_path)

        self.assertEqual(result.returncode, 2, result.stdout)
        for part in message_parts:
            self.assertIn(part, result.stderr)

    def assert_skill_rejected(
        self,
        skill: Path | None = None,
        *message_parts: str,
    ) -> None:
        case_path = self.write_cases(valid_cases(), self.temp / "cases.json")
        result = self.run_cli("validate", skill or self.skill, "--cases", case_path)

        self.assertEqual(result.returncode, 2, result.stdout)
        for part in message_parts:
            self.assertIn(part, result.stderr)

    def test_missing_skill_directory_is_rejected(self) -> None:
        missing = self.repo / "skills" / "missing-skill"

        self.assert_skill_rejected(missing, "skill directory", str(missing))

    def test_missing_skill_manifest_is_rejected(self) -> None:
        (self.skill / "SKILL.md").unlink()

        self.assert_skill_rejected(None, "SKILL.md")

    def test_non_kebab_case_skill_directory_is_rejected(self) -> None:
        skill = self.write_skill(directory=self.repo / "skills" / "My_Skill")

        self.assert_skill_rejected(skill, "My_Skill", "kebab-case")

    def test_missing_frontmatter_is_rejected(self) -> None:
        (self.skill / "SKILL.md").write_text("# My Skill\n", encoding="utf-8")

        self.assert_skill_rejected(None, "frontmatter")

    def test_unterminated_frontmatter_is_rejected(self) -> None:
        (self.skill / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Summarize documents.\n",
            encoding="utf-8",
        )

        self.assert_skill_rejected(None, "frontmatter")

    def test_missing_description_is_rejected(self) -> None:
        self.write_skill("name: my-skill\ncompatibility: none")

        self.assert_skill_rejected(None, "description")

    def test_empty_description_is_rejected(self) -> None:
        self.write_skill("name: my-skill\ndescription:")

        self.assert_skill_rejected(None, "description")

    def test_quoted_empty_description_is_rejected(self) -> None:
        for value in ('""', "''"):
            with self.subTest(value=value):
                self.write_skill(f"name: my-skill\ndescription: {value}")

                self.assert_skill_rejected(None, "description")

    def test_escaped_whitespace_description_is_rejected(self) -> None:
        self.write_skill('name: my-skill\ndescription: "\\n"')

        self.assert_skill_rejected(None, "description")

    def test_whitespace_only_block_description_is_rejected(self) -> None:
        self.write_skill("name: my-skill\ndescription: |\n   ")

        self.assert_skill_rejected(None, "description")

    def test_non_utf8_skill_manifest_is_rejected(self) -> None:
        (self.skill / "SKILL.md").write_bytes(b"\xff\xfe")

        self.assert_skill_rejected(None, "UTF-8")

    def test_disable_model_invocation_is_rejected(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "disable-model-invocation: true"
        )

        self.assert_skill_rejected(None, "disable-model-invocation", "model invocation")

    def test_quoted_disable_model_invocation_is_rejected(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            'disable-model-invocation: "true"'
        )

        self.assert_skill_rejected(None, "disable-model-invocation", "model invocation")

    def test_metadata_autoinvoke_false_is_rejected(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "metadata:\n"
            "  opencode/autoinvoke: false"
        )

        self.assert_skill_rejected(
            None, "metadata.opencode/autoinvoke", "model invocation"
        )

    def test_quoted_metadata_autoinvoke_false_is_rejected(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "metadata:\n"
            '  "opencode/autoinvoke": "false"'
        )

        self.assert_skill_rejected(
            None, "metadata.opencode/autoinvoke", "model invocation"
        )

    def test_flow_metadata_is_rejected_as_unsupported(self) -> None:
        self.write_skill(
            "name: my-skill\n"
            "description: Summarize documents and pull out the key points.\n"
            "metadata: { opencode/autoinvoke: false }"
        )

        self.assert_skill_rejected(None, "metadata", "block syntax")

    def test_whitespace_only_indented_block_description_is_rejected(self) -> None:
        self.write_skill("name: my-skill\ndescription: |2\n  ")

        self.assert_skill_rejected(None, "description")

    def test_non_string_description_is_rejected(self) -> None:
        for value in ("false", "42", "[]", "{}"):
            with self.subTest(value=value):
                self.write_skill(f"name: my-skill\ndescription: {value}")

                self.assert_skill_rejected(None, "description")

    def test_missing_default_case_file_reports_computed_path_and_hint(self) -> None:
        result = self.run_cli("validate", self.skill)

        self.assertEqual(result.returncode, 2)
        self.assertIn(str(self.default_cases), result.stderr)
        self.assertIn("--cases", result.stderr)

    def test_invalid_json_is_rejected(self) -> None:
        self.assert_rejected("{ not json", "invalid JSON")

    def test_non_utf8_case_file_is_rejected(self) -> None:
        case_path = self.default_cases
        case_path.parent.mkdir(parents=True)
        case_path.write_bytes(b"\xff\xfe")

        result = self.run_cli("validate", self.skill, "--cases", case_path)

        self.assertEqual(result.returncode, 2)
        self.assertIn("UTF-8", result.stderr)

    def test_case_file_must_be_a_json_object(self) -> None:
        self.assert_rejected([], "JSON object")

    def test_case_must_be_an_object(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = "Summarize this document for me."

        self.assert_rejected(cases, "direct-request", "must be an object")

    def test_missing_prompt_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {"expect": True}

        self.assert_rejected(cases, "direct-request", "missing", "prompt")

    def test_missing_expect_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {"prompt": "Summarize this document for me."}

        self.assert_rejected(cases, "direct-request", "missing", "expect")

    def test_empty_prompt_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {"prompt": "", "expect": True}

        self.assert_rejected(cases, "direct-request", "prompt", "empty")

    def test_whitespace_only_prompt_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {"prompt": "   ", "expect": True}

        self.assert_rejected(cases, "direct-request", "prompt", "empty")

    def test_non_string_prompt_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {"prompt": 42, "expect": True}

        self.assert_rejected(cases, "direct-request", "prompt", "string")

    def test_non_boolean_expect_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {
            "prompt": "Summarize this document for me.",
            "expect": "true",
        }

        self.assert_rejected(cases, "direct-request", "expect", "boolean")

    def test_non_kebab_case_id_is_rejected(self) -> None:
        cases = valid_cases()
        cases["Direct_Request"] = {
            "prompt": "Summarize this document for me.",
            "expect": True,
        }

        self.assert_rejected(cases, "Direct_Request", "kebab-case")

    def test_unknown_field_is_rejected(self) -> None:
        cases = valid_cases()
        cases["direct-request"] = {
            "prompt": "Summarize this document for me.",
            "expect": True,
            "notes": "not part of the schema",
        }

        self.assert_rejected(cases, "direct-request", "unknown", "notes")

    def test_duplicate_case_id_is_rejected(self) -> None:
        self.assert_rejected(
            (
                '{"direct-request": {"prompt": "One", "expect": true},'
                ' "direct-request": {"prompt": "Two", "expect": false}}'
            ),
            "duplicate key",
            "direct-request",
        )

    def test_duplicate_field_is_rejected(self) -> None:
        self.assert_rejected(
            '{"direct-request": {"prompt": "One", "prompt": "Two", "expect": true}}',
            "duplicate key",
            "prompt",
        )

    def test_fewer_than_three_positive_cases_is_rejected(self) -> None:
        cases = valid_cases()
        cases["near-miss-phrasing"]["expect"] = False

        self.assert_rejected(cases, "at least 3", "expect: true")

    def test_fewer_than_three_negative_cases_is_rejected(self) -> None:
        cases = valid_cases()
        cases["too-vague"]["expect"] = True

        self.assert_rejected(cases, "at least 3", "expect: false")

    def test_second_skill_directory_is_rejected(self) -> None:
        self.write_cases(valid_cases())

        result = self.run_cli("validate", self.skill, self.skill)

        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_repository_wide_flag_is_rejected(self) -> None:
        self.write_cases(valid_cases())

        result = self.run_cli("validate", "--all", self.skill)

        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)
