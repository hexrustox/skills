# JSON contracts

This document defines the JSON contracts used by `creating-skills`. Paths are relative to the eval workspace:

```text
<skill-name>-workspace/
└── iteration-<N>/
    ├── benchmark.json
    ├── benchmark.md
    └── eval-<ID>/
        ├── eval_metadata.json
        ├── comparison.json
        ├── analysis.json
        └── <arm>/
            ├── outputs/
            │   ├── metrics.json
            │   └── user_notes.md           # optional
            ├── timing.json
            └── grading.json
```

The `<arm>` directory is `with_skill`, `without_skill`, or `old_skill`. The benchmark files live at the iteration root. See [the eval workspace reference](evals.md) for the full layout and the run commands. `run.json` and `error.json` are workspace artifacts rather than grading contracts; they are described in that reference.

## Contents

1. [evals.json](#evalsjson)
2. [eval_metadata.json](#eval_metadatajson)
3. [grading.json](#gradingjson)
4. [metrics.json](#metricsjson)
5. [timing.json](#timingjson)
6. [benchmark.json](#benchmarkjson)
7. [comparison.json](#comparisonjson)
8. [analysis.json](#analysisjson)

---

## evals.json

Defines the evals for a skill. Located at `<skill>/evals/evals.json`.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's example prompt",
      "expected_output": "Description of the expected result",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "The output includes X",
        "The skill used script Y"
      ]
    }
  ]
}
```

**Fields:**

- `skill_name`: the name matching the skill's frontmatter.
- `evals[].id`: a unique identifier. The ID is used in the directory name and the stable run identity.
- `evals[].prompt`: the task to execute.
- `evals[].expected_output`: a human-readable description of success.
- `evals[].files`: optional input file paths relative to the skill root.
- `evals[].expectations`: verifiable statements. Prose may call them assertions, but the JSON key is always `expectations`.

---

## eval_metadata.json

The eval definition used by the workspace. Located at `<iteration>/eval-<ID>/eval_metadata.json`.

```json
{
  "eval_id": 1,
  "eval_name": "invoice-totals",
  "prompt": "User's example prompt",
  "expected_output": "Description of the expected result",
  "expectations": [
    "The output includes X",
    "The skill used script Y"
  ]
}
```

**Fields:**

- `eval_id`: the eval's identifier.
- `eval_name`: a descriptive name. The benchmark aggregator carries this value into `benchmark.json` as `runs[].eval_name`; it does not derive the name from the directory.
- `prompt`: the task to execute.
- `expected_output`: a human-readable description of success.
- `expectations`: the source of truth for grading and comparison.

The batch runner creates this file with empty `expectations` before starting a run. Existing metadata is never overwritten, so edits made while runs are in progress survive.

---

## grading.json

Output from the grader. Located at `<arm>/grading.json`.

```json
{
  "expectations": [
    {
      "text": "The output includes the name 'John Smith'",
      "passed": true,
      "evidence": "Found in transcript Step 3: 'Extracted names: John Smith, Sarah Johnson'"
    },
    {
      "text": "The spreadsheet has a SUM formula in cell B10",
      "passed": false,
      "evidence": "No spreadsheet was created. The output was a text file."
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 1,
    "total": 2,
    "pass_rate": 0.5
  },
  "execution_metrics": {
    "tool_calls": {
      "Read": 5,
      "Write": 2,
      "Bash": 8
    },
    "total_tool_calls": 15,
    "total_steps": 6,
    "files_created": ["report.md"],
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "total_tokens": 84852,
    "duration_ms": 23332,
    "total_duration_seconds": 23.3
  },
  "claims": [
    {
      "claim": "The form has 12 fillable fields",
      "type": "factual",
      "verified": true,
      "evidence": "Counted 12 fields in field_info.json"
    }
  ],
  "user_notes_summary": {
    "uncertainties": ["Used 2023 data, which may be stale"],
    "needs_review": [],
    "workarounds": ["Fell back to a text overlay for non-fillable fields"]
  },
  "eval_feedback": {
    "suggestions": [
      {
        "assertion": "The output includes the name 'John Smith'",
        "reason": "A hallucinated document that mentions the name would also pass. Consider checking that the name appears as the primary contact with matching phone and email from the input."
      }
    ],
    "overall": "Assertions check presence but not correctness. Consider adding content verification."
  }
}
```

**Fields:**

- `expectations[]`: one graded result per input expectation, in the original order. Each entry has exactly:
  - `text`: the original expectation text, unchanged.
  - `passed`: `true` or `false`.
  - `evidence`: the specific quote or observation supporting the verdict.
- `summary`: aggregate pass/fail counts.
  - `passed`, `failed`, `total`: counts over all expectations.
  - `pass_rate`: `passed / total`, from 0.0 to 1.0.
- `execution_metrics`: a copy of the run's `outputs/metrics.json` when available. It includes `tool_calls`, `total_tool_calls`, `total_steps`, `files_created`, `errors_encountered`, `output_chars`, and `transcript_chars`.
- `timing`: a copy of the arm's `timing.json` when available.
- `claims`: implicit claims extracted from the output. Each entry has `claim`, `type` (`factual`, `process`, or `quality`), `verified`, and `evidence`.
- `user_notes_summary`: optional summary of `outputs/user_notes.md`.
  - `uncertainties`, `needs_review`, `workarounds`.
- `eval_feedback`: optional critique of the evals, present only when the grader found a real gap.
  - `suggestions`: objects with a `reason` and optionally the `assertion` they concern.
  - `overall`: a brief assessment of the evals.

**Important:** the viewer and benchmark aggregator read `expectations[].text`, `.passed`, and `.evidence` exactly. Do not use `name`, `met`, `details`, or other variants.

---

## metrics.json

Derived execution metrics for one arm. Located at `<arm>/outputs/metrics.json`. The adapter derives this file from the JSONL transcript.

```json
{
  "tool_calls": {
    "Read": 5,
    "Write": 2,
    "Bash": 8,
    "Edit": 1,
    "Glob": 2,
    "Grep": 0
  },
  "total_tool_calls": 18,
  "total_steps": 6,
  "files_created": ["filled_form.pdf", "field_values.json"],
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

**Fields:**

- `tool_calls`: count per tool type.
- `total_tool_calls`: sum of all tool calls.
- `total_steps`: number of started steps, including a failed or timed-out step.
- `files_created`: output files created by the run.
- `errors_encountered`: number of errors observed during execution.
- `output_chars`: total character count of the output files.
- `transcript_chars`: character count of the Markdown transcript.

`output_chars` is a size proxy, not a token count. Token totals come from `timing.json`. The grader copies these metrics into `grading.json`; the benchmark aggregator reads token totals from timing, never from this file.

---

## timing.json

Wall-clock timing and token totals for one arm. Located at `<arm>/timing.json`.

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

**Fields:**

- `total_tokens`: the token total for the run, summed from the harness stream.
- `duration_ms`: wall-clock duration in milliseconds.
- `total_duration_seconds`: the same duration in seconds.

The runner writes this file when the run finishes. Do not reconstruct it later from a notification or from output size. If a harness reports additional timing details, keep them in `run.json` or the adapter transcript; the benchmark contract uses `total_tokens` and `total_duration_seconds`.

---

## benchmark.json

Output from benchmark aggregation. Located at `<iteration>/benchmark.json`, with a human-readable `<iteration>/benchmark.md` beside it.

```json
{
  "metadata": {
    "skill_name": "example-skill",
    "skill_path": "/path/to/example-skill",
    "executor_model": "<model-id>",
    "analyzer_model": "<model-id>",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1, 2, 3],
    "runs_per_configuration": 1
  },
  "runs": [
    {
      "eval_id": 1,
      "eval_name": "invoice-totals",
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 0.85,
        "passed": 6,
        "failed": 1,
        "total": 7,
        "time_seconds": 42.5,
        "tokens": 3800,
        "tool_calls": 18,
        "errors": 0
      },
      "expectations": [
        {"text": "The output includes X", "passed": true, "evidence": "Found in the output file"}
      ],
      "notes": [
        "Used 2023 data, which may be stale"
      ]
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.8, "max": 0.9},
      "time_seconds": {"mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0},
      "tokens": {"mean": 3800, "stddev": 400, "min": 3200, "max": 4100}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45},
      "time_seconds": {"mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0},
      "tokens": {"mean": 2100, "stddev": 300, "min": 1800, "max": 2500}
    },
    "delta": {
      "pass_rate": "+0.50",
      "time_seconds": "+13.0",
      "tokens": "+1700"
    }
  },
  "notes": [
    "Assertion 'Output is a PDF file' passes 100% in every configuration and may not differentiate skill value",
    "The skill adds 13 seconds on average but improves pass rate by 50%"
  ]
}
```

**Fields:**

- `metadata`: information about the benchmark run.
  - `skill_name`: the name of the skill.
  - `skill_path`: the path to the skill under test.
  - `executor_model`: optional model ID used for the eval arms.
  - `analyzer_model`: optional model ID used for the analysis pass.
  - `timestamp`: when the benchmark was generated.
  - `evals_run`: the eval IDs included in the benchmark.
  - `runs_per_configuration`: the number of runs per configuration per eval, derived from the data. The canonical batch writes one run per arm per eval, so this is usually 1.
- `runs[]`: individual run results.
  - `eval_id`: the eval's identifier.
  - `eval_name`: read from `<iteration>/eval-<ID>/eval_metadata.json`; do not derive it from the directory name.
  - `configuration`: `with_skill`, `without_skill`, or `old_skill`. Use this exact key and these exact values; the review page groups on them.
  - `run_number`: the run number for that eval and configuration, starting at 1.
  - `result`: `pass_rate`, `passed`, `failed`, `total`, `time_seconds`, `tokens`, `tool_calls`, and `errors`.
    - `time_seconds` comes from `timing.total_duration_seconds`.
    - `tokens` comes from `timing.total_tokens`, never from `output_chars`.
  - `expectations`: the graded expectations copied from `grading.json`.
  - `notes`: optional user-notes observations for this run.
- `run_summary`: statistical aggregates per configuration present in the benchmark.
  - `with_skill`: requires `pass_rate`, `time_seconds`, and `tokens` objects, each with `mean`, `stddev`, `min`, and `max`.
  - The baseline key is `without_skill` or `old_skill`. An iteration uses one or the other, never both.
  - `delta`: differences between `with_skill` and the baseline, written as signed strings. The delta is calculated from the arm names, not from directory order. A positive `pass_rate` delta means the skill improved results; a negative `time_seconds` or `tokens` delta means the skill was faster or cheaper.
- `notes`: freeform observations from the benchmark analysis pass, as a list of strings.

---

## comparison.json

Output from the blind comparator. Located at `<eval>/comparison.json`. If an eval has more than one comparison, use `comparison-<N>.json`. When comparing outputs from different iterations, store the file under the newer iteration's eval directory.

```json
{
  "winner": "A",
  "reasoning": "Output A provides a complete solution with proper formatting and all required fields. Output B is missing the date field and has formatting inconsistencies.",
  "rubric": {
    "A": {
      "content": {
        "correctness": 5,
        "completeness": 5,
        "accuracy": 4
      },
      "structure": {
        "organization": 4,
        "formatting": 5,
        "usability": 4
      },
      "content_score": 4.7,
      "structure_score": 4.3,
      "overall_score": 9.0
    },
    "B": {
      "content": {
        "correctness": 3,
        "completeness": 2,
        "accuracy": 3
      },
      "structure": {
        "organization": 3,
        "formatting": 2,
        "usability": 3
      },
      "content_score": 2.7,
      "structure_score": 2.7,
      "overall_score": 5.4
    }
  },
  "output_quality": {
    "A": {
      "score": 9.0,
      "strengths": ["Complete solution", "Well-formatted", "All fields present"],
      "weaknesses": ["Minor style inconsistency in the header"]
    },
    "B": {
      "score": 5.4,
      "strengths": ["Readable output", "Correct basic structure"],
      "weaknesses": ["Missing date field", "Formatting inconsistencies", "Partial data extraction"]
    }
  },
  "expectation_results": {
    "A": {
      "passed": 4,
      "total": 5,
      "pass_rate": 0.8,
      "details": [
        {"text": "Output includes name", "passed": true}
      ]
    },
    "B": {
      "passed": 3,
      "total": 5,
      "pass_rate": 0.6,
      "details": [
        {"text": "Output includes name", "passed": true}
      ]
    }
  }
}
```

**Fields:**

- `winner`: `"A"`, `"B"`, or `"TIE"`.
- `reasoning`: why the winner was chosen, or why the result is a tie.
- `rubric`: structured rubric scores for each output.
  - `content`: correctness, completeness, and accuracy scores from 1 to 5.
  - `structure`: organization, formatting, and usability scores from 1 to 5.
  - `content_score`, `structure_score`: averages of the criteria.
  - `overall_score`: the combined score scaled to 1–10.
- `output_quality`: summary strengths and weaknesses for each output.
- `expectation_results`: present only when expectations were supplied. It contains `passed`, `total`, `pass_rate`, and `details` for A and B. Each `details` entry has `text` and `passed`.

`expectation_results` is intentionally kept as the comparison's own verdict. Comparison details do not carry `evidence`; the grader's `grading.json` is the evidence record.

---

## analysis.json

Output from the post-hoc analyzer after a blind comparison. Located at `<eval>/analysis.json`.

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path/to/winner/skill",
    "loser_skill": "path/to/loser/skill",
    "comparator_reasoning": "Brief summary of why the comparator chose the winner"
  },
  "winner_strengths": [
    "Clear step-by-step instructions for handling multi-page documents",
    "Included a validation script that caught formatting errors"
  ],
  "loser_weaknesses": [
    "Vague instruction 'process the document appropriately' led to inconsistent behavior",
    "No script for validation, so the agent had to improvise"
  ],
  "instruction_following": {
    "winner": {
      "score": 9,
      "issues": ["Minor: skipped an optional logging step"]
    },
    "loser": {
      "score": 6,
      "issues": [
        "Did not use the skill's formatting template",
        "Invented its own approach instead of following step 3"
      ]
    }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "Replace 'process the document appropriately' with explicit steps",
      "expected_impact": "Would eliminate ambiguity that caused inconsistent behavior"
    }
  ],
  "transcript_insights": {
    "winner_execution_pattern": "Read skill -> Followed the five-step process -> Used the validation script",
    "loser_execution_pattern": "Read skill -> Unclear on the approach -> Tried three different methods"
  }
}
```

**Fields:**

- `comparison_summary`: the winner, skill paths, and the comparator's reasoning.
- `winner_strengths`: what the winning skill did well.
- `loser_weaknesses`: what held the losing skill back.
- `instruction_following`: a 1–10 score and issue list for each side.
- `improvement_suggestions`: prioritized changes with `priority`, `category`, `suggestion`, and `expected_impact`.
  - Categories: `instructions`, `tools`, `examples`, `error_handling`, `structure`, `references`.
  - Priorities: `high`, `medium`, `low`.
- `transcript_insights`: the execution pattern observed on each side.

The benchmark analysis pass uses a different output: a JSON array of strings. The calling agent places those strings in `benchmark.json` under `notes`.

A comparison that ends in a tie has no `analysis.json`; stop after the comparison. There is no version-history file. Iterations and the stable `eval-<ID>-<arm>` run identity carry progress across the loop.
