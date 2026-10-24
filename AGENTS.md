This repo packages authored skills as a Claude Code plugin.

## Skills
- Authored skills live in `skills/`, one directory per skill with a `SKILL.md`; topic nesting is allowed (`skills/<topic>/<name>`).
- List every authored skill directory in the `skills` array of `.claude-plugin/plugin.json` in the same change, using its plugin-root-relative path (`./skills/<topic>/<name>`).
- Load the `writing-for-agents` skill before creating or editing a skill. Format: `docs/agents/spec.md`; authoring: `docs/agents/best-practices.md`; evaluation: `docs/agents/evaluation.md`.
- `.agents/skills/` and `skills-lock.json` belong to the `skills` CLI, not this repo's authored content. leave both alone.
