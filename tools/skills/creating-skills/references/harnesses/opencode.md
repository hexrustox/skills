# OpenCode harness adapter

The adapter in `scripts/adapters/opencode.py` runs fresh agents through OpenCode's non-interactive CLI.

## Contract

The adapter implements the `Harness` protocol in `scripts/harness.py` and returns that module's normalized `RunResult` and `TriggerResult` values.

Select it by name:

```python
from scripts.adapters import get_harness

harness = get_harness("opencode")
```

## Scope preparation

The adapter creates a temporary project under the system temp directory, outside the repository. Each requested skill is copied into `<project>/.opencode/skills/<skill-id>/`, preserving references, scripts, and assets. The skill ID is the directory name, because OpenCode derives skill IDs from paths rather than frontmatter.

The project config denies every skill and then allows only the requested IDs:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permissions": [
    { "action": "skill", "resource": "*", "effect": "deny" },
    { "action": "skill", "resource": "example-skill", "effect": "allow" }
  ],
  "agents": {
    "creating-skills-no-tools": {
      "description": "Answer without using tools.",
      "mode": "primary",
      "system": "Answer the user's request directly without using tools.",
      "permissions": [{ "action": "*", "resource": "*", "effect": "deny" }]
    }
  }
}
```

A no-skill scope keeps the deny-all rule and leaves `.opencode/skills` empty. This hides skills from global config, compatibility directories, and explicit skill sources rather than relying on those sources being absent; OpenCode has no per-project switch that removes every ambient source. It is the permission rule, not the empty project, that guarantees the scope contains exactly the requested skill.

## Invocation

Normal runs use:

```text
opencode [--standalone] run --format json --agent build --auto [--model provider/model] [--file /absolute/input]
```

- `--agent build` selects the normal coding agent.
- `--auto` approves permissions that are not explicitly denied. The skill deny rules remain enforced.
- `--model` is omitted unless the caller supplies one, so the configured default model is used.
- `--standalone` is optional and gives the run a private server instead of the shared background service.
- `--file` attaches each optional input file. Relative paths resolve against the process running the adapter, so pass absolute paths.
- The prompt is written to stdin, so long prompts are not limited by argument length.
- No `--continue` or `--session` is passed, so every call starts a fresh session.

No-tools completion mode uses the generated `creating-skills-no-tools` primary agent. Its deny-all permission rule prevents tool use while still allowing a text response. This mode is for description optimization and other completion-only calls.

The subprocess runs with the scope as both its working directory and its `PWD`. OpenCode 2.2.1 resolves its project root from `PWD` before falling back to the process working directory, so setting only `cwd` is not enough. The adapter also removes `OPENCODE_CONFIG_CONTENT` from the child environment: that source loads after project configuration and could re-enable skills or override the deny rules. Provider, model, and authentication settings should come from the global config or an explicit `--model`, not from parent-supplied config content.

A timeout kills the process and returns the partial run with `timed_out=True` and a non-zero exit code.

## JSONL events

`--format json` writes one JSON object per line. The adapter expects these event types:

| Event | Fields read | Normalized into |
| --- | --- | --- |
| `text` | `part.text` | assistant text |
| `tool_use` | `part.tool`, `part.state.input`, `part.state.output`, `part.state.status`, `part.state.error` | loaded skill IDs, tool counts, errors, Markdown transcript |
| `step_start` | event type only | step count, Markdown step headings |
| `step_finish` | `part.tokens.{input,output,reasoning,cache.read,cache.write}` | token totals |
| `error` | `error.message` | error count, Markdown transcript |

A minimal stream:

```jsonl
{"type":"step_start","timestamp":1,"sessionID":"ses_test","part":{"type":"step-start"}}
{"type":"text","timestamp":2,"sessionID":"ses_test","part":{"type":"text","text":"I will load the skill."}}
{"type":"tool_use","timestamp":3,"sessionID":"ses_test","part":{"type":"tool","tool":"skill","state":{"status":"completed","input":{"id":"example-skill"},"output":"Loaded example-skill"}}}
{"type":"step_finish","timestamp":4,"sessionID":"ses_test","part":{"type":"step-finish","tokens":{"input":100,"output":20,"reasoning":5,"cache":{"read":7,"write":3}}}}
```

Lines that are not JSON objects are preserved in the raw transcript but ignored during normalization. The raw stdout is always saved as the JSONL transcript, including partial output from a failed or timed-out run.

## Normalization

- **Assistant text** joins every `text` event in stream order, separated by blank lines.
- **Loaded skill IDs** come from `tool_use` events whose tool is `skill`; the ID is `part.state.input.id`. Duplicates are removed and first-load order is preserved.
- **Token totals** sum every `step_finish` event. The total is `input + output + reasoning + cache.read + cache.write`, matching OpenCode's own token accounting.
- **Duration** is wall-clock milliseconds from process start to process exit or timeout.
- **Output files** are project files that are new or changed during the run. `.opencode/`, `.git/`, and `opencode.json` are excluded because they belong to the harness, not the agent; a skill that writes into `.opencode/` will not have those files reported as outputs.
- **Metrics** are a `RunMetrics`. `total_steps` counts started steps, so a failed or timed-out step still appears in the count. `output_chars` reads the output files as UTF-8 with replacement, and `transcript_chars` counts the Markdown transcript.
- **Markdown transcript** renders steps, assistant text, tool inputs and results, errors, and a token/duration/exit-code summary.

When `run` receives `artifacts_dir`, it writes:

```text
<artifacts_dir>/
├── transcript.jsonl
├── transcript.md
└── outputs/
    └── metrics.json
```

The caller owns the rest of the run layout, including normalized run metadata and timing. Without `artifacts_dir`, the adapter writes nothing to disk; `RunResult` still carries both transcripts and the metrics for the caller to persist.

## Trigger probe

`probe_trigger` creates a uniquely named candidate skill, `<slug>-probe-<8 hex>`, from the supplied description, puts it in a deny-all scope, and runs the query. Triggering is detected when the `skill` tool loads the candidate ID. A `read` tool call whose path contains the candidate directory is accepted as a fallback.

Each probe uses a fresh candidate name and a fresh scope, so ambient skills cannot answer for the candidate.

## Limits

- Managed system configuration can hard-deny skills or outrank project permission rules. The adapter cannot override that.
- A trigger probe cleans its scope before returning, so `run.output_files` paths from a probe no longer exist. Use the transcript when debugging a probe.
- Early termination after the first trigger observation, repeated probe runs, and trigger-rate reporting are the caller's responsibility.
