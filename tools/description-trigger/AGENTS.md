# description-trigger

Standard-library Python CLI for testing whether a skill's description triggers at the right moments. This directory is one member of the `tools/` uv workspace; `tools/uv.lock` is the only lock file.

The package has no runtime dependencies. `uv_build` is a build-time backend only.

## Install

From the repository root:

```sh
uv tool install --editable tools/description-trigger
```

Rerun the install after changing the console entry point or package metadata. Source edits are reflected without reinstalling because the install is editable.

## Run

From the repository root:

```sh
description-trigger --help
```

Development fallback, from `tools/`:

```sh
uv run --all-packages description-trigger --help
```

## Test

From `tools/`:

```sh
uv run --all-packages python -m unittest discover -s description-trigger/tests -v
```

The suite drives the CLI from outside its project directory and asserts user-observable output and exit codes.

## Verify

From `tools/`, run the workspace-wide checks:

```sh
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

## Layout

- `src/description_trigger/` — package source.
- `tests/` — standard-library `unittest` suite.
