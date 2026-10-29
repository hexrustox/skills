from validate_skill.body import ReferenceExists, check_body, check_references
from validate_skill.frontmatter import (
    check_frontmatter_fields,
    check_unknown_keys,
    parse_frontmatter,
)
from validate_skill.metadata import check_metadata
from validate_skill.model import Finding


def validate_document(
    text: str,
    directory_name: str,
    reference_exists: ReferenceExists,
) -> list[Finding]:
    frontmatter, body, findings = parse_frontmatter(text)
    if frontmatter is None:
        return findings

    findings.extend(check_frontmatter_fields(frontmatter, directory_name))
    findings.extend(check_metadata(frontmatter))
    findings.extend(check_unknown_keys(frontmatter))
    findings.extend(check_body(body))
    findings.extend(check_references(body, reference_exists))
    return findings
