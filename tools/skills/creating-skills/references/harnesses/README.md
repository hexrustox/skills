# Harness adapters

Eval, benchmark, and description-tuning work runs through a harness adapter. Read the document for the harness you are running in before starting:

- [OpenCode](opencode.md) — tested against OpenCode 2.2.1.

If your harness is not listed, stop and ask the user for an adapter. Do not substitute harness-specific commands or scripts.

Each adapter implements the three-capability `Harness` contract in `scripts/harness.py` and returns the same normalized run values. Add a sibling document and a registry entry when another harness is supported.
