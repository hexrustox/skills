import argparse
import sys
from pathlib import Path
from typing import Sequence

from validate_skill.report import render_json, render_text
from validate_skill.run import run_validation


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-skill")
    parser.add_argument(
        "path", nargs="+", type=Path, help="a SKILL.md file or skill directory"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable findings"
    )
    args = parser.parse_args(argv)

    run = run_validation(args.path)

    for failure in run.failures:
        print(f"validate-skill: {failure.message}", file=sys.stderr)

    if args.json:
        print(render_json(run))
    else:
        output = render_text(run)
        if output:
            print(output)

    if run.failures:
        return 2
    return 1 if any(result.error_count for result in run.results) else 0


if __name__ == "__main__":
    sys.exit(main())
