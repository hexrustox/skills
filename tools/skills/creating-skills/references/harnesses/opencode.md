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

The project config denies every skill and then allows only the requested IDs. It also hard-denies tool access to paths outside the temporary project:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permissions": [
    { "action": "skill", "resource": "*", "effect": "deny" },
    { "action": "skill", "resource": "example-skill", "effect": "allow" }
  ],
  "policies": [
    {
      "action": "tool.use",
      "resource": "external_directory:*",
      "effect": "deny"
    }
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

`external_directory` is the V2 check for paths outside the active Location and worktree. Encode it as a `tool.use` policy rather than a permission: policies are binary hard denials applied after permissions and saved approvals, so a global rule that allows `/tmp/*` or `read: *` cannot re-open the scope. Use OpenCode 2.2.1 or newer, which enforces `tool.use` policies.

A no-skill scope keeps the deny-all rule, leaves `.opencode/skills` empty, and keeps the external-directory policy. This hides skills from global config, compatibility directories, and explicit skill sources rather than relying on those sources being absent; OpenCode has no per-project switch that removes every ambient source. It is the permission rule, not the empty project, that guarantees the scope contains exactly the requested skill. The policy keeps the live skill source, old snapshots, the eval workspace, and sibling temporary scopes outside the run.

The adapter applies the external-directory policy to every prepared scope, including the with-skill arm and trigger probes. The copied skill and staged inputs are inside the scope, so they remain readable and writable.

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

## Fresh-context instruction runs

Grading, blind comparison, and analysis use the instruction files under `agents/`, not the eval runners. Start each as its own `opencode run`. No `--continue` or `--session` is passed, so the run gets a fresh session.

Pass the instruction file's contents as the prompt, or attach it with `--file` and tell the agent to follow it. Include absolute paths for every input and output. For example:

```bash
opencode run --format json --agent build --auto \
  --file /abs/path/to/creating-skills/agents/grader.md \
  "Follow the attached grader instructions. eval_prompt: <the eval prompt>; expectations: <expectation 1>; <expectation 2>; transcript_path: /abs/path/to/eval-1/with_skill/transcript.md; outputs_dir: /abs/path/to/eval-1/with_skill/outputs; output_path: /abs/path/to/eval-1/with_skill/grading.json"
```

- Run from a scratch directory, not from an active session and not from the project under test. Grading, comparison, and analysis do not need a skill scope.
- The fresh agent writes the output file at `output_path`. If its scope cannot write that absolute path, ask it to return the JSON and write the file yourself.
- For a comparison, stage neutral A/B copies before starting and keep arm names out of the prompt and paths. The comparator must not be able to infer which arm produced which output.
- The run's JSONL stream is the transcript of the grading run itself. The result that matters is the JSON file it writes.

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
- **Loaded skill IDs** come from `tool_use` events whose tool is `skill` and whose `part.state.status` is `completed`; the ID is `part.state.input.id`. Failed loads are not reported. Duplicates are removed and first-load order is preserved.
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

`probe_trigger` creates a uniquely named candidate skill, `<slug>-probe-<8 hex>`, from the supplied description, puts it in a deny-all scope, and runs the query. Triggering is detected when the `skill` tool successfully loads the candidate ID. A `read` tool call whose path is the candidate directory or a file inside it is accepted as a fallback when the read completes. Failed loads and failed reads do not trigger. The adapter stops the process as soon as either event appears; the returned run contains the stream up to that point and is not marked as timed out.

Each probe uses a fresh candidate name and a fresh scope, so ambient skills cannot answer for the candidate.

## Limits

- A parallel eval batch uses one adapter instance and one temporary scope per run, but the runs share the background OpenCode service. Construct `OpenCodeHarness(standalone=True)` when a private server per run matters more than startup cost.
- Managed system configuration can hard-deny skills or outrank project permission rules. The adapter cannot override that.
- The scope denies tool-mediated access to every path outside the temporary project. The hard `tool.use external_directory:*` policy covers `read`, `glob`, `grep`, `edit`, `write`, and `patch`, including calls made by subagents. It also covers shell working directories and paths that OpenCode's shell scanner can infer. Staged inputs and the copied skill stay inside the scope, so with-skill runs keep their files.
- Shell is not a sandbox. The shell scanner's directory inference is best effort; a command that hides an external path from the scanner, such as interpreter code that opens a file by a computed name, can still read outside the scope. MCP tools, plugins, and webfetch are outside the guarantee. Managed or global `allow` policies can outrank a project deny.
- Keep the scope outside the skill's repository. The default system temp directory does. A `temp_root` inside the repository makes the source an internal path and weakens the boundary.
- `loaded_skill_ids` proves the skill tool did not load. It does not prove a baseline never saw the skill source, because of the shell limit.
- A trigger probe cleans its scope before returning, so `run.output_files` paths from a probe no longer exist. Use the transcript when debugging a probe.
- Repeated probe runs and trigger-rate reporting are handled by `scripts.trigger_eval`, not the adapter.
