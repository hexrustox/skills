# Skill Authoring

A skill is a directory with a `SKILL.md` at its root. It gives an agent a reusable procedure, the project-specific facts that procedure depends on, and optionally scripts and references that load only when needed.

This guide covers writing a skill. Evaluation and benchmarking are out of scope.

## Before writing

Read any skill being changed end to end, including its references and scripts. For a new skill, confirm the name and location with the user if the repository does not make it obvious.

Done when you know the skill's directory, whether it is new or an update, and which files it must ship with.

## Capture intent

Start from what the user actually wants the agent to do. If they say "turn this into a skill", mine the conversation before asking questions: the tools used, the sequence that worked, the corrections the user made, input and output formats, and the project facts that made the task succeed.

Answer these before drafting:

- What should the agent be able to do that it cannot do reliably now?
- When should the skill trigger? Which user phrases, file types, or contexts should reach for it?
- What does a good output look like, and in what format?
- What does success look like when the task is done?
- Is this a new skill or a change to an existing one?

Read the artifacts the user points at. Do not ask for information already present in the conversation or the repository.

Done when you can state the skill's job and its trigger conditions in one sentence each.

## Interview the author

Ask only questions whose answers change the skill. Cover the gaps left by intent capture:

- **Triggers** — the phrases, adjacent tasks, and near-misses that should and should not invoke the skill.
- **Outputs** — the file, format, structure, and level of detail expected.
- **Terminology** — the terms, abbreviations, and output fields a fresh agent would not know.
- **Edge cases** — unusual inputs, missing data, partial failures, and constraints that regularly bite.
- **Examples** — a real input and the output a reviewer accepted.
- **Success criteria** — what a reviewer checks, and what makes an assertion objectively pass or fail.
- **Dependencies** — tools, packages, credentials, network access, runtime versions, and harness capabilities.
- **Evaluation** — whether the output is objectively verifiable or needs human judgment.

Propose sensible defaults and let the user correct them. Keep the interview short enough that it feels like progress, not intake paperwork.

Done when you can draft the description and a realistic test prompt without guessing.

## Draft the skill

### Name

Use a precise, lowercase kebab-case name that matches the directory. Keep it short enough to recognize and specific enough to distinguish it from neighboring skills. When updating an existing skill, keep its original name and directory; do not create a `-v2` variant.

### Description

Write the description for the invocation mode.

For a model-invocable skill, the description is the only text an agent sees before deciding to load the skill. Make it a trigger, not a summary.

- State what the skill does, then the distinct situations that should invoke it.
- Front-load the words the invoking prompt is likely to use.
- Include non-obvious triggers and the cases where this skill should win over a nearby one.
- Keep it concrete. "Use when handling PDF forms, scanned documents, or text extraction" beats "Useful for document tasks."

For a user-invoked skill (`disable-model-invocation: true`), the user chooses when to run it, so the description is a label, not a trigger. State what the skill does and the coverage or boundary of what it changes; omit "Use when" phrasing. The `setup-*` skills are the pattern.

Keep it within 1024 characters.

### Frontmatter

```yaml
---
name: example-skill
description: What it does and when to use it.
license: Apache-2.0
compatibility: Requires Python 3.11+ and network access.
---
```

Use `license` when the skill is distributed. Use `compatibility` for environment requirements only: runtime versions, system packages, network access, or required tooling. Add `metadata` or `allowed-tools` only when the skill genuinely needs them.

Set `disable-model-invocation: true` when the skill should run only on an explicit user request. It omits the skill from the model's available skills list, so the model will not discover or choose it on its own; the user can still invoke it directly. Use it for setup, migration, or other routines that should not start on the model's initiative, and rewrite the description as a label rather than a trigger.

### Body

Write the body as instructions for the agent that will use the skill, not as an essay about the topic.

- Use the imperative form: read this, run that, compare these.
- Explain why a step matters when the reason is not obvious; an agent that understands the goal handles unlisted cases better than one following unexplained rules.
- Include exact commands and project facts that defy reasonable assumptions.
- Give each step a completion criterion: what tells the agent the step is done.
- Keep harness-specific operations out of the core body. Put them in a reference when the skill ships across harnesses.

Skills must not surprise the user. Do not write instructions for malware, unauthorized access, data exfiltration, or misleading behavior.

### Progressive disclosure

Structure the skill so the agent reads only what the current task needs:

1. **Metadata** — name and description, loaded for every skill at startup.
2. **Instructions** — the `SKILL.md` body, loaded on activation. Keep it under about 500 lines.
3. **Resources** — `references/`, `scripts/`, `assets/`, and agent instructions under `agents/`, loaded only when needed.

Move branch-specific detail into `references/` and state the condition for reading each file next to the pointer. For files longer than about 300 lines, add a table of contents. Use `scripts/` for deterministic work the agent would otherwise rebuild each run, and `assets/` for templates, images, or data used in output. Put instructions for fresh-context runs under `agents/`. Reference files from `SKILL.md` with paths relative to the skill root.

## Writing patterns

Use these patterns when drafting or revising a skill body. The goal is instructions an agent can follow reliably without loading material it does not need.

### Calibrate control

Match prescriptiveness to fragility:

- **Fragile, ordered, consistency-critical work:** give the exact command or sequence, including flags. Examples: migrations, release steps, schema changes.
- **Flexible work with several valid approaches:** state the goal and why it matters, then let the agent choose. Examples: code review, research, writing a proposal.
- **Mixed skills:** calibrate each section independently and name the escape hatch. "Use `pdftotext` for text PDFs; for scanned pages use `pdftoppm` plus OCR."

A rule that exists only to satisfy one example is a smell. Explain the underlying constraint and let the agent apply it.

### Cut generic knowledge

Keep a line only when the agent would get it wrong without the skill.

- Skip definitions of common concepts. Jump to the project-specific procedure, tool, or edge case.
- Keep gotchas: naming mismatches, soft-delete filters, endpoints that report healthy while a dependency is down, fields that look interchangeable but are not.
- Remove duplicated explanation. State a rule once, in the place where the agent needs it.
- If the agent already handles the task well without the skill, add nothing.

### Define terms

When a skill introduces a term of art, abbreviation, or output field, define it at first use. If several terms need definitions, add a short `## Definitions` section or link a glossary. A skill must stand alone: the reader does not have the conversation that produced it.

### Prefer a procedure

A reusable procedure generalizes; a one-off answer does not.

```markdown
Bad: Run `SELECT * FROM orders WHERE customer_id = 42`.

Good: Read the schema, join on the customer's stable ID, apply the user's filters,
then aggregate the requested numeric columns.
```

Use a concrete example after the procedure, not instead of it.

### Output template

Show the required structure. Agents match concrete patterns better than prose descriptions of structure.

```markdown
## Review

**Verdict:** approve | request changes
**Risk:** low | medium | high

### Findings
- `<file>:<line>` — <problem>. <why it matters>. <suggested fix>.
```

Keep the template minimal. Every field should change the output; remove the rest.

### Worked example

Show one real input and the output a reviewer accepted. This is often the fastest way to communicate a format that is hard to describe.

```markdown
**Input:** Added retry handling to the upload client.

**Output:** `feat(upload): retry transient failures with backoff`
```

If the skill produces files, include a small fixture and the expected shape rather than a screenshot alone.

### Checklist

Use a checklist when the order is flexible but completeness matters. Checklist items are completion criteria, not reminders.

```markdown
- [ ] Every changed schema has a migration.
- [ ] Every migration has a rollback path.
- [ ] The API contract and the generated client agree.
```

Do not turn a checklist into a second copy of the procedure.

### Validation loop

For work that can be checked mechanically, make the loop explicit:

1. Do the work.
2. Run the validator or tests.
3. Read the failure.
4. Fix the cause, not the assertion.
5. Repeat until the check passes.

State the exact command and what a pass looks like. If the validator is noisy, say which warnings matter.

### Plan, validate, execute

For batch or destructive work, separate planning from execution:

1. Write a structured plan: the targets, the intended change, and the expected result.
2. Validate the plan against a source of truth: the schema, the inventory, the API response, or the user.
3. Execute only after validation passes.
4. Report skipped targets and reasons.

This prevents an agent from applying a plausible but wrong transformation across many files.

### Bundled script

When transcripts show the agent writing the same helper on every run, write and test it once under `scripts/`.

- Make the script self-contained or document its dependencies.
- Give it a clear CLI, useful errors, and a dry-run path when it mutates data.
- Tell the skill when to run it and what output to expect.
- Keep the script deterministic; leave judgment calls to the agent.

Scripts execute without being loaded into context, so they are cheaper than long instructions for repetitive work.

### Gotchas

Document the corrections an agent is likely to make incorrectly:

- The field called `id` is not the customer ID.
- Deleted records are filtered by `archived_at`, not by a status column.
- The health endpoint returns 200 while the queue is down.
- The staging API accepts a different enum than production.

Put gotchas where they are read before the mistake happens, usually next to the step they affect.

## Update an existing skill

When the user is improving a skill rather than creating one:

1. Keep the original name, directory, and frontmatter name. Do not rename the skill to signal a version.
2. Read the whole skill, including references and scripts, before changing one part.
3. Make the smallest coherent change that addresses the feedback.
4. Update the description if the skill's scope, triggers, or invocation mode changed.
5. Remove dead pointers and keep references, scripts, and frontmatter consistent.

Done when the skill still describes one coherent unit of work and every pointer resolves.

## Common mistakes

- **Description says what but not when.** For a model-invocable skill, add the concrete triggers; for a user-invoked skill, keep it a label that states coverage and boundaries.
- **Body repeats general knowledge.** Cut it and keep the project-specific detail.
- **Harness commands leak into the core.** Move harness-specific operations into a reference.
- **Pointers have no loading condition.** Say when to read the reference.
- **The skill is overfit to one example.** Express the pattern, not the instance.
- **The body is too long.** Move branch-specific material into references.
- **The update renamed the skill.** Preserve the name and directory.
- **Undefined term.** A term of art, abbreviation, or output field is used without a definition. Define it at first use or link one.
