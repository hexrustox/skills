## Skill authoring

User-facing skills live under `skills/`. Development-tooling skills live under `tools/skills/`.

Load the `creating-skills` skill before creating or editing a skill. Vendored third-party skills live under `.agents/skills/` and are pinned in `skills-lock.json`; do not edit them. `opencode.json` adds `tools/skills` as a project skill source and hides the vendored `skill-creator` from model invocation, so `creating-skills` is the authoring workflow advertised from that source. OpenCode resolves the source from the working directory, so launch sessions at the repository root.

Generated eval workspaces (`<skill-name>-workspace/`) are ignored by git.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, using the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
