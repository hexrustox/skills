---
name: setup-logging-conventions
description: Set up project logging conventions at docs/agents/logging.md and point AGENTS.md to it. Does not configure logging or rewrite existing calls.
disable-model-invocation: true
---

# Setup Logging Conventions

Install `assets/logging.md` as `docs/agents/logging.md` and add one pointer in `AGENTS.md`. The doc governs log record format, message wording, fields, severity, and safety.

This skill writes only `docs/agents/logging.md` and `AGENTS.md`; it creates `docs/agents/` if needed. It does not edit application code, logger configuration, linters, or CI. Keep existing content unless the user approves a change: propose, then write.

Keep the rules in the doc. A new `## Logging` section is a heading and one short paragraph; existing extra content stays unless the user approves trimming. Do not duplicate the doc in `AGENTS.md`.

## 1. Explore

Read `assets/logging.md` and the target repository:

- Root `AGENTS.md` and any nested `AGENTS.md` that could own logging rules.
- `docs/agents/logging.md` and any other logging doc, such as `LOGGING.md` or `docs/logging.md`.
- Manifests, logger setup, and a representative sample of log calls in each main language or service. Use `rg` for logger APIs such as `.info(`, `.error(`, `slog.`, or `tracing::`; stop when the conventions are clear, and do not audit every call.
- Existing style docs and linter config relevant to logging, such as Ruff G004, sloglint/logcheck, ESLint, or Clippy.
- CI checks that validate log statements or log schemas.

Build the project profile from `assets/logging.md`. For each row, record the evidence and mark it:

- `observed`: the available evidence shows one convention for this row.
- `mixed`: the available evidence shows more than one convention for this row.
- `absent`: no evidence; propose the asset default.

Record invariant conflicts separately: interpolated messages, secrets or raw PII in logs, duplicate error logging, and anything else that contradicts the asset's rules. A conflict does not change a row's label.

The rows are:

- Record format.
- Field naming.
- Timestamp.
- Message style.
- Language variant.
- Event names.
- Level mapping.

If the repository has no application code or logging yet, ask whether to proceed with the defaults.

If the repository root is not the project root, a nested `AGENTS.md` owns the logging rules, or a monorepo has independent logging stacks, ask where the doc and pointer belong and whether one project-wide profile is appropriate.

If an existing logging doc exists, read it end to end and compare its rules with the asset.

Done when you can show the profile with evidence for every row, state whether the doc and pointer already exist, and name every file the write will touch.

## 2. Present and confirm

Show:

- The proposed `AGENTS.md` block:

```markdown
## Logging

Before adding or changing a log statement, read `docs/agents/logging.md` for message wording, fields, and severity.
```

- `assets/logging.md` in full, with the proposed profile values substituted and the examples adjusted to match.
- The evidence behind each profile value (`observed`, `mixed`, or `absent`).
- The existing `docs/agents/logging.md`, if present.
- Any existing logging pointer in `AGENTS.md`; if it targets another doc, ask whether to update it or keep it.

If the doc exists, ask whether to:

- **Replace** it with the asset's text and the confirmed profile.
- **Keep** it as-is and only add the pointer.
- **Merge**: compare `##` headings; add missing sections from the asset, keep existing sections, and list headings present in both with different rules so the user can decide. Update the profile from the existing doc when it records a deliberate choice.

List the conflicts recorded in exploration. State that the skill will not rewrite existing calls.

Ask how to resolve the profile: adopt the recommended defaults, codify the observed conventions where they are consistent, or choose per row. Ask one final confirmation question covering the doc, the pointer, and creating `AGENTS.md` or `docs/agents/` if needed. Show the proposed text and let the user edit it before they answer.

Done when the user has approved or declined each artifact: doc, pointer, and file creation.

## 3. Write

- `docs/agents/logging.md`: create `docs/agents/` if needed. For a new or replaced doc, copy `assets/logging.md` and fill the project profile with the approved values. If the approved profile changes a value that appears in the examples, update the examples and field names in the doc so they match the profile. For a merge, write the approved merged text. For keep, leave the doc untouched. Leave no unresolved placeholders.
- `AGENTS.md`: create it if missing and the user approved. If a `## Logging` section exists, add the pointer line there or update the existing pointer. Otherwise append the section at the end. If an equivalent pointer exists under another heading, such as `### Logging` under `## Code style`, update it in place. Preserve surrounding content and avoid duplicate pointers. If the doc is skipped, skip the pointer and report both.
- Do not edit application code, logger configuration, linter config, or CI.
- If you create `AGENTS.md`, keep it to the approved `## Logging` section and tell the user it may need broader repository instructions.

Done when the pointer path resolves, the profile has no unresolved placeholders, and the diff for the files this skill wrote contains only the approved changes.

## 4. Report

Use this contract:

```markdown
## Logging conventions setup
- Doc: `docs/agents/logging.md` (`created` | `replaced` | `merged` | `kept` | `skipped`)
- Agent file: `AGENTS.md` (`created` | `updated` | `kept` | `skipped`)
- Section: `## Logging` (`added` | `updated` | `kept` | `skipped`)
- Profile: `<format>; <field naming>; <timestamp>; <message style>; <language>; <event names>; <levels>`
- Existing doc: `<none | kept | merged | replaced>` (`<conflicts>`)
- Conflicts: `<n>` existing practices conflict with the conventions; not rewritten.
- Files changed: `<paths>`
- Open questions: `<...>`
```

Tell the user that future agents read the doc through the pointer. Keep the doc's `##` headings stable because the skill merges by heading on a re-run. Existing code is not reformatted; use the conventions for new and changed log statements and migrate the rest separately. Re-run this skill to update the profile or merge a revised asset.
