# Description optimization

Description optimization improves the `description` in `SKILL.md` frontmatter so the skill loads for the right requests. It is separate from task evals: task evals check the output after the skill loads, while trigger evals check whether the description makes an agent load the skill at all. See [trigger evals](trigger-evals.md) for the single-description evaluator.

Use this workflow when trigger rates show a description problem, after creating a skill, or when the user asks to tune triggering. Do not add body instructions to fix a description that fails to trigger; the agent never reads the body until it loads the skill.

## Step 1: Generate trigger queries

Write about 20 queries: 8–10 should-trigger and 8–10 should-not-trigger. The agent writes these, using the guidance in [trigger evals](trigger-evals.md#write-the-query-set). Save them at `<skill>/evals/trigger_evals.json`.

Make them realistic and specific:

- Include file paths, column names, tools, casual phrasing, abbreviations, and enough context that the agent could act.
- Cover different phrasings of the same intent for should-trigger queries, including requests that never name the skill.
- Make should-not-trigger queries genuine near-misses that share keywords or concepts but need something else.
- Avoid one-step requests the agent could handle without any skill; those may not trigger even with a perfect description.

The query set is a review artifact. Do not treat the first draft as final.

## Step 2: Review the queries in a static page

Generate a standalone review page from the skill and query set:

```bash
python -m scripts.trigger_review \
  --skill path/to/my-skill \
  --eval-set path/to/my-skill/evals/trigger_evals.json
```

Run this from the `creating-skills` skill directory so the `scripts` package resolves. Without `--eval-set`, the command reads `<skill>/evals/trigger_evals.json`. It writes `trigger-review.html` beside the skill at `path/to/my-skill-workspace/trigger-review.html` and prints the path.

The page shows the skill's current description and lets the reviewer edit query text, toggle should-trigger, add queries, and delete queries. It writes no files and runs no server. The reviewer returns the edited set with **Download trigger_evals.json** or **Copy trigger_evals.json**; save the returned JSON over `<skill>/evals/trigger_evals.json`.

Use `--output PATH` to write the page somewhere else. The page needs only a browser opening the HTML file.

## Step 3: Run the optimization loop

Run the loop from the `creating-skills` skill directory:

```bash
python -m scripts.description_loop \
  --skill-path path/to/my-skill \
  --eval-set path/to/my-skill/evals/trigger_evals.json \
  --model provider/model
```

`--model` is required. Description comparison is model-sensitive, so the loop never silently falls back to the configured default model; pass the model that the real skill users run.

Useful options:

```text
--description TEXT          start from a candidate description instead of SKILL.md
--max-iterations N         stop after N attempts; default 5
--runs-per-query N         probes per query; default 3
--trigger-threshold R      pass threshold from 0 to 1; default 0.5
--holdout R                test fraction greater than 0 and less than 1; default 0.4
--seed N                   split seed; default 42
--workers N                maximum parallel probes
--timeout SECONDS          per-probe timeout; default 120
--optimizer-timeout SECONDS  per-optimizer-run timeout; default 300
--results-dir DIR          parent directory for the timestamped run folder
--harness NAME             select a registered adapter
--verbose                  mirror loop progress to stderr
```

The loop:

1. Splits the query set into train and test sets, stratified by `should_trigger`. Both sets keep the same mix of positive and negative queries, and the split is stable for a given seed. The holdout fraction must be greater than 0 and less than 1.
2. Evaluates every query in one parallel batch, then partitions the results. Evaluating together keeps the run fast; the partition is what keeps test results away from the optimizer.
3. Reports train and test scores separately. The train score drives improvement; the test score is held out.
4. If train queries still fail, asks a fresh agent to propose a new description. The optimizer runs through the harness adapter in no-tools completion mode with every skill denied. Its prompt contains the current description, train failures, prior train attempts, and the skill body. It never receives test results or test queries.
5. Repeats until every train query passes or `--max-iterations` is reached.
6. Chooses the best attempt by test score. Ties keep the earlier attempt, which is usually the simpler description.

The optimizer prompt states the 1024-character hard limit. If a proposal is still over the limit, the loop makes one fresh rewrite request with the too-long text; a description still over 1024 characters after that rewrite is rejected. A failed optimizer or rewrite call is also recorded. In both cases the loop stops with the best attempt evaluated so far, records `optimizer_error (...)` as the exit reason, and still writes the logs, results, and reports, so earlier results are not lost. A starting description over the limit is rejected before any probe runs.

## Step 4: Read the reports and logs

Each run writes a timestamped directory under `<skill-name>-workspace/description-optimization/` beside the skill, or under `--results-dir` when supplied:

```text
<skill-name>-workspace/description-optimization/<timestamp>/
├── live.html                 # refreshed after every iteration
├── report.html               # final static report
├── results.json              # full loop result and history
└── logs/
    ├── loop.log              # progress and per-iteration scores
    ├── improve_iter_<N>.json # optimizer prompt, response, and run metadata
    ├── improve_iter_<N>.transcript.jsonl
    ├── improve_iter_<N>.transcript.md
    └── improve_iter_<N>.rewrite.transcript.{jsonl,md}  # when a rewrite ran
```

`live.html` is a static HTML file with a five-second meta refresh. Open it while the loop runs to watch each attempt and its train/test cells; it always shows the best attempt so far. When the loop finishes, `live.html` is rewritten without the refresh. `report.html` is the same final report. Neither page needs a server or network access.

`results.json` follows [the results contract](schemas.md#description-optimization-results). The CLI also prints it to stdout. `logs/improve_iter_<N>.json` records the exact prompt and response, the parsed description, character counts, the rewrite attempt when one ran, and the adapter run's token, duration, exit, and loaded-skill metadata.

## Step 5: Apply and verify the result

Read `best_description` from `results.json`, show the user the before and after descriptions with the train and test scores, and update the `description` in `SKILL.md` frontmatter. Keep the body unchanged unless the failures point to a broader scope problem.

Verify the applied description with the trigger evaluator, passing the same model used for optimization:

```bash
python -m scripts.trigger_eval \
  --skill path/to/my-skill \
  --eval-set path/to/my-skill/evals/trigger_evals.json \
  --model provider/model
```

A good optimization improves held-out queries as well as the ones that drove the change. If the train score rises while the test score falls, the optimizer overfit: keep the earlier description or revise the query set so it covers broader intent. Do not copy the failing query list into the description; that overfits the sample and consumes context in every request.
