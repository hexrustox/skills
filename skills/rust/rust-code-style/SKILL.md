---
name: rust-code-style
description: Style Rust code as you write, edit, or review it — comments, names, imports, visibility, ordering, type annotations. Use whenever touching Rust code.
metadata:
  version: "1.0.0"
---

# Rust code style

Style Rust so it reads as cleanly as it runs. A pass applies all six groups below to what you changed. When the user asks you to style or clean up a file, the scope is the whole file; on a functional edit, the scope is the changed code and its neighbors — restyling the rest is a separate change, so ask first. Where the project already has a style, follow it; these rules are the default when it does not. Most rules are cosmetic: they change how the code reads, not what it computes. When a rule would change behavior, ownership, error flow, or public API, keep the code and name the exception. Attributes are not style: leave `#[derive]`, `#[allow]`, `#[cfg]`, and lint attributes alone.

## Comments

Body comments (`//`) default to none: a why-comment earns its place only when the code is hard to follow and the comment supplies reasoning the code cannot. An `unsafe` block always carries a `// SAFETY:` line naming the invariant that makes it sound. In scope, a pass audits every comment, body and doc, deletes each that fails its bar, and corrects or deletes a surviving comment whose text no longer matches the code. A doc that makes a factual claim about representation or behavior is checked against the code, and a false claim is corrected, not kept.

A doc comment (`///`) documents the public surface: one line stating a contract, invariant, or non-obvious behavior the signature cannot show. Rewrite a restating doc to that part; delete it when nothing remains. Private items follow the body-comment bar. Open a module with `//!` only when it orients the reader beyond the module name, except that a crate with `missing_docs` (or denied warnings) needs a crate-root `//!`. Under that lint, every public item keeps a one-line doc; rewrite a restating doc instead of deleting it. Keep the first sentence to one line.

## Names

A name carries what it holds. Spell out abbreviated names (`genymdhms`) and lying suffixes (`account_list` for a `HashMap`) as the value they name. A distinction must carry a difference, so two types differing only by suffix (`ProductData` beside `ProductInfo`) get role names instead. Name types with nouns and methods with verbs (`Customer`, `post_payment`). Rename a public item only when the crate is internal or the user asks for the break.

## Imports and paths

A `use` earns its place by repetition: a full path appearing more than once is hoisted into an import. A one-off name may stay imported or be written in full — choose what reads better at the call site. Keep a trait imported when you call its methods. Resolve ambiguity with an alias when the alias recurs; otherwise leave both paths fully qualified.

Reach across modules with `crate::` for anything in the crate, and `super::` for a neighbor in the same parent. Climb at most one `super::`; a longer path reads better from the crate root.

Group imports std first, external crates second, crate-local last, with a blank line between, and merge a module's names into one braced import (`use serde::{Deserialize, Serialize}`).

```rust
// input: scattered + ungrouped
use serde::Serialize;
use std::time::Duration;
use serde::Deserialize;
use crate::config::Config;
// output: grouped std / external / crate-local, merged
use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::config::Config;
```

## Publicity

Grant only the reach an item earns, by rung: private → `pub(super)` (the parent module and its descendants) → `pub(crate)` → `pub` (the crate's public interface). Pick the narrowest rung that reaches every consumer: private covers only the defining module and its descendants, so a consumer in a sibling module needs `pub(super)`. Tighten only when every consumer of that item is visible in this workspace — modules, tests, examples, benches, and docs. Measure each item's consumers, not the crate's surface as a whole: an item used only by its parent or a sibling can narrow while the crate keeps a public surface. Narrow a published crate's `pub` surface only with the user's confirmation; a downstream consumer may exist. In scope, a pass measures every visibility.

## Ordering

Order items as a descent: most abstract at the top, most concrete at the bottom — the reader gets only the order on disk.

A module file opens with its `mod` declarations, then its `use`s, then its items ranked by level: the entry point or public interface first, the mid-level code driving it next, the small private helpers last, each defined below its first caller. A type precedes its `impl` blocks, inherent before trait. Tests close the file.

The descent orders items, not statements: rearranging statements inside a body changes evaluation order.

## Type annotations

Annotate a binding when inference cannot decide it, or when the type is the point of the line — a fact a reader gains from seeing `Duration` at once. Give the type one home, the binding (`let wait: Duration = ...`) or the call (`... .collect::<Vec<_>>()`); never both — a type in two places is a type in none. Leave off an annotation the call's name already shows.

## Finish the change

Before you call a Rust change done, run a pass: re-read every in-scope file and region against all six groups above. Read test modules for context; edit one only when the user asks for test changes. Then run the project's formatter, linter, and tests — for a Cargo project, `cargo fmt`, `cargo clippy --all-targets -- -D warnings`, and `cargo test --workspace`; add `cargo check --all-targets` when the edit touched visibility or names. If a tool is unavailable, say so and treat that check as unverified; report a pre-existing failure instead of fixing it in this pass. A pass is done when every in-scope file and region has been read against all six groups, the formatter, linter, and tests pass (or their absence is reported), and every rule left unapplied is named to the user with its reason.
