import os
from collections.abc import Sequence
from pathlib import Path

from validate_skill.document import validate_document
from validate_skill.model import Run, SkillResult, TargetFailure
from validate_skill.plugin import PluginRegistry


class UsageError(Exception):
    pass


def _resolve_target(target: Path) -> tuple[Path, Path]:
    if not target.exists():
        raise UsageError(f"path does not exist: {target}")
    skill_file = target / "SKILL.md" if target.is_dir() else target
    if not skill_file.is_file():
        raise UsageError(f"path is not a SKILL.md file or skill directory: {target}")
    if not os.access(skill_file, os.R_OK):
        raise UsageError(f"skill file is not readable: {skill_file}")
    resolved = Path(os.path.abspath(skill_file))
    return resolved, resolved.parent


def _validate_target(target: Path, registry: PluginRegistry) -> SkillResult:
    skill_file, skill_dir = _resolve_target(target)
    text = skill_file.read_text(encoding="utf-8")

    result = SkillResult(path=target)
    result.findings.extend(
        validate_document(
            text,
            skill_dir.name,
            lambda candidate: (skill_dir / candidate).exists(),
        )
    )
    result.findings.extend(registry.check(skill_dir))
    return result


def run_validation(targets: Sequence[Path]) -> Run:
    registry = PluginRegistry()
    results: list[SkillResult] = []
    failures: list[TargetFailure] = []

    for target in targets:
        try:
            result = _validate_target(target, registry)
        except (UsageError, OSError, UnicodeDecodeError) as error:
            failures.append(TargetFailure(target, str(error)))
            continue
        results.append(result)

    return Run(tuple(results), tuple(failures))
