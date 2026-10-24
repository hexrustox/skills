# What belongs in AGENTS.md

`AGENTS.md` is the README for agents: the one file loaded every run. Every line spends context load on every turn, so a line earns its place only by changing behaviour the model would otherwise get wrong.

## Include

| Rule | Example |
| --- | --- |
| Commands the agent cannot guess, with order and focused verification | `pnpm test --filter <package>`; `just check` before `just test` |
| The check that closes the loop, and what done means | `Run the affected tests and fix failures from this change. Done when they pass.` |
| Conventions that differ from language or tool defaults | `Use tabs; the formatter enforces it` is derivable, `Public errors use thiserror` is not |
| Non-obvious architecture and repo structure | Service boundaries, generated code, a `home/` mirror, a vendored fork |
| Repo etiquette | Branch naming, commit format, PR conventions, review expectations |
| Environment quirks | Required variables, local services, sandbox limits, platform gotchas |
| Gotchas | Soft deletes, misleading health checks, ID aliases, retries that duplicate writes |
| Permissions plus completion | Which workflows may continue without stopping, and the condition that ends the work |
| Pointers to deeper docs | `Use docs/agents/testing.md when changing runtime behaviour.` |
| The setup-owned block | `## Agent skills`, written and audited by `setup-matt-pocock-skills` |

## Exclude

- Facts already derivable from code, config, scripts, or directory layout.
- Standard language conventions the model already follows.
- API documentation and tutorials; link to the source instead.
- Frequently changing facts such as versions, URLs, or team ownership.
- File-by-file descriptions of the codebase.
- Self-evident practices: "write clean code", "run the tests", "be careful", "never commit secrets".
- A command's options, modes, and flags; the root names the command and its trigger, the split doc holds its variations.
- A second copy of a meaning that already lives in a config, a script, or a split doc.

## Test each line

Ask in order:

1. **Would removing this cause the agent to make a mistake?** If no, cut it.
2. **Does the environment already own this fact?** If yes, leave it there.
3. **Does this line beat the model default?** If no, cut the whole sentence rather than trim words.
4. **Is this needed by every run?** If no, move it behind a pointer or into a nested `AGENTS.md`.

The strongest rules are concrete and checkable: a command, a path, a trigger, a completion condition. Vague guidance costs the same context load and changes less.

## Size and structure

- Target under 200 lines and about 5,000 tokens for the root file.
- Keep one meaning in one place. Duplication inflates a rule's prominence and rots in two places.
- Group related rules under one heading so reading one part brings its neighbours.
- Front-load each pointer with the leading word the agent will recognise.
- Split earlier when a section is branch-specific, even if the file is under budget.

## Shape

Use the root for what every run needs:

```markdown
## Commands

- `pnpm test --filter <package>` — run the affected package's tests.

## Scope

- Operate inside this repo. Run local tests and format changed files without stopping.
  Done when the affected tests and formatter pass.

## Testing

- Use `docs/agents/testing.md` when changing runtime behaviour.
```

## Sources

- [AGENTS.md](https://agents.md/): the open format, nearest-file precedence, and examples.
- [AGENTS.md README](https://github.com/openai/agents.md): the minimal sample and repository layout.
- [Claude Code memory](https://code.claude.com/docs/en/memory.md): the include/exclude table, size target, and loading behaviour.
- [Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices): keep the file short and give the agent a verification check.
- [OpenCode rules](https://opencode.ai/docs/rules/): `/init` focus areas and external-file loading.
