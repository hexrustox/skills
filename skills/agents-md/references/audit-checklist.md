# AGENTS.md Audit Checklist

Read this when auditing an existing `AGENTS.md` or doing a maintenance pass. The goal is to find costly, stale, or contradictory content, not to rewrite the file to taste.

## Procedure

1. Read the root `AGENTS.md` and every nested `AGENTS.md` end to end.
2. Run the mechanical checks below.
3. Compare the file against the repository: commands, paths, scripts, generated files, CI.
4. Report findings by severity using the format below. Apply mechanical fixes only when the user asked for an edit; confirm semantic changes first.

## Size and structure

- [ ] Root file is 100–150 lines; hard cap 200. Nested files are 60–80 lines; hard cap 100. Over the hard cap is a structural problem, not a writing problem.
- [ ] Every section has a real value; no placeholders, welcome text, or personas.
- [ ] No YAML frontmatter.
- [ ] No README duplication or project-overview prose beyond one orientation line.
- [ ] Task-specific procedures and runbooks live in a linked doc or an existing skill, not in `AGENTS.md`.

## Content

- [ ] Exact install/build/test/lint/format commands, including single-test and single-file forms.
- [ ] Working directory and required env vars are stated.
- [ ] Non-obvious directories are annotated; generated directories name their regeneration command.
- [ ] Conventions are non-inferable and include a preferred/deprecated example where useful.
- [ ] Boundaries cover always / ask first / never. Every `Never` boundary names the correct alternative or regeneration command.
- [ ] Environment gotchas are named: known-failing tests, sandbox quirks, slow commands, required rebuilds.
- [ ] A numbered "before you finish" verification gate exists.
- [ ] References are annotated with what they contain and when to read them. Linked docs live under `docs/agents/`; a skill reference names the skill and when to use it.
- [ ] Required runtime and tool versions are stated.
- [ ] No generic advice ("write clean code", "follow best practices") or personas.
- [ ] No secrets, tokens, internal URLs, or customer data.

## Consistency

- [ ] No contradictions in package manager, test command, generated-file policy, or root vs nested rules.
- [ ] No duplicated commands or rules between root and nested files.
- [ ] Nested files add only local rules and do not rely on overriding the root.
- [ ] No rule restates what a linter, formatter, or typechecker already enforces.
- [ ] `MUST`/`NEVER` are used sparingly, for true guardrails.
- [ ] The code-over-docs precedence line exists or has an equivalent.
- [ ] Every rule is current: no path, command, or policy that the repo no longer uses.

## Mechanical checks

Work from the repository root. Inventory every `AGENTS.md` outside VCS, dependency, and build-output directories (for example `.git`, `node_modules`, `vendor`, `dist`), with its line count. Search the same files for `TODO`, `TBD`, `FIXME`, and unfilled `<...>` placeholders.

- [ ] Every non-destructive command in the file was run from the stated directory; destructive, deploy, or credential-requiring commands were verified and marked unverified with a reason.
- [ ] Every referenced path, package script, Makefile target, and generated directory exists.
- [ ] The line count is within the hard cap and target budget.
- [ ] No unresolved placeholders; review angle-bracket matches, since code samples may use them.

## Maintenance

- [ ] The root file has a last-verified date and owner, or the repo records ownership elsewhere.
- [ ] A maintenance trigger exists: command/tool/layout/CI changes, repeated agent mistakes, model/tool upgrades, quarterly.
- [ ] If the repo has a 5–10 task regression set, it was run after the last significant edit; otherwise report `not available`.
- [ ] Every line added since the last audit traces to an observed failure or a verified change; if provenance is unavailable, report `not verified`.

## Known smells

In an audit, report these; apply fixes only when the user asked for an edit.

| Smell | What to look for | Fix |
| --- | --- | --- |
| Lint leakage | Rules a linter/formatter already enforces | Delete; point to the config or command |
| Context bloat | Files near or over the hard cap, low-priority detail | Cut prose, move branch detail to linked docs |
| Skill leakage | Task-specific procedures and runbooks | Link an existing skill or move to a linked doc |
| Conflicting instructions | Different package managers, test commands, or policies | Pick one and state it once |
| Init fossilization | `/init` output committed once and never reviewed | Re-derive from the repo; prune |
| Blind reference | A path with no explanation or loading condition | Add what it contains and when to read it |

## Severity

- **Error** — a command that fails, a path that no longer exists, a contradiction, a secret, a rule that would cause destructive action, or a file over its hard cap. Fix before merging.
- **Warning** — over the target budget but under the hard cap, a blind reference, lint leakage, a missing verification gate, a stale last-verified date, or a missing owner. Fix or explicitly accept.
- **Info** — a simplification, optional tooling, or a style preference. Report but do not block.

Format each finding as:

- **<severity>** `<path>:<line>` — <problem>. <why it matters>. <fix>.
