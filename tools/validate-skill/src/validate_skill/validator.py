import os
from pathlib import Path

from validate_skill.document import validate_document
from validate_skill.model import SkillResult
from validate_skill.plugin import PluginRegistry


def validate_skill(
    path: Path,
    *,
    registry: PluginRegistry | None = None,
    identity: Path | None = None,
) -> SkillResult:
    skill_file = Path(os.path.abspath(path))
    skill_dir = skill_file.parent
    text = skill_file.read_text(encoding="utf-8")

    result = SkillResult(path=identity if identity is not None else path)
    result.findings.extend(
        validate_document(
            text,
            skill_dir.name,
            lambda candidate: (skill_dir / candidate).exists(),
        )
    )
    result.findings.extend((registry or PluginRegistry()).check(skill_dir))
    return result
