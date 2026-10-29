import os
from collections.abc import Sequence
from pathlib import Path

from validate_skill.model import Run, SkillResult, TargetFailure
from validate_skill.plugin import PluginRegistry
from validate_skill.validator import validate_skill


class UsageError(Exception):
    pass


def _resolve_skill_file(path: Path) -> Path:
    if not path.exists():
        raise UsageError(f"path does not exist: {path}")
    skill_file = path / "SKILL.md" if path.is_dir() else path
    if not skill_file.is_file():
        raise UsageError(f"path is not a SKILL.md file or skill directory: {path}")
    if not os.access(skill_file, os.R_OK):
        raise UsageError(f"skill file is not readable: {skill_file}")
    return skill_file


def run_validation(targets: Sequence[Path]) -> Run:
    registry = PluginRegistry()
    results: list[SkillResult] = []
    failures: list[TargetFailure] = []

    for target in targets:
        try:
            skill_file = _resolve_skill_file(target)
            result = validate_skill(skill_file, registry=registry, identity=target)
        except (UsageError, OSError, UnicodeDecodeError) as error:
            failures.append(TargetFailure(target, str(error)))
            continue
        results.append(result)

    return Run(tuple(results), tuple(failures))
