---
name: setup-rust-code-style
description: "Set up a Rust style doc at docs/agents/rust-style.md, an AGENTS.md pointer, and a Clippy lint baseline, including workspace member opt-in. Does not audit or reformat existing code."
compatibility: Requires a Rust toolchain with Cargo and Clippy; the Cargo lint baseline needs Cargo 1.74 or newer.
disable-model-invocation: true
---

# Setup Rust Code Style

Install the canonical Rust style guide (`assets/rust-style.md`) as `docs/agents/rust-style.md`, add one pointer in `AGENTS.md`, and add one Rust lint baseline.

This skill writes only `docs/agents/rust-style.md`, `AGENTS.md`, the root `Cargo.toml`, workspace member `Cargo.toml` files (only to add `[lints] workspace = true`, or to replace a package-level lint table the user approved moving into `[workspace.lints.*]`), and `clippy.toml` (or an existing `.clippy.toml`); it does not edit any other file.

Keep existing configuration unless the user approves a change: propose, then write.

## 1. Explore

Read what exists:

- `Cargo.toml` or any `.rs` files. If neither exists, ask whether to proceed; the repository may be about to add Rust code. If the user declines, stop and report that nothing was written.
- `AGENTS.md` at the repo root. Does it have a `## Code style` section and a `### Rust` sub-block?
- `docs/agents/rust-style.md`. Does the style doc already exist?
- `Cargo.toml` files. Is the root a standalone package, a workspace with a root package, or a virtual workspace? Enumerate every workspace member (`cargo metadata --no-deps --format-version 1` lists them; skip this command when no manifest exists) and check which member manifests already inherit (`[lints] workspace = true`), define their own `[lints.*]` tables, or set a different `[lints]` value. Note any excluded or nested `Cargo.toml` that Cargo does not treat as a member.
- Existing lint config: `[lints.rust]`, `[lints.clippy]`, or `[workspace.lints.*]` in any `Cargo.toml`; `clippy.toml` or `.clippy.toml` next to the root `Cargo.toml` or in an ancestor directory, where Clippy would find it.
- `rust-version` in the root `Cargo.toml`, and the installed `rustc`/`cargo clippy` version. The `[lints]` table requires Cargo 1.74. The installed Clippy decides which lints exist now; `rust-version` decides whether the project can use them. If `rust-version` is older than the installed Clippy, check the baseline against the MSRV toolchain when it is available; otherwise ask whether to raise the MSRV or omit the unsupported lints.

Done when you can name the root manifest kind (or the user approved proceeding without one), list every workspace member with its current lint state, name the Clippy config in effect, and state which baseline lints the installed Clippy provides.

## 2. Present and confirm

Summarize what is present and missing. Show:

- The proposed `## Code style` block:

```markdown
## Code style

### Rust

See `docs/agents/rust-style.md`.
```

- `assets/rust-style.md` in full, plus the existing `docs/agents/rust-style.md` if it already exists. The asset is the source for a new or replaced doc; a merge uses the approved merged text; keep leaves the doc untouched.
- The proposed lint block for the root `Cargo.toml`. For a standalone package:

```toml
[lints.rust]
redundant_imports = "warn"

[lints.clippy]
undocumented_unsafe_blocks = "warn"
struct_field_names = "warn"
items_after_statements = "warn"
min_ident_chars = "warn"
module_name_repetitions = "warn"
redundant_type_annotations = "warn"
arbitrary_source_item_ordering = "warn"
```

For a workspace, use the same keys under `[workspace.lints.rust]` and `[workspace.lints.clippy]` in the root `Cargo.toml`, and add this table to every workspace member `Cargo.toml`:

```toml
[lints]
workspace = true
```

- The proposed `clippy.toml`:

```toml
min-ident-chars-threshold = 1
allowed-idents-below-min-chars = ["i", "j", "x", "y", "z", "n"]
```

If `docs/agents/rust-style.md` exists, ask whether to:

- **Replace** it with the asset's text.
- **Keep** it as-is and only add the pointer.
- **Merge**: compare `##` headings; add missing sections from the asset, keep existing sections, and report headings present in both with different content so the user can decide.

If root or member `Cargo.toml` lint tables or `clippy.toml`/`.clippy.toml` already exist, propose **merge**, **replace**, or **keep** for each and get approval before writing.

Ask one final confirmation question after resolving the choices above: "Install this Rust style doc, add the `## Code style` block to `AGENTS.md`, and add the Rust lint baseline to the root `Cargo.toml` and `clippy.toml`?" In a workspace, the question also covers adding `[lints] workspace = true` to every workspace member. If `AGENTS.md` does not exist, include creating it in the question. Show the proposed text and let the user edit it before they answer.

Done when the user has approved or declined each artifact: pointer block, style doc, root Cargo block, member opt-in, and clippy config.

## 3. Write

- `AGENTS.md`: if it does not exist and the user approved creating it, create it with the approved `## Code style` block. If they declined creating it, skip this write and report it. Add the pointer only when `docs/agents/rust-style.md` exists or is being written; if the style doc is skipped, skip the pointer and report both.
- If `AGENTS.md` exists, add the `## Code style` section at the end if it is missing. If the section exists, add `### Rust` when absent or update it in place. Preserve surrounding content and avoid duplicate pointers.
- Style doc: for a new or replaced doc, copy `assets/rust-style.md` verbatim. For a merge, write the approved merged text. For keep, leave the doc untouched. Create `docs/agents/` if needed.
- Cargo.toml:
  - Define lints only in the root `Cargo.toml`; never add `[lints.rust]` or `[lints.clippy]` keys to a member manifest.
  - Standalone package: add the approved block under `[lints.rust]` and `[lints.clippy]`. If those tables exist, add only the missing keys; do not duplicate table headers or overwrite existing values without approval.
  - Workspace root: add the approved block under `[workspace.lints.rust]` and `[workspace.lints.clippy]` in the root `Cargo.toml`.
  - Workspace members: handle each member once.
    - Already inherits `[lints] workspace = true`: leave it.
    - Missing `[lints]`: add `[lints] workspace = true` and leave the rest of the manifest untouched.
    - Has a `[lints]` table with values other than `workspace = true`: ask whether to merge its values into `[workspace.lints.*]` and replace it with `[lints] workspace = true`, keep the package-level config, or skip that manifest.
    - Not a workspace member (excluded crate, nested standalone package): report it and do not edit it.
  - MSRV: if `rust-version` is below 1.74, skip the Cargo lint config and report it. Otherwise omit any baseline lint the MSRV toolchain does not recognize, along with any `clippy.toml` keys that only it uses, and report them; ask before raising the MSRV.
  - If no `Cargo.toml` exists, skip the lint config and report it.
- clippy.toml:
  - If neither `clippy.toml` nor `.clippy.toml` exists, create `clippy.toml` with the approved contents next to the root `Cargo.toml`.
  - If one exists, merge the approved keys into it and preserve other keys, comments, and formatting. If both exist, ask which one to use, use that file, and report the other; do not create another config file.
  - If a key already exists with a different value, propose the change and get approval.

Done when the pointer path resolves to `docs/agents/rust-style.md`, the style doc is in place (or kept), `cargo metadata --no-deps` parses every edited manifest, every workspace member either inherits `[lints] workspace = true` or is reported as kept or skipped, and the Clippy config is in place.

## 4. Report

Use this contract:

```markdown
## Rust code style setup
- Style doc: `docs/agents/rust-style.md` (`created` | `replaced` | `merged` | `kept` | `skipped`)
- Agent file: `AGENTS.md` (`created` | `updated` | `kept` | `skipped`)
- Section: `## Code style` → `### Rust` (`added` | `updated` | `kept` | `skipped`)
- Cargo lints: `<root Cargo.toml>` (`added` | `merged` | `kept` | `skipped`)
- Member opt-in: `<n>` added, `<n>` already set, `<n>` kept, `<n>` skipped (`<reason>`; use `n/a` for a standalone package)
- Clippy config: `<path>` (`created` | `merged` | `kept` | `skipped`)
- Enabled lints: `<list>` or `none`
- Omitted lints: `<lint> (<reason>)` or `none`
- Open questions: `<...>`
```

Done when the report gives every artifact a terminal status and every skip a reason.

Tell the user that future agents can read the doc through the pointer. They can edit `docs/agents/rust-style.md` directly; keep its `##` headings stable because the setup skill merges by heading. Re-run this skill to replace or merge the style text, onboard a new workspace member, or update the lint baseline. The Clippy config is independent of the style doc; update it when the project's toolchain or naming policy changes.
