# Writing AGENTS.md

Source: [ASDLC AGENTS.md specification](https://asdlc.io/practices/agents-md-spec/), aligned with the open [AGENTS.md format](https://agents.md/).

`AGENTS.md` is the README for agents: the minimal, human-authored context that lets an agent work effectively in this repo. It complements the README; it does not repeat it. The default stance is "if a constraint can be expressed elsewhere, it must not live here."

## What earns a line

A line earns its place only when it changes behavior the model would otherwise get wrong. Budget every line as always-loaded context.

Include:

- Mission and core constraints the code cannot reveal.
- Non-standard commands with their trigger and the config or script that owns them.
- The check that closes the loop and what done means.
- Conventions that differ from language or tool defaults.
- Judgment boundaries: when to ask, what to always do, and hard limits.
- Architecture constraints, generated code, environment quirks, and gotchas.
- Repo etiquette not enforced by tooling.
- A skills roster: invocation names and definition paths.
- A context map only when the repo's structure is complex and non-obvious.
- Pointers to existing deeper docs, each with the condition for reading it.

Leave out:

- Facts already visible in code, config, scripts, or layout.
- Standard language conventions the model already follows.
- README or API documentation, tutorials, and file-by-file tours.
- Frequently changing facts such as versions, URLs, and team ownership.
- Self-evident advice such as "write clean code" or "be careful".
- A command's options, flags, and full output; name the command and trigger instead.
- A second copy of a meaning owned by a config, script, skill, or doc.
- Unverified output from `/init` or another generator.

## Shape

Use these sections only when they carry content. The template in `assets/AGENTS.md.template.md` is a starting point, not a required outline.

### Mission

Two to four sentences on what the project is and the constraints that change how an agent works. State the domain judgment the code cannot show.

### Toolchain

A table of intent, command, and authority. Include only commands an agent cannot infer from the environment.

| Intent | Command | Authority |
| --- | --- | --- |
| Build | `pnpm build` | `package.json` scripts |
| Test | `pnpm test --filter <package>` | Package scripts |
| Lint | `pnpm lint` | `biome.json` |

Do not describe what the tool enforces; the config is the authority. Include the order between commands when it matters.

### Judgment Boundaries

Use three groups:

- **Ask** — decisions that need a human, with the trigger for asking.
- **Always** — proactive behavior that closes the loop, with its completion condition.
- **Never** — hard limits only.

Phrase the positive target wherever possible. "Use `pnpm` for every package command" beats "never use npm". Keep a Never only when no positive form carries the same limit, and pair it with the behavior to use instead.

### Skills

Roster only: invocation name, one-line purpose or trigger, and the path to the definitions. Full procedures live in the skill files, not inline.

### Context Map

Optional. List only non-obvious packages, services, generated areas, or boundaries. Omit standard framework layout and file-by-file detail. A context map orients architecture; it is not a navigation shortcut.

## Root and nested files

- The root owns cross-cutting mission, repo-wide commands, verification, global boundaries, and the skills roster.
- A nested file owns package- or service-specific commands, conventions, and gotchas.
- The closest file to the edited code takes precedence. A nested rule may refine the root for its subtree; it must not contradict a root rule that still applies.
- Create nested files only at paths the user requested. A root create request produces the root only.
- Do not repeat root rules in a nested file. Keep one meaning in one home.

## Size and pointers

Keep the root to one screen, roughly 200 lines or 5,000 tokens. Split earlier when a section is reached by only some runs.

Put detail behind a pointer to an existing doc or an in-scope nested `AGENTS.md`. Each pointer names the leading word and the condition for reading it. Do not create a docs tree just to hold overflow.

Group related rules under one heading so reading one part brings its neighbours. Prefer concrete commands, paths, triggers, and completion conditions over adjectives.

## Final check

- Every line passes the include and exclude tests above.
- Every section has evidence-backed content; empty sections are gone.
- Every command, path, and pointer resolves.
- No meaning is repeated across root, nested files, or existing docs.
- Every rule names its scope; every work rule says what done means.
