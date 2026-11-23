---
name: writing-agents-md
description: Create and update a repository's AGENTS.md files, including nested files in monorepos and other subtrees. Covers verified commands, scope placement, and line budgets.
disable-model-invocation: true
---

# AGENTS.md

Write `AGENTS.md` as executable configuration, not documentation: the agent reads it and may act on it. Keep it short, current, and limited to what the agent cannot infer from the repository.

Write only `AGENTS.md` among agent instruction files; put supporting detail in linked docs.

## Route the request

Read every `AGENTS.md` end to end before changing anything: the root file and any nested files, skipping VCS, dependency, and build-output directories. Edit an existing file; preserve verified repo-specific content.

| File action | Sections |
| --- | --- |
| Create (new file) | 1 → 2 → 3 → 4 → 5 |
| Update (existing file) | 1 → 2 → 4 → 5 |

A request can require both actions: scaffold each new file, then edit each existing file. Before writing, list the files you will change and why. Change only files named by the request; ask before touching any other root or nested file.

If no root `AGENTS.md` exists and the request is an update, say so and ask whether to create one. If the user declines, do not create it; skip that file and report it. If no other file is in scope, stop and report that nothing was written; otherwise continue with the files the user approved using the Create or Update sequence.

Done when you know which files will be created, which will be edited, and which sections apply to each.

## 1. Inspect the repository

Gather evidence; do not copy the README.

- Package manager and lockfile; required runtime and versions.
- Build, test, lint, format, and typecheck commands, including single-test and single-file forms.
- CI workflows, `Makefile`/`justfile`/task runner, and package scripts.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/`, and existing `AGENTS.md` files.
- Run commands that only read the repository or write disposable build or cache outputs to confirm behavior; do not trust documentation alone.

Done when you have a verified command for every task the file will document, and a list of non-obvious facts worth including.

## 2. Choose scope and placement

Assign each rule to its narrowest home:

- Root file for repo-wide rules.
- Nested file for rules that differ by subtree: commands, conventions, or boundaries.
- A linked doc at `docs/agents/<topic>.md` (relative to the project root) for task-specific detail that would bloat the file; link it from `AGENTS.md`.
- An existing skill for procedures already packaged; name the skill and when to use it in `AGENTS.md`.

Move rules among the root file, nested files, and linked docs; do not copy them. Root routes to nested files; nested files add only local rules and do not repeat the root. Write nested files as additions; do not rely on a child file overriding the root.

Budget: root aim for 150 lines or fewer, hard cap 200; nested aim for 80 or fewer, hard cap 100. The templates are starting points and can stay shorter; every line competes with the task. Over the hard cap is a structural problem — move detail down a level, do not trim prose. Count every line, including blank lines.

Done when every rule has one home at the narrowest scope.

## 3. Scaffold a new file

Read `assets/AGENTS.template.md` for a root file or `assets/AGENTS.nested.template.md` for a nested file. Delete every section that does not apply; replace every placeholder with a verified value.

Done when the new file has every needed section and no unfilled placeholders.

## 4. Write content

Exclude:

- Rules a linter, formatter, or typechecker already enforces.
- README-like overview prose beyond one orientation line, generic quality slogans, and personas.
- Task-specific procedures and runbooks; use an existing skill or linked doc instead.
- Secrets, tokens, internal URLs, and customer data.
- Blind paths with no explanation of what they contain or when to read them.
- YAML frontmatter; `AGENTS.md` is plain Markdown.

Reserve `MUST` and `NEVER` for true guardrails; prefer positive phrasing elsewhere. One rule per bullet. Prefer tables for commands and references.

Add a precedence line unless the repo already has an equivalent: "When documentation and existing code disagree, follow the existing code and report the inconsistency." This is cheap and prevents stale instructions from overriding working code.

When updating, delete stale lines; add a line only for an observed failure or a verified change.

Done when every instruction line either changes agent behavior or prevents a known mistake. The template's one-line orientation and the `Last verified`/`Owner` footer are metadata, not instructions. An instruction that cannot change a decision is a slogan.

## 5. Validate

Run the file's commands; do not just read it.

- Treat a command as non-destructive when it may write only disposable build or cache outputs inside the worktree. Ask before running a command that installs dependencies, changes a lockfile, calls the network, or writes outside the worktree, unless the user already approved that side effect.
- Execute every non-destructive command from the stated directory.
- If a command fails, classify the cause:
  - Missing command, path, package script, or Makefile target: fix the file.
  - Environment failure (no network, missing database, absent toolchain, sandbox restriction): mark the command unverified with the reason and leave the instruction in place.
  - The command runs but the repository is broken, or a known failure is documented in the file (for example, under `## Gotchas`): keep the command, record the failure, and report it; edit the command only when the invocation itself is wrong.
- For destructive, deploy, or credential-requiring commands, verify the command and path without running them; mark them unverified and say why.
- Check that every referenced path, package script, Makefile target, and named skill is available. For a generated directory, verify the regeneration command and the do-not-edit policy instead of requiring the directory to exist before a build; count the directory as verified when that command and policy are verified.
- Check for contradictions: package manager, test command, generated-file policy, root vs nested rules.
- Scan for secrets, tokens, internal URLs, and customer data; remove any you find.
- Verify the runtime version and required environment variables against the repository.
- Check that nested files add only local rules and do not repeat root rules.
- Check that overview prose is at most one orientation line and task-specific procedures live in a linked doc or skill.
- Remove rules a linter, formatter, or typechecker already enforces, and blind references.
- Check the line budget.
- Search for unresolved `TODO`, `TBD`, `FIXME`, and `<...>` placeholders; review angle-bracket matches because code samples may use them. Set the `Last verified` date to today and confirm `Owner` is current, or record ownership elsewhere; nested files inherit the root's values when a root exists.
- Fresh-reader test: if a fresh-context reviewer with read-only repository access is available (for example, a subagent), give it the repository, the file, and one concrete small change. Ask it to restate the three most important rules and name the exact command it would run, without changing files. Pass when it restates all three rules and names a correct command. If it cannot, give it one simpler sample change and re-test; if it still cannot, report `fail`. If no reviewer is available, skip the test and report `not run`.

Done when every command and reference is verified or explicitly reported with a reason (including destructive, deploy, credential, environment, and repository-state cases); every file is within its hard cap; no unresolved placeholders remain; the last-verified date is today's date and ownership is recorded; and the fresh-reader test result is reported as pass, fail, or not run.

## Report

Use this contract:

```markdown
## AGENTS.md
- Mode: create | update | create + update | none
- Scope: root | nested at `<paths>` | root + nested `<paths>` | none
- Lines: `<path>` `<n>`/`<hard cap>` (repeat per file)
- Commands verified: `<n>/<total>` (repeat per file; unverified: `<command> (<reason>)` or `none`)
- References verified: `<n>/<total>` (repeat per file; paths, scripts, targets, skills; unverified: `<item> (<reason>)` or `none`)
- Nested files: `<paths or none>`
- Skipped files: `<paths and reasons>` or `none`
- Ownership: `<owner/date>` for the root file, or recorded in `<path>`
- Fresh-reader test: `<pass | fail | not run>`
- Open questions: `<unresolved decisions or verification gaps>` or `none`
```

`Verified` means the command ran successfully from the stated directory, or its path and invocation were checked without running because it is destructive, deploy, or credential-requiring. `Commands verified` and `References verified` count verified items against the total the file documents. `References verified` covers every path, package script, Makefile target, and named skill in the file, not only the `## References` table. `Lines` counts every line, including blank lines. For `none`, set `Mode` and `Scope` to `none`, list any skipped file, and state why nothing was written. Still emit every field in a `none` report; mark inapplicable fields `not applicable`.

For updates, show a minimal diff per changed file and the reason for each change. State what was verified and what remains uncertain.

Done when every field is filled or marked not applicable.
