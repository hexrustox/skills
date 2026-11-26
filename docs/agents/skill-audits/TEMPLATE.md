# <name> audit record

- Skill: `skills/<name>/`
- Baseline: `<commit>`
- Last updated: `<YYYY-MM-DD>`
- Last mode: `<full | verify>`

## Spec

- **Job:** <one sentence: what the skill enables the agent to do>
- **Triggers:** <one sentence: the prompts, files, or contexts that should invoke it; for a user-invoked skill, the explicit user request>
- **Output contract:** <one sentence: what the skill produces and in what shape>
- **Success:** <one sentence: what an accepted result looks like>
- **Non-goals:** <one sentence: what the skill deliberately does not do>

Change the spec only when the skill's job, triggers, output contract, or non-goals change; record why under History.

## Findings

| ID | Check / guide | Evidence | Severity | Disposition | Rationale |
| --- | --- | --- | --- | --- | --- |
| A1 | <check and guide line> | `skills/<name>/SKILL.md:<line>` | <error \| warning \| info> | <fixed \| accepted \| deferred \| open> | <why> |

Accepted and deferred findings stay closed until the text they cite changes. The user accepts or defers risk; the auditor only proposes.

## History

| Date | Mode | Baseline | Result | Spec change |
| --- | --- | --- | --- | --- |
| <YYYY-MM-DD> | <full \| verify> | `<commit>` | <n error, n warning, n info; dispositions> | <none \| why> |
