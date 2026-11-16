# Maintaining creating-skills

Maintenance notes for `tools/skills/creating-skills`. This file is not part of the skill.

The port is a harness-neutral adaptation of the `skill-creator` skill from the upstream `anthropics/skills` repository.

| Field | Value |
| --- | --- |
| Upstream repository | `https://github.com/anthropics/skills` |
| Upstream skill path | `skills/skill-creator` |
| Pinned upstream commit | `b9e19e6f44773509fbdd7001d77ff41a49a486c1` (2026-04-20, the last commit affecting the skill) |
| Vendored snapshot | `.agents/skills/skill-creator` |
| Lock entry | `skills-lock.json` → `skill-creator` |
| Lock `computedHash` | `5ea13a6d9f0d4bb694405d79acd00cadec0d21bb138c4dd10fcf3c500cb835c2` |
| Port location | `tools/skills/creating-skills` |
| License | Apache-2.0; see `tools/skills/creating-skills/LICENSE.txt` (copied unchanged from upstream) |

The vendored snapshot is the upstream reference used for future diffs.

## Port changes

The port keeps the upstream authoring and improvement loop but removes or rewrites material that assumed a specific harness, distribution channel, or UI:

- Renamed the skill to `creating-skills` and aligned the directory and frontmatter name.
- Rewrote instructions in harness-neutral language: "the agent", "fresh-context run", and "harness adapter".
- Moved authoring detail into `tools/skills/creating-skills/references/writing-patterns.md`.
- Removed packaging, archive creation, file-presentation steps, and harness-specific review instructions.
- Did not port the upstream validator or packaging script.
- Replaced the upstream `scripts/utils.py` parser with a standard-library `tools/skills/creating-skills/scripts/frontmatter.py` module and added a `unittest` suite under `tools/skills/creating-skills/tests/`.
- Added the `Harness` protocol and normalized run results in `tools/skills/creating-skills/scripts/harness.py`, plus a name-keyed adapter registry in `tools/skills/creating-skills/scripts/adapters/`.
- Added the OpenCode adapter at `tools/skills/creating-skills/scripts/adapters/opencode.py`, with its documentation and index under `tools/skills/creating-skills/references/harnesses/`. Its trigger probe builds a uniquely named candidate skill in a deny-all scope, stops once a skill load or candidate-directory read is observed, and reports the partial run.
- Added the trigger-rate evaluator at `tools/skills/creating-skills/scripts/trigger_eval.py`, documented in `tools/skills/creating-skills/references/trigger-evals.md`. It runs each should-trigger and should-not-trigger query multiple times in parallel and reports trigger rates and pass/fail per query.
- Added the canonical eval workspace and single-case runner in `tools/skills/creating-skills/scripts/workspace.py` and `tools/skills/creating-skills/scripts/eval_case.py`, documented in `tools/skills/creating-skills/references/evals.md`.
- Added the batch runner in `tools/skills/creating-skills/scripts/eval_batch.py` with its tests. It creates one iteration, prepares metadata and inputs before dispatch, runs every case's with-skill and baseline arms in parallel, aliases an `old_skill` snapshot to the live skill's name, and writes `error.json` for setup failures instead of stopping the batch.
- Added the benchmark aggregator in `tools/skills/creating-skills/scripts/benchmark.py` with its tests. It adapts the upstream `aggregate_benchmark.py` to the canonical layout: one run per arm directory containing `grading.json`, eval names from `eval_metadata.json`, `runs_per_configuration` derived from the data, mean/stddev/min/max statistics, a delta calculated from arm names, and token totals read from timing data rather than output size. It writes `benchmark.json` and `benchmark.md`; the static review page reads `benchmark.json` for its Benchmark tab.
- Added harness-neutral grader, comparator, and analyzer instructions under `tools/skills/creating-skills/agents/`, plus the JSON contract reference at `tools/skills/creating-skills/references/schemas.md`. Grading, blind comparison, and analysis run as fresh-context instructions; the unused `history.json` schema was dropped.
- Added the static review page generator at `tools/skills/creating-skills/scripts/review.py` and its template at `tools/skills/creating-skills/assets/review.html`. It writes a standalone `review.html` from normalized run data, matches previous runs by stable identity, and downloads or copies `feedback.json`; the upstream HTTP server, port handling, and browser launch were not ported.
- Eval, grading, comparison, analysis, benchmark, and description-tuning operations go through a harness adapter rather than hardcoded commands.

## Diffing an upstream update

1. Update the vendored snapshot:

   ```bash
   skills update skill-creator
   ```

2. Inspect what changed upstream:

   ```bash
   git diff -- .agents/skills/skill-creator skills-lock.json
   ```

3. Compare each changed upstream file with its port counterpart:

   ```bash
   diff -u .agents/skills/skill-creator/SKILL.md tools/skills/creating-skills/SKILL.md
   ```

   Repeat for any changed reference, agent instruction, or script. The diff will be noisy because the port intentionally renames the skill, rewrites prose, and drops packaging and harness-specific material. Read it for upstream ideas, not as a literal patch.

4. Port only changes that preserve harness neutrality: keep the authoring and improvement logic, and leave packaging, archive, presentation, and harness-specific sections in upstream. If an upstream change is useful but harness-specific, put it in the adapter documentation instead of the neutral core.

5. Update the pinned commit and `computedHash` in the table above to match the new snapshot.

6. Re-read the updated port, check every relative file reference resolves, and confirm `opencode.json` still denies the vendored `skill-creator`.

Done when the port reflects the upstream changes worth taking, every reference resolves, and the pinned commit and `computedHash` match the new snapshot.

## Updating the pinned hash

The `computedHash` comes from `skills-lock.json`. After an update, read the new value from the `skill-creator` entry and replace the one in the table. Record the upstream commit that last changed the vendored skill; use `git log` in a clone of the upstream repository or the upstream commit history for the skill path.
