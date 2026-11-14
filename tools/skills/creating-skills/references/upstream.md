# Upstream provenance

This skill is a harness-neutral adaptation of the `skill-creator` skill from the upstream `anthropics/skills` repository.

| Field | Value |
| --- | --- |
| Upstream repository | `https://github.com/anthropics/skills` |
| Upstream skill path | `skills/skill-creator` |
| Pinned upstream commit | `b9e19e6f44773509fbdd7001d77ff41a49a486c1` (2026-04-20, the last commit affecting the skill) |
| Vendored snapshot | `.agents/skills/skill-creator` |
| Lock entry | `skills-lock.json` → `skill-creator` |
| Lock `computedHash` | `5ea13a6d9f0d4bb694405d79acd00cadec0d21bb138c4dd10fcf3c500cb835c2` |
| Port location | `tools/skills/creating-skills` |
| License | Apache-2.0; see `../LICENSE.txt` (copied unchanged from upstream) |

The vendored snapshot is the upstream reference used for future diffs. Keep it untouched; update it through the skills lock rather than editing files in place.

## Port changes

The port keeps the upstream authoring and improvement loop but removes or rewrites material that assumed a specific harness, distribution channel, or UI:

- Renamed the skill to `creating-skills` and aligned the directory and frontmatter name.
- Rewrote instructions in harness-neutral language: "the agent", "fresh-context run", and "harness adapter".
- Moved authoring detail into `references/writing-patterns.md`.
- Removed packaging, archive creation, file-presentation steps, and harness-specific review instructions.
- Did not port the upstream validator or packaging script.
- Eval, benchmark, and description-tuning operations go through a harness adapter rather than hardcoded commands.

## Diffing an upstream update

1. Update the vendored snapshot:

   ```bash
   skills update skill-creator
   ```

2. Inspect what changed upstream:

   ```bash
   git diff -- .agents/skills/skill-creator skills-lock.json
   ```

3. Compare each changed upstream file with its port counterpart:

   ```bash
   diff -u .agents/skills/skill-creator/SKILL.md tools/skills/creating-skills/SKILL.md
   ```

   Repeat for any changed reference or script. The diff will be noisy because the port intentionally renames the skill, rewrites prose, and drops packaging and harness-specific material. Read it for upstream ideas, not as a literal patch.

4. Port only changes that preserve harness neutrality. Do not copy packaging, archive, presentation, or harness-specific sections. If an upstream change is useful but harness-specific, put it in the adapter documentation instead of the neutral core.

5. Update the pinned commit and `computedHash` in the table above to match the new snapshot.

6. Run the skill's content audit and tests, then manually confirm the vendored skill is still readable and still hidden from model invocation.

## Updating the pinned hash

The `computedHash` comes from `skills-lock.json`. After an update, read the new value from the `skill-creator` entry and replace the one in the table. Record the upstream commit that last changed the vendored skill; use `git log` in a clone of the upstream repository or the upstream commit history for the skill path.
