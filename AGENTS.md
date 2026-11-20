## Skill authoring

- User-facing skills live under `skills/<name>/`.
- Vendored third-party skills live under `.agents/skills/` and are pinned in `skills-lock.json`; do not edit them.
- Before creating, editing, or reviewing a skill, read `docs/agents/skill-authoring/README.md`.
- When a skill writes a doc for agents to read, the preferred location is `docs/agents/<topic>.md` in the repo where the skill is invoked.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, using the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
