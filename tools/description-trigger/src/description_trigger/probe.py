"""Create isolated OpenCode projects and run one probe in each."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

CONFIG_RELATIVE_PATH = Path(".opencode") / "opencode.json"
SKILLS_RELATIVE_PATH = Path(".opencode") / "skills"
TRANSCRIPT_NAME = "transcript.jsonl"
STDERR_NAME = "stderr.txt"
PROBE_AGENT_PREFIX = "description-trigger-probe"


class ProbeError(Exception):
    """Raised when a probe cannot be prepared or launched."""

    def __init__(self, message: str, probe: Probe | None = None) -> None:
        super().__init__(message)
        self.probe = probe


@dataclass(frozen=True)
class Probe:
    """One disposable project with the target skill and probe agent."""

    directory: Path
    agent_name: str
    config_path: Path
    transcript_path: Path
    stderr_path: Path


@dataclass(frozen=True)
class ProbeRun:
    """The process outcome used to interpret the transcript."""

    returncode: int
    stdout: str


def read_opencode_version() -> str:
    """Return the installed OpenCode version or reject the environment."""
    try:
        completed = subprocess.run(
            ["opencode", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise ProbeError(f"could not run OpenCode: {error}") from error

    version = completed.stdout.strip() or completed.stderr.strip()
    if completed.returncode != 0:
        detail = f": {version}" if version else ""
        raise ProbeError(
            f"opencode --version exited with {completed.returncode}{detail}"
        )
    if not version:
        raise ProbeError("opencode --version printed nothing")
    return version


def create_probe(skill_dir: Path, case_id: str, skill_id: str) -> Probe:
    """Create a fresh project containing only the target skill."""
    try:
        directory = Path(
            tempfile.mkdtemp(prefix=f"description-trigger-{skill_id}-{case_id}-")
        )
    except OSError as error:
        raise ProbeError(f"could not create a probe directory: {error}") from error
    agent_name = f"{PROBE_AGENT_PREFIX}-{uuid.uuid4().hex}"
    probe = Probe(
        directory=directory,
        agent_name=agent_name,
        config_path=directory / CONFIG_RELATIVE_PATH,
        transcript_path=directory / TRANSCRIPT_NAME,
        stderr_path=directory / STDERR_NAME,
    )

    local_skill = directory / SKILLS_RELATIVE_PATH / skill_id
    try:
        local_skill.parent.mkdir(parents=True)
        shutil.copytree(skill_dir, local_skill)
        probe.config_path.write_text(
            json.dumps(_probe_config(agent_name, skill_id), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise ProbeError(
            f"could not prepare probe directory {directory}: {error}",
            probe,
        ) from error
    return probe


def run_probe(probe: Probe, prompt: str, model: str) -> ProbeRun:
    """Run OpenCode once in the probe project and retain its output."""
    command = [
        "opencode",
        "run",
        "--format",
        "json",
        "--agent",
        probe.agent_name,
        "--model",
        model,
        "--archived",
    ]
    environment = {**os.environ, "PWD": str(probe.directory)}
    try:
        completed = subprocess.run(
            command,
            cwd=probe.directory,
            env=environment,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise ProbeError(
            f"could not run OpenCode in {probe.directory}: {error}"
        ) from error

    try:
        probe.transcript_path.write_text(completed.stdout, encoding="utf-8")
        probe.stderr_path.write_text(completed.stderr, encoding="utf-8")
    except OSError as error:
        raise ProbeError(
            f"could not retain probe output in {probe.directory}: {error}",
            probe,
        ) from error

    return ProbeRun(returncode=completed.returncode, stdout=completed.stdout)


def _probe_config(agent_name: str, skill_id: str) -> dict[str, object]:
    return {
        "$schema": "https://opencode.ai/config.json",
        "agents": {
            agent_name: {
                "description": "Isolated description-trigger probe.",
                "mode": "primary",
                "permissions": [
                    {"action": "*", "resource": "*", "effect": "deny"},
                    {"action": "skill", "resource": skill_id, "effect": "allow"},
                ],
            }
        },
    }
