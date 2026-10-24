# Split AGENTS.md

Split when the root exceeds about 200 lines or 5,000 tokens, or when a section is reached by only some runs. A monorepo may prefer nested `AGENTS.md` files instead of a flat docs split.

## Keep in the root

- The project's one-line purpose and any cross-cutting map.
- Commands every run needs, including the verification gate.
- Scope, permissions, and completion conditions.
- The `## Agent skills` block.
- One pointer per split doc.

## Move to `docs/agents/<topic>.md`

- Detailed testing strategy and fixtures.
- Architecture, service boundaries, and data flow.
- Conventions that apply to one kind of work.
- Deployment, migration, and runbook steps.
- Gotchas and operational notes.
- Multi-step workflows that only some runs reach.

Name the file after its topic: `testing.md`, `architecture.md`, `deployment.md`, `gotchas.md`, `workflows.md`.

## Reserved names

`issue-tracker.md`, `triage-labels.md`, and `domain.md` belong to `setup-matt-pocock-skills`; leave them to that skill. Pick a distinct topic name when a split doc overlaps their subject.

## Write the pointer

The root keeps the trigger; the doc keeps the detail. Move the meaning, never copy it.

The split doc owns the detail. Never reduce an existing split doc to a pointer back at the root; if the root is the only place a detail lives, move it into the doc before pointing at it. A root pointer whose doc points back is a loop with no detail.

```markdown
## Testing

- Use `docs/agents/testing.md` when changing runtime behaviour. Done when the affected tests pass.
```

One pointer per doc. Front-load the leading word the agent will use. A blanket "read all docs" line spends context load on every run and defeats the split.

## Monorepos

A nested `AGENTS.md` in a package is the closest file to that package's code, so it takes precedence. Use it for package-specific commands, conventions, and gotchas. Keep the root for cross-cutting rules and a short map of the packages.

Use `docs/agents/` for cross-cutting detail that is too branch-specific for the root but not owned by a package.

## Before and after

Before:

```markdown
## Testing

Run `pnpm test` before committing. The API tests need Redis and use the
`test-api` fixture. Integration tests live in `tests/integration/` and take
about ten minutes. Use `pnpm test --filter api` for a focused run. After
changing a handler, also run `pnpm test:contract`. Do not run the full suite
on every edit.
```

After, in the root:

```markdown
## Testing

- Use `docs/agents/testing.md` when changing runtime behaviour. Done when the affected tests pass.
```

After, in `docs/agents/testing.md`:

```markdown
# Testing

- Run `pnpm test --filter <package>` for a focused run.
- Start Redis before the API tests; they use the `test-api` fixture.
- After changing a handler, run `pnpm test:contract`.
- Reserve `pnpm test` for the final check; the full suite takes about ten minutes.
```
