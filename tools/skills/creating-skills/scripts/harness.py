"""The harness contract and the normalized values it returns."""

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self, runtime_checkable


@dataclass
class PreparedScope:
    """A temporary project containing exactly the requested skills or none."""

    path: Path
    skill_ids: tuple[str, ...] = ()

    def cleanup(self) -> None:
        """Remove the temporary project."""
        shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.cleanup()


@dataclass(frozen=True)
class TokenTotals:
    """Token usage summed over every step of a run."""

    input: int = 0
    output: int = 0
    reasoning: int = 0
    cache_read: int = 0
    cache_write: int = 0

    @property
    def total(self) -> int:
        return (
            self.input
            + self.output
            + self.reasoning
            + self.cache_read
            + self.cache_write
        )


@dataclass(frozen=True)
class RunMetrics:
    """Execution metrics derived from a run's JSONL events."""

    tool_calls: dict[str, int]
    total_tool_calls: int
    total_steps: int
    files_created: tuple[str, ...]
    errors_encountered: int
    output_chars: int
    transcript_chars: int


@dataclass(frozen=True)
class RunResult:
    """A normalized run, independent of the harness that produced it."""

    assistant_text: str
    transcript_jsonl: str
    transcript_markdown: str
    tokens: TokenTotals
    duration_ms: int
    loaded_skill_ids: tuple[str, ...]
    output_files: tuple[Path, ...]
    exit_code: int
    stderr: str
    metrics: RunMetrics
    timed_out: bool = False


@dataclass(frozen=True)
class TriggerResult:
    """Whether a trigger probe loaded its candidate skill, and the run behind it."""

    triggered: bool
    candidate_skill_id: str
    run: RunResult


@runtime_checkable
class Harness(Protocol):
    """The three capabilities the creating-skills scripts require.

    One harness instance may be used for concurrent ``prepare_scope``,
    ``run``, and ``probe_trigger`` calls. Adapters must keep per-run state on
    the prepared scope or in locals, never in mutable attributes on the
    adapter.
    """

    def prepare_scope(self, skills: Sequence[Path] = ()) -> PreparedScope:
        """Create a fresh scope containing exactly ``skills`` or no skill."""
        ...

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
        ...

    def probe_trigger(
        self,
        skill_name: str,
        description: str,
        query: str,
        *,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> TriggerResult:
        """Run ``query`` against a candidate skill built from the description.

        Implementations may terminate the run once triggering is observed.
        """
        ...
