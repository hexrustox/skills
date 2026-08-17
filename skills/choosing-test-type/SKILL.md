---
name: choosing-test-type
description: Decide which kind of test to write — unit, integration, property, or none — via a language-agnostic decision tree. Use when writing or adding tests, choosing a test type for a behavior, or reviewing whether a suite covers the behaviors that can break.
---

Decide the test type for a behavior. Run the tree once per behavior — writing a new test, or auditing a suite (each existing test should sit on the branch its behavior falls on).

## The tree

1. **Is the risk in the boundary?** Does the behavior's correctness depend on wiring to a real database, network service, filesystem, clock, or external process — where a stub would void what can break? If yes, write an **integration test**.
   - Assert the contract against the real boundary: the query against the schema, the request against the service's semantics, the values carried through the wiring. Done when the integration proves the boundary holds that no fake could.

2. **Is the risk in the input space?** Is the behavior a transformation over a wide or unknown set of inputs where you can state an invariant that must hold for every input — a round-trip (`decode(encode(x)) == x`), idempotence, sortedness, a bound, never-throws? If yes, write a **property test**.
   - State the invariant in one line first, then generate inputs and assert it. A failing run shrinks to the minimal counterexample. Done when the invariant holds across generated inputs.

3. **Is the unit's own logic the risk?** Is the behavior the isolated logic of a function or module, callable with collaborators stubbed and inputs pinned? Write a **unit test**.
   - Stub the collaborators and pin concrete examples as assertions. Done when every distinct path the logic can take is pinned by an example.

4. **Is the path thin?** Is this single-use glue or throwaway scaffold that cannot change an outcome? Write **no test** — and default toward writing, so this branch has to earn itself. Done when you can name the outcome it cannot change.

A behavior that both boundary and transformation can answer follows the risk that can actually break: the fake-able boundary belongs on branch 2, the transformation on its own run of the tree.