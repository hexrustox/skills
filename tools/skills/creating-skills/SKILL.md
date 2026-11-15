---
name: creating-skills
description: Creates, edits, evaluates, benchmarks, and tunes the description of agent skills. Use when the user wants to create a skill from scratch or from a conversation, turn a workflow or completed task into a skill, improve or review an existing skill, write or critique a SKILL.md, set up skill evals or benchmarks, compare with-skill and baseline runs, or optimize a skill description for better triggering.
license: Apache-2.0
compatibility: Requires Python 3.11+ and a harness adapter for eval, grading, comparison, analysis, benchmark, and description-tuning workflows.
---

# Creating Skills

A skill is a directory with a `SKILL.md` at its root. It gives an agent a reusable procedure, the project-specific facts that procedure depends on, and optionally scripts and references that load only when needed.

This skill covers the authoring and improvement loop. It is harness-neutral: starting fresh agents, loading a skill into a scope, and reading a harness's transcripts are adapter responsibilities.

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
- **Evaluation** — whether the output is objectively verifiable or needs human judgment, and whether the user wants a with-skill/baseline comparison.

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
name: creating-skills
description: What it does and when to use it.
license: Apache-2.0
compatibility: Requires Python 3.11+ and a harness adapter.
---
```

Use `license` when the skill is distributed. Use `compatibility` for environment requirements only: runtime versions, system packages, network access, or required harness capabilities. Add `metadata` or `allowed-tools` only when the skill genuinely needs them.

### Body

Write the body as instructions for the agent that will use the skill, not as an essay about the topic.

- Use the imperative form: read this, run that, compare these.
- Explain why a step matters when the reason is not obvious; an agent that understands the goal handles unlisted cases better than one following unexplained rules.
- Prefer a short procedure with one worked example over an exhaustive manual.
- Include gotchas, exact commands, naming mismatches, and project facts that defy reasonable assumptions.
- Cut explanations of common concepts and anything the agent would get right without the skill.
- Give each step a completion criterion: what tells the agent the step is done.
- Keep harness-specific operations out of the core body. The adapter owns them.

Skills must not surprise the user. Do not write instructions for malware, unauthorized access, data exfiltration, or misleading behavior.

### Progressive disclosure

Structure the skill so the agent reads only what the current task needs:

1. **Metadata** — name and description, loaded for every skill at startup.
2. **Instructions** — the `SKILL.md` body, loaded on activation. Keep it under about 500 lines.
3. **Resources** — `references/`, `scripts/`, `assets/`, and agent instructions under `agents/`, loaded only when needed.

Move branch-specific detail into `references/` and state the condition for reading each file next to the pointer. For files longer than about 300 lines, add a table of contents. Use `scripts/` for deterministic work the agent would otherwise rebuild each run, and `assets/` for templates, images, or data used in output. The `agents/` directory holds instructions to pass to fresh-context runs; read the relevant file when grading, comparing, or analyzing. Reference files from `SKILL.md` with paths relative to the skill root.

## Use writing patterns

Read [the writing patterns](references/writing-patterns.md) when drafting or revising the body. It covers output templates, worked examples, checklists, validation loops, plan-validate-execute, bundled scripts, gotchas, and how much prescriptiveness to use.

## Update an existing skill

When the user is improving a skill rather than creating one:

1. Snapshot the current skill before editing it if evals will compare against the old version. Put it at `<skill-name>-workspace/skill-snapshot/` and pass it with `--baseline-skill`.
2. Keep the original name, directory, and frontmatter name. Do not rename the skill to signal a version.
3. Read the whole skill, including references and scripts, before changing one part.
4. Make the smallest coherent change that addresses the feedback.
5. Update the description if the skill's scope or triggers changed.
6. Remove dead pointers and keep references, scripts, and frontmatter consistent.

Done when the skill still describes one coherent unit of work and every pointer resolves.

## Test, review, and improve

Before eval, grading, comparison, or analysis work, read the [harness adapter index](references/harnesses/README.md). When writing or checking the resulting JSON, follow [the JSON contracts](references/schemas.md).

The loop is: draft, run realistic cases with and without the skill, review the outputs, improve the skill, and repeat.

1. **Write 2–3 realistic test prompts.** Use something a real user would type, including input files and the expected output. Save them with the skill, for example under `evals/`.
2. **Run with-skill and baseline arms in fresh contexts.** Run the batch command in [the eval workspace reference](references/evals.md); it launches every case's with-skill and baseline arms together. For a new skill the baseline has no skill; for an existing skill pass a snapshot of the previous version taken before edits. Both baseline scopes should deny other skills so ambient skills do not contaminate the result.
3. **Capture the evidence.** Save outputs, transcripts, timing, and token totals under the canonical workspace. The default workspace is `<skill-name>-workspace/` beside the skill directory, organized as `iteration-<N>/eval-<ID>/<arm>/`. The batch writes the layout, metadata, inputs, outputs, transcripts, timing, and normalized run metadata, then prints the iteration directory.
4. **Draft assertions while runs are in progress.** The batch writes `eval_metadata.json` with empty expectations before launching any run. While the arms execute, edit `expectations` in each `<iteration>/eval-<ID>/eval_metadata.json`; existing metadata is never overwritten. Make them objectively verifiable and name them so a reviewer understands what passed. Subjective qualities such as writing style belong in human review, not forced assertions.
5. **Grade in a fresh context.** Start a fresh-context run with [the grader instructions](agents/grader.md), the eval prompt and expectations from `eval_metadata.json`, the arm's `transcript.md`, and its `outputs/`. Write the result to `<arm>/grading.json` with `expectations` entries using `text`, `passed`, and `evidence`. Prefer a script for anything that can be checked programmatically. The grader copies derived execution metrics from `outputs/metrics.json`, copies timing from `timing.json`, and summarizes any optional `outputs/user_notes.md`. Read its optional `eval_feedback` and fix assertions that would pass for a wrong output before the next iteration.
6. **Show the review before judging it yourself.** Generate the review page from the iteration's normalized run data, give the reviewer its path, and wait for the returned JSON, pasted into the conversation or saved as `<iteration>/feedback.json`. Use [the review instructions](references/evals.md#review-the-runs) for the command, previous-iteration matching, and how to read the feedback. Do not judge the outputs yourself first.
7. **Improve from the feedback and repeat.** Use a new iteration directory and keep the previous run identity stable so feedback and outputs can be matched across iterations.

### Generalize from feedback

The test cases are a small sample of how the skill will be used. Improve the skill, not the sample.

- **Generalize.** If a change only fixes the exact test prompt, it is probably overfit. Look for the underlying pattern and express that.
- **Keep the prompt lean.** Read the transcripts, not just the final outputs. Remove instructions that make the agent waste time or that no longer pull their weight.
- **Explain the why.** Prefer reasoning over all-caps commands and rigid structures. If you cannot explain why a rule exists, question the rule.
- **Look for repeated work.** If every run reinvents the same helper script, bundle it once under `scripts/` and tell the skill to use it.
- **Check the description too.** If the skill works once loaded but does not trigger, revise the description rather than adding more body text.

Stop when the user is satisfied, the feedback is empty, or another iteration is not making meaningful progress.

## Blind comparison

Use a blind comparison when close versions need a more rigorous judgment than the review page provides. It is optional and requires fresh-context runs. Read [the eval workspace reference](references/evals.md#compare-two-outputs-blindly) for the procedure, then use [the comparator instructions](agents/comparator.md) and [the analyzer instructions](agents/analyzer.md). A tie ends the comparison; there is no winner for the analyzer to explain.

Most comparisons do not need this step. The human review loop is usually enough.
