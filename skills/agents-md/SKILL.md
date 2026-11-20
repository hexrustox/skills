---
name: agents-md
description: Create, audit, and maintain AGENTS.md files. Use when asked to write or update AGENTS.md, set up repository agent instructions, review or prune AGENTS.md, or split instructions across a monorepo.
---

# AGENTS.md

`AGENTS.md` is the repository's instruction channel to coding agents. Treat it as executable configuration: the agent reads it as context and may act on it. Keep it short, current, and limited to what the agent cannot infer from the repository.

The highest-value content is operational: exact commands, a short annotated layout, non-inferable conventions, boundaries, environment gotchas, a verification gate, and annotated references. Everything else is usually cost.

This skill assumes the harness loads `AGENTS.md`. Write only `AGENTS.md`; do not create or modify any other agent instruction file.

## Route the request

Read every existing `AGENTS.md` end to end before changing anything: the root file and any nested files. Do not regenerate over an existing file; edit it and preserve verified repo-specific content.

| Request | Do |
| --- | --- |
| Create | Inspect the repo, choose scope, draft from the template, validate |
| Update | Read the existing file, prune stale content, edit, validate |
| Audit | Read the existing files, run `references/audit-checklist.md`, report findings by severity |

Done when you know the mode, the files in scope, and whether the user asked for a report or an edit.

## 1. Inspect the repository

Gather evidence; do not copy the README.

- Package manager and lockfile; required runtime and versions.
- Build, test, lint, format, and typecheck commands, including single-test and single-file forms.
- CI workflows, `Makefile`/`justfile`/task runner, and package scripts.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/`, and existing `AGENTS.md` files.
- Run read-only commands to confirm behavior; do not trust documentation alone.

Done when you can name the exact commands and paths and know which facts are non-obvious.

## 2. Choose scope and shape

- Root file for repo-wide rules.
- Nested file only when a subtree has genuinely different commands, conventions, or boundaries.
- Root routes to nested files; nested files add only local rules and do not repeat the root.
- Do not rely on a child file overriding the root. Write nested files as additions.
- Budget: root 100–150 lines, hard cap 200; nested 60–80 lines. A file over 300 lines is a structural problem, not a writing problem.

Done when every rule has one home.

## 3. Draft

Read `assets/AGENTS.template.md` for a root file or `assets/AGENTS.nested.template.md` for a nested file. Delete every section that does not apply; replace every placeholder with a verified value.

When a linked doc is required, put it at `docs/agents/<topic>.md` relative to the project root and link it from `AGENTS.md`.

Include only what the agent cannot infer:

- Exact install/build/test/lint/format commands, with the working directory and required env vars.
- An annotated layout of non-obvious directories, including generated directories and how to regenerate them.
- Non-inferable conventions, plus one preferred/deprecated pattern from this repo.
- Boundaries: always / ask first / never, each paired with the correct alternative or regeneration command.
- Environment gotchas: known-failing tests, sandbox quirks, slow commands, required rebuild steps.
- A numbered "before you finish" verification gate.
- Annotated references with when to read them.
- Required runtime and tool versions.

Exclude:

- Rules a linter, formatter, or typechecker already enforces.
- README-like overview prose, generic quality slogans, and personas.
- Task-specific procedures and runbooks; link to a skill or doc instead.
- Secrets, tokens, internal URLs, and customer data.
- Blind paths with no explanation of what they contain or when to read them.
- Duplicated commands or rules between root and nested files.
- YAML frontmatter; `AGENTS.md` is plain Markdown.

Use `MUST` or `NEVER` two or three times in the whole file, not thirty. One rule per bullet. Prefer tables for commands and references.

Add a precedence line unless the repo already has an equivalent: "When documentation and existing code disagree, follow the existing code and report the inconsistency." This is cheap and prevents stale instructions from overriding working code.

Done when every line either changes agent behavior or prevents a known mistake.

## 4. Validate

Run the file's commands; do not just read it.

- Execute every non-destructive command from the stated directory.
- For destructive, deploy, or credential-requiring commands, verify the command and path without running them; mark them unverified and say why.
- Check that every referenced path, package script, Makefile target, and generated directory exists.
- Check for contradictions: package manager, test command, generated-file policy, root vs nested rules.
- Remove duplicated linter rules and blind references.
- Check the line budget.
- Fresh-reader test: if a fresh-context subagent that can read and write within the repo is available, give it the repository and the file, then ask it to restate the three most important rules and complete a small task. If no such subagent is available, skip the test and report `not run`; do not substitute self-review. If it cannot complete the task, the file is ambiguous or too long.

Done when commands, paths, and counts are verified and the fresh-reader test passes or is explicitly reported as not run.

## 5. Maintain and audit

Read `references/audit-checklist.md` for the audit procedure, maintenance triggers, and severity. Delete stale lines; add a line only for an observed failure or a verified change. For an audit, report findings first and do not apply semantic changes without confirmation; mechanical fixes such as typos and dead links can be applied when the user asked for an edit.

Done when the file matches the repository and every remaining rule is still true.

## Report

Use this contract:

```markdown
## AGENTS.md
- Mode: create | update | audit
- Scope: root | nested at `<path>`
- Lines: `<n>` (budget `<n>`)
- Commands verified: `<n>/<n>` (unverified: `<...>`)
- Paths verified: `<n>/<n>`
- Nested files: `<paths or none>`
- Fresh-reader test: `<pass | fail | not run>`
- Open questions: `<...>`
```

For updates, show a minimal diff and the reason for each change. For audits, report findings by severity (error / warning / info). Do not promise productivity gains; the evidence is mixed. State what was verified and what remains uncertain.

## Gotchas

- A rule that cannot change a decision is a slogan. Tie it to an observable action or cut it.
- "Never edit generated files" is incomplete without the regeneration command.
- A nested file that repeats the root adds context cost without changing behavior.
- A known-failing test or sandbox quirk is more valuable than a general warning; name it.
