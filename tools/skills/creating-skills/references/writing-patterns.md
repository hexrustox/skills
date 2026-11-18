# Writing patterns

Use these patterns when drafting or revising a skill body. The goal is instructions an agent can follow reliably without loading material it does not need.

## Calibrate control

Match prescriptiveness to fragility:

- **Fragile, ordered, consistency-critical work:** give the exact command or sequence, including flags. Examples: migrations, release steps, schema changes.
- **Flexible work with several valid approaches:** state the goal and why it matters, then let the agent choose. Examples: code review, research, writing a proposal.
- **Mixed skills:** calibrate each section independently and name the escape hatch. "Use `pdftotext` for text PDFs; for scanned pages use `pdftoppm` plus OCR."

A rule that exists only to satisfy one example is a smell. Explain the underlying constraint and let the agent apply it.

## Cut generic knowledge

Keep a line only when the agent would get it wrong without the skill.

- Skip definitions of common concepts. Jump to the project-specific procedure, tool, or edge case.
- Keep gotchas: naming mismatches, soft-delete filters, endpoints that report healthy while a dependency is down, fields that look interchangeable but are not.
- Remove duplicated explanation. State a rule once, in the place where the agent needs it.
- If the agent already handles the task well without the skill, add nothing.

## Prefer a procedure

A reusable procedure generalizes; a one-off answer does not.

```markdown
Bad: Run `SELECT * FROM orders WHERE customer_id = 42`.

Good: Read the schema, join on the customer's stable ID, apply the user's filters,
then aggregate the requested numeric columns.
```

Use a concrete example after the procedure, not instead of it.

## Output template

Show the required structure. Agents match concrete patterns better than prose descriptions of structure.

```markdown
## Review

**Verdict:** approve | request changes
**Risk:** low | medium | high

### Findings
- `<file>:<line>` — <problem>. <why it matters>. <suggested fix>.
```

Keep the template minimal. Every field should change the output; remove the rest.

## Worked example

Show one real input and the output a reviewer accepted. This is often the fastest way to communicate a format that is hard to describe.

```markdown
**Input:** Added retry handling to the upload client.

**Output:** `feat(upload): retry transient failures with backoff`
```

If the skill produces files, include a small fixture and the expected shape rather than a screenshot alone.

## Checklist

Use a checklist when the order is flexible but completeness matters. Checklist items are completion criteria, not reminders.

```markdown
- [ ] Every changed schema has a migration.
- [ ] Every migration has a rollback path.
- [ ] The API contract and the generated client agree.
```

Do not turn a checklist into a second copy of the procedure.

## Validation loop

For work that can be checked mechanically, make the loop explicit:

1. Do the work.
2. Run the validator or tests.
3. Read the failure.
4. Fix the cause, not the assertion.
5. Repeat until the check passes.

State the exact command and what a pass looks like. If the validator is noisy, say which warnings matter.

## Plan, validate, execute

For batch or destructive work, separate planning from execution:

1. Write a structured plan: the targets, the intended change, and the expected result.
2. Validate the plan against a source of truth: the schema, the inventory, the API response, or the user.
3. Execute only after validation passes.
4. Report skipped targets and reasons.

This prevents an agent from applying a plausible but wrong transformation across many files.

## Bundled script

When transcripts show the agent writing the same helper on every run, write and test it once under `scripts/`.

- Make the script self-contained or document its dependencies.
- Give it a clear CLI, useful errors, and a dry-run path when it mutates data.
- Tell the skill when to run it and what output to expect.
- Keep the script deterministic; leave judgment calls to the agent.

Scripts execute without being loaded into context, so they are cheaper than long instructions for repetitive work.

## Gotchas

Document the corrections an agent is likely to make incorrectly:

- The field called `id` is not the customer ID.
- Deleted records are filtered by `archived_at`, not by a status column.
- The health endpoint returns 200 while the queue is down.
- The staging API accepts a different enum than production.

Put gotchas where they are read before the mistake happens, usually next to the step they affect.

## Common mistakes

- **Description says what but not when.** Add the concrete triggers.
- **Body repeats general knowledge.** Cut it and keep the project-specific detail.
- **Harness commands leak into the core.** Move them behind the adapter.
- **Pointers have no loading condition.** Say when to read the reference.
- **The skill is overfit to one example.** Express the pattern, not the instance.
- **The body is too long.** Move branch-specific material into references.
- **The update renamed the skill.** Preserve the name and directory.
