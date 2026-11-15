"""Shared helpers for the creating-skills test suite."""

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

_FAKE_OPENCODE = """
import json
import os
import sys
import time
from pathlib import Path

config = json.loads(Path(os.environ["FAKE_OPENCODE_CONFIG"]).read_text(encoding="utf-8"))
if config.get("sleep"):
    time.sleep(config["sleep"])

skills_dir = Path(".opencode/skills")
skills = sorted(path.name for path in skills_dir.iterdir()) if skills_dir.is_dir() else []
config_doc = json.loads(Path("opencode.json").read_text(encoding="utf-8"))
invocation = {
    "argv": sys.argv[1:],
    "stdin": sys.stdin.read(),
    "cwd": os.getcwd(),
    "pwd": os.environ.get("PWD"),
    "config_content": os.environ.get("OPENCODE_CONFIG_CONTENT"),
    "skills": skills,
    "permissions": config_doc.get("permissions", []),
    "skill_md": (skills_dir / skills[0] / "SKILL.md").read_text(encoding="utf-8")
    if skills
    else None,
}
Path(config["invocation"]).write_text(json.dumps(invocation), encoding="utf-8")

if config.get("stdout_file"):
    sys.stdout.write(Path(config["stdout_file"]).read_text(encoding="utf-8"))
elif config.get("stdout"):
    sys.stdout.write(config["stdout"])

trigger = config.get("trigger")
if trigger and skills:
    candidate = skills[0]
    if trigger == "skill":
        part = {
            "type": "tool",
            "tool": "skill",
            "state": {
                "status": "completed",
                "input": {"id": candidate},
                "output": f"Loaded {candidate}",
                "metadata": {},
                "time": {},
            },
        }
    else:
        read_path = config.get(
            "read_path", ".opencode/skills/{candidate}/SKILL.md"
        ).format(candidate=candidate)
        part = {
            "type": "tool",
            "tool": "read",
            "state": {
                "status": "completed",
                "input": {"path": read_path},
                "output": "skill contents",
                "metadata": {},
                "time": {},
            },
        }
    event = {
        "type": "tool_use",
        "timestamp": 2,
        "sessionID": "ses_fake",
        "part": part,
    }
    sys.stdout.write(json.dumps(event) + "\\n")

for name in config.get("touch", []):
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.get("touch_content", "output\\n"), encoding="utf-8")

sys.stderr.write(config.get("stderr", ""))
raise SystemExit(config.get("exit_code", 0))
"""


def write_skill(root: Path, name: str) -> Path:
    """Write a minimal skill directory under ``root`` and return it."""
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {name}
            description: Does {name} work.
            ---

            # {name}
            """
        ),
        encoding="utf-8",
    )
    return skill


def fixture(name: str) -> Path:
    """Return the path of an OpenCode JSONL fixture."""
    return Path(__file__).resolve().parent / "fixtures" / "opencode" / name


class FakeOpenCode:
    """A stand-in for the ``opencode`` executable used by adapter tests."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.script = root / "fake-opencode.py"
        self.script.write_text(
            textwrap.dedent(_FAKE_OPENCODE).lstrip("\n"), encoding="utf-8"
        )
        self.config_path = root / "fake-opencode.json"
        self.invocation_path = root / "invocation.json"

    def command(self) -> tuple[str, str]:
        return (sys.executable, str(self.script))

    def environment(self) -> dict[str, str]:
        return {"FAKE_OPENCODE_CONFIG": str(self.config_path)}

    def configure(self, **options: object) -> None:
        options["invocation"] = str(self.invocation_path)
        self.config_path.write_text(json.dumps(options), encoding="utf-8")

    def invocation(self) -> dict[str, Any]:
        return json.loads(self.invocation_path.read_text(encoding="utf-8"))
