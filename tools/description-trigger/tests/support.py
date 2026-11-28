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
import fcntl
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path


def log_event(event: str) -> None:
    path = os.environ.get("FAKE_OPENCODE_EVENT_LOG")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"event": event, "time": time.time(), "pid": os.getpid()})
            + "\\n"
        )


def wait_for_peers() -> None:
    directory_path = os.environ.get("FAKE_OPENCODE_PEER_DIR")
    if not directory_path:
        return
    expected = int(os.environ.get("FAKE_OPENCODE_EXPECT_PEERS", "1"))
    directory = Path(directory_path)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{os.getpid()}.peer").touch()
    deadline = time.monotonic() + 5
    while len(list(directory.iterdir())) < expected and time.monotonic() < deadline:
        time.sleep(0.01)


def next_response_index(key: str) -> int:
    state_directory = os.environ.get("FAKE_OPENCODE_STATE")
    if not state_directory:
        return 0
    directory = Path(state_directory)
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    counter_path = directory / f"{digest}.count"
    with open(counter_path, "a+", encoding="utf-8") as counter:
        fcntl.flock(counter, fcntl.LOCK_EX)
        counter.seek(0)
        raw = counter.read().strip()
        index = int(raw) if raw else 0
        counter.seek(0)
        counter.truncate()
        counter.write(str(index + 1))
        counter.flush()
    return index


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

log_event("start")
wait_for_peers()
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
prompts = spec.get("prompts", {})
if prompt in prompts:
    response = prompts[prompt]
    response_key = prompt
else:
    response = spec.get("default", {})
    response_key = "<default>"
if isinstance(response, list):
    index = next_response_index(response_key)
    response = response[index % len(response)] if response else {}
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
log_event("end")
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
