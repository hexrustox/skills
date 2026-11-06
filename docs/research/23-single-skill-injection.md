# Single-skill injection for coder-eval's with-skill arm

**Ticket:** [#23](https://github.com/hexrustox/skills/issues/23) · **Map:** [#16](https://github.com/hexrustox/skills/issues/16) · **Date:** 2026-11-06

## Answer

A bare skill directory works. It does **not** need a `.claude-plugin/plugin.json`.

For coder-eval 0.12.16 + OpenCode 1.19.5, use a `type: local` plugin entry whose
`path` is the absolute path of the individual skill directory:

```yaml
plugins:
  - type: local
    path: /abs/path/to/repo/skills/authoring-agents-md
```

This injects exactly one path and exposes only `authoring-agents-md` from the
repo's four skills. No plugin root or manifest is required.

## Why it resolves that way

`OpenCodeAgent.start()` calls `_plugin_skill_dirs(self.config.plugins)` and then
merges the result into `OPENCODE_CONFIG_CONTENT`
([opencode_agent.py L792-L799](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/opencode_agent.py#L792-L799),
[L916-L948](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/opencode_agent.py#L916-L948)).

For a plugin root, `manifest_skill_dirs()` reads the `skills` array from
`<root>/.claude-plugin/plugin.json`; when that manifest is absent it falls back
to `<root>/skills`
([_skills.py L27-L49](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/_skills.py#L27-L49)).
`_plugin_skill_dirs()` keeps only candidate directories that actually exist, and
if none do, uses the plugin path itself
([_skills.py L84-L89](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/_skills.py#L84-L89)).

For `skills/authoring-agents-md`:

1. No `.claude-plugin/plugin.json` exists under the skill directory.
2. The default candidate is `skills/authoring-agents-md/skills`, which does not exist.
3. The resolver falls back to the plugin path itself: `skills/authoring-agents-md`.
4. A warning is logged because there is no `<name>/SKILL.md` immediately below
   that path (`SKILL.md` is at its root). The path is still injected
   ([_skills.py L90-L101](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/_skills.py#L90-L101)).
   The warning is benign for this shape.

## Exact `OPENCODE_CONFIG_CONTENT`

With no inherited `OPENCODE_CONFIG_CONTENT`, coder-eval produces this JSON
(`json.dumps` formatting, absolute path):

```json
{"skills": {"paths": ["/abs/path/to/repo/skills/authoring-agents-md"]}}
```

For the main checkout at `/home/user/Projects/skills`, the value is:

```json
{"skills": {"paths": ["/home/user/Projects/skills/skills/authoring-agents-md"]}}
```

coder-eval also records the resolved list as `opencode_skill_paths` in the task
environment info, which is the easiest post-run assertion that injection
happened ([opencode_agent.py L861-L864](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/opencode_agent.py#L861-L864)).

## What OpenCode 1.19.5 does with it

OpenCode 1.19.5 still honors `skills.paths`. The V1 config schema defines it as
`string[]`, described as "Additional paths to skill folders"
([packages/core/src/v1/config/skills.ts L5-L12](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/core/src/v1/config/skills.ts#L5-L12)).
The skills guide does not document the field, but the discovery code is explicit:
it iterates `cfg.skills?.paths`, resolves `~/` and relative entries, then scans
each path with `SKILL_PATTERN = "**/SKILL.md"`
([packages/opencode/src/skill/index.ts L23-L25](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/src/skill/index.ts#L23-L25),
[L210-L220](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/src/skill/index.ts#L210-L220)).
The scan uses node-glob with `absolute: true`, `include: "file"`, and
`symlink: true` ([packages/core/src/util/glob.ts L25-L31](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/core/src/util/glob.ts#L25-L31),
`glob` 13.0.5 per [packages/opencode/package.json L124](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/package.json#L124)).

In node-glob, `**` matches "zero or more directories and subdirectories", so
`**/SKILL.md` matches the `SKILL.md` at the root of the injected directory as
well as any nested ones ([node-glob README, globstar](https://github.com/isaacs/node-glob/blob/v13.0.5/README.md#L593-L597)).
Because coder-eval passes the skill directory itself, OpenCode finds
`skills/authoring-agents-md/SKILL.md` and registers one skill. Its frontmatter
name matches the directory name (`authoring-agents-md`,
[skills/authoring-agents-md/SKILL.md L2](https://github.com/hexrustox/skills/blob/main/skills/authoring-agents-md/SKILL.md#L2)).

## Path-shape comparison

| `plugins[].path` | Paths in `OPENCODE_CONFIG_CONTENT` | Skills exposed from the repo |
| --- | --- | --- |
| `skills/authoring-agents-md` (bare skill dir) | `["<repo>/skills/authoring-agents-md"]` | only `authoring-agents-md` |
| `<repo>` (plugin root, manifest declares four) | four paths, manifest order | all four |
| a plugin root whose manifest declares only the target | `["<root>/skills/authoring-agents-md"]` | only `authoring-agents-md` (works, but manifest is unnecessary) |
| `skills` (parent directory) | `["<repo>/skills"]` | all four, because `**/SKILL.md` is recursive |

For the repo-root shape, `.claude-plugin/plugin.json` declares all four entries
([.claude-plugin/plugin.json L2-L7](https://github.com/hexrustox/skills/blob/main/.claude-plugin/plugin.json#L2-L7)),
so the exact value is:

```json
{"skills": {"paths": ["/abs/path/to/repo/skills/authoring-agents-md", "/abs/path/to/repo/skills/rust/rust-code-style", "/abs/path/to/repo/skills/to-behavior-contract", "/abs/path/to/repo/skills/audit-behavior-contract"]}}
```

## Edge cases

- **Ambient skills are additive, not replaced.** `skills.paths` is one input to
  discovery. OpenCode 1.19.5 also scans project `.opencode/skills`,
  `.claude/skills`, and `.agents/skills` while walking up to the worktree, plus
  their global equivalents
  ([skill/index.ts L185-L208](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/src/skill/index.ts#L185-L208)).
  This repo has a populated `.agents/skills/` directory. If an eval task runs
  with a cwd inside this worktree, the arm will see those skills too, regardless
  of the injected path. `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` suppresses the
  `.claude` and `.agents` scans (undocumented flag, source:
  [runtime-flags.ts L16-L30](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/src/effect/runtime-flags.ts#L16-L30));
  `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` suppresses only `.claude`. Neither
  suppresses `.opencode` config directories or global `~/.config/opencode/skills`.
  The built-in `customize-opencode` skill is also always registered
  ([skill/index.ts L276-L283](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/src/skill/index.ts#L276-L283)).
  For a strictly exclusive arm, run tasks from a clean directory outside the
  repo (or make the fixture's directory tree free of `.agents`, `.claude`, and
  `.opencode` skill dirs), not just a single injected plugin.
- **Do not add a `skills/` subdirectory to the bare skill dir.** If
  `skills/authoring-agents-md/skills/` ever exists, coder-eval treats it as the
  declared skills root and does not fall back to the skill directory itself, so
  the target can silently disappear.
- **Inherited `OPENCODE_CONFIG_CONTENT` is merged.** A valid JSON object is
  preserved, its existing `skills.paths` are kept, and the new path is appended
  only if not already present; invalid JSON or a non-object value is replaced.
  Exact output therefore includes any inherited keys
  ([opencode_agent.py L925-L948](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/opencode_agent.py#L925-L948)).
- **Only `type: local` maps to skills.** Other plugin types are ignored with a
  warning ([_skills.py L65-L69](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/_skills.py#L65-L69)).
- **Relative paths resolve against coder-eval's process cwd**, not the config
  file or task directory (`Path(expanded).resolve()`,
  [_skills.py L70-L74](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/_skills.py#L70-L74)).
  Prefer an absolute path, or guarantee the eval runner's cwd.
- **The `<name>/SKILL.md` warning is expected.** It fires for the bare skill dir
  and even for each leaf path declared in this repo's manifest. It does not stop
  injection.
- **A path that does not exist injects nothing.** The resolver logs and skips it
  ([_skills.py L75-L82](https://github.com/UiPath/coder_eval/blob/v0.12.16/src/coder_eval/agents/_skills.py#L75-L82)).
  OpenCode likewise warns and skips a missing `skills.paths` entry
  ([skill/index.ts L211-L220](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/opencode/src/skill/index.ts#L211-L220)).

## Recommendation

Use the bare skill path in `plugins:`:

```yaml
plugins:
  - type: local
    path: /abs/path/to/repo/skills/authoring-agents-md
```

It is the simplest shape that yields one injected path, it exposes only the
target skill from the repo, and it avoids maintaining a second plugin manifest.
If the eval requires a guaranteed single-skill environment, combine it with a
clean task cwd (or `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`) and assert
`opencode_skill_paths` in the run record.
