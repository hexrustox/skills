---
name: writing-tests
description: Write, revise, or review an individual test function or case so it states one observable behavior, fails for one reason, and is deterministic and diagnostic. Use when adding or changing a unit or integration test, naming a test, choosing assertions or fixtures, deciding what to mock, improving a flaky test's isolation, or asking whether a test is any good.
---

# Writing Tests

A good test is a small, self-contained claim about observable behavior. It should fail for one understandable reason and tell a reader what broke without opening the implementation. Optimize for diagnosis and confidence, not coverage or DRY.

The rules below are defaults with reasons. When you depart from one, say why. The unit of work is one test function or case, including one row of a parameterized test.

This skill covers writing and reviewing a single test. Suite-level strategy, framework setup, and CI are outside its scope.

The short version:

- One behavior, one reason to fail. Multiple assertions are allowed.
- Arrange, Act, Assert. One act unless the workflow is the behavior.
- DAMP (Descriptive And Meaningful Phrases) over DRY: inline what matters, hide only what does not.
- Assert the observable contract with actionable failure output.
- Deterministic and isolated: no sleeps, order dependence, or shared mutable state.
- Use doubles at boundaries; verify state over interactions.
- A test you have not seen fail is a guess.

## 1. Decide the behavior and name it

Write the claim before the body:

> Given <context>, when <action>, then <observable outcome>.

- **One behavior.** A behavior is a guarantee about how the system responds, not a method call. If the claim needs "and" to join two outcomes, you have two tests.
- **One reason to fail.** Name the bug this test catches. If you cannot, it is ceremony; do not write it.
- **The risky path.** Prefer boundaries, empty or invalid input, error paths, permissions, and concurrency over another happy-path duplicate.
- **A contract.** Decide what is public for this unit: an API for a library, a request/response or message schema for a service, an accessible role/name for a UI. Assertions stay inside that contract.
- **The lowest level that expresses the behavior.** Use a unit test for pure logic; use an integration test for wiring, persistence, or configuration. Do not mock half the system to keep a test "unit".
- **No duplicate.** Search for an existing test of the same behavior. Extend, parameterize, or replace it instead of adding a near-copy.
- **A name that states the claim.** Use `<condition> <expected outcome>` or `given <context>, when <action>, then <outcome>`. Examples: `expired coupon is rejected`, `withdrawing more than the balance leaves the balance unchanged`. Avoid `test1`, `testCheckout`, and `should work`. "Should" is acceptable when the outcome is specific. A method name alone is not a behavior, and the name should still make sense if the production method is renamed.
- **Domain vocabulary.** Use the project's established domain terms; do not invent a synonym.

Done when you can state the behavior, the bug it catches, the contract, the test level, the name, and why no existing test already covers it.

## 2. Write the body as Arrange, Act, Assert

```ts
test("<condition> <expected outcome>", () => {
  // Arrange: create the world; make outcome-relevant values explicit
  // Act: one call that exercises the behavior
  // Assert: observable outcome, one reason to fail
});
```

Given/When/Then is the same structure in domain language. The example uses a Jest/Vitest-shaped API; translate the structure to the project's framework.

### Arrange

- Create a fresh fixture per test, or use a documented isolation mechanism (transaction rollback, unique schema) that gives the same guarantee.
- Make values that affect the outcome visible and named. Hide irrelevant fields behind a builder or defaults.
- A helper may hide incidental setup, but must not hide the act or the assertion. If a reader has to open the helper to understand the claim, inline it.
- No assertions in arrange except precondition guards. No branching, no sleeps.
- Avoid mystery guests: data from a file, global, or another test that the body does not show.

### Act

- One call that exercises the behavior. Setup calls belong in arrange.
- Do not assert between acts unless the intermediate state is part of the behavior, as in "retry succeeds after a transient failure".
- Keep the act obvious. Do not bury it in a helper named `doEverything()`.

### Assert

- At least one assertion on an observable outcome: return value, state read through the public interface, emitted message, or persisted record.
- Assert the contract, not internals: no private fields, internal call order, SQL text, log strings, or exact serialization unless that is the contract.
- Multiple assertions are fine when they are facets of one outcome and a single fix would address them. Split when a failure would send you to different places.
- Make failure output actionable: it should name the behavior, the input, the expected value, and the actual value. Prefer specific matchers over truthiness. Add a message if the framework only prints "expected true but was false".
- Error paths: assert the error type, code, or semantic property, and that no side effect occurred. Do not assert the full prose unless it is the API.
- No assertion-free tests. If the only failure mode is a crash, say it is a smoke test and add an assertion if the behavior matters.

Done when the body has one behavior, one act (or a justified workflow), data that matters is visible, and at least one diagnostic assertion on the contract.

## 3. Make it reliable

- No shared mutable state, no order dependence, no global, singleton, or environment mutation. Inject or reset what the test needs.
- Control time, randomness, network, filesystem, and concurrency. Inject a clock or ID generator, freeze time, seed random generators, and fake external boundaries. Use a unique temp directory or database schema.
- No fixed sleeps. Await the condition, advance fake timers, or poll with a timeout.
- Clean up in teardown or `finally`, even when the test fails.
- Keep unit tests in the local feedback loop. Move slow, broad checks to an integration tier rather than mocking away the risk.
- Run the test alone, twice, in random order, and in parallel if the suite supports it.

Done when the test passes alone, repeatedly, in the full suite, and in random order, with no uncontrolled external dependency.

## 4. Verify it can fail

A test that has never failed is a guess.

- Run it against the broken or old behavior first. It must fail for the expected reason; if it passes, it is not testing what you think.
- Read the failure output. If it does not identify the behavior, input, expected, and actual, improve the matcher or message.
- Run a mutation thought experiment: temporarily change the production line or reason about the mutation. Does the test catch it? If not, the assertion is weak. If mutation testing is available, use it on the changed lines.
- Run the full suite and confirm the test leaves no state behind.

Done when you have seen it fail for the right reason and pass for the right reason.

## Worked example

Bad:

```ts
test("checkout", async () => {
  const payment = { charge: vi.fn().mockResolvedValue({ id: "ch_1" }) };
  const repo = { saveOrder: vi.fn() };
  const cart = { items: [{ price: 1000, qty: 2 }], coupon: "EXPIRED" };

  const result = await checkout(cart, payment, repo);

  expect(payment.charge).not.toHaveBeenCalled();
  expect(repo.saveOrder).not.toHaveBeenCalled();
  expect(result).toBeFalsy();
});
```

Problems:

- The name says nothing.
- `"EXPIRED"` is a magic value that hides the scenario.
- Internal collaborators are mocked and their calls are asserted.
- `toBeFalsy` accepts `null`, `undefined`, `0`, and `""`; it does not prove the rejection reason.
- The failure does not say which assertion broke.

Better:

```ts
test("expired coupon is rejected without charging the customer", async () => {
  const cart = cartWith({ coupon: expiredCoupon(), items: [item({ priceCents: 2000 })] });
  const payments = new FakePaymentGateway();

  const result = await checkout(cart, payments);

  expect(result).toEqual({ status: "rejected", reason: "coupon_expired" });
  expect(payments.charges).toEqual([]);
});
```

Why it is better:

- The name is the claim.
- `cartWith` defaults irrelevant fields while the relevant coupon and item stay visible. If the project has no builder, inline the object; the point is to show the data that matters, not to require a helper.
- `FakePaymentGateway` is a boundary fake, and the test asserts its state rather than internal calls.
- The two assertions share one reason to fail: the rejection and the absence of a charge are one guarantee.
- Use `toMatchObject` instead of `toEqual` when extra result fields are allowed by the contract.

## Judgment calls

| Decision | Default | Exception or nuance |
| --- | --- | --- |
| DAMP vs DRY | Inline setup that explains the behavior. Extract only incidental repetition. | Helpers and builders are fine for stable, non-behavioral setup. Never share mutable fixtures. If a reader must open the helper to understand the claim, inline it. |
| "One thing" | One behavior and one reason to fail. Multiple assertions that describe that outcome are fine. | Split when assertions imply different fixes. A name needing "and" is a smell, not proof. Literal one-assert-per-test is not required. |
| One act | One call that exercises the behavior. | A workflow test is acceptable when intermediate states are part of the behavior; mark the phases and keep one behavior. |
| Multiple assertions | Group facets of one outcome; use the framework's grouped or soft assertions so all failures report. | Split unrelated checks. Do not let assertion #1 hide a different behavior's assertion #2. |
| Test doubles | Real objects and fakes inside the domain; doubles at process, I/O, time, network, and third-party boundaries. Verify state. | Verify interactions only when call count or order is the contract. Wrap third-party APIs in an adapter you own and fake the adapter. |
| Test data | Minimal and intention-revealing; builders with defaults; named values when a relationship is not obvious. | A literal is often clearer than a builder in a tiny test. Do not build a data framework for one test. |
| Parameterized tests | Same behavior, several inputs; each row named and independently diagnosable. | Different setup or assertions mean separate tests. Property-based tests cover invariants, not named business scenarios. |
| Snapshots | Small, deterministic, reviewed output; assert specific properties for important logic. | A snapshot catches change, not correctness. Never blind-update a snapshot to get green. |
| Coverage | A diagnostic for finding untested branches, not a target. Add a regression test for every bug. | Mutation testing and property-based tests give stronger confidence where affordable. |
| Test level | Lowest level that expresses the behavior; a few broader tests for wiring, persistence, and fidelity. | No fixed pyramid ratio; choose by fidelity and cost. |
| Flaky test | Treat it as a defect. Find the shared state, time, order, or resource-contention cause. | Never normalize retries or sleeps to get green. Fix the cause before changing the test. |
| Naming grammar | Condition plus expectation in domain words; consistent within the suite. | "Should" is fine. `Method_Scenario_Expected` is acceptable if the project uses it, but the behavior must still be clear. |

Two rows are genuinely contested: mocking style and the literal one-assertion rule. The defaults favor refactoring resistance and diagnosis. Depart from them when the contract or workflow justifies it, and say why.

## Anti-patterns

| Symptom | Repair |
| --- | --- |
| **Assertion roulette** — several assertions and the failure does not say which one failed. | Add distinct messages, group related assertions, or split unrelated ones. |
| **Eager test** — one test exercises several behaviors and methods. | Split by behavior; share setup through a builder, not a mega-test. |
| **Obscure test, mystery guest, or general fixture** — cause and effect are hidden in helpers, files, or oversized setup. | Inline what matters; name values; use a minimal per-test fixture. |
| **Conditional test logic** — `if`, loops, `try/catch`, or computed expectations in the body. | Parameterize or split; write literal expected values. |
| **Fragile or change-detector test** — asserts internals, private state, call order, or exact strings. | Assert the public contract; keep only contract-relevant interactions. |
| **Over-mocked test** — every collaborator is a mock and every call is verified. | Use real objects or fakes; double only at boundaries. |
| **Tautological test** — expected value is computed the same way as production. | Hard-code an independent value or use an oracle or round-trip property. |
| **Assertion-free test** — runs code but proves nothing. | Assert the observable outcome; enable the framework's assert-count guard. |
| **Sleep, order dependence, or shared global** — the test depends on timing or another test's side effects. | Await a condition, inject the clock, create a fresh fixture, reset or inject globals. |
| **Snapshot blind update** — regenerating until green. | Review the diff; keep snapshots small; assert important logic explicitly. |
| **Happy-path-only test** — no error, boundary, empty, or timeout case. | Add failure paths and boundary values deliberately. |
| **Method-mirror suite** — one test per method, named after the method. | Test guarantees; one behavior may span methods. |
| **Test-only production hook** — an `if (testing)` branch in production. | Use dependency injection or a seam. |
| **Coverage theatre** — high line coverage with weak assertions. | Test risks and behaviors; use coverage only to find holes. |

## Review gate

For a review, read the test and its contract first. Start with four questions:

- Would it fail if the behavior were wrong?
- Would it pass if the implementation were rewritten equivalently?
- Can a stranger diagnose the failure from the output?
- Does it pass alone, repeatedly, and in any order?

If any answer is no, the test needs revision. Do not rewrite silently; report findings.

Use this contract:

```markdown
## Test review
**Verdict:** pass | revise
**Behavior:** <one sentence the test claims to prove>

### Findings
- `<file>:<line>` — <problem>. <why it matters>. <fix>.
```

Classify each finding:

- **Product bug** — the test exposes wrong behavior; fix the product, not the assertion.
- **Test bug** — the test is wrong, brittle, or incomplete; fix the test.
- **Changed requirement** — the behavior intentionally changed; update the test and say so.

Never weaken an assertion, delete a test, or add a retry to get green. If the right fix is unclear, say what evidence would settle it.

### Checklist

- [ ] The name states condition and expectation; no `test1`, `should work`, or bare method name.
- [ ] The test covers one behavior and one reason to fail.
- [ ] Arrange, Act, Assert are visible; one act, or a workflow exception is justified.
- [ ] At least one assertion is on an observable outcome; the failure names input, expected, and actual.
- [ ] No private state, internal call order, log strings, or unstable exact strings unless contractual.
- [ ] No control flow or computed expected values in the body.
- [ ] The test creates a fresh fixture and has no order dependence or shared mutable state.
- [ ] Time, randomness, network, filesystem, and concurrency are controlled or injected; no fixed sleeps.
- [ ] Doubles are at boundaries; state is verified over interactions.
- [ ] Data is minimal; outcome-relevant values are visible; there is no mystery guest.
- [ ] The test fails for the expected reason when the behavior is broken.
- [ ] The test passes alone, repeatedly, and in the full suite.

Fix the cause of any unchecked box and re-check. Done when every finding is classified and every checklist item passes or has a stated, justified exception.
