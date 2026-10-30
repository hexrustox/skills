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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list every checked skill and always print the summary",
    )
    args = parser.parse_args(argv)

    run = run_validation(args.path)

    if args.json:
        print(render_json(run))
    else:
        for failure in run.failures:
            print(f"error: {failure.message}", file=sys.stderr)
        output = render_text(run, verbose=args.verbose)
        if output:
            print(output)

    return run.exit_code


if __name__ == "__main__":
    sys.exit(main())
