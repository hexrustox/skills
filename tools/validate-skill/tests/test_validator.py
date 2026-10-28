import json
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

    def test_unregistered_skill_reports_registration_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)
        self.write_manifest(["./other"])

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(rules(result.findings), ["plugin.unregistered"])

    def test_missing_plugin_manifest_reports_manifest_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(rules(result.findings), ["plugin.manifest-missing"])

    def test_equivalent_manifest_path_spellings_register_the_skill(self) -> None:
        entries = ["./example", "example", "././example/", ".\\example"]
        for index, entry in enumerate(entries):
            with self.subTest(entry=entry):
                base = self.root / f"case-{index}"
                skill_dir = self.write_document(
                    "# Example",
                    base=base,
                    register=False,
                )
                self.write_manifest([entry], plugin_root=base)

                result = validate_skill(skill_dir / "SKILL.md")

                self.assertEqual(result.findings, [])

    def test_nearest_plugin_manifest_governs_registration(self) -> None:
        nested = self.root / "nested"
        skill_dir = self.write_document(
            "# Example",
            base=nested,
            register=False,
        )
        self.write_manifest(["./nested/example"])
        self.write_manifest(["./other"], plugin_root=nested)

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(rules(result.findings), ["plugin.unregistered"])

    def test_invalid_plugin_manifest_json_reports_manifest_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)
        manifest = self.root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text("{not json", encoding="utf-8")

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(rules(result.findings), ["plugin.manifest-invalid"])

    def test_registered_skill_reached_through_symlink_passes(self) -> None:
        plugin_root = self.root / "plugin"
        skill_dir = self.write_document(
            "# Example",
            base=self.root / "targets",
            register=False,
        )
        self.write_manifest(["./example"], plugin_root=plugin_root)
        linked_skill = plugin_root / "example"
        linked_skill.symlink_to(skill_dir, target_is_directory=True)

        result = validate_skill(linked_skill / "SKILL.md")

        self.assertEqual(result.findings, [])

    def test_plugin_manifest_without_skills_array_reports_manifest_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)
        manifest = self.root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"skills": "example"}), encoding="utf-8")

        result = validate_skill(skill_dir / "SKILL.md")

        self.assertEqual(rules(result.findings), ["plugin.manifest-invalid"])


if __name__ == "__main__":
    unittest.main()
