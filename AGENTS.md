## Skill authoring

Load the `creating-skills` skill before creating or editing a skill.

- User-facing skills live under `skills/<name>/`.
- Development-tooling skills live under `tools/skills/<name>/`.
- Vendored third-party skills live under `.agents/skills/` and are pinned in `skills-lock.json`; do not edit them.

OpenCode exposes `tools/skills` as a project skill source and hides the vendored `skill-creator` from model invocation; launch sessions at the repository root so the source resolves.

### Maintaining the `creating-skills` port

Read `docs/agents/creating-skills-maintenance.md` before syncing upstream or updating the port's provenance, pinned commit, or lock hash.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, using the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
