"""Shared helpers for the creating-skills test suite."""

import json
import shutil
import sys
import tempfile
import textwrap
import threading
from collections.abc import Mapping, Sequence
from dataclasses import replace
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
sys.stdout.flush()

trigger = config.get("trigger")
if trigger and skills:
    candidate = skills[0]
    if trigger == "skill":
        skill_id = config.get("trigger_id", "{candidate}").format(candidate=candidate)
        part = {
            "type": "tool",
            "tool": "skill",
            "state": {
                "status": "completed",
                "input": {"id": skill_id},
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
    sys.stdout.flush()
    if config.get("trigger_sleep"):
        time.sleep(config["trigger_sleep"])

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


def embedded_data(html: str, marker: str = "const EMBEDDED_DATA = ") -> dict[str, Any]:
    """Return the JSON object a standalone page embeds after ``marker``."""
    start = html.index(marker) + len(marker)
    data, _end = json.JSONDecoder().raw_decode(html[start:])
    if not isinstance(data, dict):
        raise TypeError("embedded data must be a JSON object")
    return data


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
    output_text: str = "The answer.\n",
    exit_code: int = 0,
    stderr: str = "",
    timed_out: bool = False,
) -> RunResult:
    """Build a deterministic run result with one output file."""
    output = scope / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(output_text, encoding="utf-8")
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
            output_chars=len(output_text),
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


class ScriptedCompletionHarness(RecordingHarness):
    """Return scripted assistant text from each completion run."""

    def __init__(self, root: Path, responses: list[str]) -> None:
        super().__init__(root)
        self.responses = list(responses)

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
        response = self.responses.pop(0)
        super().run(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=input_files,
            no_tools=no_tools,
            artifacts_dir=artifacts_dir,
        )
        return replace(canned_run_result(scope.path), assistant_text=response)


class CannedTriggerHarness(RecordingHarness):
    """A harness double with scripted trigger outcomes per query."""

    def __init__(
        self, root: Path, outcomes: Mapping[str, Sequence[bool | None]]
    ) -> None:
        super().__init__(root)
        self.outcomes = {query: list(values) for query, values in outcomes.items()}
        self.probe_calls: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def probe_trigger(
        self,
        skill_name: str,
        description: str,
        query: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> TriggerResult:
        with self._lock:
            values = self.outcomes.get(query)
            outcome = values.pop(0) if values else False
            index = len(self.probe_calls)
            self.probe_calls.append(
                {
                    "skill_name": skill_name,
                    "description": description,
                    "query": query,
                    "model": model,
                    "timeout_seconds": timeout_seconds,
                }
            )
        if outcome is None:
            raise RuntimeError(f"probe failed for {query!r}")
        run = canned_run_result(
            self.root / "probe",
            output_name=f"probe-{index}.md",
            loaded_skill_ids=("candidate",) if outcome else (),
        )
        return TriggerResult(
            triggered=outcome,
            candidate_skill_id="candidate",
            run=run,
        )


class BarrierTriggerHarness(RecordingHarness):
    """A trigger harness that blocks until every probe has started."""

    def __init__(self, root: Path, parties: int) -> None:
        super().__init__(root)
        self.barrier = threading.Barrier(parties, timeout=5)
        self.thread_ids: set[int] = set()
        self._lock = threading.Lock()

    def probe_trigger(
        self,
        skill_name: str,
        description: str,
        query: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> TriggerResult:
        with self._lock:
            self.thread_ids.add(threading.get_ident())
        self.barrier.wait()
        run = canned_run_result(
            self.root / "probe",
            output_name=f"probe-{threading.get_ident()}.md",
        )
        return TriggerResult(
            triggered=True,
            candidate_skill_id="candidate",
            run=run,
        )


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
