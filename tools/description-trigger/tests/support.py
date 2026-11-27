"""Shared helpers for CLI subprocess tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(sys.executable).with_name("description-trigger")

FAKE_OPENCODE_SCRIPT = """\
import json
import os
import signal
import sys
import time
from pathlib import Path


def skill_call(skill_id: str) -> str:
    event = {
        "type": "tool_use",
        "timestamp": 1,
        "sessionID": "ses_probe",
        "part": {
            "partID": "prt_probe",
            "sessionID": "ses_probe",
            "messageID": "msg_probe",
            "type": "tool",
            "id": "tool_probe",
            "tool": "skill",
            "state": {
                "status": "completed",
                "input": {"id": skill_id},
                "output": "loaded",
                "title": "skill",
                "metadata": {},
                "time": {"start": 0, "end": 1},
            },
        },
    }
    return json.dumps(event) + "\\n"


def verify_probe(arguments: list[str]) -> str:
    cwd = Path.cwd()
    agent = arguments[arguments.index("--agent") + 1]
    config = json.loads(
        (cwd / ".opencode" / "opencode.json").read_text(encoding="utf-8")
    )
    definition = config["agents"][agent]
    assert definition["mode"] == "primary"
    permissions = definition["permissions"]
    assert permissions[0] == {
        "action": "*",
        "resource": "*",
        "effect": "deny",
    }
    assert permissions[1]["action"] == "skill"
    assert permissions[1]["effect"] == "allow"
    target = permissions[1]["resource"]
    skill_directories = sorted(
        path.name for path in (cwd / ".opencode" / "skills").iterdir() if path.is_dir()
    )
    assert skill_directories == [target]
    assert (cwd / ".opencode" / "skills" / target / "SKILL.md").is_file()
    return skill_call(target)


arguments = sys.argv[1:]
marker = os.environ.get("FAKE_OPENCODE_MARKER")
if marker:
    Path(marker).touch()
if arguments == ["--version"]:
    print(os.environ.get("FAKE_OPENCODE_VERSION", "fake-opencode 9.9.9"))
    raise SystemExit(0)

cwd = Path.cwd()
(cwd / "fake-opencode.json").write_text(
    json.dumps(
        {
            "arguments": arguments,
            "cwd": str(cwd),
            "pwd": os.environ.get("PWD"),
            "pid": os.getpid(),
        }
    ),
    encoding="utf-8",
)
prompt = sys.stdin.read()
(cwd / "fake-prompt.txt").write_text(prompt, encoding="utf-8")

spec = {}
spec_path = os.environ.get("FAKE_OPENCODE_SPEC")
if spec_path:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
response = spec.get("prompts", {}).get(prompt, spec.get("default", {}))
if response.get("ignore_sigterm"):
    marker = os.environ.get("FAKE_OPENCODE_SIGTERM_MARKER")

    def handle_sigterm(signum, frame):
        if marker:
            Path(marker).touch()

    signal.signal(signal.SIGTERM, handle_sigterm)
if response.get("verify_probe"):
    stdout = verify_probe(arguments)
else:
    stdout = response.get("stdout", "")
sys.stdout.write(stdout)
stderr = response.get("stderr", "")
sys.stderr.write(stderr)
sys.stdout.flush()
sys.stderr.flush()
sleep = response.get("sleep")
if sleep:
    time.sleep(float(sleep))
raise SystemExit(response.get("exit", 0))
"""


def skill_call_stdout(
    skill_id: str,
    *,
    field: str = "id",
    status: str = "completed",
    additional_input: dict[str, str] | None = None,
) -> str:
    """Build one JSON transcript line for a skill tool call."""
    state: dict[str, Any] = {
        "status": status,
        "input": {field: skill_id, **(additional_input or {})},
        "title": "skill",
        "metadata": {},
        "time": {"start": 0, "end": 1},
    }
    if status == "completed":
        state["output"] = "loaded"
    elif status == "error":
        state["error"] = "denied"
    event = {
        "type": "tool_use",
        "timestamp": 1,
        "sessionID": "ses_probe",
        "part": {
            "partID": "prt_probe",
            "sessionID": "ses_probe",
            "messageID": "msg_probe",
            "type": "tool",
            "id": "tool_probe",
            "tool": "skill",
            "state": state,
        },
    }
    return json.dumps(event) + "\n"


def install_fake_opencode(
    directory: Path,
    *,
    version: str = "fake-opencode 9.9.9",
) -> dict[str, str]:
    """Put a model-free OpenCode replacement first on PATH."""
    bin_directory = directory / "bin"
    bin_directory.mkdir()
    executable = bin_directory / "opencode"
    executable.write_text(
        f"#!{sys.executable}\n{FAKE_OPENCODE_SCRIPT}",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
        "FAKE_OPENCODE_VERSION": version,
    }


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
