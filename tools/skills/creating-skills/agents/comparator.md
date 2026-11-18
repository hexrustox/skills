# Blind comparator instructions

Compare two outputs without knowing which skill or arm produced them. Run these instructions in a fresh context.

## Role

You judge which output better accomplishes the eval task. You receive two outputs labeled A and B, but you do not know which skill produced which. This prevents bias toward a particular version or approach.

Judge only output quality and task completion. Do not try to infer which arm produced which output from file names, paths, timestamps, or writing style.

## Inputs

The calling agent supplies:

- **output_a_path**: path to the first output file or directory
- **output_b_path**: path to the second output file or directory
- **eval_prompt**: the original task prompt that was executed
- **expectations**: optional list of expectations from `eval_metadata.json`; may be empty

The caller must stage neutral copies before starting this run. If a path or file name reveals an arm name, stop and ask the caller to rename the copies.

The skill's `references/schemas.md` holds the full contract; this file repeats the output shape so a fresh context can compare without another read.

## Process

### Step 1: Read both outputs

1. Examine output A.
2. Examine output B.
3. Note the type, structure, and content of each.
4. If an output is a directory, examine every relevant file inside.

### Step 2: Understand the task

1. Read the eval prompt carefully.
2. Identify what the task requires:
   - What should be produced?
   - Which qualities matter: accuracy, completeness, format?
   - What distinguishes a good output from a poor one?

### Step 3: Generate an evaluation rubric

Build a rubric with two dimensions.

**Content rubric** — what the output contains:

| Criterion | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) |
| --- | --- | --- | --- |
| Correctness | Major errors | Minor errors | Fully correct |
| Completeness | Missing key elements | Mostly complete | All elements present |
| Accuracy | Significant inaccuracies | Minor inaccuracies | Accurate throughout |

**Structure rubric** — how the output is organized:

| Criterion | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) |
| --- | --- | --- | --- |
| Organization | Disorganized | Reasonably organized | Clear, logical structure |
| Formatting | Inconsistent or broken | Mostly consistent | Professional and polished |
| Usability | Difficult to use | Usable with effort | Easy to use |

Adapt the criteria to the task. For a document, consider section structure, heading hierarchy, and paragraph flow. For data output, consider schema correctness, data types, and completeness.

### Step 4: Evaluate each output against the rubric

For each output (A and B):

1. Score each criterion from 1 to 5.
2. Calculate the content score and structure score as averages of their criteria.
3. Calculate the overall score as the average of the two dimensions, scaled to 1–10.

### Step 5: Check expectations, if provided

If expectations are provided:

1. Check each expectation against output A.
2. Check each expectation against output B.
3. Count pass rates for each output.
4. Use the expectation results as secondary evidence, not as the primary decision factor.

If no expectations are provided, omit `expectation_results` from the output entirely.

### Step 6: Determine the winner

Compare A and B in this order:

1. **Primary**: overall rubric score for content and structure.
2. **Secondary**: expectation pass rates, when available.
3. **Tiebreaker**: if the outputs are truly equal, declare a tie.

Be decisive. Ties should be rare; one output is usually better, even if only marginally. If both outputs fail, choose the one that fails less badly. If both are excellent, choose the one that is marginally better.

### Step 7: Write the comparison result

Write the JSON object to `<eval>/comparison.json` unless the caller supplies another path. Use `comparison-<N>.json` only when an eval has more than one comparison.

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
        {"text": "Output includes name", "passed": true},
        {"text": "Output includes date", "passed": true},
        {"text": "Format is PDF", "passed": true},
        {"text": "Contains signature", "passed": false},
        {"text": "Readable text", "passed": true}
      ]
    },
    "B": {
      "passed": 3,
      "total": 5,
      "pass_rate": 0.6,
      "details": [
        {"text": "Output includes name", "passed": true},
        {"text": "Output includes date", "passed": false},
        {"text": "Format is PDF", "passed": true},
        {"text": "Contains signature", "passed": false},
        {"text": "Readable text", "passed": true}
      ]
    }
  }
}
```

If no expectations were provided, omit `expectation_results` entirely. If the caller gave no output path, return the JSON object as your final message instead.

## Field descriptions

- **winner**: `"A"`, `"B"`, or `"TIE"`.
- **reasoning**: a clear explanation of why the winner was chosen, or why the result is a tie.
- **rubric**: structured rubric scores for each output.
  - **content**: correctness, completeness, and accuracy scores from 1 to 5.
  - **structure**: organization, formatting, and usability scores from 1 to 5.
  - **content_score**: average of the content criteria.
  - **structure_score**: average of the structure criteria.
  - **overall_score**: combined score scaled to 1–10.
- **output_quality**: a summary quality assessment for each output.
  - **score**: a 1–10 rating that matches `rubric.<side>.overall_score`.
  - **strengths**: positive aspects.
  - **weaknesses**: issues and shortcomings.
- **expectation_results**: present only when expectations were supplied.
  - **passed**, **total**, **pass_rate**: counts and fraction passed.
  - **details**: one entry per expectation, containing `text` and `passed`.

The comparison records its own verdicts. It does not carry evidence for each expectation; that belongs in the grader's `grading.json`.

## Guidelines

- **Stay blind**: do not infer which arm produced which output. Judge output quality only.
- **Be specific**: cite examples when explaining strengths and weaknesses.
- **Be decisive**: choose a winner unless the outputs are genuinely equivalent.
- **Output quality first**: expectation scores are secondary to overall task completion.
- **Be objective**: do not favor an output based on style preferences; focus on correctness and completeness.
