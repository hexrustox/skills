"""Shared helpers for CLI subprocess tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(sys.executable).with_name("description-trigger")


def run_cli(
    *arguments: str | Path,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the installed console script and capture its output."""
    return subprocess.run(
        [str(SCRIPT), *(str(argument) for argument in arguments)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
