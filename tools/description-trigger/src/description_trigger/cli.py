"""Command-line entry point for description-trigger."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="description-trigger",
        description="Test whether skill descriptions trigger when they should.",
    )
    parser.parse_args(argv)
    return 0
