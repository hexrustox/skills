"""Command-line entry point for description-trigger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from description_trigger.cases import CaseFileError, load_case_set


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="description-trigger",
        description="Test whether skill descriptions trigger when they should.",
    )
    subparsers = parser.add_subparsers(required=True)

    validate = subparsers.add_parser(
        "validate",
        help="Validate one skill's trigger case file.",
        description="Validate one skill's trigger case file without running OpenCode.",
    )
    validate.add_argument(
        "skill_dir",
        metavar="skill-dir",
        type=Path,
        help="Skill directory to validate.",
    )
    validate.add_argument(
        "--cases",
        dest="cases_path",
        metavar="PATH",
        type=Path,
        help="Case file to validate instead of the default derived from the skill directory.",
    )

    arguments = parser.parse_args(argv)
    return _run_validate(arguments)


def _run_validate(arguments: argparse.Namespace) -> int:
    try:
        case_set = load_case_set(arguments.skill_dir, arguments.cases_path)
    except CaseFileError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Skill: {case_set.skill_id}")
    print(f"Case file: {case_set.path}")
    print(f"Positive: {case_set.positive_count}")
    print(f"Negative: {case_set.negative_count}")
    return 0
