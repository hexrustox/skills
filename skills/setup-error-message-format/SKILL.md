---
name: setup-error-message-format
description: "Install a project-wide standard for user-facing error messages at docs/agents/error-message.md, with an AGENTS.md pointer. Does not cover logs and does not audit existing messages."
disable-model-invocation: true
---

# Setup Error Message Format

Install the canonical error-message standard (`assets/error-message.md`) as `docs/agents/error-message.md`, add one pointer in `AGENTS.md`, and record the repo's conventions under the doc's `## Project conventions` heading.

This skill writes only `docs/agents/error-message.md` and `AGENTS.md`; it does not edit message strings, localization files, or any other file. It does not audit existing messages or govern logs.

Keep existing content unless the user approves a change: propose, then write.

## 1. Explore

Read what exists:

- `AGENTS.md` at the repo root. Find every reference to `docs/agents/error-message.md`: the heading, the line, and whether it resolves. Note the file's reference style: a `## References` table, a dedicated section, or prose.
- `docs/agents/error-message.md`. If it exists, read it end to end. List its `##` headings and the content under `## Project conventions`.
- Inspect source layout, manifests, and lockfiles to identify languages, frameworks, and surfaces:
  - **CLI:** binary entry points, command modules, argument parsers.
  - **Library/SDK:** error enums or types and their `Display`/`Error`/exception implementations.
  - **HTTP API:** handlers, error middleware, problem-details types, OpenAPI or API docs.
  - **UI:** forms, validation, alert components, and message catalogs.
- `README.md`, `CONTRIBUTING.md`, `docs/`, relevant `docs/adr/` decisions, and adjacent `docs/agents/*.md` that touch API, UI copy, or style. Record conflicts or approved deviations from the standard for `## Project conventions`.
- Existing messages. Search error construction sites and message catalogs. From representative strings, record the severity prefix, casing, punctuation, code format and registry path, message source paths, and localization system, source locale, and placeholder syntax. Do not inventory every message.
- `GLOSSARY.md`. If `GLOSSARY-MAP.md` exists, read it and each `GLOSSARY.md` it points to for the relevant contexts. Use their terms for message vocabulary; do not invent a synonym.
- Ownership. Look for the team that owns the conventions in `CODEOWNERS`, `CONTRIBUTING.md`, the doc, or the user. Use `none detected` when the repo does not say, and use today's date for `last reviewed` when creating or refreshing the doc.
- If no surface is detected, ask whether to proceed; the repo may be docs-only or about to add code. If the user declines, stop and report that nothing was written.

Done when every field in `## Project conventions` is filled from evidence or marked `none detected`/`not applicable`, each detected surface has a path, and you know whether the doc exists and every existing `AGENTS.md` pointer to it.

## 2. Present and confirm

Summarize what is present and missing. If `docs/agents/error-message.md` exists, ask whether to:

- **Replace** it with the asset's text and the new project section. This drops project-specific sections not in the asset.
- **Keep** it as-is and only add or update the pointer.
- **Merge**: keep existing content, add missing canonical sections, and build the merged doc described below.

Then show the exact final doc for the chosen path:

- New or replaced: the asset's text with `## Project conventions` filled from the exploration.
- Kept: the existing doc, unchanged.
- Merged: the full merged doc. Use the asset's canonical `##` headings in asset order; keep the content under existing headings unless the user approves the asset's content; append extra project sections after the canonical sections; and merge `## Project conventions` by starting from its existing bullets, updating the fields the exploration verified, and filling still-unknown fields with `none detected` or `not applicable`. If an existing heading clearly maps to a canonical heading under another name, ask whether to rename it instead of adding a duplicate.

Show the proposed `AGENTS.md` pointer:

```markdown
## Error messages

Read `docs/agents/error-message.md` before writing, changing, or reviewing user-facing errors in the CLI, library/SDK, HTTP API, or UI.
```

When `AGENTS.md` has a `## References` table, add this row instead:

```markdown
| Error messages | `docs/agents/error-message.md` — before writing, changing, or reviewing user-facing errors in the CLI, library/SDK, HTTP API, or UI |
```

Apply this decision table:

| Situation | Proposal |
| --- | --- |
| No `AGENTS.md` | Ask whether to create it with the pointer; skip the pointer if the user declines. |
| No reference | Add one in the file's style: a `## References` row or a `## Error messages` section at the end. |
| Reference under `## Error messages` | Keep it if it resolves; otherwise update it in place. |
| Reference under another heading or in prose | Update it in place and report the actual location; do not move it without approval. |
| Multiple references | Propose one pointer, remove the duplicates with approval, and report them. |
| Doc skipped | Skip the pointer and report both. |

Ask one final confirmation question: "Apply this error-message setup: write or keep `docs/agents/error-message.md` as proposed, and add, update, or keep the pointer in `AGENTS.md`?" Include the mode and any `AGENTS.md` creation. Show the exact text and let the user edit `## Project conventions` and the pointer before they answer. The canonical sections are installed as planned unless the user explicitly asks to change them.

Done when the user has approved or declined the doc, the pointer, and—when the doc exists—the mode, and the approved final text is recorded for step 3.

## 3. Write

- `docs/agents/error-message.md`:
  - Created, replaced, or merged: write the approved final text exactly. Do not change canonical sections the user did not explicitly approve changing.
  - Kept: leave the doc untouched.
  - Skipped: leave it absent.
  - Create `docs/agents/` if needed.
  - For a created, replaced, or merged doc, replace every `<...>` placeholder in `## Project conventions`; use `none detected` or `not applicable` instead of leaving one.
- `AGENTS.md`:
  - Apply the approved edit from step 2: create the file, add the pointer, update it in place, or consolidate duplicates.
  - Preserve surrounding content and the file's existing reference style.
  - Add only the pointer; do not inline rules from the doc.
  - If the doc is skipped, skip the pointer and report both.
- If a write fails, stop. Do not add the pointer to a doc that was not written. Report the failure and the artifacts left untouched.

Done when the approved doc text is in place (or kept/skipped); for a created, replaced, or merged doc, every canonical `##` heading appears exactly once, no placeholder remains in `## Project conventions`, every path named there exists, absent surfaces are recorded as `none detected` or `not applicable` rather than as paths, and every heading conflict is reported; and `AGENTS.md` contains exactly one pointer that resolves, or the pointer is skipped with a reason.

## 4. Report

Use this contract:

```markdown
## Error message setup
- Standard: `docs/agents/error-message.md` (`created` | `replaced` | `merged` | `kept` | `skipped` | `failed`)
- Agent file: `AGENTS.md` (`created` | `updated` | `kept` | `skipped` | `failed`)
- Section: `<heading>` (`added` | `updated` | `kept` | `skipped` | `failed`)
- Surfaces: `<surface (path); ...>` or `none detected`
- Project conventions: `<code format; localization; severity prefix; exceptions>` or `none detected`/`n/a`
- Validation: headings `<pass | n/a | fail>`; paths `<n>/<n> | n/a`; placeholders `<none | n/a>`; pointer `<resolved | skipped | failed>`
- Conflicts: `<heading (kept | replaced); ...>` or `none`
- Skips and failures: `<artifact: reason; ...>` or `none`
- Open questions: `<...>` or `none`
```

For a kept or skipped doc, report doc-content checks as `n/a`.

If the pointer resolves, tell the user that future agents can read the standard through it. If the doc was written or kept, tell them they can edit `docs/agents/error-message.md` directly and keep its `##` headings stable because this skill merges by heading. Re-run this skill to update the standard or record new project conventions.

Done when every artifact has a terminal status, every skip or failure has a reason, and every conflict is listed.
