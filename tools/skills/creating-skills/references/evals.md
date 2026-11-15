# Eval workspace

Eval definitions live in `<skill>/evals/evals.json`. Each entry has an `id`, a `prompt`, an optional `expected_output`, optional input `files` relative to the skill root, and optional `expectations`. See [the JSON contracts](schemas.md) for the full field definitions.

## Where runs go

The default workspace is `<skill-name>-workspace/` beside the skill directory. Pass `--workspace` to relocate it; the repository has no workspace setting.

The batch command creates one `iteration-<N>/` and runs every selected case in both arms. A new batch picks the next unused iteration number. Pass `--iteration N` to add runs to an existing iteration; the iteration must already exist. The single-case command below adds one arm to an existing iteration.

## Layout

```text
<skill-name>-workspace/
└── iteration-<N>/
    ├── benchmark.json                      # after aggregation
    ├── benchmark.md
    └── eval-<ID>/
        ├── eval_metadata.json
        ├── inputs/                         # only when the case lists files
        │   └── <path relative to skill>
        ├── comparison.json                 # optional, blind comparison
        ├── analysis.json                   # optional, post-hoc analysis
        ├── with_skill/
        │   ├── outputs/
        │   │   ├── metrics.json
        │   │   ├── user_notes.md           # optional
        │   │   └── <agent output files>
        │   ├── transcript.jsonl
        │   ├── transcript.md
        │   ├── timing.json
        │   ├── run.json
        │   └── grading.json
        └── without_skill/                  # or old_skill
            └── ...
```

`eval_metadata.json` starts with `eval_id`, `eval_name`, `prompt`, `expected_output`, and an empty `expectations` list. Replace `eval_name` with a descriptive name and fill in the expectations when you draft assertions. Existing metadata is never overwritten. The benchmark aggregator reads `eval_name` from this file; it does not derive the name from the directory.

A setup failure, such as a missing input file or a scope preparation error, writes `error.json` in the affected arm directory instead of inventing a run. The rest of the batch continues.

## Run identity

The stable identity is `eval-<ID>-<arm>`, for example `eval-1-with_skill`. It is the path from the iteration directory with `/` replaced by `-`, and it does not depend on the iteration number or workspace location. Use it to match outputs and feedback across iterations.

## Arms

- `with_skill` runs the skill under test.
- `without_skill` runs an empty scope for a new skill. It is the default when no baseline snapshot is supplied.
- `old_skill` runs a baseline snapshot. Pass its directory with `--baseline-skill`.

Both baseline forms deny every other skill. Take the `old_skill` snapshot before editing the skill:

```bash
mkdir -p path/to/example-skill-workspace
cp -r path/to/example-skill path/to/example-skill-workspace/skill-snapshot
```

The batch copies the snapshot once under the live skill's name, so both arms report the same loaded skill ID even when the snapshot directory has a different name. The baseline must contain `SKILL.md`, must not be the live skill, and its frontmatter `name` must match the live skill.

## Input files

Every path in `files` resolves against the skill root. The runner copies each file into `<eval>/inputs/<path relative to skill>` before the run, then stages the preserved copy into the isolated project at the same relative path. The adapter attaches those staged files to the prompt. Inputs are preserved once per eval directory: a later arm or rerun uses the preserved copy even if the source file changed. Start a new iteration when the inputs change.

## Artifacts

- `outputs/` holds the files the agent produced plus the derived `metrics.json`.
- `outputs/user_notes.md` is optional. A run or a user may leave uncertainties, items needing review, or workarounds there; the grader summarizes it. Its absence does not block grading.
- `transcript.jsonl` is the raw adapter stream.
- `transcript.md` is the human-readable transcript.
- `timing.json` holds `total_tokens`, `duration_ms`, and `total_duration_seconds`.
- `run.json` holds the normalized run metadata: the stable run ID, assistant text, token totals, duration, loaded skill IDs, relative output paths, exit code, stderr, derived metrics, and whether the run timed out.
- `grading.json` is the grader's result. It holds `expectations` with `text`, `passed`, and `evidence`, plus summary counts, copied execution metrics and timing, claims, an optional user-notes summary, and optional eval feedback.
- `comparison.json` and `analysis.json` are optional outputs of a blind comparison. They live in the eval directory.

`outputs/metrics.json` is derived from the run's JSONL transcript. It records tool calls, steps, files created, errors, output characters, and transcript characters. Token totals for a benchmark come from `timing.json`.

A failed or timed-out run still writes the full artifact set so the failure can be diagnosed. A setup error that prevents the run from starting writes `error.json`, containing the run ID, arm, eval ID, error type, message, and traceback.

## Run the batch

Run this from the `creating-skills` skill directory so the `scripts` package resolves:

```bash
python -m scripts.eval_batch --skill path/to/my-skill
```

For an existing skill, pass the snapshot taken before editing:

```bash
python -m scripts.eval_batch \
  --skill path/to/my-skill \
  --baseline-skill path/to/my-skill-workspace/skill-snapshot
```

Useful options:

```text
--workspace DIR       relocate the workspace
--case ID             run only this eval ID; repeat to select several
--iteration N         add runs to an existing iteration
--baseline-skill DIR  use old_skill from this pre-edit snapshot
--model ID            override the harness model
--timeout SECONDS     per-run timeout
--harness NAME        select a registered adapter
```

The batch writes `eval_metadata.json` with empty expectations for every selected case before starting any run, then prints the iteration path and launches both arms for every case together. Draft assertions while the runs are in progress by editing `expectations` in each `<iteration>/eval-<ID>/eval_metadata.json`; existing metadata is never overwritten.

A filtered batch creates a partial iteration for debugging; run the complete set when you need a benchmark across every case. An iteration cannot mix `without_skill` and `old_skill` runs. If `<workspace>/skill-snapshot/` exists but `--baseline-skill` was not passed, the command warns rather than silently choosing `without_skill`.

Exit codes are `0` when every run is ok, `1` when any run failed or errored, and `2` when the batch could not start.

## Grade the runs

Grade after the runs finish and the expectations are written. Grading an empty expectation list is meaningless.

1. Read [the grader instructions](../agents/grader.md).
2. For each arm, start a fresh-context run through the harness adapter. Give it the eval prompt and expectations from `<eval>/eval_metadata.json`, the arm's `transcript.md` as `transcript_path`, the arm's `outputs/` as `outputs_dir`, and the arm's `grading.json` as `output_path`. The [OpenCode adapter](harnesses/opencode.md) documents a concrete command.
3. The grader writes `<arm>/grading.json`. If the fresh-context run cannot write outside its scope, have it return the JSON and write the file yourself.
4. Check the result. There must be one entry per expectation, in the same order and with the original `text`, using exactly the keys `text`, `passed`, and `evidence`. Confirm that the `summary` counts and `pass_rate` match.
5. Prefer a script for anything you can check programmatically. A script is faster, more reliable, and repeatable across iterations.
6. Read the optional `eval_feedback`. An assertion that would pass for a wrong output, or an important outcome with no assertion, is a gap to fix in `eval_metadata.json` and `evals/evals.json` before the next iteration. Do not force subjective qualities such as writing style into assertions.
7. The grader copies `outputs/metrics.json` into `execution_metrics`, copies `timing.json` into `timing`, and summarizes optional `outputs/user_notes.md`. Never substitute output characters for tokens.

## Compare two outputs blindly

Use a blind comparison when close versions need a more rigorous judgment than the review page, for example when the user asks whether a new version is actually better. It is optional and needs fresh-context runs plus completed grading.

1. Choose the two outputs. Usually this is `with_skill` and the baseline for one eval. A cross-iteration comparison is also valid; store its result under the newer iteration's eval directory.
2. Copy the two `outputs/` directories to neutral paths that do not reveal the arms, and keep the mapping private. Use a temporary directory, not the arm names.
3. Run [the comparator instructions](../agents/comparator.md) in a fresh context with `output_a_path`, `output_b_path`, the eval prompt, and the expectations. It writes `<eval>/comparison.json`; the `expectation_results` field records its own A/B verdicts.
4. Unblind the result with your private mapping. If the comparator returned a tie, stop: there is no winner to explain. Otherwise run [the analyzer instructions](../agents/analyzer.md) with the winning side, both skills, both transcripts, and the comparison file. It writes `<eval>/analysis.json` and explains why the winner won.
5. Delete the neutral copies. Use the analysis to improve the losing version in generalizable ways, not to tune the test prompt.

## Analyze benchmark patterns

After benchmark aggregation, use the "Analyze benchmark results" half of [the analyzer instructions](../agents/analyzer.md). It reads `benchmark.json` and returns a JSON array of strings. Place those strings in `benchmark.json` under `notes`. This pass reports patterns and anomalies across runs; it does not suggest skill changes.

## Debug one arm

Run this from the `creating-skills` skill directory so the `scripts` package resolves:

```bash
python -m scripts.eval_case \
  --skill path/to/my-skill \
  --eval-id 1 \
  --arm with_skill
```

Useful options:

```text
--workspace DIR       relocate the workspace
--iteration N         add this arm to an existing iteration
--baseline-skill DIR  required for the old_skill arm
--model ID            override the harness model
--timeout SECONDS     per-run timeout
--harness NAME        select a registered adapter
```

Use this to retry or inspect one arm. For a normal arm comparison, use the batch command, which runs both arms together.
