# Post-hoc analyzer instructions

Explain why one output won a blind comparison, and separately surface patterns in benchmark results. Run these instructions in a fresh context.

The two parts are independent jobs; use only the part the caller asks for. The skill's `references/schemas.md` holds the full contract; this file repeats the output shape so a fresh context can analyze without another read.

## Part 1: Analyze a blind comparison

### Role

After a blind comparator chooses a winner, unblind the result by examining the skills and transcripts. Extract actionable insight: what made the winner better, and how can the loser be improved?

If the comparison is a tie, stop and report the tie. There is no winner to explain and no losing version to improve.

### Inputs

The calling agent supplies:

- **winner**: `"A"` or `"B"` from the blind comparison
- **winner_skill_path**: path to the skill that produced the winning output
- **winner_transcript_path**: the winning arm's `transcript.md`
- **loser_skill_path**: path to the skill that produced the losing output
- **loser_transcript_path**: the losing arm's `transcript.md`
- **comparison_result_path**: path to the comparator's `comparison.json`
- **output_path**: where to write `analysis.json`, normally `<eval>/analysis.json`

The caller unblinds the result and supplies the real skill and transcript paths. Do not infer them from the comparison file.

### Process

#### Step 1: Read the comparison result

1. Read the comparator's output at `comparison_result_path`.
2. Note the winning side, the reasoning, and the scores.
3. Understand what the comparator valued in the winning output.

#### Step 2: Read both skills

1. Read the winner's `SKILL.md` and its key referenced files.
2. Read the loser's `SKILL.md` and its key referenced files.
3. Identify structural differences:
   - clarity and specificity of instructions;
   - script and tool usage patterns;
   - example coverage;
   - edge-case handling.

#### Step 3: Read both transcripts

1. Read the winner's transcript.
2. Read the loser's transcript.
3. Compare execution patterns:
   - how closely did each run follow its skill's instructions?
   - which tools were used differently?
   - where did the loser diverge from optimal behavior?
   - did either run hit errors or make recovery attempts?

#### Step 4: Analyze instruction following

For each transcript, evaluate:

- Did the agent follow the skill's explicit instructions?
- Did it use the skill's provided tools and scripts?
- Were there missed opportunities to use skill content?
- Did it add unnecessary steps that the skill did not ask for?

Score instruction following from 1 to 10 and note specific issues.

#### Step 5: Identify the winner's strengths

Determine what made the winner better:

- clearer instructions that led to better behavior;
- better scripts or tools that produced better output;
- more comprehensive examples that guided edge cases;
- better error-handling guidance.

Be specific. Quote from the skills and transcripts where relevant.

#### Step 6: Identify the loser's weaknesses

Determine what held the loser back:

- ambiguous instructions that led to suboptimal choices;
- missing tools or scripts that forced workarounds;
- gaps in edge-case coverage;
- poor error handling that caused failures.

#### Step 7: Generate improvement suggestions

Produce actionable suggestions for improving the losing skill:

- specific instruction changes;
- tools or scripts to add or modify;
- examples to include;
- edge cases to address.

Prioritize by impact. Focus on changes that would have changed the outcome.

#### Step 8: Write the analysis result

Save the JSON object to `output_path`. If no output path is supplied, return it as your final message.

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
    "Included a validation script that caught formatting errors",
    "Explicit guidance on fallback behavior when OCR fails"
  ],
  "loser_weaknesses": [
    "Vague instruction 'process the document appropriately' led to inconsistent behavior",
    "No validation script, so the agent improvised and made errors",
    "No guidance on OCR failure, so the agent gave up instead of trying alternatives"
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
        "Invented its own approach instead of following step 3",
        "Missed the 'always validate output' instruction"
      ]
    }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "Replace 'process the document appropriately' with explicit steps: 1) extract text, 2) identify sections, 3) format per template",
      "expected_impact": "Would eliminate ambiguity that caused inconsistent behavior"
    },
    {
      "priority": "high",
      "category": "tools",
      "suggestion": "Add a validate_output.py script similar to the winner's validation approach",
      "expected_impact": "Would catch formatting errors before the final output"
    },
    {
      "priority": "medium",
      "category": "error_handling",
      "suggestion": "Add fallback instructions: 'If OCR fails, try a different resolution, preprocess the image, then fall back to manual extraction'",
      "expected_impact": "Would prevent early failure on difficult documents"
    }
  ],
  "transcript_insights": {
    "winner_execution_pattern": "Read skill -> Followed the five-step process -> Used the validation script -> Fixed two issues -> Produced output",
    "loser_execution_pattern": "Read skill -> Unclear on the approach -> Tried three different methods -> No validation -> Output had errors"
  }
}
```

### Field descriptions

- **comparison_summary**: the winner, the paths to both skills, and a short reason from the comparator.
- **winner_strengths**: what the winning skill did well.
- **loser_weaknesses**: what held the losing skill back.
- **instruction_following**: a 1–10 score and issue list for each side.
- **improvement_suggestions**: prioritized changes, each with a category, suggestion, and expected impact.
- **transcript_insights**: the execution pattern observed on each side.

### Suggestion categories

| Category | Description |
| --- | --- |
| `instructions` | Changes to the skill's prose instructions |
| `tools` | Scripts, templates, or utilities to add or modify |
| `examples` | Example inputs or outputs to include |
| `error_handling` | Guidance for handling failures |
| `structure` | Reorganization of skill content |
| `references` | External docs or resources to add |

### Priority levels

- **high**: would likely change the outcome of this comparison.
- **medium**: would improve quality but may not change win or loss.
- **low**: nice to have, marginal improvement.

### Guidelines

- **Be specific**: quote from the skills and transcripts rather than saying "instructions were unclear".
- **Be actionable**: suggestions should be concrete changes, not vague advice.
- **Focus on skill improvements**: improve the losing skill, not critique the agent.
- **Prioritize by impact**: which changes would most likely have changed the outcome?
- **Consider causation**: did the skill weakness actually cause the worse output, or is it incidental?
- **Stay objective**: analyze what happened; do not editorialize.
- **Think about generalization**: would this improvement help on other evals too?

---

## Part 2: Analyze benchmark results

When analyzing benchmark results, surface patterns and anomalies across multiple runs. Do not suggest skill improvements here; that belongs to the comparison analysis or the improvement loop.

### Role

Review all benchmark run results and produce freeform notes that help the user understand skill performance. Focus on patterns that the aggregate metrics hide.

### Inputs

The calling agent supplies:

- **benchmark_data_path**: path to `benchmark.json` with the run results
- **skill_path**: path to the skill being benchmarked
- **output_path**: where to write the notes as a JSON array of strings

### Process

#### Step 1: Read the benchmark data

1. Read `benchmark.json`.
2. Note the configurations present: `with_skill` and either `without_skill` or `old_skill`.
3. Understand the `run_summary` aggregates that are already calculated.

An iteration never mixes `without_skill` and `old_skill`. If both appear, flag the data as inconsistent.

#### Step 2: Analyze per-expectation patterns

For each expectation across all runs, check whether it:

- **always passes** in every configuration (it may not differentiate skill value);
- **always fails** in every configuration (it may be broken or beyond current capability);
- **passes with `with_skill` but fails in the baseline** (the skill adds value here);
- **fails with `with_skill` but passes in the baseline** (the skill may be hurting);
- **varies widely** across runs (a flaky expectation or non-deterministic behavior).

#### Step 3: Analyze cross-eval patterns

Look for patterns across evals:

- Are certain eval types consistently harder or easier?
- Do some evals show high variance while others are stable?
- Are there surprising results that contradict expectations?

#### Step 4: Analyze metric patterns

Look at `time_seconds`, `tokens`, and `tool_calls`:

- Does the skill significantly increase execution time?
- Is resource usage highly variable?
- Are there outlier runs that skew the aggregates?

#### Step 5: Generate notes

Write freeform observations as a list of strings. Each note should:

- state a specific observation;
- be grounded in the data, not speculation;
- help the user understand something the aggregate metrics do not show.

Examples:

- "Assertion 'Output is a PDF file' passes 100% in every configuration and may not differentiate skill value"
- "Eval 3 shows high variance (50% ± 40%); run 2 had an unusual failure that may be flaky"
- "Baseline runs consistently fail on table-extraction expectations (0% pass rate)"
- "The skill adds 13 seconds on average but improves pass rate by 50%"
- "Token usage is 80% higher with the skill, primarily from script output parsing"

#### Step 6: Write the notes

Save the notes to `output_path` as a JSON array of strings. If no output path is supplied, return the array as your final message.

```json
[
  "Assertion 'Output is a PDF file' passes 100% in every configuration and may not differentiate skill value",
  "Eval 3 shows high variance (50% ± 40%); run 2 had an unusual failure",
  "Baseline runs consistently fail on table-extraction expectations",
  "The skill adds 13 seconds on average but improves pass rate by 50%"
]
```

The calling agent puts these strings in `benchmark.json` under `notes`.

### Guidelines

**Do:**

- report what you observe in the data;
- be specific about which evals, expectations, or runs you mean;
- note patterns that aggregate metrics would hide;
- provide context that helps interpret the numbers.

**Do not:**

- suggest improvements to the skill;
- make subjective quality judgments about the outputs;
- speculate about causes without evidence;
- repeat information already present in the `run_summary` aggregates.
