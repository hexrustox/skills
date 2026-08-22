# AGENTS.md

This repo builds personal Agent Skills. First-party skills live under `skills/<category>/<name>/SKILL.md`, grouped into `skills/general/` (language-agnostic) and `skills/rust/` (Rust-specific); the format spec and best practices are at https://agentskills.io/ (spec, best practices, evaluating skills, optimizing descriptions).

## Skill format
- `skills/<name>/` holds `SKILL.md` (YAML frontmatter + Markdown body) plus optional `scripts/`, `references/`, `assets/`.
- `name` and `description` are required frontmatter. `name` must match the parent directory: lowercase alphanumerics and hyphens only — no leading, trailing, or double hyphens.
- `description` states what the skill does and when to use it, with keywords matching likely prompts; it is the only thing agents see at startup, so it decides activation. Keep it to the *what* and the *when* only — no how/detail (details live in the SKILL.md body). Under 400 characters (the spec max is 1024).
- Keep `SKILL.md` under ~500 lines / 5000 tokens. Move detail to `references/` files and tell the agent when to load each (e.g. "read references/x.md if ...").
- `description` must not mention other skills.
- No validation or verification step is required after writing a skill.
- Write skill content using the installed `writing-for-agents` skill and its `SKILL-MECHANICS.md`; they are the authority on authoring agent-facing documents.
- When adding a skill, add its row to the README's `Skills` table, drawn from the frontmatter `description`.

## Skill independence
- Each skill is self-contained and works on its own; never make a skill depend on another skill to do its job.
- Do not reference other skills as pointers or suggestions: no "see also", "related skills", "relevant skills", or "next step: use X skill". A skill's body covers only its own task, and links create chained dependencies.
- Reference another skill only when ALL of these hold:
  - it is necessary — the current skill genuinely cannot complete its task without it;
  - it complements the current context — it supplies required procedure or data, not optional background;
  - the needed piece cannot be inlined instead — if copying the relevant portion into the current skill removes the need to reference, inline it.
- When a reference is warranted, frame it as a direct instruction naming the skill (e.g. "run the X skill and follow it"), never as a suggestion.
- Collect every warranted reference in a single `## Pointers` section at the end of the skill, instead of scattering skill names through the body.
  - `## Pointers` is a dependency list, not a discovery list: it holds only references that meet the criteria above, one per line.
  - Format each entry as a conditional direct instruction: "When <situation>, run the X skill and follow it."
  - In the body, signal the need at the point it arises: "If <situation>, see Pointers." Do not name the skill in the body.
  - `references/` files are doc files, not other skills; other skills go only in `## Pointers`.

## Layout
- `skills/` — first-party skills, the repo's output.
- `.agents/skills/` — vendored, locked third-party skills; do not hand-edit.
- `skills-lock.json` — registry of installed third-party pins (source, `skillPath`, `computedHash`).
