import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from validate_skill.model import SkillResult
from validate_skill.validator import ManifestCache, validate_skill


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
        print(finding.as_text())


def _summary_counts(results: Sequence[SkillResult]) -> dict[str, int]:
    return {
        "skills": len(results),
        "errors": sum(result.error_count for result in results),
        "warnings": sum(result.warning_count for result in results),
    }


def _print_summary(results: Sequence[SkillResult]) -> None:
    counts = _summary_counts(results)
    skills = counts["skills"]
    errors = counts["errors"]
    warnings = counts["warnings"]
    print(
        f"{skills} skill{'s' if skills != 1 else ''} checked, "
        f"{errors} error{'s' if errors != 1 else ''}, "
        f"{warnings} warning{'s' if warnings != 1 else ''}"
    )


def _result_payload(result: SkillResult) -> dict[str, object]:
    return {
        "path": str(result.path),
        "findings": [finding.as_dict() for finding in result.findings],
    }


def _print_json(results: Sequence[SkillResult]) -> None:
    payload = {
        "skills": [_result_payload(result) for result in results],
        "summary": _summary_counts(results),
    }
    print(json.dumps(payload, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-skill")
    parser.add_argument(
        "path", nargs="+", type=Path, help="a SKILL.md file or skill directory"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable findings"
    )
    args = parser.parse_args(argv)

    results: list[SkillResult] = []
    usage_failed = False
    cache = ManifestCache()
    for path in args.path:
        try:
            skill_file = _resolve_skill_file(path)
            result = validate_skill(skill_file, cache)
        except (UsageError, OSError, UnicodeDecodeError) as error:
            print(f"validate-skill: {error}", file=sys.stderr)
            usage_failed = True
            continue
        result.path = path
        results.append(result)

    if args.json:
        _print_json(results)
    else:
        for result in results:
            _print_result(result)
        if results:
            _print_summary(results)

    if usage_failed:
        return 2
    return 1 if any(result.error_count for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
