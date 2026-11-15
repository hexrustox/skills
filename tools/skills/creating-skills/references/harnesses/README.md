# Harness adapters

Eval, benchmark, and description-tuning work runs through a harness adapter. Read the document for your harness before starting:

- [OpenCode](opencode.md) — tested against OpenCode 2.2.1.

If your harness is not listed, stop and ask the user to add an adapter.

## Adding another harness

Implement the `Harness` protocol in `scripts/harness.py`, register the adapter in `scripts/adapters/__init__.py`, and add a sibling document linked from this index. Keep the normalized result values identical so callers can rely on them. Adapter tests use canned streams or a fake executable and never call a live model.

A single adapter instance may be used for concurrent `prepare_scope` and `run` calls. Keep per-run state on the prepared scope or in locals, never in mutable attributes on the adapter.
