# Eval workspace

Eval definitions live in `<skill>/evals/evals.json`. Each entry has an `id`, a `prompt`, an optional `expected_output`, optional input `files` relative to the skill root, and optional `expectations`.

## Where runs go

The default workspace is `<skill-name>-workspace/` beside the skill directory. Pass `--workspace` to relocate it; the repository has no workspace setting.

The batch command creates one `iteration-<N>/` and runs every selected case in both arms. A new batch picks the next unused iteration number. Pass `--iteration N` to add runs to an existing iteration; the iteration must already exist. The single-case command below adds one arm to an existing iteration.

## Layout

```text
<skill-name>-workspace/
└── iteration-<N>/
    └── eval-<ID>/
        ├── eval_metadata.json
        ├── inputs/                         # only when the case lists files
        │   └── <path relative to skill>
        ├── with_skill/
        │   ├── outputs/
        │   │   ├── metrics.json
        │   │   └── <agent output files>
        │   ├── transcript.jsonl
        │   ├── transcript.md
        │   ├── timing.json
        │   └── run.json
        └── without_skill/                  # or old_skill
            └── ...
```

`eval_metadata.json` starts with `eval_id`, `eval_name`, `prompt`, `expected_output`, and an empty `expectations` list. Replace `eval_name` with a descriptive name and fill in the expectations when you draft assertions. Existing metadata is never overwritten.

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
- `transcript.jsonl` is the raw adapter stream.
- `transcript.md` is the human-readable transcript.
- `timing.json` holds `total_tokens`, `duration_ms`, and `total_duration_seconds`.
- `run.json` holds the normalized run metadata: the stable run ID, assistant text, token totals, duration, loaded skill IDs, relative output paths, exit code, stderr, derived metrics, and whether the run timed out.

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

Exit codes are `0` when every run is ok, `1` when any run failed or errored, and `2` when the batch could not start.

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

Use this to retry or inspect one arm. For the normal comparison, use the batch command, which runs both arms together.
