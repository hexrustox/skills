# Skill format

Create a skill as a directory with a `SKILL.md` at its root. Format the file as YAML frontmatter followed by Markdown instructions.

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

`SKILL.md` is the only required file. Add `scripts/`, `references/`, and `assets/` only when the skill needs them; the directory may contain any other files or directories.

## Frontmatter

```yaml
---
name: pdf-processing
description: Extracts text and tables from PDFs, fills forms, and merges PDFs. Use when handling PDF documents, forms, or text extraction.
---
```

| Field | Required | Rules |
| --- | --- | --- |
| `name` | Yes | 1–64 characters; lowercase letters, digits, and hyphens only; no leading or trailing hyphen and no `--`; match the skill directory name. |
| `description` | Yes | 1–1024 characters; state what the skill does and when to use it; include the keywords that identify the task. |
| `disable-model-invocation` | No | Set `true` to make the skill user-invoked: only the human can invoke it by name, no other skill can reach it, and its `description` stays out of the agent's always-loaded context, becoming a human-facing one-line summary. Omit it to make the skill model-invoked: the agent and other skills can reach it, at the cost of always loading `description`. Set `true` only when the skill fires by hand and nothing else must invoke it. |
| `license` | No | Set a license name or a reference to a bundled license file. |
| `compatibility` | No | 1–500 characters; state environment requirements only, such as product, system packages, network access, or runtime. |
| `metadata` | No | Add a string-to-string map for extra properties; use reasonably unique keys. |
| `allowed-tools` | No | Set a space-separated string of pre-approved tools; experimental and implementation-dependent. |

## Body

Put the skill instructions in the Markdown body. Use ordered steps, input and output examples, and common edge cases.

The consuming agent loads the entire body on activation. Keep it focused.

## Progressive disclosure

Structure the skill so the agent reads only what the current task needs:

1. **Metadata** — `name` and `description`, loaded for every skill at startup (about 100 tokens).
2. **Instructions** — the full `SKILL.md` body, loaded on activation; keep it under 500 lines and 5,000 tokens.
3. **Resources** — files in `scripts/`, `references/`, or `assets/`, loaded only when needed.

Move detailed material into `references/`. For each file, state its loading condition: "Read `references/api-errors.md` when the API returns a non-200 status."

## Optional directories

Add optional directories only when the skill needs them:

- `scripts/` — executable code; self-contained or with documented dependencies, useful error messages, and edge-case handling.
- `references/` — focused documentation loaded on demand; smaller files cost less context.
- `assets/` — templates, images, data files, and other static resources.

## File references

Reference files with paths relative to the skill root, one level deep from `SKILL.md`:

```markdown
See [the reference guide](references/REFERENCE.md) for details.

Run `scripts/extract.py`.
```
