# Write a skill

Ground the skill in domain expertise, not general knowledge. Generic procedure text produces vague instructions ("handle errors appropriately"); a real task captures the exact commands, conventions, and edge cases that make the skill useful.

## Ground it in real work

Extract the skill from one of two sources:

- **A completed hands-on task.** Extract the steps that worked, the corrections, the input and output formats, and the project context.
- **Existing project artifacts.** Mine runbooks, style guides, API specs, schemas, code review comments, issue history, and resolved failures for the specifics a generic reference lacks.

## Add only what the consuming agent lacks

Keep a line only when the consuming agent would get it wrong without it. Cut the rest.

- Skip explanations of common concepts (what a PDF is, how HTTP works); jump to the project-specific procedure, tool, or edge case.
- Keep the gotchas: environment facts that defy reasonable assumptions, naming mismatches, soft deletes, misleading health checks.
- If the agent handles the task well without the skill, add nothing.

## Make the description a trigger

The description is the only pointer the consuming agent sees before activation. State what the skill does, then the distinct cases that invoke it, front-loading the words the invoking prompt will use.

```yaml
description: Extracts text and tables from PDFs, fills forms, and merges PDFs. Use when handling PDF documents, forms, or text extraction.
```

Cut synonyms that rename one trigger, and cut details the body already establishes.

## Design the unit

Scope the skill like a function: one coherent unit of work that composes with others.

- **Too narrow:** one task forces several skills to load, adding overhead and conflicting instructions.
- **Too broad:** the skill becomes hard to trigger precisely.
- **Moderate detail:** prefer concise, stepwise guidance with one working example over an exhaustive manual.

## Spend context deliberately

- Keep the core instructions in `SKILL.md`; move detail into `references/` and state the condition for loading each file.
- Use `scripts/` when the agent would otherwise rebuild the same logic every run; use `assets/` for templates or data needed only in some cases.
- Use a short template instead of a prose description of an output format.

## Calibrate control

Match prescriptiveness to fragility:

- **Fragile, ordered, or consistency-critical work:** give the exact command or sequence, including flags.
- **Flexible work with several valid approaches:** state the goal and why it matters; let the agent choose.
- **Mixed skills:** calibrate each section independently.

Pick one default and name alternatives as escape hatches: "Use `pdfplumber` for text extraction. For scanned PDFs, use `pdf2image` with `pytesseract`."

Prefer a reusable procedure over a one-off answer: "Read the schema, join on `_id`, apply the user's filters, then aggregate numeric columns." A specific query works only for that instance; a procedure generalizes.

## Patterns worth reusing

- **Gotchas** — concrete corrections to mistakes the agent will make: soft-delete filters, ID field aliases, endpoints that report healthy while dependencies are down. Keep them in `SKILL.md` where they are read before the situation appears.
- **Output template** — show the required structure; agents match concrete patterns well.
- **Checklist** — track multi-step workflows with dependencies or validation gates.
- **Validation loop** — do the work, run a validator, fix failures, repeat until it passes.
- **Plan-validate-execute** — for batch or destructive work, write a structured plan, validate it against a source of truth, then execute.
- **Bundled script** — when traces show the agent reinventing the same helper each run, write and test it once in `scripts/`.

## Refine with execution

Treat the first draft as a hypothesis. Run the skill on real tasks and read execution traces, not just final outputs. Watch for three failure modes: vague instructions trigger trial and error, irrelevant instructions get followed anyway, and menus without defaults stall the agent. Move every correction into the skill, usually as a gotcha, and cut instructions that produce no useful work.

For the formal test loop, read [evaluation.md](evaluation.md).
