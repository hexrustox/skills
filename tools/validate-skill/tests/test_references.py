import unittest

from validate_skill.references import Reference, scan_references


class ScanReferencesTestCase(unittest.TestCase):
    def test_markdown_link_is_scanned(self) -> None:
        self.assertEqual(
            scan_references("See [the guide](references/guide.md)."),
            [Reference("references/guide.md", 1)],
        )

    def test_reference_style_link_is_scanned(self) -> None:
        body = "See [the guide][guide].\n\n[guide]: references/guide.md"
        self.assertEqual(scan_references(body), [Reference("references/guide.md", 3)])

    def test_inline_code_is_scanned(self) -> None:
        self.assertEqual(
            scan_references("Run `scripts/run.sh`."),
            [Reference("scripts/run.sh", 1)],
        )

    def test_multiple_paths_in_one_code_span_share_a_line(self) -> None:
        body = "Intro\n\nRun `scripts/run.sh references/guide.md`."
        self.assertEqual(
            scan_references(body),
            [Reference("scripts/run.sh", 3), Reference("references/guide.md", 3)],
        )

    def test_references_are_returned_in_document_order(self) -> None:
        body = "`scripts/run.sh`\n\nSee [the guide](references/guide.md)."
        self.assertEqual(
            scan_references(body),
            [Reference("scripts/run.sh", 1), Reference("references/guide.md", 3)],
        )

    def test_duplicate_references_are_returned(self) -> None:
        body = "Read [a](references/a.md) and [a again](references/a.md)."
        self.assertEqual(
            scan_references(body),
            [Reference("references/a.md", 1), Reference("references/a.md", 1)],
        )

    def test_fenced_code_is_ignored(self) -> None:
        body = (
            "```markdown\n"
            "See [the guide](references/missing.md) and run `scripts/missing.sh`.\n"
            "```"
        )
        self.assertEqual(scan_references(body), [])

    def test_reference_after_fenced_code_keeps_its_line_number(self) -> None:
        body = "```\nfenced text\n```\n\nSee [the guide](references/guide.md)."
        self.assertEqual(scan_references(body), [Reference("references/guide.md", 5)])

    def test_paths_are_normalized_and_stripped_of_fragments(self) -> None:
        body = "See [the guide](references\\guide.md#usage)."
        self.assertEqual(scan_references(body), [Reference("references/guide.md", 1)])

    def test_angle_bracket_reference_is_scanned(self) -> None:
        body = "[guide]: <references/guide.md>"
        self.assertEqual(scan_references(body), [Reference("references/guide.md", 1)])

    def test_urls_anchors_absolute_paths_and_other_directories_are_ignored(self) -> None:
        body = "\n".join(
            (
                "[site](https://example.com/scripts/guide.md)",
                "[anchor](#section)",
                "[absolute](/tmp/scripts/run.sh)",
                "`https://example.com/scripts/run.sh`",
                "`#section`",
                "`/tmp/scripts/run.sh`",
                "`C:\\scripts\\run.sh`",
                "[other](docs/guide.md)",
            )
        )
        self.assertEqual(scan_references(body), [])


if __name__ == "__main__":
    unittest.main()
