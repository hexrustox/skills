# Skill Audit

The goal is to check whether the skill the user requested will not trigger, will mislead the agent, will surprise the user, or carry stale guidance. The standard is the [skill authoring guide](skill-authoring/README.md); read the guide before judging content.

An audit is a conformance check against the skill's recorded spec and the guide, not a fresh design review. It ends when every finding has a terminal disposition (`fixed`, `accepted`, or `deferred`); an `open` finding is a decision request for the user, not a reason for another audit. Do not re-report a finding with a terminal disposition unless the text it cites changed or the fix regressed.

## Modes

| Mode | Use when | Coverage |
| --- | --- | --- |
| Full | No record exists, or the skill's job, triggers, output contract, or non-goals changed. | The whole skill; update the record. |
| Verify | Default after a fix or a non-material edit. | Open findings and the diff since the baseline; report regressions and new Errors only. |

Read the record before choosing the mode. Check for changes with `git diff <baseline> -- skills/<name>` and `git status --short -- skills/<name>`. If the skill is unchanged since the baseline, report the record and stop; run a Full audit only if the user explicitly asks for a fresh review after reading it.

## Record

Each audited skill has a record at `docs/agents/skill-audits/<name>.md`, created from [`TEMPLATE.md`](skill-audits/TEMPLATE.md). Read it first; create it during a Full audit. The record holds:

- **Spec** — job, triggers, output contract, success criteria, and non-goals, each in one sentence. Freeze it. Change it only when the skill's job, triggers, output contract, or non-goals change, and record why.
- **Baseline** — the commit whose skill content was audited.
- **Findings** — ID, check, evidence, severity, disposition, and rationale. Dispositions are `fixed`, `accepted`, `deferred`, or `open`.
- **History** — date, mode, baseline, result, and any spec change.

On a Full audit, propose the spec from the skill's description and body, and ask the user to confirm it before judging. After a Full audit or a passing Verify, set the baseline to the audited commit and add a History row. Accepted and deferred findings are closed until the text they cite changes. The auditor proposes a disposition; the user accepts or defers the risk. Never mark a finding accepted or deferred without the user's agreement.

## Finding bar

A finding must name all three:

1. The check and the guide line it fails.
2. A concrete failure: which prompt will not trigger the skill, which step cannot be followed as written, which term a fresh reader cannot explain, or which behavior surprises the user.
3. The smallest fix.

If you cannot name the concrete failure, the observation is a preference. Put it under `Open questions`, not `Findings`. Do not report hypothetical gotchas or "could be clearer" wording.

## Severity and gate

- **Error** — the skill is unusable or dangerous: instructions that cannot be followed as written, a description that sends the skill to a different job than the body performs, or behavior the user did not authorize. Fix before shipping; do not accept or defer one.
- **Warning** — the skill is likely to under-trigger or under-deliver, and you can name the concrete failure. Fix it when the fix is low-risk and cheaper than living with the failure; otherwise propose accept or defer. The user decides.
- **Info** — a simplification, wording improvement, unnecessary frontmatter field, or optional restructuring. Record it; never fix it during an audit.

Structural preferences are Info unless they cross the guide's budgets: branch-specific detail that forces irrelevant loading, or a `SKILL.md` over about 500 lines. Moving text into `references/` is not a finding by itself.

## Procedure

1. **Mode.** Choose Full or Verify from the record and the user's request. Done when the mode, skill, and baseline are named.
2. **Read.** Read the record, then the skill's files. In Full, read `SKILL.md` end to end and every text file under the skill directory. In Verify, read the changed files and the sections the open findings cite, with enough context to judge them. Note the skill-specific terms, abbreviations, and output fields in the files you read. Done when every file the mode requires has been read.
3. **Judge.** Apply the checks below. In Verify mode, judge only the checks affected by open findings and the lines changed since the baseline; report regressions and new Errors, not new Warnings or Info, and do not re-run the full checklist. Done when every check you applied is pass, fail, n/a, or `not verified`.
4. **Report.** Report findings and update the record. Edit skill files only when the user asked for fixes. Done when every finding has a path, evidence, and a proposed fix, and every open finding has a proposed disposition.

## Judgment checks

Judge only the named skill. Do not compare it with other skills: trigger collisions, relative fit, and whether another skill would do the job better are not part of this audit.

- [ ] The description states what the skill does and the coverage the body delivers; a model-invocable skill also names the situations that invoke it.
- [ ] A model-invocable description front-loads words the invoking prompt is likely to use and names non-obvious triggers.
- [ ] Frontmatter carries only fields that apply: `license` for distribution, `compatibility` for environment requirements, `disable-model-invocation` for user-only skills, and `metadata` or `allowed-tools` when the skill genuinely needs them.
- [ ] The body is imperative instructions to the agent, not an essay; each step has a completion criterion.
- [ ] Exact commands, paths, formats, and non-obvious project facts are present; common knowledge the agent would get right is omitted.
- [ ] The output contract is explicit: format, required sections, what each field means, and how to handle uncertainty.
- [ ] Every skill-specific term, abbreviation, and output field is defined at first use or linked to a definition.
- [ ] A fresh reader can explain the output contract and key terms without the author's context. Check this once when the spec is recorded or the output contract or key terms change; use a fresh-context reviewer for that acceptance check, or a self cold read marked `not verified`. Do not repeat it on every Verify.
- [ ] Gotchas and failure modes are named where they change behavior.
- [ ] Branch-specific detail is in `references/`, and each pointer says what the file contains and when to read it.
- [ ] Long references have a table of contents or another way to navigate.
- [ ] The skill expresses the pattern rather than one instance where it is meant to generalize.
- [ ] The skill's behavior stays within what its description promises and what the user authorized.
- [ ] The skill still describes one coherent unit of work.

## Common misses

- Repetition is not definition: a term repeated in the body, a reference, or the output contract is still undefined if none of them explains it.
- An explicit field format is not an explicit meaning; check what value belongs there and why.
- Standard technical vocabulary is not a finding; a skill-specific term that is never defined is.
- A check that passed is closed. Do not re-open it because you would have designed the skill differently.

## Stop rule

Run one Full audit per material change, then at most two Verify rounds per change or fix batch. Stop when zero Errors remain and every Warning and Info is fixed, accepted, or deferred. "The reviewer found nothing new" is not the pass condition.

At the cap, report the remaining findings and stop. Do not start another Full audit to check a fix; fix the cause, run Verify, and update the record.

## Report

Format each finding as:

```markdown
- **<severity>** `skills/<name>/<path>:<line>` — <problem>. <why it matters>. <proposed fix>.
```

Close with:

```markdown
## Skill audit
- Mode: `<full | verify>`
- Skill: `skills/<name>/`
- Baseline: `<commit>`
- Findings: `<n>` error · `<n>` warning · `<n>` info
- Dispositions: `<n>` fixed · `<n>` accepted · `<n>` deferred · `<n>` open
- Record: `docs/agents/skill-audits/<name>.md`
- Not verified: `<items and reasons>`
- Open questions: `<...>`
```
