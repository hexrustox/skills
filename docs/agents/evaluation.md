# Evaluate a skill

Evaluation answers one question: does loading this skill improve an agent's output enough to justify the extra context it costs? A single plausible output does not answer it. This procedure produces evidence: paired runs with and without the skill, graded against assertions, then reviewed by a human for what assertions cannot capture.

Run the static gate first. The loop below measures behavior; it does not replace format and security checks.

## 1. Gate on static checks

```bash
skillevaluator tier1 skills/<path> -o .eval/<skill>/tier1
```

Fix every blocking finding and rerun. A skill that fails the gate is not ready for behavioral evaluation.

## 2. Write test cases

Create `.eval/<skill>/evals.json`. Start with two or three cases: enough to expose a pattern, small enough to iterate on.

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": "top-months",
      "prompt": "I have sales.csv in this folder. Can you find the top 3 months by revenue and chart them?",
      "expected_output": "A bar chart of the top 3 months by revenue, with labeled axes.",
      "files": ["files/sales.csv"]
    }
  ]
}
```

Write prompts that sound like users: file paths, column names, context, casual phrasing. Vary the phrasing and level of detail across cases. Make at least one case a boundary: malformed input, an ambiguous request, or a task the skill almost handles.

`expected_output` describes success for the reviewer. Assertions are the gradable claims and come after the first run. List input files relative to `.eval/<skill>` and copy them into the run's working directory.

## 3. Run each case twice

Store the test cases and artifacts under `.eval/<skill>/`:

```text
.eval/csv-analyzer/
├── evals.json
├── files/
│   └── sales.csv
└── iteration-1/
    └── top-months/
        ├── with_skill/
        │   ├── outputs/
        │   ├── transcript.md
        │   └── grading.json
        └── without_skill/
            └── ...
```

Dispatch each run to a fresh-context subagent. The authoring session already knows the skill and the intended output, so it cannot stand in for a run.

Give the run agent four things: the skill path (or no skill), the prompt, the input files, and the output directory. Withhold the expected output, the assertions, and the comparison purpose. Have it write every produced file under `outputs/`.

For a new skill, the baseline is no skill. For a revision, snapshot the skill before editing, point the baseline at the snapshot, and save its results under `old_skill/` instead of `without_skill/`. This compares the new instructions with the old ones rather than with nothing.

Keep the transcript when the client provides one. Read the transcripts before grading. The with-skill run must show `SKILL.md` being loaded; the baseline must show no such load. If the baseline picked the skill up from the environment, run it from a clean directory or disable the skill, then rerun.

## 4. Grade the outputs

After the first with-skill run, look at the outputs and add assertions to each case. A good assertion is observable from the artifacts alone:

- `The output includes a bar chart image file`
- `The chart shows exactly 3 months`
- `The report recommends at least 3 changes`

Avoid `The output is good` (unverifiable) and `The title is exactly "Top 3 Months by Revenue"` (brittle). Style, design, and usefulness belong to human review in step 6.

Grade every assertion PASS or FAIL with evidence: the file, value, or quoted line that proves it. Put mechanical checks (valid JSON, row counts, dimensions, file existence) in a script; they are more reliable than judgment and reusable across iterations. For the rest, use a fresh grader that receives the outputs and assertions but not the configuration label or your authoring history. A PASS without concrete evidence is a FAIL.

```json
{
  "assertion_results": [
    { "text": "The chart shows exactly 3 months", "passed": true, "evidence": "Bars for March, July, and November" },
    { "text": "Both axes are labeled", "passed": false, "evidence": "Y-axis labeled 'Revenue ($)'; X-axis unlabeled" }
  ],
  "summary": { "passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5 }
}
```

Review the assertions while grading. One that passes in both configurations measures the base model, not the skill. One that fails in both may be unverifiable or too strict. One that flips between runs is flaky. Fix the assertion or the case for the next iteration.

## 5. Aggregate and read the pattern

Write `benchmark.json` with pass rate per configuration, plus the lift:

```json
{
  "run_summary": {
    "with_skill": { "pass_rate": 0.83 },
    "without_skill": { "pass_rate": 0.33 },
    "lift": { "pass_rate": 0.50 }
  }
}
```

With one run per case, report raw counts and lift; standard deviation needs repeated runs. Then classify each assertion:

- **Passes in both configurations:** remove it or replace it with something the base model gets wrong.
- **Fails in both:** fix the assertion or the case. Do not tune the skill to a broken test.
- **Passes only with the skill:** this is the skill's contribution. Name the instructions responsible.
- **Flaky:** rerun the case three times. Persistent variance points to ambiguous instructions or a flaky test, not a bad skill.

## 6. Get human review

Assertions only test what you thought to assert. Before changing the skill, give the reviewer a compact packet: the prompt, both outputs, the grades, transcript paths, and your specific doubts. Ask about concrete qualities ("What is missing from this report?") rather than general impressions. Record the answer in `feedback.json`, keyed by eval id; an empty string means the case was acceptable.

```json
{ "top-months": "Months are alphabetical; they should be chronological." }
```

Wait for the review before iterating. If no reviewer is available, mark the iteration provisional and say so in the final report.

## 7. Iterate

Start `iteration-N+1`. Give a fresh LLM the failed assertions, `feedback.json`, the transcripts, and the current `SKILL.md`, and ask for changes that generalize. Apply them, rerun `skillevaluator tier1`, and rerun every case. When two versions are close, grade blind: present outputs labeled A and B without saying which skill produced them.

Guidelines for the changes:

- Fix the underlying instruction, not the example. Adding the literal failed prompt is overfitting.
- Keep the skill lean. Remove instructions that produced no useful work; fewer, better instructions beat exhaustive rules.
- Explain the why so the model applies the instruction beyond the test case.
- Move work that every run repeats into `scripts/`.

Stop when all assertions pass and feedback is empty, or when two consecutive iterations show no meaningful lift. Report the final lift and the remaining failures.

## Completion checklist

An evaluation is done when:

- `skillevaluator tier1` passes.
- The eval suite (`.eval/<skill>/evals.json` and its input files) and iteration artifacts are under `.eval/<skill>/`.
- Every case ran with and without the skill (or the old skill) in fresh contexts.
- Transcripts confirm the skill loaded only in the with-skill runs.
- Every assertion has an evidence-backed pass or fail.
- `benchmark.json` and `feedback.json` exist under `.eval/<skill>/iteration-N/`.
- The skill changes address general causes rather than the test cases.
- The final report states the lift, its cost, and anything the human still dislikes.
