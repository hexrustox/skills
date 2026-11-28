# Description-Trigger Testing

`description-trigger` tests whether a skill's description makes OpenCode load the skill at the right moments. Each skill gets one case file.

## Terms

| Term | Meaning |
| --- | --- |
| **Case** | One prompt and its expected trigger outcome. |
| **Expected trigger** | The case's `expect` value: `true` when the prompt should load the skill, `false` when it should not. |
| **Actual trigger** | Whether the probe loaded the target skill: `true` after a completed target-skill call, `false` after a clean run with no target call, undecided otherwise. |
| **Decisive run** | A probe whose actual trigger is `true` or `false`, not undecided. |
| **Repeat** | One execution of a case's probe; `--repeats N` runs each case N times. |
| **Probe** | One disposable OpenCode run in a fresh temporary project containing only the target skill, with every agent action denied except loading that skill. |
| **Authoring workflow** | Write and validate one skill's case file. It never evaluates. |
| **Evaluation workflow** | Run probes against a validated case file. It never edits cases or the skill description. |
| **PASS** | Every repeat is decisive and every actual trigger matches the expected trigger. |
| **FAIL** | Every repeat is decisive and at least one actual trigger differs from the expected trigger. |
| **ERROR** | At least one repeat is undecided. ERROR takes precedence over FAIL. |

## Case file

One JSON file per skill at `tests/<skill-id>/description-trigger.json`; `<skill-id>` is the skill directory basename, not the frontmatter `name`. The repo-level `tests/` directory is reserved for test data; create the skill's directory when writing its first case file. The tool's Python tests live in `tools/description-trigger/tests/`.

For `skills/<skill-id>`, `validate` and `evaluate` derive that path by default. `--cases PATH` points at any other file, including for a synthetic or out-of-tree skill. A missing derived file exits 2 with the computed path and a hint to pass `--cases`.

The file is an object keyed by case ID. Each case has exactly `prompt` and `expect`:

```json
{
  "direct-invoice-text": {
    "prompt": "Pull the text out of the scanned invoice in this folder.",
    "expect": true
  },
  "summarize-pdf-argument": {
    "prompt": "Summarize the argument in this PDF.",
    "expect": false
  }
}
```

- Case IDs are lowercase kebab-case.
- `prompt` is a non-empty string; `expect` is a JSON boolean, not `"true"` or `"false"`.
- At least three cases have `expect: true` and at least three have `expect: false`.
- Unknown fields, missing fields, duplicate JSON keys, and wrong types are rejected.
- The skill directory must exist, use a kebab-case name, contain `SKILL.md`, have a non-empty description, and remain visible to model invocation. `disable-model-invocation: true` and `metadata.opencode/autoinvoke: false` are rejected. Validation is a narrow frontmatter scan and never launches OpenCode.

## Authoring workflow

Author cases for one skill at a time. Do not edit another skill's cases in the same session.

1. **Scope the skill.** Read `skills/<skill-id>/SKILL.md` and its description. Read the descriptions of neighbouring skills in `skills/*/SKILL.md` to find the nearest alternatives. Done when you can state the target's promise and name the neighbours a prompt might confuse it with.
2. **Write the cases.** Create `tests/<skill-id>/description-trigger.json` with at least three positive and three negative cases, covering every category below. Done when each category has a case and the counts pass.
3. **Validate and stop.** Run `description-trigger validate skills/<skill-id>`. A pass prints the skill, case file, and positive/negative counts and exits 0. Fix the reported problem and rerun on exit 2. Done when validation exits 0 and you have stopped without running `evaluate` in this session.

### Prompt categories

| `expect` | Category | The prompt should... |
| --- | --- | --- |
| `true` | Direct request | name the task or artifact the skill handles. |
| `true` | Indirect request | describe the goal or symptom without naming the task directly. |
| `true` | Near-miss phrasing | resemble a neighbour's task but still match this skill's promise. |
| `false` | Adjacent task | belong to a neighbouring skill, not this one. |
| `false` | Out-of-scope task sharing keywords | use this skill's vocabulary for a different job. |
| `false` | Too-vague request | carry too little signal for any skill to claim it. |

### Prompt rules

- Write a single-turn request a user could send as-is; include the context and data the prompt needs.
- Keep every prompt self-contained: no fixture files, repository paths, conversation history, or follow-up turns.
- Test description triggering, not explicit invocation: do not write "use the <skill> skill", "load <skill>", or name the skill as a command.
- Test one decision per prompt.

### No description edits

Do not edit `SKILL.md`, its description, or other skill files while authoring cases. If the description needs work, record the change and stop; changing the description is a separate task from authoring its cases.

### Authoring checklist

- [ ] One skill's case file is written at `tests/<skill-id>/description-trigger.json`.
- [ ] At least three `expect: true` and three `expect: false` cases.
- [ ] Direct, indirect, and near-miss positives; adjacent, keyword-sharing out-of-scope, and too-vague negatives.
- [ ] Case IDs are lowercase kebab-case; each case has exactly `prompt` and `expect`; `expect` is a JSON boolean.
- [ ] Every prompt is self-contained, single-turn, and does not explicitly invoke the skill.
- [ ] No skill or description edits were made.
- [ ] `description-trigger validate skills/<skill-id>` exited 0.
- [ ] The session ended without running `evaluate`.

## Evaluation workflow

Run evaluation in a session that did not author or edit the cases or the description. If this session did, stop and start a new one.

1. **Choose the model.** `--model` is required; there is no default. Pass `provider/model` or `provider/model#variant`. Results apply only to that model, and the report records it. Done when you can name the model string you will pass.
2. **Validate first.** Run `description-trigger validate skills/<skill-id>` and confirm exit 0. `evaluate` repeats this preflight and exits 2 without launching probes when the skill or case file is invalid. Done when validation passes.
3. **Run the probes.** From the repository root:

   ```sh
   description-trigger evaluate skills/<skill-id> --model <provider/model[#variant]>
   ```

   Options: `--repeats N` (default 1), `--jobs N` (parallel probes, default 1), `--timeout SECONDS` (default 300), `--keep` (keep passing probe directories), `--standalone` (avoid a shared background OpenCode service), and `--cases PATH` (default derived case path). Done when every probe has finished and the report is printed.
4. **Interpret the results.** Read every PASS, FAIL, and ERROR with the rules below. Done when every case has a state and every FAIL or ERROR has its actual value and diagnostic.
5. **Report and stop.** Report the run summary and any kept probe paths. If the description needs a change, record it as a separate task. Do not edit the cases or the description in this session. Done when the report is delivered and the session has made no case or description edits.

### Reading a case result

A mismatch is under-triggering when `expected=true actual=false` and over-triggering when `expected=false actual=true`. ERROR means the actual trigger is unknown, not `false`.

An actual trigger is `true` when a target-skill call reaches completed status, even if OpenCode later times out or exits non-zero; the report adds a note. It is `false` only when the run finishes cleanly with no target-skill call. A target call that errors, a run-level error, a malformed transcript with no decisive target event, or a timeout or non-zero exit before a target call completes is ERROR. Calls to other skills are diagnostics and never decide the result.

With `--repeats`, actual values are listed in run order and `matched=N/M` shows how many matched.

### Report fields and exit codes

Each case line shows state, case ID, expected trigger, actual trigger (`ERROR` when undecided), optional `matched=N/M`, and duration. Each kept probe's directory, transcript, and stderr are printed with any note, error, or diagnostic. Passing cases' probe directories are deleted unless `--keep`; failing and errored cases keep every repeat's directory. The summary prints passed, failed, and error counts; cases; runs; total duration; skill; case file; model; and OpenCode version.

| Exit | Meaning |
| --- | --- |
| 0 | Every case passed. |
| 1 | At least one case failed and none errored. |
| 2 | At least one case errored, or the invocation, skill, or case file is invalid. |

`validate` exits 0 on success and 2 on invalid input; it never launches OpenCode.

## Commands

Install the tool as an editable uv tool before the first session; the install command, reinstall conditions, development fallback, and tool test/verify commands live in [`tools/description-trigger/AGENTS.md`](../../tools/description-trigger/AGENTS.md).

```sh
# Authoring session: validate and stop.
description-trigger validate skills/<skill-id>

# Validation with an explicit case path.
description-trigger validate skills/<skill-id> --cases <path>

# Evaluation session: --model is required.
description-trigger evaluate skills/<skill-id> --model <provider/model[#variant]>
```

## Limits

- Tests description triggering only. It does not test skill execution, supporting files, tool use after loading, or output quality.
- Tests one skill in isolation. Only the target skill is installed, so it cannot measure competition or selection among neighbouring skills.
- Results are model-specific. A pass or fail applies to the model passed with `--model`, not to every model.
- Prompts are single-turn and self-contained; there are no fixture files, multi-turn conversations, or repository setup.
- One skill per invocation. There is no repository-wide or `--all` mode.
- The probe denies all actions except loading the target skill, but global OpenCode configuration, instructions, and plugins can still influence a run.
- Frontmatter validation is a narrow scan; OpenCode remains the loader.
- Timeouts terminate the probe (SIGTERM, then SIGKILL after a short grace). Process termination targets Linux, the repository's environment. There is no step cap.
- The tool reports results; it does not recommend or apply description changes.
- Coverage is per authored case file. Skills without a case file are not audited, and renamed skills are not detected.
