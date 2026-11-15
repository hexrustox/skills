"""Shared helpers for the creating-skills test suite."""

import json
import shutil
import sys
import tempfile
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scripts.harness import (
    PreparedScope,
    RunMetrics,
    RunResult,
    TokenTotals,
    TriggerResult,
)

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
    "files": {
        path: Path(path).read_text(encoding="utf-8", errors="replace")
        for index, path in enumerate(sys.argv[1:])
        if index and sys.argv[1:][index - 1] == "--file"
    },
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


def write_evals(skill: Path, evals: list[dict[str, Any]]) -> Path:
    """Write an eval definition under ``skill`` and return its path."""
    directory = skill / "evals"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "evals.json"
    path.write_text(
        json.dumps({"skill_name": skill.name, "evals": evals}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def canned_run_result(
    scope: Path,
    *,
    loaded_skill_ids: tuple[str, ...] = (),
    output_name: str = "answer.md",
    exit_code: int = 0,
    stderr: str = "",
    timed_out: bool = False,
) -> RunResult:
    """Build a deterministic run result with one output file."""
    output = scope / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("The answer.\n", encoding="utf-8")
    transcript_markdown = "# Transcript\n\nDone.\n"
    return RunResult(
        assistant_text="Done.",
        transcript_jsonl='{"type":"text"}\n',
        transcript_markdown=transcript_markdown,
        tokens=TokenTotals(
            input=100, output=20, reasoning=5, cache_read=7, cache_write=3
        ),
        duration_ms=1500,
        loaded_skill_ids=loaded_skill_ids,
        output_files=(output,),
        exit_code=exit_code,
        stderr=stderr,
        metrics=RunMetrics(
            tool_calls={"write": 1},
            total_tool_calls=1,
            total_steps=1,
            files_created=(output_name,),
            errors_encountered=0,
            output_chars=len("The answer.\n"),
            transcript_chars=len(transcript_markdown),
        ),
        timed_out=timed_out,
    )


class RecordingHarness:
    """A harness double that records scopes and returns a canned result."""

    def __init__(
        self,
        root: Path,
        *,
        exit_code: int = 0,
        stderr: str = "",
        timed_out: bool = False,
    ) -> None:
        self.root = root
        self.exit_code = exit_code
        self.stderr = stderr
        self.timed_out = timed_out
        self.prepare_calls: list[tuple[Path, ...]] = []
        self.run_calls: list[dict[str, Any]] = []
        self.scope_files: dict[str, str] = {}

    def prepare_scope(self, skills: Sequence[Path] = ()) -> PreparedScope:
        project = Path(tempfile.mkdtemp(prefix="recording-scope-", dir=self.root))
        skill_ids: list[str] = []
        for skill in skills:
            skill = Path(skill)
            target = project / ".opencode" / "skills" / skill.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill, target)
            skill_ids.append(skill.name)
        self.prepare_calls.append(tuple(Path(skill) for skill in skills))
        return PreparedScope(path=project, skill_ids=tuple(skill_ids))

    def run(
        self,
        scope: PreparedScope,
        prompt: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        input_files: Sequence[Path] = (),
        no_tools: bool = False,
        artifacts_dir: Path | None = None,
    ) -> RunResult:
        self.scope_files = {
            path.relative_to(scope.path).as_posix(): path.read_text(
                encoding="utf-8", errors="replace"
            )
            for path in scope.path.rglob("*")
            if path.is_file()
            and ".opencode" not in path.parts
            and path.name != "opencode.json"
        }
        self.run_calls.append(
            {
                "prompt": prompt,
                "model": model,
                "timeout_seconds": timeout_seconds,
                "input_files": tuple(Path(path) for path in input_files),
                "no_tools": no_tools,
                "artifacts_dir": artifacts_dir,
                "skill_ids": scope.skill_ids,
            }
        )

        return canned_run_result(
            scope.path,
            loaded_skill_ids=scope.skill_ids,
            exit_code=self.exit_code,
            stderr=self.stderr,
            timed_out=self.timed_out,
        )

    def probe_trigger(
        self,
        skill_name: str,
        description: str,
        query: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> TriggerResult:
        raise NotImplementedError("trigger probes are not used by these tests")


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
