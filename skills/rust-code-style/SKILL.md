---
name: rust-code-style
description: Apply Rust code style — cosmetic rules that change how the code reads, never what it computes — covering comments and doc comments, imports and full paths, type annotations, and struct-literal shorthand. Use when writing, editing, or reviewing Rust code: commenting or documenting, choosing `use` vs a qualified path, tidying imports, annotating types, or simplifying struct literals.
---

# Rust code style

Style Rust so the code reads as cleanly as it runs. Every rule here is cosmetic: it changes how the code reads, never what it computes. Apply them over every Rust file you write or touch. Where the styled version would change behavior, ownership, or error flow, that edit is out of scope — name it and leave the code as it is.

## Comments

A comment earns its place by meaning the code cannot carry — the reasoning behind a shape, an invariant that must hold, a choice made deliberately against an alternative. It states *why*, never *what*: the code already states what. `// increment i` restates the line it guards and is deleted on sight; `// i stays aligned with buf.len()` stays — it tells a reader the relationship that keeps the loop alive.

A public item gets a doc comment that says what the item is for. `///` documents one item; `//!` opens a module with the module's purpose. The first sentence is one line and names the item plainly. When behavior is subtle, a doctest inside the comment proves the wording. Library crates get `#![warn(missing_docs)]` at the crate root, so a public item without a doc comment fails the build.

## Imports and paths

A `use` at the top earns its place by repetition — a name that appears several times, or a trait whose methods the code calls — or by ambiguity that needs resolving. A name used once reads better written in full at its call site than as an import the reader must track back to. Decide by reading: which version shows the name next to where it works.

Reach across modules with `crate::` and `super::`, never `..`. `crate::` for anything reachable from the crate root; `super::` for a neighbor in the same parent.

Group imports three ways: std first, external crates second, crate-local last, with a blank line between the groups. When a module is used several times, merge its names into one braced import (`use serde::{Deserialize, Serialize}`) rather than one line each. If the project's `rustfmt.toml` sets `group_imports` or `imports_granularity`, the formatter owns grouping and granularity — you only decide what to import, then stay out of its way.

When two crates offer the same name, alias on import (`use legacy::Result as LegacyResult`) when the alias recurs; leave both fully qualified when each appears once.

## Type annotations

Annotate a binding when inference cannot decide it, or when the type is the point of the line — a fact a reader gains from seeing `Duration` at once. Choose one home for the type, the binding (`let wait: Duration = ...`) or the call (`... .collect::<Vec<_>>()`); never both — a type in two places is a type in none. When the call's name already shows the type, an annotation restates it — leave it off.

## Struct literals

Set a field as shorthand when the binding carries the field's name (`Point { x, y }`); keep the `: binding` form only to join a differently-named value. When most fields carry over from an existing value, use functional update — `..base` — for the unchanged tail instead of restating its fields. When a field cannot be shorthand, write the literal in full and stay consistent: mixed shorthand reads as a half-finished edit.