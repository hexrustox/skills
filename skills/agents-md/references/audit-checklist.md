# AGENTS.md Audit Checklist

Read this when auditing an existing `AGENTS.md` or doing a maintenance pass. The goal is to find costly, stale, or contradictory content, not to rewrite the file to taste.

## Procedure

1. Read the root `AGENTS.md` and every nested `AGENTS.md` end to end.
2. Run the mechanical checks below.
3. Compare the file against the repository: commands, paths, scripts, generated files, CI.
4. Report findings by severity. Apply only mechanical fixes unless the user asked for semantic edits.

## Size and structure

- [ ] Root file is 100–150 lines; hard cap 200. Nested files are 60–80 lines.
- [ ] Any file over 300 lines is treated as a structural problem.
- [ ] Every section has a real value; no placeholders, welcome text, or personas.
- [ ] No YAML frontmatter.
- [ ] No README duplication or project-overview prose beyond one orientation line.
- [ ] Rules that belong in a skill or linked doc are moved out.

## Content

- [ ] Exact install/build/test/lint/format commands, including single-test and single-file forms.
- [ ] Working directory and required env vars are stated.
- [ ] Non-obvious directories are annotated; generated directories name their regeneration command.
- [ ] Conventions are non-inferable and include a preferred/deprecated example where useful.
- [ ] Boundaries cover always / ask first / never, each with an alternative or regeneration command.
- [ ] Environment gotchas are named: known-failing tests, sandbox quirks, slow commands, required rebuilds.
- [ ] A numbered "before you finish" verification gate exists.
- [ ] References are annotated with what they contain and when to read them; linked docs live under `docs/agents/`.
- [ ] Required runtime and tool versions are stated.
- [ ] No generic advice ("write clean code", "follow best practices") or personas.
- [ ] No secrets, tokens, internal URLs, or customer data.

## Consistency

- [ ] No contradictions in package manager, test command, generated-file policy, or root vs nested rules.
- [ ] No duplicated commands or rules between root and nested files.
- [ ] Nested files add only local rules and do not rely on overriding the root.
- [ ] No rule restates what a linter, formatter, or typechecker already enforces.
- [ ] `MUST`/`NEVER` are used sparingly, for true guardrails.
- [ ] Every "never" has a correct alternative or regeneration command.
- [ ] The code-over-docs precedence line exists or has an equivalent.
- [ ] Every rule is current: no path, command, or policy that the repo no longer uses.

## Mechanical checks

Run from the repository root. Adapt paths as needed, and use an equivalent regex tool if `rg` is unavailable.

```bash
find . -name AGENTS.md -not -path './.git/*' -exec wc -l {} +
rg -n '(TODO|TBD|FIXME|<[^>]+>)' -g 'AGENTS.md' .  # leftover placeholders
```

- [ ] Every command in the file was run from the stated directory, or explicitly marked unverified with a reason.
- [ ] Every referenced path, package script, Makefile target, and generated directory exists.
- [ ] The line count is within budget.
- [ ] No unresolved placeholders.

## Maintenance

- [ ] The root file has a last-verified date and owner, or the repo records ownership elsewhere.
- [ ] A maintenance trigger exists: command/tool/layout/CI changes, repeated agent mistakes, model/tool upgrades, quarterly.
- [ ] A 5–10 task regression set was run after the last significant edit, or the user explicitly declined.
- [ ] Every line added since the last audit traces to an observed failure or a verified change.

## Known smells

| Smell | What to look for | Fix |
| --- | --- | --- |
| Lint leakage | Rules a linter/formatter already enforces | Delete; point to the config or command |
| Context bloat | Files at or above 200 lines, low-priority detail | Cut prose, move branch detail to linked docs |
| Skill leakage | Task-specific procedures and runbooks | Move to a skill or linked doc |
| Conflicting instructions | Different package managers, test commands, or policies | Pick one and state it once |
| Init fossilization | `/init` output committed once and never reviewed | Re-derive from the repo; prune |
| Blind reference | A path with no explanation or loading condition | Add what it contains and when to read it |

## Severity

- **Error** — a command that fails, a path that no longer exists, a contradiction, a secret, or a rule that would cause destructive action. Fix before merging.
- **Warning** — over budget, blind reference, lint leakage, missing verification gate, stale last-verified date, missing owner. Fix or explicitly accept.
- **Info** — a simplification, optional tooling, or style preference. Report but do not block.
