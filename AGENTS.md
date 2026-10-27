This repo authors agent skills and packages them as a Claude Code plugin.

## Skills
- When adding or renaming an authored skill, register it in the `skills` array of `.claude-plugin/plugin.json` with its plugin-root-relative path under `./skills/`.
- `.agents/skills/` and `skills-lock.json` belong to the `skills` CLI; do not edit them by hand.
- When writing or modifying a skill (new or existing), load the `writing-for-agents` skill and read `docs/agents/spec.md` and `docs/agents/best-practices.md`. When evaluating a skill, read `docs/agents/evaluation.md`.
- Every authored `SKILL.md` carries `metadata` with `version` as its only key. New skills start at `"1.0.0"`; bump `version` in the same change whenever an existing skill is updated.

## Verification
- After creating a new skill or changing `.claude-plugin/plugin.json`, run `jq -e . .claude-plugin/plugin.json >/dev/null` and `diff <(find skills -name SKILL.md -printf '%h\n' | sort) <(jq -r '.skills[]' .claude-plugin/plugin.json | sed 's|^\./||' | sort)`. Done when both exit 0.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, using the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
