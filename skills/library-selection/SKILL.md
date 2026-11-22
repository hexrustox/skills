---
name: library-selection
description: Select the best library, package, or dependency for a task by turning requirements into hard gates and weighted criteria, researching candidates against primary sources, checking supply-chain and maintenance risk, and recommending with evidence. Use when asked which library/package/dependency to use, to compare options, to evaluate whether a package is safe, healthy, or worth adopting, or to find an alternative to an existing library. Research only; does not install, execute, or benchmark code.
compatibility: Requires network access for registry, repository, advisory, and documentation lookups.
---

# Library Selection

Best is contextual: the candidate that clears every hard constraint and has the best risk-adjusted fit and total cost of ownership for this task, this codebase, and this team — not the most popular, newest, or most-starred.

Scale the evidence depth to the decision: the minimum gates plus at least a docs and maintenance check for a throwaway script; the full evidence pass and sensitivity check for a one-way-door production choice. Keep gates, weighted tradeoffs, and confidence separate. This skill stops at the recommendation; wiring the chosen library into the codebase is a separate task.

## Route the request

| Request | Mode | Recommendation shape |
| --- | --- | --- |
| "Which library should I use for X?" | Select | best candidate |
| "Compare A vs B" | Compare | best of the named options |
| "Is X safe, healthy, or worth adopting?" | Evaluate | adopt, avoid, or adopt with mitigations |
| "Find an alternative to X" | Replace | replacement, or keep the incumbent |

All modes use the same gates and scorecard. They differ in the candidate set and the baseline: Compare starts with the named options; Evaluate starts with one candidate and treats the status quo as the baseline; Replace starts with the incumbent and the reason for leaving it.

Done when you know the mode, the starting candidate set, and the recommendation shape.

## 1. Frame the decision

Inspect the repo when one is available: language and runtime, package manager, existing dependencies, license, CI, and conventions.

Capture:

- **Task** — what the library must do, including the specific use case, not just the category.
- **Must-haves** — capabilities, platform/runtime versions, performance envelope, security or compliance requirements, license policy.
- **Nice-to-haves** — convenience, ecosystem fit, tooling.
- **Non-goals** — what you are deliberately not optimizing for.
- **Criticality** — throwaway, internal tool, production dependency, or security-sensitive.
- **Reversibility** — two-way door (cheap to swap) or one-way door (public API, data format, deep integration).

Infer from the repo first; ask only when a missing fact could change the winner — typically license policy, deployment target, or acceptable risk. Then infer the gates and weights from this context.

Done when you can state the task, applied gates, weights, and rigor level in one short paragraph.

## 2. Generate candidates

Include:

- The incumbent, if one exists.
- Any existing dependency that already covers the task.
- The standard library, platform feature, or a small build-your-own option.
- At least two external candidates when the ecosystem has them.

Find candidates through registry search, framework and platform docs, ecosystem indexes, dependency graphs, issue threads, and migration guides. Use awesome lists, blog posts, and AI summaries as leads; confirm every candidate and claim in a primary source.

Verify package identity before researching: exact name on the expected registry, publisher, source repository, and whether the package and repository actually point at each other. Confirm the publisher and repo, not just the name.

Done when you have three to five candidates, or fewer with a stated reason. Every external candidate has a registry URL and a source repository URL; the baseline and any internal incumbent have a docs URL or a one-line definition.

## 3. Gather evidence

Gather evidence for every applied gate and every weighted axis. The table below maps each research area to what it decides.

| Area | Feeds | What to check |
| --- | --- | --- |
| Identity and provenance | Identity gate; security/supply-chain axis | Exact package, publisher, repo match, release signatures or attestations, recent ownership changes, maintainer account security where visible. |
| License | License gate | Declared license, transitive licenses, compatibility with distribution and org policy. |
| Capability and API | Capability gate; task-fit axis | Every must-have; API shape, escape hatches, type safety, composability; task-specific examples. |
| Supply-chain red flags | Supply-chain gate; security/supply-chain axis | Malware advisories, obfuscated code, install scripts, unexpected network or credential access, typosquat risk, unusual transitive dependencies. |
| Security advisories | Security gate; security/supply-chain axis | Known advisories, severity and relevance, disclosure policy, time to patch, dependency freshness. |
| Maintenance and governance | Viability gate; maintenance axis | Release cadence, changelog, issue/PR triage, contributor concentration, funding/governance, deprecation policy, archived status. |
| Correctness and reliability | Correctness axis | Tests and conformance, error handling, API stability, bug history. |
| Documentation and DX | Documentation axis | Quickstart, API reference, task-specific examples, migration guide, types/stubs, clear errors, troubleshooting, versioned docs. |
| Compatibility | Platform gate; compatibility/ecosystem axis | Required runtime, OS/arch, and version range; peer dependencies, module formats, integration points. |
| Performance | Performance axis | Independent benchmarks or documented complexity; project-run benchmarks are claims, not proof. |
| Adoption | Viability gate; compatibility/ecosystem axis | Production users, dependents, community support, support channels. Treat downloads and stars as weak signals. |
| Cost and reversibility | Cost/reversibility axis | Integration effort, upgrade burden, exit cost, data-format lock-in, support cost. |

Cite a primary source URL and access date for every material claim, including versions, release dates, download counts, and advisory IDs. Mark anything you could not verify as `unknown`. If a source is unreachable, state the gap and lower confidence; do not fill it from memory.

Treat documented behavior as a claim; runtime behavior is unverified until tested. Read source and docs; do not install, execute, or benchmark code. A quickstart, benchmark, or spike is a separate task.

Done when every applied gate and every weighted axis has cited evidence or `unknown`, and every runtime-only claim is on the unverified list.

## 4. Gate and compare

Eliminate candidates that fail a gate. Give the reason and the evidence; do not score them further. If no external candidate passes, recommend the baseline or a change to the constraints.

Score the survivors with the rubric at the end of this skill. Use `strong`, `adequate`, `weak`, or `unknown`. Unknown is not average; it lowers confidence.

Run a sensitivity check:

- Would the winner change if security, maintenance, compatibility, cost, performance/footprint, or team familiarity were weighted higher?
- Would the winner change if the `unknown`s resolved against it?

If either changes the winner, name the tradeoff and the condition under which the alternative wins.

Done when you have a primary recommendation, a runner-up or a reason none exists, and a clear condition under which the alternative wins. In Evaluate, the recommendation is adopt, avoid, or adopt with mitigations, with the condition that would flip it.

## 5. Recommend

Answer inline unless the user asks for a file. Show at most three candidates in the scorecard. List gate failures under Eliminated, and mention any other omitted candidate with a one-line reason.

Use this template:

```markdown
## Library choice: <task>

**Mode:** Select | Compare | Evaluate | Replace
**Recommendation:** <candidate or decision> — confidence: high | medium | low
**Runner-up:** `<name>` — choose it if <condition>; or `none` — <reason>.
**Baseline:** <standard library | build-your-own | incumbent> — rejected because <reason>; or recommended because <reason>.

### How I defined "best"
- Task / criticality / reversibility / non-goals: <...>
- Gates applied: <subset for this criticality>
- Weights: <axis n, axis n, ...; sum 100>

### Scorecard
Ratings: `strong` | `adequate` | `weak` | `unknown`. Add one row per scored axis. The scorecard holds judgments; cite the facts behind them in Why, Eliminated, and Sources.

| Axis (weight) | <name> | <name> | <name> |
| --- | --- | --- | --- |
| <axis> (<n>) | <rating> | <rating> | <rating> |

### Why
- <evidence-backed reason> [1]

### Eliminated
- `<name>` — <gate failure or reason for omission>: <evidence> [2]
- none — <reason>

### Risks and mitigations
- <risk> → <mitigation>

### Not verified
- <gate fact, runtime behavior, benchmark, or quickstart that research could not confirm> — would be settled by <test, benchmark, or source>

### Revisit when
- <new major version, security advisory, maintainer change, scale change>

### Sources
1. <URL> (accessed <date>)
```

Fill every section; write `none` or `unknown` where empty. Choose one alternative in the Runner-up, Baseline, and Eliminated lines. In Select and Compare, name the candidate; in Replace, name the replacement or keep the incumbent; in Evaluate, use adopt, avoid, or adopt with mitigations.

Set confidence deliberately:

- **High** — every applied gate has cited evidence, the key axes are strong, and the winner survives reweighting and the unknowns.
- **Medium** — some unknowns remain, there are no material red flags, and the unknowns do not change the winner.
- **Low** — a key gate or a high-weight axis is unverified, or the top two candidates are close enough that runtime behavior decides. Name the spike or prototype that would settle it.

Done when every box is checked:

- [ ] Every applied gate and every weighted axis has cited evidence or `unknown`.
- [ ] No candidate that failed a gate appears in the scorecard; every elimination cites evidence.
- [ ] Every material claim has a source URL and access date.
- [ ] Every unverified claim is under Not verified and reflected in confidence.
- [ ] Every template section is present, with `none` or `unknown` where empty.

Fix the cause of any unchecked box and re-check.

## Rubric

### Gates

| Gate | Pass condition |
| --- | --- |
| Identity | Exact name on the expected registry; publisher and repo match; no typosquat or dependency-confusion risk. |
| Supply chain | No malware advisory, obfuscated payload, unexpected install script, credential/network access, or suspicious ownership transfer. |
| Security | No unpatched critical/high advisory affecting the intended use; a disclosure path exists. |
| License | Compatible with distribution and org policy, including transitive licenses. |
| Platform | Supports the required runtime, OS/arch, and version range. |
| Capability | Meets every must-have requirement. |
| Viability | Not archived or deprecated; for non-critical use, an archived library needs an explicit security-fix plan; for critical use, a responsive maintainer and a security-fix path. |

The Security gate is a floor: no unpatched critical/high advisory affecting the intended use. The Security and supply chain axis carries the rest of the judgment; an empty advisory list is absence of evidence, not proof of security.

Gates are pass/fail minimums; the scored axes apply at every criticality with the preset weights. Start with this set and add any gate the task makes material:

- **Throwaway script** — Identity, License, Platform, Capability.
- **Internal tool** — add Viability.
- **Production dependency** — add Supply chain and Security.
- **Security-sensitive** — all gates, with security evidence decisive.

### Scored axes

| Axis | What good looks like |
| --- | --- |
| Task fit and API | Solves the real use case with little glue; escape hatches; type safety; composable. |
| Correctness and reliability | Tests and conformance; sane error handling; stable API; low-severity bug history. |
| Security and supply chain | Few transitive dependencies; no install scripts; provenance; fast vulnerability response; no surprise telemetry. |
| Maintenance and governance | Releases and security fixes; triaged issues/PRs; bus factor above one; funding; deprecation policy. |
| Documentation and DX | Quickstart, API reference, task-specific examples, migration guide, types, clear errors. |
| Performance and footprint | Meets the workload; bundle size, memory, startup, native dependencies. |
| Compatibility and ecosystem | Works with the stack; peer dependencies; plugins; production users; support channels. |
| Cost and reversibility | Cheap to adopt, upgrade, and leave; no lock-in; acceptable support cost. |

**Proxy traps.** Maintenance means responsiveness (issues, PRs, security reports), currency (releases, dependency updates), sustainability (bus factor, funding), and stability (semver, changelog, deprecation policy) — not the last commit date. A quiet, stable library can be healthy. Documentation means accuracy (the quickstart matches the current release), completeness (API reference), task relevance (examples for this use case), and upgradability (migration guide, types) — not README length.

### Weight presets

Start from these, then adjust to the task and state the change:

| Context | Starting weights |
| --- | --- |
| Throwaway script | Task fit 50, Documentation 20, Maintenance 10, Security 10, Compatibility/ecosystem 5, Cost 5 |
| Internal tool | Task fit 35, Maintenance 20, Documentation 15, Security 15, Correctness 10, Cost 5 |
| Production dependency | Task fit 25, Security 20, Maintenance 20, Correctness 15, Documentation 10, Performance 5, Cost 5 |
| Security-sensitive | Security 30, Maintenance 20, Task fit 20, Correctness 15, Documentation 5, Performance 5, Cost 5 |

Axes not listed carry 0 in that preset; add any axis the task makes material and rebalance to 100. Short names map to the full axes above; Task fit covers API fit, Security includes supply chain, and Cost includes reversibility.

### Rating anchors

- **Strong** — verified, current evidence shows the candidate is better than the alternatives on this axis for this task.
- **Adequate** — meets the need with no material concern; any evidence gap is named and does not change the rating.
- **Weak** — a real gap or risk the user should accept knowingly; name the mitigation.
- **Unknown** — not verified; record what evidence would settle it and lower confidence.
