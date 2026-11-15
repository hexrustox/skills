# Eval workspace

Eval definitions live in `<skill>/evals/evals.json`. Each entry has an `id`, a `prompt`, an optional `expected_output`, optional input `files` relative to the skill root, and optional `expectations`.

## Where runs go

The default workspace is `<skill-name>-workspace/` beside the skill directory. Pass `--workspace` to relocate it; the repository has no workspace setting.

Each invocation writes into `iteration-<N>/`. A new invocation picks the next unused iteration number. Pass `--iteration N` to add an arm to an existing iteration; the iteration must already exist.

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

## Run identity

The stable identity is `eval-<ID>-<arm>`, for example `eval-1-with_skill`. It is the path from the iteration directory with `/` replaced by `-`, and it does not depend on the iteration number or workspace location. Use it to match outputs and feedback across iterations.

## Arms

- `with_skill` runs the skill under test.
- `without_skill` runs an empty scope for a new skill.
- `old_skill` runs a baseline snapshot. Pass its directory with `--baseline-skill`.

Both baseline forms deny every other skill. Take the `old_skill` snapshot before editing the skill.

## Input files

Every path in `files` resolves against the skill root. The runner copies each file into `<eval>/inputs/<path relative to skill>` before the run, then stages the preserved copy into the isolated project at the same relative path. The adapter attaches those staged files to the prompt. Inputs are preserved once per eval directory: a later arm or rerun uses the preserved copy even if the source file changed. Start a new iteration when the inputs change.

## Artifacts

- `outputs/` holds the files the agent produced plus the derived `metrics.json`.
- `transcript.jsonl` is the raw adapter stream.
- `transcript.md` is the human-readable transcript.
- `timing.json` holds `total_tokens`, `duration_ms`, and `total_duration_seconds`.
- `run.json` holds the normalized run metadata: the stable run ID, assistant text, token totals, duration, loaded skill IDs, relative output paths, exit code, stderr, derived metrics, and whether the run timed out.

A failed or timed-out run still writes the full artifact set so the failure can be diagnosed.

## Run one case

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

To compare both arms, run the same case with `--arm with_skill` and `--arm without_skill` (or `old_skill`) into one explicit iteration.
