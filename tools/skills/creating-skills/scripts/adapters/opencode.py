"""OpenCode harness adapter."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO

from scripts.harness import (
    PreparedScope,
    RunMetrics,
    RunResult,
    TokenTotals,
    TriggerResult,
)

_NO_TOOLS_AGENT = "creating-skills-no-tools"
_HARNESS_PATHS = {".opencode", ".git"}


@dataclass(frozen=True)
class _Execution:
    """The raw process output and timing behind one run."""

    stdout: str
    stderr: str
    duration_ms: int
    exit_code: int
    timed_out: bool


class OpenCodeHarness:
    """Run fresh agents through ``opencode run --format json``."""

    def __init__(
        self,
        *,
        command: Sequence[str] = ("opencode",),
        standalone: bool = False,
        temp_root: Path | None = None,
    ) -> None:
        self._command = tuple(command)
        self._standalone = standalone
        self._temp_root = temp_root

    def prepare_scope(self, skills: Sequence[Path] = ()) -> PreparedScope:
        """Create a temporary project containing exactly ``skills`` or no skill."""
        project = Path(
            tempfile.mkdtemp(prefix="creating-skills-scope-", dir=self._temp_root)
        )
        skill_ids: list[str] = []

        try:
            skills_dir = project / ".opencode" / "skills"
            skills_dir.mkdir(parents=True)
            for skill in skills:
                skill = Path(skill)
                if not (skill / "SKILL.md").is_file():
                    raise ValueError(
                        f"skill directory {str(skill)!r} does not contain SKILL.md"
                    )
                skill_id = skill.name
                if skill_id in skill_ids:
                    raise ValueError(f"duplicate skill id {skill_id!r}")
                shutil.copytree(skill, skills_dir / skill_id)
                skill_ids.append(skill_id)

            config = _scope_config(tuple(skill_ids))
            (project / "opencode.json").write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )
        except Exception:
            shutil.rmtree(project, ignore_errors=True)
            raise

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
        """Run a fresh agent in ``scope`` and return its normalized result."""
        if not scope.path.is_dir():
            raise ValueError(f"scope directory {str(scope.path)!r} does not exist")
        before = _snapshot(scope.path)
        execution = self._execute(
            scope,
            prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            input_files=input_files,
            no_tools=no_tools,
        )
        result = _run_result(scope.path, before, execution)

        if artifacts_dir is not None:
            _write_artifacts(artifacts_dir, result)

        return result

    def _execute(
        self,
        scope: PreparedScope,
        prompt: str,
        *,
        model: str | None,
        timeout_seconds: float,
        input_files: Sequence[Path] = (),
        no_tools: bool = False,
        stop_on: Callable[[dict[str, Any]], bool] | None = None,
    ) -> _Execution:
        command = self._build_command(
            model=model, input_files=input_files, no_tools=no_tools
        )
        environment = {
            key: value
            for key, value in os.environ.items()
            if key != "OPENCODE_CONFIG_CONTENT"
        }
        environment["PWD"] = str(scope.path)

        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=scope.path,
                env=environment,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"could not start harness command {command[0]!r}"
            ) from error

        stopped = threading.Event()
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        io_threads = [
            threading.Thread(
                target=_write_prompt,
                args=(process.stdin, prompt),
                daemon=True,
            ),
            threading.Thread(
                target=_read_stdout,
                args=(process.stdout, stdout_parts, stop_on, stopped),
                daemon=True,
            ),
            threading.Thread(
                target=_drain_stream,
                args=(process.stderr, stderr_parts),
                daemon=True,
            ),
        ]
        for thread in io_threads:
            thread.start()

        timed_out = False
        try:
            while process.poll() is None:
                if stopped.wait(0.01):
                    process.kill()
                    break
                if time.monotonic() - started >= timeout_seconds:
                    timed_out = True
                    process.kill()
                    break
            process.wait()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            for thread in io_threads:
                thread.join()

        return _Execution(
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            duration_ms=round((time.monotonic() - started) * 1000),
            exit_code=process.returncode if process.returncode is not None else -1,
            timed_out=timed_out,
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
        """Run ``query`` against a candidate skill built from ``description``."""
        candidate_id = _candidate_skill_id(skill_name)
        source = Path(
            tempfile.mkdtemp(prefix="creating-skills-probe-", dir=self._temp_root)
        )

        try:
            candidate = source / candidate_id
            candidate.mkdir()
            (candidate / "SKILL.md").write_text(
                _probe_skill_md(skill_name, description), encoding="utf-8"
            )
            with self.prepare_scope([candidate]) as scope:
                before = _snapshot(scope.path)
                execution = self._execute(
                    scope,
                    query,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    stop_on=lambda event: _event_triggers(event, candidate_id),
                )
                result = _run_result(scope.path, before, execution)
        finally:
            shutil.rmtree(source, ignore_errors=True)

        return TriggerResult(
            triggered=_triggered(result, candidate_id),
            candidate_skill_id=candidate_id,
            run=result,
        )

    def _build_command(
        self,
        *,
        model: str | None,
        input_files: Sequence[Path],
        no_tools: bool,
    ) -> list[str]:
        command = list(self._command)
        if self._standalone:
            command.append("--standalone")
        command.extend(
            [
                "run",
                "--format",
                "json",
                "--agent",
                _NO_TOOLS_AGENT if no_tools else "build",
                "--auto",
            ]
        )
        if model:
            command.extend(["--model", model])
        for input_file in input_files:
            command.extend(["--file", str(Path(input_file).resolve())])
        return command


def _scope_config(skill_ids: tuple[str, ...]) -> dict[str, object]:
    permissions: list[dict[str, str]] = [
        {"action": "skill", "resource": "*", "effect": "deny"}
    ]
    permissions.extend(
        {"action": "skill", "resource": skill_id, "effect": "allow"}
        for skill_id in skill_ids
    )
    return {
        "$schema": "https://opencode.ai/config.json",
        "permissions": permissions,
        "agents": {
            _NO_TOOLS_AGENT: {
                "description": "Answer without using tools.",
                "mode": "primary",
                "system": "Answer the user's request directly without using tools.",
                "permissions": [{"action": "*", "resource": "*", "effect": "deny"}],
            }
        },
    }


def _candidate_skill_id(skill_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", skill_name.lower()).strip("-") or "skill"
    base = base[:48].strip("-") or "skill"
    return f"{base}-probe-{uuid.uuid4().hex[:8]}"


def _probe_skill_md(skill_name: str, description: str) -> str:
    name = json.dumps(skill_name, ensure_ascii=False)
    summary = json.dumps(description, ensure_ascii=False)
    return (
        f"---\n"
        f"name: {name}\n"
        f"description: {summary}\n"
        f"---\n\n"
        f"# {skill_name}\n\n"
        f"This skill exists to test whether its description triggers.\n"
    )


def _run_result(
    scope_path: Path,
    before: dict[Path, tuple[int, int]],
    execution: _Execution,
) -> RunResult:
    events = parse_events(execution.stdout)
    tokens = _tokens(events)
    transcript_markdown = _render_transcript(
        events,
        tokens=tokens,
        duration_ms=execution.duration_ms,
        exit_code=execution.exit_code,
        timed_out=execution.timed_out,
    )
    output_files = _output_files(scope_path, before)
    return RunResult(
        assistant_text=_assistant_text(events),
        transcript_jsonl=execution.stdout,
        transcript_markdown=transcript_markdown,
        tokens=tokens,
        duration_ms=execution.duration_ms,
        loaded_skill_ids=_loaded_skill_ids(events),
        output_files=output_files,
        exit_code=execution.exit_code,
        stderr=execution.stderr,
        metrics=_metrics(events, output_files, scope_path, transcript_markdown),
        timed_out=execution.timed_out,
    )


def _triggered(result: RunResult, candidate_id: str) -> bool:
    return any(
        _event_triggers(event, candidate_id)
        for event in parse_events(result.transcript_jsonl)
    )


def _event_triggers(event: dict[str, Any], candidate_id: str) -> bool:
    tool_use = _tool_use(event)
    if tool_use is None:
        return False
    tool, inputs = tool_use

    if tool == "skill":
        return inputs.get("id") == candidate_id
    if tool != "read":
        return False

    path = inputs.get("path") or inputs.get("filePath")
    if not isinstance(path, str):
        return False
    normalized = path.replace("\\", "/")
    marker = f".opencode/skills/{candidate_id}"
    return normalized.endswith(marker) or f"{marker}/" in normalized


def _tool_use(event: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    if event.get("type") != "tool_use":
        return None
    part = _part(event)
    tool = part.get("tool")
    state = part.get("state")
    inputs = state.get("input") if isinstance(state, dict) else None
    if not isinstance(tool, str) or not isinstance(inputs, dict):
        return None
    return tool, inputs


def _write_prompt(stream: TextIO | None, prompt: str) -> None:
    if stream is None:
        return
    try:
        stream.write(prompt)
    except OSError:
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _read_stdout(
    stream: TextIO | None,
    parts: list[str],
    stop_on: Callable[[dict[str, Any]], bool] | None,
    stopped: threading.Event,
) -> None:
    if stream is None:
        return
    try:
        for line in stream:
            parts.append(line)
            if stop_on is None or stopped.is_set():
                continue
            event = _parse_event(line)
            if event is not None and stop_on(event):
                stopped.set()
    finally:
        stream.close()


def _drain_stream(stream: TextIO | None, parts: list[str]) -> None:
    if stream is None:
        return
    try:
        parts.append(stream.read())
    finally:
        stream.close()


def parse_events(transcript_jsonl: str) -> list[dict[str, Any]]:
    """Parse the JSONL stream, ignoring lines that are not JSON objects."""
    events: list[dict[str, Any]] = []
    for line in transcript_jsonl.splitlines():
        event = _parse_event(line)
        if event is not None:
            events.append(event)
    return events


def _parse_event(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


def _part(event: dict[str, Any]) -> dict[str, Any]:
    part = event.get("part")
    return part if isinstance(part, dict) else {}


def _as_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _assistant_text(events: Sequence[dict[str, Any]]) -> str:
    texts: list[str] = []
    for event in events:
        if event.get("type") != "text":
            continue
        text = _part(event).get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    return "\n\n".join(texts)


def _loaded_skill_ids(events: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    skill_ids: list[str] = []
    for event in events:
        tool_use = _tool_use(event)
        if tool_use is None:
            continue
        tool, inputs = tool_use
        if tool != "skill":
            continue
        skill_id = inputs.get("id")
        if isinstance(skill_id, str) and skill_id and skill_id not in skill_ids:
            skill_ids.append(skill_id)
    return tuple(skill_ids)


def _tokens(events: Sequence[dict[str, Any]]) -> TokenTotals:
    totals = {
        "input": 0,
        "output": 0,
        "reasoning": 0,
        "cache_read": 0,
        "cache_write": 0,
    }
    for event in events:
        if event.get("type") != "step_finish":
            continue
        tokens = _part(event).get("tokens")
        if not isinstance(tokens, dict):
            continue
        totals["input"] += _as_int(tokens.get("input"))
        totals["output"] += _as_int(tokens.get("output"))
        totals["reasoning"] += _as_int(tokens.get("reasoning"))
        cache = tokens.get("cache")
        if isinstance(cache, dict):
            totals["cache_read"] += _as_int(cache.get("read"))
            totals["cache_write"] += _as_int(cache.get("write"))
    return TokenTotals(**totals)


def _tool_calls(events: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        if event.get("type") != "tool_use":
            continue
        tool = _part(event).get("tool")
        if isinstance(tool, str) and tool:
            counts[tool] = counts.get(tool, 0) + 1
    return counts


def _steps(events: Sequence[dict[str, Any]]) -> int:
    return sum(1 for event in events if event.get("type") == "step_start")


def _errors(events: Sequence[dict[str, Any]]) -> int:
    errors = 0
    for event in events:
        if event.get("type") == "error":
            errors += 1
        elif event.get("type") == "tool_use":
            state = _part(event).get("state")
            if isinstance(state, dict) and state.get("status") == "error":
                errors += 1
    return errors


def _render_transcript(
    events: Sequence[dict[str, Any]],
    *,
    tokens: TokenTotals,
    duration_ms: int,
    exit_code: int,
    timed_out: bool,
) -> str:
    lines = ["# OpenCode transcript", ""]
    step = 0
    for event in events:
        kind = event.get("type")
        part = _part(event)
        if kind == "step_start":
            step += 1
            lines.extend([f"## Step {step}", ""])
        elif kind == "text":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                lines.extend(["### Assistant", "", text.strip(), ""])
        elif kind == "tool_use":
            lines.extend(_render_tool(part))
        elif kind == "error":
            lines.extend(["### Error", "", _error_message(event.get("error")), ""])

    if step == 0:
        lines.extend(["No steps were recorded.", ""])

    status = f"- Exit code: {exit_code}"
    if timed_out:
        status += " (timed out)"
    lines.extend(
        [
            "## Summary",
            "",
            f"- Steps: {_steps(events)}",
            (
                f"- Tokens: {tokens.input} input, {tokens.output} output, "
                f"{tokens.reasoning} reasoning, {tokens.cache_read} cache read, "
                f"{tokens.cache_write} cache write (total {tokens.total})"
            ),
            f"- Duration: {duration_ms / 1000:.3f}s",
            status,
            "",
        ]
    )
    return "\n".join(lines)


def _render_tool(part: dict[str, Any]) -> list[str]:
    tool = part.get("tool")
    name = tool if isinstance(tool, str) and tool else "tool"
    lines = [f"### Tool: `{name}`", ""]
    state = part.get("state")
    if not isinstance(state, dict):
        return lines

    inputs = state.get("input")
    if isinstance(inputs, dict):
        lines.extend(
            [
                "Input:",
                "",
                "~~~json",
                json.dumps(inputs, indent=2, sort_keys=True),
                "~~~",
                "",
            ]
        )

    if state.get("status") == "error":
        lines.extend(["Error:", "", _error_message(state.get("error")), ""])
        return lines

    output = state.get("output")
    if isinstance(output, str) and output.strip():
        lines.extend(["Result:", "", "~~~", output.rstrip(), "~~~", ""])
    return lines


def _error_message(value: object) -> str:
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str):
            return message
    return str(value)


def _snapshot(root: Path) -> dict[Path, tuple[int, int]]:
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if _is_harness_path(relative):
            continue
        stat = path.stat()
        snapshot[relative] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def _is_harness_path(relative: Path) -> bool:
    if relative == Path("opencode.json"):
        return True
    return bool(relative.parts) and relative.parts[0] in _HARNESS_PATHS


def _output_files(root: Path, before: dict[Path, tuple[int, int]]) -> tuple[Path, ...]:
    after = _snapshot(root)
    changed = sorted(
        relative
        for relative, signature in after.items()
        if before.get(relative) != signature
    )
    return tuple(root / relative for relative in changed)


def _metrics(
    events: Sequence[dict[str, Any]],
    output_files: Sequence[Path],
    root: Path,
    transcript_markdown: str,
) -> RunMetrics:
    tool_calls = _tool_calls(events)
    return RunMetrics(
        tool_calls=tool_calls,
        total_tool_calls=sum(tool_calls.values()),
        total_steps=_steps(events),
        files_created=tuple(str(path.relative_to(root)) for path in output_files),
        errors_encountered=_errors(events),
        output_chars=sum(_output_chars(path) for path in output_files),
        transcript_chars=len(transcript_markdown),
    )


def _output_chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def _write_artifacts(artifacts_dir: Path, result: RunResult) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "transcript.jsonl").write_text(
        result.transcript_jsonl, encoding="utf-8"
    )
    (artifacts_dir / "transcript.md").write_text(
        result.transcript_markdown, encoding="utf-8"
    )
    metrics_dir = artifacts_dir / "outputs"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    (metrics_dir / "metrics.json").write_text(
        json.dumps(asdict(result.metrics), indent=2) + "\n", encoding="utf-8"
    )
