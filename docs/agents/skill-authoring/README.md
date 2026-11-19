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

The description is the only text an agent sees before deciding to load the skill. Make it a trigger, not a summary.

- State what the skill does, then the distinct situations that should invoke it.
- Front-load the words the invoking prompt is likely to use.
- Include non-obvious triggers and the cases where this skill should win over a nearby one.
- Keep it concrete. "Use when handling PDF forms, scanned documents, or text extraction" beats "Useful for document tasks."
- Keep it within 1024 characters.

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

### Body

Write the body as instructions for the agent that will use the skill, not as an essay about the topic.

- Use the imperative form: read this, run that, compare these.
- Explain why a step matters when the reason is not obvious; an agent that understands the goal handles unlisted cases better than one following unexplained rules.
- Prefer a short procedure with one worked example over an exhaustive manual.
- Include gotchas, exact commands, naming mismatches, and project facts that defy reasonable assumptions.
- Cut explanations of common concepts and anything the agent would get right without the skill.
- Give each step a completion criterion: what tells the agent the step is done.
- Keep harness-specific operations out of the core body. Put them in a reference when the skill ships across harnesses.

Skills must not surprise the user. Do not write instructions for malware, unauthorized access, data exfiltration, or misleading behavior.

### Progressive disclosure

Structure the skill so the agent reads only what the current task needs:

1. **Metadata** — name and description, loaded for every skill at startup.
2. **Instructions** — the `SKILL.md` body, loaded on activation. Keep it under about 500 lines.
3. **Resources** — `references/`, `scripts/`, `assets/`, and agent instructions under `agents/`, loaded only when needed.

Move branch-specific detail into `references/` and state the condition for reading each file next to the pointer. For files longer than about 300 lines, add a table of contents. Use `scripts/` for deterministic work the agent would otherwise rebuild each run, and `assets/` for templates, images, or data used in output. Put instructions for fresh-context runs under `agents/`. Reference files from `SKILL.md` with paths relative to the skill root.

## Use writing patterns

Read [the writing patterns](writing-patterns.md) when drafting or revising the body. It covers output templates, worked examples, checklists, validation loops, plan-validate-execute, bundled scripts, gotchas, and how much prescriptiveness to use.

## Update an existing skill

When the user is improving a skill rather than creating one:

1. Keep the original name, directory, and frontmatter name. Do not rename the skill to signal a version.
2. Read the whole skill, including references and scripts, before changing one part.
3. Make the smallest coherent change that addresses the feedback.
4. Update the description if the skill's scope or triggers changed.
5. Remove dead pointers and keep references, scripts, and frontmatter consistent.

Done when the skill still describes one coherent unit of work and every pointer resolves.
