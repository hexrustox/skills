import re
from collections.abc import Mapping

from validate_skill.frontmatter import Frontmatter
from validate_skill.model import Finding

_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _missing_version() -> Finding:
    return Finding.error(
        "metadata.version.missing",
        "metadata.version is required",
        "metadata.version",
    )


def _metadata_mapping(
    frontmatter: Frontmatter,
) -> tuple[Mapping[object, object] | None, list[Finding]]:
    if "metadata" not in frontmatter:
        return None, [_missing_version()]
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        return None, [
            Finding.error(
                "metadata.type", "metadata must be a mapping of strings to strings", "metadata"
            )
        ]
    return metadata, []


def _check_metadata_entries(metadata: Mapping[object, object]) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in metadata.items():
        if not isinstance(key, str):
            findings.append(
                Finding.error("metadata.key-type", "metadata keys must be strings", "metadata")
            )
            continue
        if key != "version" and not isinstance(value, str):
            findings.append(
                Finding.error(
                    "metadata.value-type",
                    f"metadata.{key} must be a string",
                    f"metadata.{key}",
                )
            )
    return findings


def _check_metadata_version(metadata: Mapping[object, object]) -> list[Finding]:
    if "version" not in metadata:
        return [_missing_version()]
    version = metadata.get("version")
    if not isinstance(version, str):
        return [
            Finding.error(
                "metadata.version.type",
                "metadata.version must be a string",
                "metadata.version",
            )
        ]
    if not version.strip():
        return [
            Finding.error(
                "metadata.version.empty",
                "metadata.version must not be empty",
                "metadata.version",
            )
        ]
    if _SEMVER_PATTERN.fullmatch(version) is None:
        return [
            Finding.error(
                "metadata.version.semver",
                "metadata.version must be a valid semantic version (e.g. 1.0.0)",
                "metadata.version",
            )
        ]
    return []


def _check_metadata_extra_keys(metadata: Mapping[object, object]) -> list[Finding]:
    return [
        Finding.warning(
            "metadata.extra-key",
            f"metadata.{key} is not part of the repo convention; only version is expected",
            f"metadata.{key}",
        )
        for key in metadata
        if isinstance(key, str) and key != "version"
    ]


def check_metadata(frontmatter: Frontmatter) -> list[Finding]:
    metadata, findings = _metadata_mapping(frontmatter)
    if metadata is None:
        return findings
    findings.extend(_check_metadata_entries(metadata))
    findings.extend(_check_metadata_version(metadata))
    findings.extend(_check_metadata_extra_keys(metadata))
    return findings
