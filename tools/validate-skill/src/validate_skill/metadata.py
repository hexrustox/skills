from collections.abc import Mapping

from validate_skill.frontmatter import Frontmatter
from validate_skill.model import Finding


def _metadata_mapping(
    frontmatter: Frontmatter,
) -> tuple[Mapping[object, object] | None, list[Finding]]:
    if "metadata" not in frontmatter:
        return None, []
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        return None, [
            Finding.error(
                "metadata.type",
                "metadata must be a mapping of strings to strings",
                "metadata",
            )
        ]
    return metadata, []


def _check_metadata_entries(metadata: Mapping[object, object]) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in metadata.items():
        if not isinstance(key, str):
            findings.append(
                Finding.error(
                    "metadata.key-type", "metadata keys must be strings", "metadata"
                )
            )
            continue
        if not isinstance(value, str):
            findings.append(
                Finding.error(
                    "metadata.value-type",
                    f"metadata.{key} must be a string",
                    f"metadata.{key}",
                )
            )
    return findings


def check_metadata(frontmatter: Frontmatter) -> list[Finding]:
    metadata, findings = _metadata_mapping(frontmatter)
    if metadata is None:
        return findings
    findings.extend(_check_metadata_entries(metadata))
    return findings
