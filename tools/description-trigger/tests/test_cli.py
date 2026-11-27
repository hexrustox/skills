"""Smoke tests for the installed console script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import SCRIPT, run_cli


class CliSmokeTest(unittest.TestCase):
    def test_help_runs_from_outside_the_project(self) -> None:
        self.assertTrue(SCRIPT.is_file(), "missing console script")

        with tempfile.TemporaryDirectory() as directory:
            result = run_cli("--help", cwd=Path(directory))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: description-trigger", result.stdout)
