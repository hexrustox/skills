"""Adapter registry for the creating-skills harness contract."""

from collections.abc import Callable
from typing import Any

from scripts.adapters.opencode import OpenCodeHarness
from scripts.harness import Harness

HarnessFactory = Callable[..., Harness]

_HARNESSES: dict[str, HarnessFactory] = {"opencode": OpenCodeHarness}


def available_harnesses() -> tuple[str, ...]:
    """Return the names of every registered harness adapter."""
    return tuple(sorted(_HARNESSES))


def get_harness(name: str, **options: Any) -> Harness:
    """Return the harness adapter registered under ``name``."""
    factory = _HARNESSES.get(name)
    if factory is None:
        available = ", ".join(available_harnesses())
        raise ValueError(
            f"no harness adapter named {name!r}; available: {available}. "
            "Add an adapter for this harness."
        )
    return factory(**options)
