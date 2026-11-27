"""Smoke tests for the installed console script."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliSmokeTest(unittest.TestCase):
    def test_help_runs_from_outside_the_project(self) -> None:
        script = Path(sys.executable).with_name("description-trigger")
        self.assertTrue(script.exists(), "missing console script")

        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(script), "--help"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: description-trigger", result.stdout)
