import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "validate_skill", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        self._registrations: dict[Path, list[str]] = {}

    def write_manifest(
        self, entries: list[str], *, plugin_root: Path | None = None
    ) -> Path:
        manifest = (plugin_root or self.root) / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"skills": entries}), encoding="utf-8")
        return manifest

    def write_skill(
        self,
        content: str,
        name: str = "example",
        *,
        base: Path | None = None,
        register: bool = True,
    ) -> Path:
        skill_dir = (base or self.root) / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(textwrap.dedent(content), encoding="utf-8")
        if register:
            entries = self._registrations.setdefault(skill_dir.parent, [])
            entries.append(f"./{name}")
            self.write_manifest(entries, plugin_root=skill_dir.parent)
        return skill_dir

    def write_valid_skill(
        self, body: str, *, name: str = "example", base: Path | None = None
    ) -> Path:
        content = (
            "---\n"
            f"name: {name}\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "---\n\n"
            f"{body}\n"
        )
        return self.write_skill(content, name=name, base=base)

    def test_valid_skill_exits_zero_with_summary(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example

            Follow these steps.
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"skill: {skill_dir}", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 0 warnings", result.stdout)

    def test_missing_frontmatter_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill("# Example\n\nNo frontmatter here.\n")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.missing", result.stdout)
        self.assertIn("1 skill checked, 1 error, 0 warnings", result.stdout)

    def test_malformed_yaml_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: [unclosed
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.malformed", result.stdout)

    def test_non_mapping_frontmatter_exits_one_with_frontmatter_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            - one
            - two
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.not-mapping", result.stdout)

    def test_missing_name_exits_one_with_name_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.missing", result.stdout)

    def test_missing_description_exits_one_with_description_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error description.missing", result.stdout)

    def test_empty_name_and_description_exit_one_with_relevant_rules(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: "  "
            description: ""
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.empty", result.stdout)
        self.assertIn("error description.empty", result.stdout)

    def test_non_string_name_and_description_exit_one_with_relevant_rules(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: 123
            description: [not, text]
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.type", result.stdout)
        self.assertIn("error description.type", result.stdout)

    def test_skill_file_path_is_accepted(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir / "SKILL.md"), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 errors", result.stdout)

    def test_findings_are_grouped_per_skill_before_summary(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], f"skill: {skill_dir}")
        self.assertTrue(lines[1].startswith("  error name.missing:"))
        self.assertTrue(lines[2].startswith("  error description.missing:"))
        self.assertEqual(lines[-1], "1 skill checked, 2 errors, 0 warnings")

    def test_no_arguments_exits_two(self) -> None:
        result = run_cli(cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)

    def test_nonexistent_path_exits_two(self) -> None:
        result = run_cli(str(self.root / "missing"), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)

    def test_directory_without_skill_file_exits_two(self) -> None:
        empty_dir = self.root / "empty"
        empty_dir.mkdir()

        result = run_cli(str(empty_dir), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("not a SKILL.md file or skill directory", result.stderr)

    def test_referenced_scripts_are_not_executed(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            Run `scripts/mutate.sh`.
            """
        )
        script = skill_dir / "scripts" / "mutate.sh"
        script.parent.mkdir()
        marker = self.root / "executed"
        script.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
        script.chmod(0o755)

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_name_over_64_characters_exits_one_with_length_rule(self) -> None:
        long_name = "a" * 65
        skill_dir = self.write_skill(
            f"""\
            ---
            name: {long_name}
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            name=long_name,
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.length", result.stdout)

    def test_name_with_invalid_grammar_exits_one_with_grammar_rule(self) -> None:
        for invalid_name in ("Example", "example_skill", "-example", "example-", "ex--ample"):
            with self.subTest(name=invalid_name):
                skill_dir = self.write_skill(
                    f"""\
                    ---
                    name: "{invalid_name}"
                    description: Does an example task.
                    metadata:
                      version: "1.0.0"
                    ---

                    # Example
                    """,
                    name=invalid_name,
                )

                result = run_cli(str(skill_dir), cwd=self.root)

                self.assertEqual(result.returncode, 1)
                self.assertIn("error name.grammar", result.stdout)

    def test_name_not_matching_directory_exits_one_with_directory_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: other
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error name.directory", result.stdout)

    def test_name_and_description_at_maximum_length_exit_zero(self) -> None:
        max_name = "a" * 64
        skill_dir = self.write_skill(
            f"""\
            ---
            name: {max_name}
            description: {"d" * 1024}
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            name=max_name,
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)

    def test_description_over_1024_characters_exits_one_with_length_rule(self) -> None:
        skill_dir = self.write_skill(
            f"""\
            ---
            name: example
            description: {"d" * 1025}
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error description.length", result.stdout)

    def test_valid_optional_fields_exit_zero(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            disable-model-invocation: true
            license: MIT
            compatibility: Requires Python 3.11 or newer.
            metadata:
              version: "1.0.0"
            allowed-tools: Bash Read Write
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)

    def test_non_boolean_disable_model_invocation_exits_one_with_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            disable-model-invocation: "yes"
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.disable-model-invocation.type", result.stdout)

    def test_non_string_license_exits_one_with_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            license: 123
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.license.type", result.stdout)

    def test_non_string_compatibility_exits_one_with_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            compatibility: [linux]
            metadata:
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.compatibility.type", result.stdout)

    def test_compatibility_outside_1_to_500_characters_exits_one_with_length_rule(self) -> None:
        for compatibility in ("", "c" * 501):
            with self.subTest(length=len(compatibility)):
                name = f"example-{len(compatibility)}"
                skill_dir = self.write_skill(
                    f"""\
                    ---
                    name: {name}
                    description: Does an example task.
                    compatibility: "{compatibility}"
                    metadata:
                      version: "1.0.0"
                    ---

                    # Example
                    """,
                    name=name,
                )

                result = run_cli(str(skill_dir), cwd=self.root)

                self.assertEqual(result.returncode, 1)
                self.assertIn("error frontmatter.compatibility.length", result.stdout)

    def test_non_mapping_metadata_exits_one_with_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata: [one]
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.type", result.stdout)

    def test_non_string_metadata_value_exits_one_with_value_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
              owner: 5
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.value-type", result.stdout)

    def test_malformed_allowed_tools_shape_exits_one_with_shape_rule(self) -> None:
        for index, allowed_tools in enumerate(("", "Bash\\nRead")):
            with self.subTest(allowed_tools=allowed_tools):
                name = f"example-{index}"
                skill_dir = self.write_skill(
                    f"""\
                    ---
                    name: {name}
                    description: Does an example task.
                    metadata:
                      version: "1.0.0"
                    allowed-tools: "{allowed_tools}"
                    ---

                    # Example
                    """,
                    name=name,
                )

                result = run_cli(str(skill_dir), cwd=self.root)

                self.assertEqual(result.returncode, 1)
                self.assertIn("error frontmatter.allowed-tools.shape", result.stdout)

    def test_non_string_allowed_tools_exits_one_with_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            allowed-tools: [Bash]
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error frontmatter.allowed-tools.type", result.stdout)

    def test_missing_metadata_exits_one_with_version_missing_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.version.missing", result.stdout)

    def test_empty_metadata_mapping_exits_one_with_version_missing_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata: {}
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.version.missing", result.stdout)

    def test_non_string_metadata_key_exits_one_with_key_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              1: one
              version: "1.0.0"
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.key-type", result.stdout)

    def test_empty_metadata_version_exits_one_with_version_empty_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "  "
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.version.empty", result.stdout)

    def test_non_string_metadata_version_exits_one_with_version_type_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: 1.0
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error metadata.version.type", result.stdout)

    def test_extra_metadata_key_warns_and_exits_zero(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
              owner: team
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning metadata.extra-key", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 1 warning", result.stdout)

    def test_unknown_top_level_key_warns_and_exits_zero(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            unknown: value
            ---

            # Example
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning frontmatter.unknown-key", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 1 warning", result.stdout)

    def test_empty_body_exits_one_with_body_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---
            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error body.empty", result.stdout)

    def test_whitespace_only_body_exits_one_with_body_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---



            """
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error body.empty", result.stdout)

    def test_body_over_500_lines_warns_and_exits_zero(self) -> None:
        body = "\n".join(f"Line {index}" for index in range(501))
        skill_dir = self.write_valid_skill(body)

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning body.lines", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 1 warning", result.stdout)

    def test_body_over_5000_estimated_tokens_warns_and_exits_zero(self) -> None:
        body = "x" * 20_001
        skill_dir = self.write_valid_skill(body)

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning body.tokens", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 1 warning", result.stdout)

    def test_missing_local_references_warn_and_exit_zero(self) -> None:
        skill_dir = self.write_valid_skill(
            "See [the guide](references/guide.md), the logo in "
            "[assets](assets/logo.png), and run `scripts/run.sh`."
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning reference.missing", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 3 warnings", result.stdout)

    def test_references_in_fenced_code_are_ignored(self) -> None:
        skill_dir = self.write_valid_skill(
            "```markdown\n"
            "See [the guide](references/missing.md) and run `scripts/missing.sh`.\n"
            "```"
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("warning reference.", result.stdout)
        self.assertIn("0 errors, 0 warnings", result.stdout)

    def test_reference_style_link_is_checked(self) -> None:
        skill_dir = self.write_valid_skill(
            "See [the guide][guide].\n\n[guide]: references/missing.md"
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning reference.missing", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 1 warning", result.stdout)

    def test_multiple_paths_in_one_code_span_are_checked(self) -> None:
        skill_dir = self.write_valid_skill(
            "Run `scripts/run.sh references/guide.md`."
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning reference.missing", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 2 warnings", result.stdout)

    def test_reference_with_parentheses_is_checked(self) -> None:
        skill_dir = self.write_valid_skill("Read [the guide](references/guide_(v2).md).")
        reference = skill_dir / "references" / "guide_(v2).md"
        reference.parent.mkdir(parents=True)
        reference.write_text("# Guide\n", encoding="utf-8")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("warning reference.", result.stdout)
        self.assertIn("0 errors, 0 warnings", result.stdout)

    def test_reference_more_than_one_level_below_root_warns_and_exits_zero(self) -> None:
        skill_dir = self.write_valid_skill("Run `scripts/deep/run.sh`.")
        script = skill_dir / "scripts" / "deep" / "run.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/sh\n", encoding="utf-8")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning reference.too-deep", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 1 warning", result.stdout)

    def test_urls_anchors_and_absolute_paths_do_not_warn(self) -> None:
        skill_dir = self.write_valid_skill(
            "\n".join(
                (
                    "[site](https://example.com/scripts/guide.md)",
                    "[anchor](#section)",
                    "[absolute](/tmp/scripts/run.sh)",
                    "`https://example.com/scripts/run.sh`",
                    "`#section`",
                    "`/tmp/scripts/run.sh`",
                    "`C:\\scripts\\run.sh`",
                )
            )
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("warning reference.", result.stdout)
        self.assertIn("1 skill checked, 0 errors, 0 warnings", result.stdout)

    def test_body_at_line_and_token_limits_does_not_warn(self) -> None:
        cases = {
            "lines": "\n".join(f"Line {index}" for index in range(500)),
            "tokens": "x" * 20_000,
        }
        for name, body in cases.items():
            with self.subTest(limit=name):
                skill_dir = self.write_valid_skill(body, name=name)

                result = run_cli(str(skill_dir), cwd=self.root)

                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertNotIn("warning body.", result.stdout)
                self.assertIn("0 errors, 0 warnings", result.stdout)

    def test_reference_one_level_below_root_does_not_warn(self) -> None:
        skill_dir = self.write_valid_skill("Read [the guide](./references/guide.md#usage).")
        reference = skill_dir / "references" / "guide.md"
        reference.parent.mkdir(parents=True)
        reference.write_text("# Guide\n", encoding="utf-8")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("warning reference.", result.stdout)
        self.assertIn("0 errors, 0 warnings", result.stdout)

    def test_unregistered_skill_exits_one_with_registration_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            register=False,
        )
        self.write_manifest(["./other"])

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error plugin.unregistered", result.stdout)

    def test_missing_plugin_manifest_exits_one_with_manifest_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            register=False,
        )

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error plugin.manifest-missing", result.stdout)

    def test_equivalent_manifest_path_spellings_register_the_skill(self) -> None:
        entries = ["./example", "example", "././example/", ".\\example"]
        for index, entry in enumerate(entries):
            with self.subTest(entry=entry):
                base = self.root / f"case-{index}"
                skill_dir = self.write_skill(
                    """\
                    ---
                    name: example
                    description: Does an example task.
                    metadata:
                      version: "1.0.0"
                    ---

                    # Example
                    """,
                    base=base,
                    register=False,
                )
                self.write_manifest([entry], plugin_root=base)

                result = run_cli(str(skill_dir), cwd=self.root)

                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("0 errors", result.stdout)

    def test_nearest_plugin_manifest_governs_registration(self) -> None:
        nested = self.root / "nested"
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            base=nested,
            register=False,
        )
        self.write_manifest(["./nested/example"])
        self.write_manifest(["./other"], plugin_root=nested)

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error plugin.unregistered", result.stdout)

    def test_invalid_plugin_manifest_json_exits_one_with_manifest_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            register=False,
        )
        manifest = self.root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text("{not json", encoding="utf-8")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error plugin.manifest-invalid", result.stdout)

    def test_registered_skill_reached_through_symlink_exits_zero(self) -> None:
        plugin_root = self.root / "plugin"
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            base=self.root / "targets",
            register=False,
        )
        self.write_manifest(["./example"], plugin_root=plugin_root)
        linked_skill = plugin_root / "example"
        linked_skill.symlink_to(skill_dir, target_is_directory=True)

        result = run_cli(str(linked_skill), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)

    def test_plugin_manifest_without_skills_array_exits_one_with_manifest_rule(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            ---

            # Example
            """,
            register=False,
        )
        manifest = self.root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"skills": "example"}), encoding="utf-8")

        result = run_cli(str(skill_dir), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error plugin.manifest-invalid", result.stdout)

    def test_multiple_paths_are_validated_in_one_run(self) -> None:
        first = self.write_valid_skill("First skill.", name="first")
        second = self.write_valid_skill("Second skill.", name="second")

        result = run_cli(str(first), str(second), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"skill: {first}", result.stdout)
        self.assertIn(f"skill: {second}", result.stdout)
        self.assertIn("2 skills checked, 0 errors, 0 warnings", result.stdout)

    def test_validation_continues_after_an_earlier_path_fails(self) -> None:
        failing = self.write_skill(
            """\
            ---
            name: failing
            metadata:
              version: "1.0.0"
            ---

            # Failing
            """,
            name="failing",
        )
        passing = self.write_valid_skill("Passing skill.", name="passing")

        result = run_cli(str(failing), str(passing), cwd=self.root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("error description.missing", result.stdout)
        self.assertIn(f"skill: {passing}", result.stdout)
        self.assertNotIn("error ", result.stdout.split(f"skill: {passing}", 1)[1])
        self.assertIn("2 skills checked, 1 error, 0 warnings", result.stdout)

    def test_multiple_paths_with_only_warnings_exit_zero(self) -> None:
        first = self.write_skill(
            """\
            ---
            name: first
            description: Does an example task.
            metadata:
              version: "1.0.0"
            unknown: value
            ---

            First skill.
            """,
            name="first",
        )
        second = self.write_valid_skill("Second skill.", name="second")

        result = run_cli(str(first), str(second), cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warning frontmatter.unknown-key", result.stdout)
        self.assertIn("2 skills checked, 0 errors, 1 warning", result.stdout)

    def test_nonexistent_path_in_a_batch_exits_two(self) -> None:
        valid = self.write_valid_skill("Valid skill.")

        result = run_cli(str(self.root / "missing"), str(valid), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)
        self.assertIn(f"skill: {valid}", result.stdout)

    def test_json_output_contains_skills_findings_and_summary(self) -> None:
        warning = self.write_skill(
            """\
            ---
            name: warning
            description: Does an example task.
            metadata:
              version: "1.0.0"
              owner: team
            ---

            # Warning
            """,
            name="warning",
        )
        failing = self.write_skill(
            """\
            ---
            name: failing
            metadata:
              version: "1.0.0"
            ---

            # Failing
            """,
            name="failing",
        )

        result = run_cli("--json", str(warning), str(failing), cwd=self.root)

        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"skills", "summary"})
        self.assertEqual(payload["summary"], {"skills": 2, "errors": 1, "warnings": 1})
        self.assertEqual(
            [skill["path"] for skill in payload["skills"]],
            [str(warning), str(failing)],
        )
        for skill in payload["skills"]:
            for finding in skill["findings"]:
                self.assertEqual(
                    set(finding), {"severity", "rule", "message", "location"}
                )
                self.assertIn(finding["severity"], {"error", "warning"})
                for value in finding.values():
                    self.assertIsInstance(value, str)
                    self.assertTrue(value)
        self.assertEqual(
            payload["skills"][0]["findings"],
            [
                {
                    "severity": "warning",
                    "rule": "metadata.extra-key",
                    "message": "metadata.owner is not part of the repo convention; "
                    "only version is expected",
                    "location": "metadata.owner",
                }
            ],
        )
        self.assertEqual(payload["skills"][1]["findings"][0]["rule"], "description.missing")

    def test_json_findings_match_text_findings(self) -> None:
        warning = self.write_skill(
            """\
            ---
            name: warning
            description: Does an example task.
            metadata:
              version: "1.0.0"
              owner: team
            ---

            Read `references/missing.md`.
            """,
            name="warning",
        )
        failing = self.write_skill(
            """\
            ---
            name: failing
            description: Does an example task.
            metadata: {}
            ---

            # Failing
            """,
            name="failing",
        )

        text_result = run_cli(str(warning), str(failing), cwd=self.root)
        json_result = run_cli("--json", str(warning), str(failing), cwd=self.root)

        self.assertEqual(json_result.returncode, text_result.returncode)
        payload = json.loads(json_result.stdout)
        text_finding_count = sum(
            line.startswith(("  error ", "  warning "))
            for line in text_result.stdout.splitlines()
        )
        json_finding_count = sum(
            len(skill["findings"]) for skill in payload["skills"]
        )
        self.assertEqual(json_finding_count, text_finding_count)
        self.assertIn("metadata.extra-key", text_result.stdout)
        for skill in payload["skills"]:
            for finding in skill["findings"]:
                self.assertIn(
                    f"{finding['severity']} {finding['rule']}: "
                    f"{finding['message']} [{finding['location']}]",
                    text_result.stdout,
                )

    def test_json_output_for_warnings_only_exits_zero(self) -> None:
        skill_dir = self.write_skill(
            """\
            ---
            name: example
            description: Does an example task.
            metadata:
              version: "1.0.0"
            unknown: value
            ---

            # Example
            """,
        )

        result = run_cli(str(skill_dir), "--json", cwd=self.root)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"], {"skills": 1, "errors": 0, "warnings": 1})
        self.assertEqual(len(payload["skills"][0]["findings"]), 1)

    def test_json_output_with_usage_error_exits_two(self) -> None:
        result = run_cli("--json", str(self.root / "missing"), cwd=self.root)

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["skills"], [])
        self.assertEqual(payload["summary"], {"skills": 0, "errors": 0, "warnings": 0})

    def test_all_authored_skills_validate_together(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        paths = sorted(str(path) for path in repo_root.glob("skills/**/SKILL.md"))
        self.assertGreater(len(paths), 0)

        result = run_cli(*paths, cwd=repo_root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"{len(paths)} skills checked, 0 errors", result.stdout)


if __name__ == "__main__":
    unittest.main()
