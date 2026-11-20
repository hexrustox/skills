---
name: agents-md
description: Create, update, and audit a repository's AGENTS.md files, including nested monorepo files. Use when setting up repository agent instructions, reviewing or pruning an existing file, or splitting an oversized root.
---

# AGENTS.md

Write `AGENTS.md` as executable configuration, not documentation: the agent reads it and may act on it. Keep it short, current, and limited to what the agent cannot infer from the repository.

Write only `AGENTS.md` among agent instruction files; put supporting detail in linked docs.

## Route the request

Read every existing `AGENTS.md` end to end before changing anything: the root file and any nested files. Edit an existing file; preserve verified repo-specific content.

| Request | Do |
| --- | --- |
| Create | Inspect the repo, choose scope and placement, draft from the template, validate |
| Update | Inspect the file against the repo, prune stale content, edit, validate |
| Audit | Read the existing files, run `references/audit-checklist.md`, report findings by severity |

Steps 1–5 are the create/update path; an audit goes from the checklist straight to Report.

Done when you know the mode, the files in scope, and whether the deliverable is a report or file changes.

## 1. Inspect the repository

Gather evidence; do not copy the README.

- Package manager and lockfile; required runtime and versions.
- Build, test, lint, format, and typecheck commands, including single-test and single-file forms.
- CI workflows, `Makefile`/`justfile`/task runner, and package scripts.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/`, and existing `AGENTS.md` files.
- Run read-only commands to confirm behavior; do not trust documentation alone.

Done when you have a verified command for every task the file will document, and a list of non-obvious facts worth including.

## 2. Choose scope and placement

Assign each rule to its narrowest home:

- Root file for repo-wide rules.
- Nested file for rules that differ by subtree: commands, conventions, or boundaries.
- A linked doc at `docs/agents/<topic>.md` (relative to the project root) for task-specific detail that would bloat the file; link it from `AGENTS.md`.
- An existing skill for procedures already packaged; reference it from `AGENTS.md`.

Move rules between files; do not copy them. Root routes to nested files; nested files add only local rules and do not repeat the root. Write nested files as additions; do not rely on a child file overriding the root.

Budget: root 100–150 lines, hard cap 200; nested 60–80, hard cap 100. These are attention budgets, not style targets: every line competes with the task. Over the hard cap is a structural problem — move detail down a level, do not trim prose.

Done when every rule has one home at the narrowest scope.

## 3. Draft

Read `assets/AGENTS.template.md` for a root file or `assets/AGENTS.nested.template.md` for a nested file. Delete every section that does not apply; replace every placeholder with a verified value.

Exclude:

- Rules a linter, formatter, or typechecker already enforces.
- README-like overview prose, generic quality slogans, and personas.
- Task-specific procedures and runbooks; use an existing skill or linked doc instead.
- Secrets, tokens, internal URLs, and customer data.
- Blind paths with no explanation of what they contain or when to read them.
- YAML frontmatter; `AGENTS.md` is plain Markdown.

Use `MUST` or `NEVER` two or three times in the whole file, not thirty. One rule per bullet. Prefer tables for commands and references.

Add a precedence line unless the repo already has an equivalent: "When documentation and existing code disagree, follow the existing code and report the inconsistency." This is cheap and prevents stale instructions from overriding working code.

Done when every line either changes agent behavior or prevents a known mistake. A line that cannot change a decision is a slogan.

## 4. Validate

Run the file's commands; do not just read it.

- Execute every non-destructive command from the stated directory.
- For destructive, deploy, or credential-requiring commands, verify the command and path without running them; mark them unverified and say why.
- Check that every referenced path, package script, Makefile target, and generated directory exists.
- Check for contradictions: package manager, test command, generated-file policy, root vs nested rules.
- Remove rules a linter, formatter, or typechecker already enforces, and blind references.
- Check the line budget.
- Fresh-reader test: if a fresh-context reviewer that can read and write within the repo is available (for example, a subagent), give it the repository and the file, then ask it to restate the three most important rules and complete a small task. If none is available, skip the test and report `not run`. If it cannot complete the task, treat that as a signal: narrow the task and re-test before concluding the file is ambiguous or too long.

Done when every non-destructive command and path is verified, destructive commands are marked unverified with a reason, the line budget is checked, and the fresh-reader test passes or is reported `not run`.

## 5. Maintain

For a maintenance pass, read the Maintenance section of `references/audit-checklist.md`. Delete stale lines; add a line only for an observed failure or a verified change.

Done when stale lines are gone and every added line traces to an observed failure or a verified change, or its provenance is reported as unverified.

## Report

Use this contract:

```markdown
## AGENTS.md
- Mode: create | update | audit
- Scope: root | nested at `<path>` | root + nested `<paths>`
- Lines: `<path>` `<n>`/`<hard cap>` (repeat per file)
- Commands verified: `<n>/<n>` (unverified: `<...>`)
- Paths verified: `<n>/<n>`
- Nested files: `<paths or none>`
- Findings (audits only): `<n>` error · `<n>` warning · `<n>` info
- Fresh-reader test: `<pass | fail | not run>`
- Open questions: `<...>`
```

For updates, show a minimal diff and the reason for each change. For audits, report findings by severity (error / warning / info) using the format in `references/audit-checklist.md`. State what was verified and what remains uncertain.

Done when every field is filled or marked not applicable.
