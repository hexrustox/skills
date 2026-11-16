"""Generate a standalone review page for a generated trigger eval set."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scripts.frontmatter import parse_skill_md
from scripts.html_embed import embed_json
from scripts.trigger_eval import load_trigger_queries
from scripts.workspace import default_workspace

_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "trigger_review.html"
)
_MARKER = "/*__EMBEDDED_DATA__*/"


def write_trigger_review(
    skill_path: Path,
    eval_set: Path | None = None,
    *,
    output_path: Path | None = None,
) -> Path:
    """Write a static page for editing and exporting generated trigger queries."""
    skill = Path(skill_path).resolve()
    document = parse_skill_md(skill)
    queries = load_trigger_queries(
        Path(eval_set)
        if eval_set is not None
        else skill / "evals" / "trigger_evals.json"
    )
    data: dict[str, Any] = {
        "skill_name": document.name,
        "description": document.description,
        "queries": [
            {"query": query.query, "should_trigger": query.should_trigger}
            for query in queries
        ],
    }
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    if _MARKER not in template:
        raise ValueError(
            f"trigger review template {str(_TEMPLATE_PATH)!r} has no marker"
        )
    embedded = embed_json(data)
    html = template.replace(_MARKER, embedded)
    destination = (
        Path(output_path)
        if output_path is not None
        else default_workspace(skill) / "trigger-review.html"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    """Generate a trigger eval review page from the command line."""
    parser = argparse.ArgumentParser(
        description="Write a standalone page for reviewing generated trigger queries."
    )
    parser.add_argument("--skill", required=True, type=Path)
    parser.add_argument("--eval-set", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        path = write_trigger_review(
            args.skill,
            args.eval_set,
            output_path=args.output,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"trigger review: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
