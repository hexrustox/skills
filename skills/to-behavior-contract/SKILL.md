---
name: to-behavior-contract
description: "Synthesize the current conversation and codebase into behavior-contract docs under `docs/behavior/`."
metadata:
  version: "1.2.4"
disable-model-invocation: true
---

# To Behavior Contract

Turn the current conversation and codebase into behavior contracts under `docs/behavior/`. It asks two questions before writing: first the proposed file set and its division of behavior, then any behavior the conversation leaves unspecified.

## Instructions

### 1. Read the repo first

Explore the code paths the conversation touches and read every existing file under `docs/behavior/**/*.md` in full. Use the project's domain glossary vocabulary throughout, and respect any ADRs in the area you are touching.

Done when the current behavior, the existing contracts, and the settled terms are in context.

### 2. Fix the file set

Write one kebab-case file per feature at `docs/behavior/<feature-name>.md`; nested directories may group related features. A feature is a user-visible capability, not a module or a channel. Derive each name from the project's domain vocabulary. A feature that already has a file gets that file updated, never duplicated.

Assign each fact to the contract that already defines it; a new file owns new behavior and references the existing facts it consumes. Propose the file set and which behavior each file owns. Ask whether this division matches the user's expectations, and wait.

Done when the user confirms the file set and its division.

### 3. Surface gaps

Collect every in-scope behavior the conversation, code, and existing contracts leave unspecified: the boundary nobody decided, the error with no outcome, the retry with no clock. A gap is a dimension no settled decision fixes. A gap is not a conflict, and it is not yours to invent.

Propose the gaps and ask how each should resolve, including which may stay open. Wait.

Done when the user resolves each gap or accepts that it stays open.

### 4. Write the contract

Write from the confirmed division and answers. Pin only behavior settled by the conversation, the code, or the user's answer.

Source audit: as you draft, name each rule's source — conversation, code, or the user's answer. Delete every rule with no source. A rule that answers an open gap is an invention, even when the answer seems obvious. Keep the audit as working notes, not in the contract.

Before the close-out, re-read each open gap against the draft and delete every rule that states an answer to it. A schedule or table that assumes an answer counts as a rule.

Pin exact behavior at its layer: inputs, outputs, user-visible effects, edge cases, exact rules, state machines, error taxonomy, and how behaviors compose. Describe what the code does, or will do if not yet implemented, without recording implementation status.

Stay silent on why: that belongs to the ADR, which the contract references.

Stay silent on implementation structure — module layout, function signatures, file names, and performance choices — unless they are hard requirements.

Depth test: a good contract lets two engineers build the same program independently without coordinating. Reach for pseudocode, state tables, and schemas whenever they pin behavior more precisely than prose.

Use the skeleton in `references/contract-template.md` when `docs/behavior/` has no established shape; follow the existing contracts' shape when it does.

Done when every in-scope behavior is pinned or recorded as an open gap, every pinned rule names a source, no pinned rule resolves an open gap, and there is no implementation status or rationale.

### 5. Single source of truth

Ownership audit: for each rule, name its owning file and heading. If the owner is another contract, replace the rule with a reference. State this file's positive rule; when another contract owns an excluded case, the reference carries it, so leave the exclusion unnamed.

Among docs, `docs/behavior/` is the source of truth for how the solution behaves. Contracts never duplicate each other or the ADRs. Shared behavior lives in one file; everywhere else references it.

Use these reference shapes:

- `docs/behavior/<path>.md § <Heading>` for another contract.
- `§ <Heading>` for a heading in the current file.
- `docs/behavior/` for the tree as a whole.
- `docs/adr/<file>.md` for the reasoning behind a rule.

Reference, never restate: another contract for behavior, an ADR for reasoning. Name the heading in every cross-file reference to a behavior file.

Reference audit: before the close-out, list every cross-file behavior reference and confirm it names a heading; a bare path is not a reference. Done when each meaning appears once, every rule sits with its owner, every cross-file behavior is a reference, and every reference names its heading.

### 6. Stop on conflict

If two existing contracts disagree on the same behavior, or the code contradicts a contract, stop and raise the conflict to the user before writing. The user decides which side is wrong.

A behavior the contracts are silent on is a gap, owned by step 3, not a conflict. Done when no unresolved conflict remains.

### 7. Done

Every in-scope behavior is pinned or recorded as an open gap, every pinned rule names a source, each rule has one owner, every reference names its heading and resolves, and the close-out summary lists the files written or updated, the gaps left open, and any conflicts raised.
