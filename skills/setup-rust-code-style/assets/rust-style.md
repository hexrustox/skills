# Rust code style

These rules assume Rust 2018 or newer and the standard library; a `no_std` crate follows the same style using `core` and `alloc` paths.

## Comments

Default to no comment — body (`//`) and doc (`///`) alike. A comment earns its place only on a strong reason: the code is hard to understand, and the comment supplies the reasoning the code cannot. Obvious code gets nothing, whatever the comment says; a why-comment dies too when the why reads straight off the code. Keep any comment that clears this bar true to the code it annotates.

`// SAFETY:` comments and license headers (including SPDX identifiers) are exceptions: every `unsafe` block and `unsafe impl` gets a `// SAFETY:` comment explaining why it is sound.

Doc comments follow the same default. The exception is a library's public API: those items get a doc comment, and a one-liner carrying only the non-obvious satisfies it.

When a doc comment earns its place, cover the item with `///`, open a module with `//!`, make the first sentence one line, and prove subtle wording with a doctest for a public item — but a doc line that restates the item's name or signature (`/// Returns the sum.` over `fn sum`) is a what-comment; reduce it to the non-obvious part.

## Names

A name carries what it holds: decode-names (`genymdhms`, `d`) and lying suffixes (`account_list` for a `HashMap`) are spelled out as the value they name.

A distinction must carry a difference, so two types differing only by suffix (`ProductData` beside `ProductInfo`) get role names instead (`ProductRecord` for the stored row, `ProductCard` for the display model). Name types with nouns and methods with verbs (`Customer`, `post_payment`) — a type is a thing, a method does something.

## Imports and paths

A `use` at the top earns its place by repetition — a name used more than once, or a trait whose methods the code calls — or by ambiguity that needs resolving. A name used once reads better written in full at its call site than as an import the reader must track back to.

```rust
// avoid: once-used name imported
use std::time::Duration;
fn wait(timeout: Duration) -> Status { ... }
// prefer: full path at the call site, import dropped
fn wait(timeout: std::time::Duration) -> Status { ... }
```

Use `crate::` for paths outside the current module and its parent; `super::` for the parent's items and siblings; avoid `super::super::` chains.

Group imports three ways: std first, external crates second, crate-local last, with a blank line between the groups. When a crate or module is used more than once, merge its names into one braced import (`use serde::{Deserialize, Serialize}`) rather than one line each.

When two crates or modules offer the same name, alias on import (`use legacy::Result as LegacyResult`) when the alias is used more than once; leave both fully qualified when each appears once.

```rust
// avoid: scattered + ungrouped
use serde::Serialize;
use std::time::Duration;
use serde::Deserialize;
use crate::config::Config;
// prefer: grouped std / external / crate-local, merged
use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::config::Config;
```

## Publicity

Grant only the reach an item earns, by rung: private → `pub(super)` (visible to the parent module and its descendants) → `pub(crate)` (the whole crate) → `pub` (the crate's public interface).

Choose the tightest rung that compiles and serves the intended caller: an internal helper is `pub(crate)` rather than `pub`; a helper only one module needs is private; a helper the parent's subtree needs is `pub(super)`.

## Ordering

Rust lets items sit in any order — the compiler resolves them regardless of position, except for `macro_rules!`, whose textual scope depends on where it is defined — but the reader gets only the order on disk. Make that order a descent: most abstract at the top, most concrete at the bottom.

A module file opens with its `mod` declarations, then its `use`s, then its items: the entry point or public interface first, the mid-level code driving it next, the small private helpers last, each defined below its first caller. A type precedes its `impl` blocks, inherent before trait; constants serving one type live inside those blocks rather than at file scope.

Read top-down, the file answers *what* before *how*. All inline modules (`mod <ident> { ... }`) pin what everything above established. The descent orders items, not statements.

## Type annotations

Annotate a binding when the reader cannot infer the type from the line, or when the type is the point of the line — a fact a reader gains from seeing `Duration` at once.

Choose one home for the type, the binding (`let wait: Duration =`) or the call (`.collect::<Vec<_>>()`); a type in two places is a type in none. When the call's name already shows the type, an annotation restates it — leave it off.

```rust
// prefer: one home for the type
let wait: Duration = parse_timeout();
let names = rows.collect::<Vec<_>>();
```

## Struct literals

When most fields carry over from an existing value, use functional update — `..base` — for the unchanged tail instead of restating its fields; if `base` must stay usable, restate the fields instead.

```rust
// prefer: functional update for the unchanged tail
let wider = Rect { width: 20, ..base };
```
