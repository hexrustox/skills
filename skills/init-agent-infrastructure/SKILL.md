---
name: init-agent-infrastructure
description: Initialize or audit the project's AGENTS.md, split oversized content into docs/agents/, and delegate Matt Pocock skills setup to setup-matt-pocock-skills.
metadata:
  version: "1.0.0"
  author: "hexrustox <231717567+hexrustox@users.noreply.github.com>"
disable-model-invocation: true
---

# Init Agent Infrastructure

Build `AGENTS.md` as the project's always-loaded instruction file, keep it lean enough to be followed, and move branch-specific detail behind pointers in `docs/agents/`.

Two modes:

- **Init**: no root `AGENTS.md` yet. Harvest, draft, split.
- **Audit**: a root `AGENTS.md` exists. Run the keep-test on every line, rewrite or delete, then split.

`AGENTS.md` is the root instruction file this skill owns. When a root `CLAUDE.md` exists, migrate its content into `AGENTS.md` and leave `CLAUDE.md` as an `@AGENTS.md` pointer, so one file owns the instructions. Read nested `AGENTS.md` files; write them only when splitting a monorepo package or when the user asks.

## Instructions

### 1. Explore

Read the repo before writing a line. The environment is already a source of truth for commands, paths, and structure:

- `AGENTS.md` at the root, any nested `AGENTS.md` under packages or services, and a root `CLAUDE.md` with whether it points at `AGENTS.md`.
- `docs/agents/`, `docs/adr/`, `GLOSSARY.md`, `GLOSSARY-MAP.md`, and `.scratch/`.
- `git remote -v`, the default branch, and recent `git log --oneline`.
- Manifests and task runners: `package.json`, `pnpm-workspace.yaml`, `Cargo.toml`, `Makefile`, `justfile`, `flake.nix`, `pyproject.toml`, and equivalents.
- CI workflows, scripts, `.env.example`, and developer setup docs.
- Existing tool instruction files: `.cursor/rules/`, `.github/copilot-instructions.md`, `.windsurfrules`, and similar.

Set the mode from the root `AGENTS.md`. Done when the mode is named and every source above is checked.

### 2. Hand setup to `setup-matt-pocock-skills`

Call the Skill tool with `setup-matt-pocock-skills` and tell it the instruction file is `AGENTS.md`.

- No setup yet: ask it to initialize.
- Setup already present: ask it to verify and update its own output in place.
- Leave its artifacts to that skill; it owns their format and audit.
- If the skill is unavailable or model invocation is blocked, ask the user to run `/setup-matt-pocock-skills` and wait for confirmation.
- If it writes `CLAUDE.md` instead, migrate: move its content and setup block into `AGENTS.md`, then reduce `CLAUDE.md` to an `@AGENTS.md` pointer.

Done when the setup skill reports initialization or audit complete (or the user confirms), and exactly one root instruction file owns the content while the other, if present, only imports it.

### 3. Draft or audit `AGENTS.md`

**Init.** Read [references/agents-md-content.md](references/agents-md-content.md). Harvest rules from the exploration and from any content the user supplied. Every rule must tie to a harvested item: a real correction, a command the agent cannot guess, a convention that differs from the default, or a gotcha no config confesses. Start from [assets/agents-md-template.md](assets/agents-md-template.md) and merge it with any file setup created.

**Audit.** Read [references/audit.md](references/audit.md). Run the keep-test on every line. Delete sediment, no-ops, and environment-owned facts. Rewrite blanket rules into contextual pointers and permissions plus completion.

An existing instruction file (root or nested `AGENTS.md`, root `CLAUDE.md`) is a harvested source: a project-specific convention it states (tabs, `Result` errors, a workflow rule) stays unless the behaviour it describes has changed. Current code that has not adopted the convention yet is a discrepancy to report, not staleness.

Preserve the setup-owned `## Agent skills` block unchanged. Done when every surviving line ties to a harvested item or passes the keep-test, every rule names its trigger, every permission names its completion, and each meaning appears once.

### 4. Split when the root is over budget

Read [references/split.md](references/split.md) when `AGENTS.md` exceeds about 200 lines or 5,000 tokens, or when a section is reached by only some runs.

Keep cross-cutting commands, scope, verification, the setup block, and pointers in the root. Move branch-specific detail into `docs/agents/<topic>.md`. Prefer nested `AGENTS.md` files for monorepo packages.

Done when the root is a one-screen map, every branch-specific meaning has exactly one home, every split doc carries the detail its pointer promises without pointing back at the root, and every split doc has a root pointer that names its trigger.

### 5. Confirm and write

Present the findings, the keep/move/cut list, and the draft. Let the user edit before writing. Then write `AGENTS.md` and any split docs.

Done when the user approves and the files match the approved draft.

### 6. Verify in a fresh context

Dispatch a fresh-context subagent to re-read the root, every nested `AGENTS.md`, and every split doc. Give it the paths and the checks below; it reads the files itself and reports each finding with its file and line.

- Every pointer resolves to an existing file.
- No meaning lives in two places.
- No rule conflicts across the root, nested `AGENTS.md` files, and split docs.
- The `## Agent skills` block is intact and its references resolve.
- The `setup-matt-pocock-skills` audit is clean.

Fix each finding and re-dispatch. If the host exposes `/context` or `/memory`, use it to confirm `AGENTS.md` loads. Done when a fresh-context subagent reports every check passing; on a host with no subagent tool, your own re-read must pass the same checks.
