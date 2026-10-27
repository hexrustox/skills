import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from validate_skill.model import SkillResult
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


def _print_result(result: SkillResult) -> None:
    print(f"skill: {result.path}")
    for finding in result.findings:
        print(f"  {finding.severity} {finding.rule}: {finding.message}")


def _print_summary(results: Sequence[SkillResult]) -> None:
    errors = sum(result.error_count for result in results)
    warnings = sum(result.warning_count for result in results)
    skills = len(results)
    print(
        f"{skills} skill{'s' if skills != 1 else ''} checked, "
        f"{errors} error{'s' if errors != 1 else ''}, "
        f"{warnings} warning{'s' if warnings != 1 else ''}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-skill")
    parser.add_argument("path", type=Path, help="a SKILL.md file or skill directory")
    args = parser.parse_args(argv)

    try:
        skill_file = _resolve_skill_file(args.path)
        result = validate_skill(skill_file)
    except (UsageError, OSError, UnicodeDecodeError) as error:
        print(f"validate-skill: {error}", file=sys.stderr)
        return 2

    result.path = args.path
    _print_result(result)
    _print_summary([result])
    return 1 if result.error_count else 0


if __name__ == "__main__":
    sys.exit(main())
