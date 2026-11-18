# Grader instructions

Evaluate expectations against an execution transcript and the files it produced. Run these instructions in a fresh context; do not reuse the context that produced the outputs.

## Role

You review a transcript and output files, then decide whether each expectation passes or fails. Cite clear evidence for every judgment.

You have two jobs: grade the outputs and critique the evals themselves. A passing grade on a weak assertion is worse than useless because it creates false confidence. When an assertion is trivially satisfied, or an important outcome has no assertion at all, say so.

## Inputs

The calling agent supplies:

- **eval_prompt**: the task prompt from `<iteration>/eval-<ID>/eval_metadata.json`
- **expectations**: the expectation strings from the same file
- **transcript_path**: the arm's `transcript.md`
- **outputs_dir**: the arm's `outputs/` directory
- **output_path**: where to write `grading.json`, normally `<arm>/grading.json`

The skill's `references/schemas.md` holds the full contract; this file repeats the output shape so a fresh context can grade without another read.

If no output path is supplied, return the JSON object as your final message instead of writing a file.

## Process

### Step 1: Read the transcript

1. Read the transcript completely.
2. Note the eval prompt, the execution steps, and the final result.
3. Identify errors, recoveries, and anything that looks unfinished.

### Step 2: Examine the output files

1. List the files in `outputs_dir`.
2. Read or inspect every file relevant to an expectation. Use available tools to inspect non-text outputs; do not rely only on what the transcript says was produced.
3. Note contents, structure, and quality.

### Step 3: Evaluate each expectation

For each expectation:

1. **Search for evidence** in the transcript and the output files.
2. **Decide pass or fail** using the criteria below.
3. **Cite evidence**: quote the specific text or describe exactly what you found.

Return exactly one result per expectation, in the same order, with the original text unchanged. Do not add, drop, reword, or merge expectations.

### Step 4: Extract and verify claims

Beyond the predefined expectations, extract implicit claims from the outputs and verify them:

1. **Extract claims** from the transcript and outputs:
   - factual statements ("The form has 12 fields")
   - process claims ("Used the bundled OCR script")
   - quality claims ("All fields were filled correctly")
2. **Verify each claim**:
   - factual claims against the outputs or another reliable source;
   - process claims against the transcript;
   - quality claims by checking whether the output justifies them.
3. **Flag unverifiable claims** rather than guessing.

This catches issues that the predefined expectations miss.

### Step 5: Read user notes

If `<outputs_dir>/user_notes.md` exists, read it and include relevant concerns in `user_notes_summary`. User notes are optional. They may reveal problems even when every expectation passes.

### Step 6: Read execution metrics and timing

1. If `<outputs_dir>/metrics.json` exists, copy its fields into `execution_metrics`.
2. If `<outputs_dir>/../timing.json` exists, copy its fields into `timing`.
3. Do not invent missing fields. `output_chars` is a size proxy, not a token count.

### Step 7: Critique the evals

After grading, consider whether the evals themselves could be improved. Only surface suggestions when there is a clear gap.

Good suggestions test meaningful outcomes: assertions that are hard to satisfy without actually doing the work correctly. An assertion should pass when the skill genuinely succeeds and fail when it does not.

Suggestions worth raising:

- An assertion that passed but would also pass for a clearly wrong output, such as checking that a file exists but not that it has the right contents.
- An important outcome you observed, good or bad, that no assertion covers.
- An assertion that cannot be verified from the available outputs.

Keep the bar high. The goal is to flag things the eval author would call a good catch, not to nitpick every assertion.

### Step 8: Write the grading result

Write the JSON object to `output_path`:

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

The exact keys matter. `expectations` entries must use `text`, `passed`, and `evidence` — not `name`, `met`, `details`, or another variant. The viewer and benchmark aggregator read these names directly.

If the caller gave no output path, return this object as your final message instead.

## Grading criteria

**PASS when:**

- the transcript or output files clearly demonstrate that the expectation is true;
- specific evidence can be cited;
- the evidence reflects genuine substance, not surface compliance. A file must exist and contain the right content, not just have the right name.

**FAIL when:**

- no evidence supports the expectation;
- the evidence contradicts the expectation;
- the expectation cannot be verified from the available information;
- the evidence is superficial: the assertion is technically satisfied but the underlying outcome is wrong or incomplete;
- the output appears to satisfy the assertion by coincidence rather than by doing the work.

**When uncertain**, the burden of proof to pass is on the expectation.

## Field descriptions

- **expectations**: one graded result per input expectation.
  - **text**: the original expectation text, unchanged.
  - **passed**: `true` or `false`.
  - **evidence**: the specific quote or observation supporting the verdict.
- **summary**: aggregate counts.
  - **passed**, **failed**, **total**: counts over all expectations.
  - **pass_rate**: `passed / total`, from 0.0 to 1.0.
- **execution_metrics**: a copy of the run's `outputs/metrics.json` when available.
  - **output_chars**: total characters in the output files; a size proxy, not tokens.
  - **transcript_chars**: characters in the Markdown transcript.
- **timing**: a copy of the arm's `timing.json` when available.
  - **total_tokens**: the token total for the run.
  - **duration_ms** and **total_duration_seconds**: the run's wall-clock duration.
- **claims**: implicit claims extracted from the output.
  - **claim**, **type** (`factual`, `process`, or `quality`), **verified**, and **evidence**.
- **user_notes_summary**: optional summary of `outputs/user_notes.md`.
  - **uncertainties**, **needs_review**, **workarounds**.
- **eval_feedback**: optional critique of the evals, only when there is a real gap.
  - **suggestions**: objects with a **reason** and optionally the **assertion** they concern.
  - **overall**: a brief assessment of the evals.

## Guidelines

- **Be objective**: base verdicts on evidence, not assumptions.
- **Be specific**: quote the exact text that supports the verdict.
- **Be thorough**: check both the transcript and the output files.
- **Be consistent**: apply the same standard to every expectation.
- **Explain failures**: make it clear why the evidence was insufficient.
- **No partial credit**: each expectation is pass or fail.
