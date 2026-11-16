# Trigger evals

A trigger eval measures whether a description makes an agent load the skill for realistic queries. Task evals ask whether the skill produces good output once loaded; trigger evals ask whether the agent finds the skill at all.

## Write the query set

Save the queries with the skill, normally at `<skill>/evals/trigger_evals.json`:

```json
[
  {
    "query": "my boss sent me this xlsx and wants a profit margin column added",
    "should_trigger": true
  },
  {
    "query": "explain what a profit margin is",
    "should_trigger": false
  }
]
```

Each entry needs a non-empty `query` and a boolean `should_trigger`. Duplicate queries are rejected because they would be measured twice without adding information.

Write realistic prompts, not topic labels. Include file paths, column names, abbreviations, casual speech, and enough context that the agent could act:

- **Should-trigger queries** (8–10) cover different phrasings of the same intent. Include the cases where the user never names the skill or file type but clearly needs it.
- **Should-not-trigger queries** (8–10) are near-misses that share keywords or concepts with the skill but need something else. Avoid obviously unrelated prompts; they do not test the boundary.
- Make the prompts substantive. A one-step request the agent can handle with a basic tool may not consult a skill even when the description matches.

## Run the evaluation

Run this from the `creating-skills` skill directory so the `scripts` package resolves:

```bash
python -m scripts.trigger_eval \
  --skill path/to/my-skill \
  --eval-set path/to/my-skill/evals/trigger_evals.json
```

The command reads the skill name and description from `SKILL.md` unless `--description` overrides the description. It then runs every query several times in parallel through the harness adapter. The adapter owns how the candidate skill is built and isolated; see the adapter documentation for those details.

Useful options:

```text
--description TEXT     test a candidate description without editing SKILL.md
--runs-per-query N     runs per query; default 3
--trigger-threshold R  pass threshold from 0 to 1; default 0.5
--workers N            maximum parallel probes; default min(10, queries × runs)
--model ID             override the harness model
--timeout SECONDS      per-probe timeout; default 120
--harness NAME         select a registered adapter
--output PATH          also write the JSON document to this path
```

The JSON document goes to stdout, and a one-line `PASS`/`FAIL` summary per query goes to stderr. Exit code `0` means every query passed, `1` means at least one query failed, and `2` means the evaluation could not run.

## Pass and fail

For each query, `trigger_rate` is `triggers / runs`.

- A should-trigger query passes when its rate is at least `--trigger-threshold`.
- A should-not-trigger query passes when its rate is below the threshold.
- A probe that raises counts as no trigger, marks its query failed, and prints a warning. Infrastructure failures must not look like a successful non-trigger.

A single run is noisy. Use at least three runs per query, and treat a rate near the threshold as uncertain rather than a clean pass or fail.

## Output

Each result records `query`, `should_trigger`, `triggers`, `runs`, `errors`, `trigger_rate`, and `pass`. The summary counts `total`, `passed`, and `failed` queries. See [the JSON contract](schemas.md#trigger_evaljson) for the full document.

Save the document beside the trigger eval set or in the skill's workspace so the next description attempt can be compared against it. The query format is defined in [trigger_evals.json](schemas.md#trigger_evalsjson).
