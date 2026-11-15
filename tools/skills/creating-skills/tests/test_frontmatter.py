import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.frontmatter import FrontmatterError, parse_skill_md


class ParseSkillMdTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.skill_dir = Path(self._temp_dir.name) / "example-skill"
        self.skill_dir.mkdir()

    def write_skill(self, text: str) -> str:
        content = textwrap.dedent(text).lstrip("\n")
        (self.skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return content

    def test_returns_name_description_and_full_content(self) -> None:
        content = self.write_skill(
            """
            ---
            name: example-skill
            description: Does example work.
            license: Apache-2.0
            ---

            # Example

            Follow these steps.
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(skill.name, "example-skill")
        self.assertEqual(skill.description, "Does example work.")
        self.assertEqual(skill.content, content)

    def test_folds_a_folded_description_into_one_line(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: >-
              Does the first thing and
              then the second thing.
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(
            skill.description, "Does the first thing and then the second thing."
        )

    def test_joins_a_literal_description_into_one_line(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: |
              Does the first thing and
              then the second thing.
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(
            skill.description, "Does the first thing and then the second thing."
        )

    def test_accepts_quoted_values_and_escaped_quotes(self) -> None:
        self.write_skill(
            r"""
            ---
            name: "example-skill"
            description: "Use when the user says \"review this\"."
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(skill.name, "example-skill")
        self.assertEqual(skill.description, 'Use when the user says "review this".')

    def test_preserves_colons_in_an_unquoted_description(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: Use when: the user needs an example.
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(skill.description, "Use when: the user needs an example.")

    def test_joins_an_indented_plain_continuation(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: Does the first thing and
              then the second thing.
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(
            skill.description, "Does the first thing and then the second thing."
        )

    def test_accepts_single_quoted_values(self) -> None:
        self.write_skill(
            """
            ---
            name: 'example-skill'
            description: 'Use when the user says ''review this''.'
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(skill.name, "example-skill")
        self.assertEqual(skill.description, "Use when the user says 'review this'.")

    def test_strips_inline_comments_from_unquoted_values(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: Does example work. # Shown in the skill list.
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(skill.description, "Does example work.")

    def test_rejects_an_unsupported_inline_value(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: [unclosed
            ---
            """
        )

        with self.assertRaisesRegex(FrontmatterError, "unsupported inline value"):
            parse_skill_md(self.skill_dir)

    def test_ignores_unrelated_and_nested_frontmatter(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            compatibility: Requires Python 3.11+.
            description: Does example work.
            metadata:
              owner: example
              nested:
                key: value
            allowed-tools:
              - Read
              - Grep
            ---
            """
        )

        skill = parse_skill_md(self.skill_dir)

        self.assertEqual(skill.name, "example-skill")
        self.assertEqual(skill.description, "Does example work.")

    def test_rejects_a_missing_opening_delimiter(self) -> None:
        self.write_skill("# Example\n\nNo frontmatter here.\n")

        with self.assertRaisesRegex(FrontmatterError, "start with a '---'"):
            parse_skill_md(self.skill_dir)

    def test_rejects_a_missing_closing_delimiter(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: Does example work.
            """
        )

        with self.assertRaisesRegex(FrontmatterError, "closing '---'"):
            parse_skill_md(self.skill_dir)

    def test_rejects_a_malformed_frontmatter_line(self) -> None:
        self.write_skill(
            """
            ---
            name example-skill
            description: Does example work.
            ---
            """
        )

        with self.assertRaisesRegex(
            FrontmatterError, "line 2 is not a 'key: value' entry"
        ):
            parse_skill_md(self.skill_dir)

    def test_rejects_a_duplicate_key(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            name: another-skill
            description: Does example work.
            ---
            """
        )

        with self.assertRaisesRegex(FrontmatterError, "repeats key 'name'"):
            parse_skill_md(self.skill_dir)

    def test_rejects_a_missing_name(self) -> None:
        self.write_skill(
            """
            ---
            description: Does example work.
            ---
            """
        )

        with self.assertRaisesRegex(FrontmatterError, "missing required 'name'"):
            parse_skill_md(self.skill_dir)

    def test_rejects_a_missing_description(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            ---
            """
        )

        with self.assertRaisesRegex(FrontmatterError, "missing required 'description'"):
            parse_skill_md(self.skill_dir)

    def test_rejects_an_empty_description(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: ""
            ---
            """
        )

        with self.assertRaisesRegex(FrontmatterError, "must not be empty"):
            parse_skill_md(self.skill_dir)

    def test_rejects_an_unsupported_block_scalar_indicator(self) -> None:
        self.write_skill(
            """
            ---
            name: example-skill
            description: >2
              Does example work.
            ---
            """
        )

        with self.assertRaisesRegex(
            FrontmatterError, "unsupported block scalar indicator"
        ):
            parse_skill_md(self.skill_dir)

    def test_parses_the_creating_skills_skill(self) -> None:
        skill_root = Path(__file__).resolve().parents[1]

        skill = parse_skill_md(skill_root)

        self.assertEqual(skill.name, "creating-skills")
        self.assertEqual(
            skill.content, (skill_root / "SKILL.md").read_text(encoding="utf-8")
        )
