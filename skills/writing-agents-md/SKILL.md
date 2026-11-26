---
name: writing-agents-md
description: Create and update a repository's AGENTS.md files, including nested files in monorepos and other subtrees, plus the linked docs under docs/agents/. Covers verified commands, scope placement, and line budgets.
disable-model-invocation: true
---

# AGENTS.md

Write `AGENTS.md` as executable configuration, not documentation: the agent reads it and may act on it. Keep it short, current, and limited to what the agent cannot infer from the repository.

Write only `AGENTS.md` files and linked `docs/agents/<topic>.md` docs; ignore `CLAUDE.md`, `.cursor/rules`, and other agent instruction files.

## Route the request

Read every `AGENTS.md` and every linked doc you will change end to end before changing anything: the root file, any nested files, and existing `docs/agents/<topic>.md` files, skipping VCS, dependency, and build-output directories. Edit an existing file; preserve verified repo-specific content.

| File action | Sections |
| --- | --- |
| Create (new file) | 1 → 2 → 3 → 4 → 5 |
| Update (existing file) | 1 → 2 → 4 → 5 |

A request can require both actions: scaffold each new file, then edit each existing file. Before writing, list every file you expect to change and why; add any file validation discovers to the list before editing it. Change only `AGENTS.md` files and linked `docs/agents/<topic>.md` docs; ask before touching anything else.

If no root `AGENTS.md` exists and the request is an update, say so and ask whether to create one. If the user declines, do not create it; skip that file and report it, skip and report any new nested file or linked doc that would have no `AGENTS.md` to link it, and record any existing unreachable file under `Open questions`. If no other file is in scope, stop and report that nothing was written; otherwise continue with the files the user approved using the Create or Update sequence.

Done when you have listed every file you will create or edit for the user, with the reason for each, and know which sections apply.

## 1. Inspect the repository

Gather evidence; do not copy the README.

- Package manager and lockfile; required runtime and versions.
- Build, test, lint, format, and typecheck commands, including single-test and single-file forms.
- CI workflows, `Makefile`/`justfile`/task runner, and package scripts.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/`, and existing `AGENTS.md` files.
- Run commands that only read the repository or write disposable build or cache outputs inside the worktree to confirm behavior. Apply the step 5 side-effect rules before any command that installs dependencies, changes a lockfile, calls the network, or writes outside the worktree. Do not trust documentation alone.

Done when every task the file will document has a verified command or is explicitly marked unverified with the reason, and you have a list of non-obvious facts worth including.

## 2. Choose scope and placement

Assign each rule to its narrowest home:

- Root file for repo-wide rules.
- Nested file for rules that differ by subtree: commands, conventions, or boundaries.
- A linked doc at `docs/agents/<topic>.md` (relative to the repository root) for task-specific detail that would bloat the file; link it from `AGENTS.md`. Write it as reference: one orientation sentence, task-specific sections, and no repetition of `AGENTS.md` rules.
- An existing skill for procedures already packaged; name the skill and when to use it in `AGENTS.md`.

Move rules among the root file, nested files, and linked docs; do not copy them. Root routes to nested files; nested files add only local rules and do not repeat the root. Write nested files as additions; do not rely on a child file overriding the root. A nested file needs a parent `AGENTS.md`, and a linked doc needs an `AGENTS.md` that links it; if none exists, ask whether to create the root or skip the new file.

Budget: root aim for 150 lines or fewer, hard cap 200; nested aim for 80 or fewer, hard cap 100; linked docs aim for 150 or fewer, hard cap 200. The templates are starting points and can stay shorter; every line competes with the task. Over the hard cap is a structural problem — move detail down a level, do not trim prose. If a linked doc is over its hard cap, split it by task into multiple docs and link each from `AGENTS.md`. Count every line, including blank lines.

Done when every rule has one home at the narrowest scope.

## 3. Scaffold a new file

Read `assets/AGENTS.template.md` for a root file or `assets/AGENTS.nested.template.md` for a nested file. For a linked doc, follow the reference shape in step 2; do not use the `AGENTS.md` templates. Delete every section that does not apply; replace every placeholder with a verified value. When you create a nested file or linked doc, add or update its pointer in the owning `AGENTS.md` and list that pointer edit as part of the change.

Done when the new file has every needed section and no unfilled placeholders.

## 4. Write content

Exclude:

- Rules a linter, formatter, or typechecker already enforces.
- README-like overview prose beyond one orientation sentence, generic quality slogans, and personas.
- Task-specific procedures and runbooks; use an existing skill or linked doc instead.
- Secrets, tokens, internal URLs, and customer data.
- Blind paths with no explanation of what they contain or when to read them.
- YAML frontmatter; `AGENTS.md` is plain Markdown.

Reserve `MUST` and `NEVER` for true guardrails; prefer positive phrasing elsewhere. One rule per bullet. Prefer tables for commands and references.

When updating without a specific line request, delete stale lines and add only lines that address an observed failure or a verified change. When the user requests a specific line, check it against the repository before writing it. If it contradicts verified repository behavior, show the conflict and ask whether to change the line or the repository; do not write both versions. Never write a requested line that falls under the exclusions in step 4; show which exclusion applies and ask for a compliant replacement, and record any unresolved request under `Open questions`.

Done when every instruction line either changes agent behavior or prevents a known mistake. The template's one-sentence orientation is metadata, not an instruction. An instruction that cannot change a decision is a slogan.

## 5. Validate

Run the commands in every in-scope `AGENTS.md` file and linked doc; do not just read them. In scope means every `AGENTS.md` and `docs/agents/<topic>.md` in the repository, excluding VCS, dependency, and build-output directories.

- Fix every violation you find in an in-scope file, including pre-existing ones in files the request did not name. When validation adds a file to the change set, list it and the reason before editing it. Report violations that require changes outside `AGENTS.md` files and linked docs; do not edit those files without asking. If a fix is impossible or the user declines it, record the violation under `Open questions`; secrets, tokens, internal URLs, and customer data are always removed.
- Treat a command as non-destructive when it may write only disposable build or cache outputs inside the worktree. Treat commands that install dependencies, change a lockfile, call the network, or write outside the worktree as approval-gated: ask before running them, and run them only after approval. A destructive, deploy, or credential-requiring command is never run, even if it is also approval-gated.
- Execute every non-destructive command from the stated directory.
- If a command fails, classify the cause:
  - Missing command, path, package script, or Makefile/justfile/task-runner target: fix the file.
  - Environment failure (no network, missing database, absent toolchain, sandbox restriction): mark the command unverified with the reason and leave the instruction in place.
  - The command runs but the repository is broken, or a known failure is documented in the file (for example, under `## Gotchas`): keep the command, mark it unverified with the failure reason, and report it; edit the command only when the invocation itself is wrong.
- For destructive, deploy, or credential-requiring commands, check the command and path without running them; list them as unverified with the reason.
- Check that every referenced path, package script, Makefile/justfile/task-runner target, and named skill is available in every in-scope `AGENTS.md` file and linked doc. For a generated directory, verify the regeneration command and the do-not-edit policy instead of requiring the directory to exist before a build; count the directory as verified when that command and policy are verified.
- Check for contradictions: package manager, test command, generated-file policy, root vs nested vs linked-doc rules. Fix stale instructions to match verified repository behavior. When two in-scope files still conflict, keep the rule at its narrowest home and remove the other copy; ask when the fix changes a user-requested line; record unresolved conflicts under `Open questions`.
- Scan for secrets, tokens, internal URLs, and customer data; remove any you find.
- Verify the runtime version and required environment variables against the repository.
- Check that nested files add only local rules, do not repeat root rules, and are linked from the root or a parent `AGENTS.md`.
- Check that linked docs do not repeat `AGENTS.md` rules and are linked from an `AGENTS.md` file.
- Check that overview prose is at most one orientation sentence and task-specific procedures live in a linked doc or skill.
- Remove rules a linter, formatter, or typechecker already enforces, and blind references.
- Check the line budget.
- Search every in-scope `AGENTS.md` file and linked doc for unresolved `TODO`, `TBD`, `FIXME`, and `<...>` placeholders; review angle-bracket matches because code samples may use them.
- Fresh-reader test: if a fresh-context reviewer with read-only repository access is available (for example, a subagent), run the test for every file you created or edited.
  - For each file, give the reviewer the repository, that file, and one concrete small change; before asking, choose the three most important rules or facts that file must convey for that change.
  - Ask the reviewer to restate those three, describe its first step for the change, and name the exact command and directory it would run, without changing files. If the file documents no command, the reviewer uses the nearest applicable `AGENTS.md` (the file itself, its parent, or a file that links the doc) and names a command it would run, or states that the change needs no command.
  - Pass when it restates all three, describes a first step consistent with the file, and names a correct command and directory or gives a valid no-command reason. If the change needs a command and no applicable `AGENTS.md` documents one, report `fail` for that file. If it cannot pass, give it one simpler sample change and re-test; if it still cannot, report `fail` for that file.
  - If no reviewer is available, report `not run` for every changed file.

Done when every command and reference is verified or explicitly marked unverified with a reason (including destructive, deploy, credential, environment, and repository-state cases); every in-scope file is within its hard cap; every nested file and linked doc is reachable from an `AGENTS.md` file or recorded under `Open questions`; no unresolved placeholders remain; every contradiction is resolved or recorded under `Open questions`; and every changed file has a fresh-reader result of pass, fail, or not run.

## Report

Use this contract:

```markdown
- Mode: create | update | create + update | none
- Scope: root | nested at `<paths>` | root + nested `<paths>` | none
- Lines: `<path>` `<n>`/`<hard cap>` (repeat per file)
- Commands verified: `<n>/<total>` (repeat per file; unverified: `<command> (<reason>)` or `none`)
- References verified: `<n>/<total>` (repeat per file; paths, scripts, Makefile/justfile/task-runner targets, skills; unverified: `<item> (<reason>)` or `none`)
- Nested files: `<paths or none>`
- Linked docs: `<paths or none>`
- Skipped files: `<paths and reasons>` or `none`
- Fresh-reader test: `<path>` `<pass | fail | not run>` (repeat per changed file)
- Open questions: `<unresolved decisions or verification gaps>` or `none`
```

`Verified` means the command ran successfully from the stated directory. Destructive, deploy, and credential-requiring commands are unverified because they were not run; count them in `<total>`, omit them from `<n>`, and list them under `unverified` with the reason. For `References verified`, an item is verified when its path, package script, Makefile/justfile/task-runner target, or named skill was checked as available. `Commands verified` and `References verified` count verified items against the total the file documents. Count each command invocation the file documents once, and count each reference item once; `References verified` covers every such item in the file, not only the `## References` table. `Lines` counts every line, including blank lines. For `none`, set `Mode` and `Scope` to `none`, list any skipped file, and state why nothing was written. Still emit every field in a `none` report; mark inapplicable fields `not applicable`.

For every changed file, show a minimal diff and the reason for each change. State what was verified and what remains uncertain.

Done when every field is filled or marked not applicable.
