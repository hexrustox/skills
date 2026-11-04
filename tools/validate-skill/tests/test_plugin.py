import json
import unittest

from support import RepoTestCase, rules
from validate_skill.plugin import PluginRegistry


class PluginRegistryTestCase(RepoTestCase):
    def test_unregistered_skill_reports_registration_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)
        self.write_manifest(["./other"])

        findings = PluginRegistry().check(skill_dir)

        self.assertEqual(rules(findings), ["plugin.unregistered"])

    def test_missing_plugin_manifest_reports_manifest_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)

        findings = PluginRegistry().check(skill_dir)

        self.assertEqual(rules(findings), ["plugin.manifest-missing"])

    def test_equivalent_manifest_path_spellings_register_the_skill(self) -> None:
        entries = ["./example", "example", "././example/"]
        for index, entry in enumerate(entries):
            with self.subTest(entry=entry):
                base = self.root / f"case-{index}"
                skill_dir = self.write_document(
                    "# Example",
                    base=base,
                    register=False,
                )
                self.write_manifest([entry], plugin_root=base)

                findings = PluginRegistry().check(skill_dir)

                self.assertEqual(findings, [])

    def test_nearest_plugin_manifest_governs_registration(self) -> None:
        nested = self.root / "nested"
        skill_dir = self.write_document(
            "# Example",
            base=nested,
            register=False,
        )
        self.write_manifest(["./nested/example"])
        self.write_manifest(["./other"], plugin_root=nested)

        findings = PluginRegistry().check(skill_dir)

        self.assertEqual(rules(findings), ["plugin.unregistered"])

    def test_invalid_plugin_manifest_json_reports_manifest_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)
        manifest = self.root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text("{not json", encoding="utf-8")

        findings = PluginRegistry().check(skill_dir)

        self.assertEqual(rules(findings), ["plugin.manifest-invalid"])

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

        findings = PluginRegistry().check(linked_skill)

        self.assertEqual(findings, [])

    def test_plugin_manifest_without_skills_array_reports_manifest_rule(self) -> None:
        skill_dir = self.write_document("# Example", register=False)
        manifest = self.root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"skills": "example"}), encoding="utf-8")

        findings = PluginRegistry().check(skill_dir)

        self.assertEqual(rules(findings), ["plugin.manifest-invalid"])


if __name__ == "__main__":
    unittest.main()
