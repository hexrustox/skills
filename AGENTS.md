## Skill authoring

- User-facing skills live under `skills/<name>/`.
- Vendored third-party skills live under `.agents/skills/` and are pinned in `skills-lock.json`; do not edit them.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, using the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
