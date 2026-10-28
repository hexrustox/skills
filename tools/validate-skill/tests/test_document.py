import unittest
from collections.abc import Iterable

from support import build_document, rules, valid_frontmatter
from validate_skill.document import validate_document
from validate_skill.model import Finding


def validate(
    text: str,
    *,
    directory_name: str = "example",
    existing: Iterable[str] = (),
) -> list[Finding]:
    return validate_document(text, directory_name, frozenset(existing).__contains__)


class DocumentTestCase(unittest.TestCase):
    def assert_document_rules(
        self,
        text: str,
        expected: list[str],
        *,
        directory_name: str = "example",
        existing: Iterable[str] = (),
    ) -> None:
        self.assertEqual(
            rules(validate(text, directory_name=directory_name, existing=existing)),
            expected,
        )

    def test_valid_document_has_no_findings(self) -> None:
        self.assert_document_rules(build_document("# Example\n\nFollow these steps."), [])

    def test_missing_frontmatter_reports_only_the_parse_rule(self) -> None:
        self.assert_document_rules("# Example\n\nNo frontmatter here.\n", ["frontmatter.missing"])

    def test_malformed_yaml_reports_the_parse_rule(self) -> None:
        self.assert_document_rules(
            "---\nname: [unclosed\n---\n\n# Example\n",
            ["frontmatter.malformed"],
        )

    def test_unclosed_frontmatter_reports_the_parse_rule(self) -> None:
        self.assert_document_rules("---\nname: example\n\n# Example\n", ["frontmatter.malformed"])

    def test_non_mapping_frontmatter_reports_the_parse_rule(self) -> None:
        self.assert_document_rules(
            "---\n- one\n- two\n---\n\n# Example\n",
            ["frontmatter.not-mapping"],
        )

    def test_missing_name_reports_name_missing(self) -> None:
        frontmatter = (
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(build_document(frontmatter=frontmatter), ["name.missing"])

    def test_missing_description_reports_description_missing(self) -> None:
        frontmatter = 'name: example\nmetadata:\n  version: "1.0.0"\n'
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["description.missing"],
        )

    def test_empty_name_and_description_report_empty_rules(self) -> None:
        frontmatter = (
            'name: ""\n'
            'description: ""\n'
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["name.empty", "description.empty"],
        )

    def test_non_string_name_and_description_report_type_rules(self) -> None:
        frontmatter = (
            "name: 5\n"
            "description: [text]\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["name.type", "description.type"],
        )

    def test_name_over_64_characters_reports_length(self) -> None:
        long_name = "a" * 65
        self.assert_document_rules(
            build_document(frontmatter=valid_frontmatter(name=long_name), name=long_name),
            ["name.length"],
            directory_name=long_name,
        )

    def test_invalid_name_grammar_reports_grammar(self) -> None:
        for invalid_name in ("Example", "example_skill", "-example", "example-", "ex--ample"):
            with self.subTest(name=invalid_name):
                self.assert_document_rules(
                    build_document(
                        frontmatter=valid_frontmatter(name=invalid_name),
                        name=invalid_name,
                    ),
                    ["name.grammar"],
                    directory_name=invalid_name,
                )

    def test_name_not_matching_directory_reports_directory(self) -> None:
        self.assert_document_rules(
            build_document(frontmatter=valid_frontmatter(name="other"), name="other"),
            ["name.directory"],
            directory_name="example",
        )

    def test_name_and_description_at_maximum_length_pass(self) -> None:
        max_name = "a" * 64
        frontmatter = (
            f"name: {max_name}\n"
            f"description: {'d' * 1024}\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter, name=max_name),
            [],
            directory_name=max_name,
        )

    def test_description_over_1024_characters_reports_length(self) -> None:
        frontmatter = (
            "name: example\n"
            f"description: {'d' * 1025}\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["description.length"],
        )

    def test_valid_optional_fields_pass(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "disable-model-invocation: true\n"
            "license: MIT\n"
            "compatibility: Requires Python 3.11 or newer.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "allowed-tools: Bash Read Write\n"
        )
        self.assert_document_rules(build_document(frontmatter=frontmatter), [])

    def test_non_boolean_disable_model_invocation_reports_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            'disable-model-invocation: "yes"\n'
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["frontmatter.disable-model-invocation.type"],
        )

    def test_non_string_license_reports_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "license: 123\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["frontmatter.license.type"],
        )

    def test_non_string_compatibility_reports_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "compatibility: [linux]\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["frontmatter.compatibility.type"],
        )

    def test_compatibility_outside_1_to_500_characters_reports_length(self) -> None:
        for compatibility in ("", "c" * 501):
            with self.subTest(length=len(compatibility)):
                frontmatter = (
                    "name: example\n"
                    "description: Does an example task.\n"
                    f'compatibility: "{compatibility}"\n'
                    "metadata:\n"
                    '  version: "1.0.0"\n'
                )
                self.assert_document_rules(
                    build_document(frontmatter=frontmatter),
                    ["frontmatter.compatibility.length"],
                )

    def test_non_mapping_metadata_reports_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata: [one]\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.type"],
        )

    def test_non_string_metadata_value_reports_value_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "  owner: 5\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.value-type", "metadata.extra-key"],
        )

    def test_malformed_allowed_tools_shape_reports_shape(self) -> None:
        for allowed_tools in ("", "Bash\\nRead"):
            with self.subTest(allowed_tools=allowed_tools):
                frontmatter = (
                    "name: example\n"
                    "description: Does an example task.\n"
                    "metadata:\n"
                    '  version: "1.0.0"\n'
                    f'allowed-tools: "{allowed_tools}"\n'
                )
                self.assert_document_rules(
                    build_document(frontmatter=frontmatter),
                    ["frontmatter.allowed-tools.shape"],
                )

    def test_non_string_allowed_tools_reports_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "allowed-tools: [Bash]\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["frontmatter.allowed-tools.type"],
        )

    def test_missing_metadata_reports_version_missing(self) -> None:
        frontmatter = "name: example\ndescription: Does an example task.\n"
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.version.missing"],
        )

    def test_empty_metadata_mapping_reports_version_missing(self) -> None:
        frontmatter = "name: example\ndescription: Does an example task.\nmetadata: {}\n"
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.version.missing"],
        )

    def test_non_string_metadata_key_reports_key_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "  5: five\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.key-type"],
        )

    def test_empty_metadata_version_reports_version_empty(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: ""\n'
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.version.empty"],
        )

    def test_non_string_metadata_version_reports_version_type(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            "  version: 1\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.version.type"],
        )

    def test_extra_metadata_key_warns(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "  owner: team\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["metadata.extra-key"],
        )

    def test_unknown_top_level_key_warns(self) -> None:
        frontmatter = (
            "name: example\n"
            "description: Does an example task.\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            "unknown: value\n"
        )
        self.assert_document_rules(
            build_document(frontmatter=frontmatter),
            ["frontmatter.unknown-key"],
        )

    def test_empty_body_reports_body_empty(self) -> None:
        self.assert_document_rules(build_document(""), ["body.empty"])

    def test_whitespace_only_body_reports_body_empty(self) -> None:
        self.assert_document_rules(build_document("   \n\t"), ["body.empty"])

    def test_body_over_500_lines_warns(self) -> None:
        body = "\n".join(f"Line {index}" for index in range(501))
        self.assert_document_rules(build_document(body), ["body.lines"])

    def test_body_over_5000_estimated_tokens_warns(self) -> None:
        self.assert_document_rules(build_document("x" * 20_001), ["body.tokens"])

    def test_missing_local_references_warn(self) -> None:
        body = (
            "See [the guide](references/guide.md), the logo in "
            "[assets](assets/logo.png), and run `scripts/run.sh`."
        )
        self.assert_document_rules(
            build_document(body),
            ["reference.missing", "reference.missing", "reference.missing"],
        )

    def test_references_in_fenced_code_are_ignored(self) -> None:
        body = (
            "```markdown\n"
            "See [the guide](references/missing.md) and run `scripts/missing.sh`.\n"
            "```"
        )
        self.assert_document_rules(build_document(body), [])

    def test_reference_style_link_is_checked(self) -> None:
        body = "See [the guide][guide].\n\n[guide]: references/missing.md"
        self.assert_document_rules(build_document(body), ["reference.missing"])

    def test_multiple_paths_in_one_code_span_are_checked(self) -> None:
        self.assert_document_rules(
            build_document("Run `scripts/run.sh references/guide.md`."),
            ["reference.missing", "reference.missing"],
        )

    def test_reference_with_parentheses_is_checked(self) -> None:
        self.assert_document_rules(
            build_document("Read [the guide](references/guide_(v2).md)."),
            [],
            existing={"references/guide_(v2).md"},
        )

    def test_reference_more_than_one_level_below_root_warns(self) -> None:
        self.assert_document_rules(
            build_document("Run `scripts/deep/run.sh`."),
            ["reference.too-deep"],
            existing={"scripts/deep/run.sh"},
        )

    def test_urls_anchors_and_absolute_paths_do_not_warn(self) -> None:
        body = "\n".join(
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
        self.assert_document_rules(build_document(body), [])

    def test_body_at_line_and_token_limits_does_not_warn(self) -> None:
        cases = {
            "lines": "\n".join(f"Line {index}" for index in range(499)),
            "tokens": "x" * 19_998,
        }
        for name, body in cases.items():
            with self.subTest(limit=name):
                self.assert_document_rules(build_document(body), [])

    def test_body_trailing_blank_lines_count_toward_line_limit(self) -> None:
        body = "\n".join(f"Line {index}" for index in range(499)) + "\n\n"
        self.assert_document_rules(build_document(body), ["body.lines"])

    def test_body_token_estimate_counts_the_full_body(self) -> None:
        self.assert_document_rules(build_document("x" * 19_999), ["body.tokens"])

    def test_reference_one_level_below_root_does_not_warn(self) -> None:
        self.assert_document_rules(
            build_document("Read [the guide](./references/guide.md#usage)."),
            [],
            existing={"references/guide.md"},
        )

    def test_duplicate_references_are_reported_once(self) -> None:
        body = (
            "Read [a](references/a.md) and "
            "[a again](references/a.md)."
        )
        self.assert_document_rules(build_document(body), ["reference.missing"])

    def test_reference_location_counts_body_lines(self) -> None:
        findings = validate(
            build_document("# Example\n\nSee [x](references/a.md).")
        )
        self.assertEqual(findings[0].rule, "reference.missing")
        self.assertEqual(findings[0].location, "body:4")

    def test_reference_location_after_fenced_code_counts_body_lines(self) -> None:
        findings = validate(
            build_document("```\nfenced\n```\n\nSee [x](references/a.md).")
        )
        self.assertEqual(findings[0].rule, "reference.missing")
        self.assertEqual(findings[0].location, "body:6")


if __name__ == "__main__":
    unittest.main()
