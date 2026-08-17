# AGENTS.md

This repo builds personal Agent Skills. First-party skills live under `skills/<name>/SKILL.md`; the format spec and best practices are at https://agentskills.io/ (spec, best practices, evaluating skills, optimizing descriptions).

## Skill format
- `skills/<name>/` holds `SKILL.md` (YAML frontmatter + Markdown body) plus optional `scripts/`, `references/`, `assets/`.
- `name` and `description` are required frontmatter. `name` must match the parent directory: lowercase alphanumerics and hyphens only — no leading, trailing, or double hyphens.
- `description` states what the skill does and when to use it, with keywords matching likely prompts; it is the only thing agents see at startup, so it decides activation.
- Keep `SKILL.md` under ~500 lines / 5000 tokens. Move detail to `references/` files and tell the agent when to load each (e.g. "read references/x.md if ...").
- Validate with `skills-ref validate ./my-skill` (github.com/agentskills/agentskills).
- Write skill content using the installed `writing-for-agents` skill and its `SKILL-MECHANICS.md`; they are the authority on authoring agent-facing documents.

## Layout
- `skills/` — first-party skills, the repo's output.
- `.agents/skills/` — vendored, locked third-party skills; do not hand-edit.
- `skills-lock.json` — registry of installed third-party pins (source, `skillPath`, `computedHash`).
