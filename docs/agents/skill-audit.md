# Skill Audit

The goal is to find skills that will not trigger, will mislead the agent, will surprise the user, or carry stale guidance. The standard is the [skill authoring guide](skill-authoring/README.md); read it, including **Common mistakes**, before judging content.

## Procedure

1. **Scope.** Audit the named skill, or every directory under `skills/` when the user asks for a library review. Done when you can list every skill in scope.
2. **Read.** Read `SKILL.md` end to end, then every text file under the skill directory; judge the whole skill, not just its description. Done when every file in scope has been read.
3. **Judge.** Apply the judgment checks below to each skill. Done when every check is marked pass, fail, n/a, or `not verified`.
4. **Report.** Report findings by severity; edit files only when the user asked for fixes. Done when every finding has a path, evidence, and a proposed fix, and the summary is filled in.

## Judgment checks

- [ ] The description states what the skill does, the situations that invoke it, and the coverage the body delivers.
- [ ] The description front-loads words the invoking prompt is likely to use and names non-obvious triggers.
- [ ] Each authored skill has a distinct trigger; when two descriptions collide, name the pair and the job each should win.
- [ ] When an installed skill fits the same prompts better, this skill distinguishes itself or points at the other skill.
- [ ] Frontmatter carries only fields that apply: `license` for distribution, `compatibility` for environment requirements, and `metadata` or `allowed-tools` when the skill genuinely needs them.
- [ ] The body is imperative instructions to the agent, not an essay; each step has a completion criterion.
- [ ] Exact commands, paths, formats, and non-obvious project facts are present; common knowledge the agent would get right is omitted.
- [ ] The output contract is explicit: format, required sections, and how to handle uncertainty.
- [ ] Gotchas and failure modes are named where they change behavior.
- [ ] Branch-specific detail is in `references/`, and each pointer says what the file contains and when to read it.
- [ ] Long references have a table of contents or another way to navigate.
- [ ] The skill expresses the pattern rather than one instance where it is meant to generalize.
- [ ] The skill's behavior stays within what its description promises and what the user authorized.
- [ ] The skill still describes one coherent unit of work.

## Severity

- **Error** — the skill is unusable or dangerous: instructions that cannot be followed as written, a description that sends the skill to a different job than the body performs, or behavior the user did not authorize.
- **Warning** — the skill is likely to under-trigger or under-deliver: a summary-style description, a trigger collision, a missing completion criterion or output contract, stale or contradictory guidance, a blind pointer, a body carrying detail a reference should hold, or a gotcha that will bite but is not mentioned.
- **Info** — a simplification, wording improvement, unnecessary frontmatter field, or optional restructuring.

## Report

Format each finding as:

```markdown
- **<severity>** `skills/<name>/<path>:<line>` — <problem>. <why it matters>. <proposed fix>.
```

Close with:

```markdown
## Skill audit
- Scope: `<all | skills/<name>>`
- Skills checked: `<n>`
- Findings: `<n>` error · `<n>` warning · `<n>` info
- Not verified: `<items and reasons>`
- Open questions: `<...>`
```
