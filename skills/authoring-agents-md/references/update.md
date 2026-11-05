# Updating AGENTS.md

Update starts with discovery in `SKILL.md`. Read `references/authoring.md` first; it owns the content standard. This file covers the audit, rewrites, cross-file checks, and close-out.

## 1. Audit every line

Delete the whole sentence when any of these is true:

1. **Stale**: it no longer bears on the work, or the behavior it describes has changed. A stated project convention the code has not adopted yet is a discrepancy to report, not a stale rule.
2. **Default**: the model already does it without being told.
3. **Environment-owned**: a config, script, manifest, or directory layout already owns the fact.
4. **Repeated**: another line, nested file, skill, or doc states the same meaning.
5. **Branch-specific**: only some runs need it; move it only into an in-scope nested file or an existing doc, otherwise report the split.
6. **Unearned**: it copies README or API docs, tours files, or repeats unverified output from an init command.

Deleting is the default. Adding a line needs a source and a reason it changes behavior.

## 2. Rewrite what survives

| Instead of | Write |
| --- | --- |
| Blanket read: "before every edit, read architecture.md" | Conditional pointer: "Use `docs/architecture.md` when changing service boundaries." |
| Always-test: "always run the full suite" | The check that matches the change, with its trigger and completion. |
| Blanket ask: "never run commands" | Permission plus completion: what may continue, and the condition that ends it. |
| Prohibition: "don't use npm" | Positive target: "Use `pnpm` for every script and package command." |
| Vague target: "handle errors well" | Concrete target: "Return `thiserror` enums from public APIs." |
| Restated config: "the linter bans `var`" | Pointer: "Run `pnpm lint`; see `eslint.config.js`." |
| Duplicated rule in a nested file | One owner, with a reference from the other file when needed. |

Keep a prohibition only as a hard guardrail that cannot be phrased positively, and pair it with the positive target.

## 3. Check the tree

- Every root and nested file has a distinct job. Nested files refine the root for their subtree; they do not repeat or contradict it.
- Every pointer, doc, and skill definition exists. Every project-specific command exists in a manifest, task runner, script, or CI workflow.
- The root stays within about 200 lines and 5,000 tokens. When it does not, move detail only into an in-scope nested file or an existing doc; otherwise report the split.
- Every rule names its scope; every work rule says what done means. Every section has content.
- The skills roster names invocation triggers and definition paths, not full procedures.

## 4. Close out

Apply every change supported by evidence. Stop and ask when a root/nested conflict or an unanswered judgment decision would change the content, or when a fix needs a new file outside the target set.

Report:

- Files updated.
- Lines removed and why.
- Rules rewritten or moved.
- Conflicts, unverifiable commands, and splits left open.
