import unittest

from support import RepoTestCase, rules
from validate_skill.validator import validate_skill


class ValidatorTestCase(RepoTestCase):
    def test_registration_is_reported_when_frontmatter_is_missing(self) -> None:
        skill_file = self.write_skill(
            "# Example\n\nNo frontmatter here.\n", register=False
        ) / "SKILL.md"

        result = validate_skill(skill_file)

        self.assertEqual(
            rules(result.findings),
            ["frontmatter.missing", "plugin.manifest-missing"],
        )

    def test_document_and_registration_findings_combine(self) -> None:
        skill_dir = self.write_document(
            frontmatter="""\
            name: example
            metadata:
              version: "1.0.0"
            """,
            register=False,
        )
        self.write_manifest(["./other"])

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(
            rules(result.findings),
            ["description.missing", "plugin.unregistered"],
        )

    def test_reference_resolver_checks_the_skill_root(self) -> None:
        skill_dir = self.write_document(
            "Read [the guide](references/guide.md).",
            register=False,
        )
        self.write_manifest(["./example"])
        reference = skill_dir / "references" / "guide.md"
        reference.parent.mkdir()
        reference.write_text("# Guide\n", encoding="utf-8")

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(result.findings, [])


if __name__ == "__main__":
    unittest.main()
