---
name: audit-behavior-contract
description: Audit code against the behavior contracts in docs/behavior/ and report drift in either direction.
metadata:
  version: "1.0.0"
disable-model-invocation: true
---

# Audit Behavior Contract

Check the code against `docs/behavior/` and report divergence in both directions: pinned rules the code contradicts or lacks, and observable code behavior no contract pins. The audit is read-only; the contracts stay as written and the code stays as built. The user decides which side is wrong.

A divergence needs evidence at both ends: the contract side (a rule, or the searched tree that has none) and the code side (a live path, or the mapped entry points that have none). One end alone is a lead, not a finding.

## Instructions

### 1. Load the contracts

Read every file under `docs/behavior/**/*.md` in full, or only the contract or feature the user names. Use the project's domain glossary vocabulary.

Build a rule inventory: for each file and heading, list every pinned rule, its inputs, outputs, state transitions, error outcomes, and composition references. Mark open gaps as gaps; they are not pinned behavior. If `docs/behavior/` has no contracts, report that and suggest `/to-behavior-contract`; stop.

Done when every in-scope contract has a rule inventory and its open gaps are marked.

### 2. Map features to code

Map each contract feature to its entry points: routes, CLI commands, handlers, event consumers, exported APIs, and UI flows. Use the feature name, the domain terms in its rules, and its references. Record each entry point as `file:line`.

Treat tests, comments, docs, and type signatures as leads to the code, not as witnesses. When a feature maps nowhere, record it as `unmapped`; do not invent a path.

Done when every in-scope feature has at least one entry point or is recorded unmapped.

### 3. Witness every pinned rule

For each rule, trace each mapped entry point and find the live code that enforces it. Cover all six contract dimensions: inputs, rules and boundaries, states, outputs and effects, errors, and composition.

Give every rule one verdict:

- `match` — the code enforces the rule; cite the code.
- `contradiction` — the code does something else; cite the code and quote the alternative.
- `missing` — no enforcing path; name the entry points and paths searched.
- `unverifiable` — the rule depends on an unknown runtime value, an external service, or an unresolved reference; name what is missing.

A match at one entry point leaves the others open: check every mapped path. For a rule that composes with another feature, follow the reference to the owning contract and witness that behavior there.

Done when every pinned rule has one verdict and every `match` or `contradiction` has a code witness.

### 4. Sweep for unpinned behavior

From the mapped entry points, walk the observable branches: accepted inputs, defaults, feature flags, validation, returned values, records written, messages sent, state changes, and error outcomes. Record each behavior no pinned rule covers, and name the contracts and headings searched; an absent rule needs a search as much as an absent path does.

Observable means what a caller or user can see. Internal structure and performance are divergences only when the contract pins them. An open gap is already unspecified; note code that decides one separately, not as a divergence.

Done when every mapped entry point's observable branches are either pinned or reported unpinned.

### 5. Classify, dedupe, verify

Give each finding one category: `contradiction`, `missing`, `unpinned`, `unverifiable`, or `blocked reference`. Report `contradiction`, `missing`, and `unpinned` as divergences; report `unverifiable` and `blocked reference` separately with what is missing. Set confidence: high when the rule and path are exact, medium when the path is inferred, low when the behavior depends on configuration or an unavailable runtime.

Give each finding one owner: the contract and heading whose rule it breaks, or the feature whose behavior is unpinned. Deduplicate findings that cross contract files.

Re-open every cited code line and contract heading. Drop a finding whose witness no longer reads as reported.

Done when each divergence has evidence at both ends, each unverifiable or blocked finding names what would make it checkable, and every finding has one category, one owner, and a confidence.

### 6. Report

Write the report in the conversation. Put coverage first so the user can see what was and was not audited, then group divergences by contract. Report contradictions before missing behavior, then unpinned behavior.

```markdown
## Scope and coverage

- Contracts audited: <paths>
- Entry points mapped: <count>
- Unmapped features: <feature> — <what is missing>

## Divergences

### docs/behavior/<path>.md § <Heading>

- Rule: <the pinned behavior, quoted or closely paraphrased>
- Code: `path:line` — `<quoted code>`
- Kind: contradiction | missing | unpinned
- Confidence: high | medium | low
- Difference: <the contract end against the code end>
- Decision needed: <change the code | change the contract | accept it>

## Open gaps decided by code

<Any open contract gap that the code now answers, with the code witness.>

## Unverifiable or blocked

<What would make each one checkable.>
```

State the decision each divergence needs. Offer no edit to either side until the user chooses.

Done when every finding appears once, the counts reconcile with the coverage section, and every divergence names its decision.

## Guards

- Search before declaring absence. Name the entry points and paths; `not found` without a search is a guess.
- Check every entry point for a rule. One match does not clear the others.
- Follow configuration, feature flags, and defaults to the value the running system uses.
- Ignore dead code and generated output. A witness must be reachable from a mapped entry point.
- Keep implementation details out: module layout, function signatures, and performance are divergences only when the contract pins them.
- A contract rule with no code is `missing`; a code path with no rule is `unpinned`. Neither tells you which side is wrong.
