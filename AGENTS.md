## Writing skills

Create new skills under `skills/`. `.agents/skills/` holds vendored third-party skills tracked in `skills-lock.json`.
When creating or editing a skill, read `docs/agents/skill-spec.md` and `docs/agents/skill-best-practices.md`.
Name skills in the gerund form (`processing-pdfs`, `writing-documentation`), keeping one pattern across the collection.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, using the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
