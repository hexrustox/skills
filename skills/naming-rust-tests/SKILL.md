---
name: naming-rust-tests
description: Name Rust tests — plain `#[test]` functions and parametrized cases (`test-case`, `rstest`) — so `cargo test` output reads as the contract. Use when writing, renaming, adding, or reviewing Rust test names.
---

Name Rust tests so a failing name states what broke. Two kinds of test name themselves differently — plain and parametrized.

## Plain tests

A `#[test]` function's name is the test name: `cargo test` prints its path (`<module>::<name>`) and a failure names that function. The function name carries the whole name.

Name it as behavior + pinned outcome — what the code does, then what the test pins. snake_case, like any fn:
- `rejects_invalid_json` — `parse(json)` errs on malformed input.
- `preserves_unicode_on_roundtrip` — `decode(encode(x))` returns x for multibyte input.

The name proves itself in a failure: a stranger reading the failing path knows what broke and what was pinned. Done when every `#[test] fn` name reads behavior + outcome.

## Parametrized tests

`test-case` splits the naming in two. One function runs many cases:

```rust
#[test_case(2, 3, 5; "adds_two_and_three")]
fn add(a: i32, b: i32, expected: i32) {}
```

`cargo test` prints the case as `<parent_module>::add::adds_two_and_three` — the function becomes the group, the `; "..."` string is the test name. A failure names a case, not the function. Split the naming accordingly:

- **The function names the group** — what every case shares: the behavior family and what varies (`add`, `split_between_markers`). The pinned outcome is left to each case.
- **The `; "..."` string names the test** — it does the pinned-outcome job. It accepts any static str, but enforce snake_case: lowercase, words joined with `_` (`adds_two_and_three`, never `adds two and three`).

Done when the function names the group and every `; "..."` is snake_case and states what that case pins.

### Other parametrized crates

rstest and the rest split naming the same way — function is the group, the per-case label is the test name; only the label syntax varies (rstest: `#[case::name(...)]`). Before building CI filters on case names, check the crate's docs for how it assembles the printed path.