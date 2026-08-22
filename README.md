# skills

Personal collection of Agent Skills — language-agnostic testing and writing skills, plus Rust-specific testing and code style.

## About

These are first-party skills in the standard Agent Skills format ([spec](https://agentskills.io)). Skills-compatible agents load them via progressive disclosure: the frontmatter `description` is available at startup, and the full `SKILL.md` instructions load when a task matches.

## Installation

Install with the [skills CLI](https://skills.sh/docs):

```bash
npx skills add https://github.com/hexrustox/skills --list   # preview the skills
npx skills add https://github.com/hexrustox/skills          # install all skills
```

Add `-s <name>` to install one skill, or `-a <agent>` to target a specific agent (e.g. `opencode`).

## Skills

### General

| Skill | What it does | When to use |
| --- | --- | --- |
| `choosing-test-type` | Decision tree for unit, integration, property, or no test, possibly more than one type per behavior | Writing or reviewing tests, any language |
| `writing-test-cases` | Design the case set for a behavior: spec-first expectations, one case per path, strong assertions, red-proofed | Writing or adding tests, or reviewing a suite, any language |
| `writing-error-messages` | One-voice error message rules | Writing, editing, or reviewing error text, any language |

### Rust

| Skill | What it does | When to use |
| --- | --- | --- |
| `rust-dependencies` | Write every Cargo.toml dependency at its exact `major.minor.patch` minimum; route workspace versions through `[workspace.dependencies]` with per-crate `workspace = true` activation | Adding, installing, or bumping a dependency or dev-dependency in a Rust project |
| `rust-code-style` | Cosmetic Rust style: comments, naming, imports, visibility, annotations | Writing, editing, or reviewing Rust |
| `rust-test-case-crate` | Parametrized tests with the `test-case` crate | Many cases from one test function |
| `rust-insta-crate` | Snapshot testing with the `insta` crate | Pinning a value's output in Rust tests |
| `rust-proptest-crate` | Property-based testing with the `proptest` crate | Invariants that must hold across generated inputs |
| `rust-miette-crate` | Fancy diagnostics with the `miette` crate: `#[derive(Diagnostic)]` errors, `#[label]` positioned notes, `help` advice, `miette::Result` rendering | Writing, editing, or reviewing miette error types and error handling in Rust |
