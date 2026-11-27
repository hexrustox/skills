"""Command-line entry point for description-trigger."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from description_trigger.cases import CaseFileError, CaseSet, load_case_set
from description_trigger.evaluate import evaluate_cases, format_report
from description_trigger.probe import ProbeError, read_opencode_version
from description_trigger.skill import SkillError, validate_skill

DEFAULT_TIMEOUT_SECONDS = 300


def _timeout_seconds(value: str) -> float:
    """Parse a positive timeout duration in seconds."""
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be a number") from error
    if not math.isfinite(seconds):
        raise argparse.ArgumentTypeError("timeout must be finite")
    if seconds <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return seconds


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="description-trigger",
        description="Test whether skill descriptions trigger when they should.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate",
        help="Validate one skill and its trigger case file.",
        description="Validate one skill and its trigger case file without running OpenCode.",
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
    validate.set_defaults(handler=_run_validate)

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Run one isolated probe per trigger case.",
        description="Run one isolated OpenCode probe per trigger case.",
    )
    evaluate.add_argument(
        "skill_dir",
        metavar="skill-dir",
        type=Path,
        help="Skill directory to evaluate.",
    )
    evaluate.add_argument(
        "--cases",
        dest="cases_path",
        metavar="PATH",
        type=Path,
        help="Case file to evaluate instead of the default derived from the skill directory.",
    )
    evaluate.add_argument(
        "--model",
        required=True,
        metavar="MODEL",
        help="Model to probe, as provider/model[#variant].",
    )
    evaluate.add_argument(
        "--timeout",
        type=_timeout_seconds,
        default=DEFAULT_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help="Seconds before a probe is terminated (default: %(default)s).",
    )
    evaluate.set_defaults(handler=_run_evaluate)

    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


def _preflight(arguments: argparse.Namespace) -> CaseSet | None:
    try:
        validate_skill(arguments.skill_dir)
        return load_case_set(arguments.skill_dir, arguments.cases_path)
    except (CaseFileError, SkillError) as error:
        print(f"error: {error}", file=sys.stderr)
        return None


def _run_validate(arguments: argparse.Namespace) -> int:
    case_set = _preflight(arguments)
    if case_set is None:
        return 2

    print(f"Skill: {case_set.skill_id}")
    print(f"Case file: {case_set.path}")
    print(f"Positive: {case_set.positive_count}")
    print(f"Negative: {case_set.negative_count}")
    return 0


def _run_evaluate(arguments: argparse.Namespace) -> int:
    case_set = _preflight(arguments)
    if case_set is None:
        return 2

    try:
        opencode_version = read_opencode_version()
    except ProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    report = evaluate_cases(
        arguments.skill_dir,
        case_set,
        arguments.model,
        opencode_version,
        arguments.timeout,
    )
    print(format_report(report))
    return report.exit_code
