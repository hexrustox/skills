# Audit AGENTS.md

Run one pass per line. Each line gets two judgements: keep-test and rewrite.

## Keep-test

Delete the whole sentence when any of these is true:

1. **Stale or irrelevant**: it no longer bears on the work, or the behaviour it describes has changed. Code that has not adopted a stated convention yet is a discrepancy to report, not a stale rule.
2. **Default behaviour**: the model already does it without being told.
3. **Environment-owned**: a config, script, or the directory layout already owns the fact.
4. **Repeated**: another line or doc states the same meaning.
5. **Branch-specific**: only some runs need it, so it belongs behind a pointer.

Deleting is the default move; adding needs a harvested item.

## Rewrite moves

| Instead of | Write |
| --- | --- |
| Blanket read: `before every edit, read architecture.md` | Contextual pointer: `Use docs/agents/architecture.md when changing service boundaries.` |
| Always-test: `always run the full suite` | Triggered check: the suite or focused check that matches the change, plus its condition |
| Hard ask-first boundary: `never run commands` | Permission plus completion: what may continue, and `done when …` |
| Stop-for-review after a first pass | Completion bound: what fully done means, and where exploration stops |
| Prohibition: `don't use npm` | Positive target: `Use pnpm for every script and package command` |
| Vague target: `handle errors well` | Concrete target: `Return thiserror enums from public APIs` |
| Restated config: `scripts: build, test, lint` | Pointer to the environment: `Use the scripts in package.json` only when the names are not discoverable |

Keep a prohibition only as a hard guardrail you cannot phrase positively, and pair it with the positive target.

## Staleness checks

- Commands exist in the manifest, task runner, or CI.
- Referenced files and directories exist.
- Nested `AGENTS.md` files agree with the root.
- Split docs carry only detail the root and each other lack.
- The `## Agent skills` block points at files that exist. Hand any setup mismatch to `setup-matt-pocock-skills`; it owns its format.
