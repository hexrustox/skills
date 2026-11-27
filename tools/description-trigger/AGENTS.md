# description-trigger

Standard-library Python CLI for testing whether a skill's description triggers at the right moments. This directory is one member of the `tools/` uv workspace; `../uv.lock` is the only lock file.

The package has no runtime dependencies. `uv_build` is a build-time backend only.

## Install

```sh
uv tool install --editable .
```

Rerun the install after changing the console entry point or package metadata. Source edits are reflected without reinstalling because the install is editable.

## Run

```sh
description-trigger --help
```

The installed entry point works from any directory.

Development fallback:

```sh
uv run description-trigger --help
```

## Test

```sh
uv run python -m unittest discover -s tests -v
```

## Verify

Workspace-wide checks live in `../AGENTS.md`.

## Layout

- `src/description_trigger/` — package source.
- `tests/` — standard-library `unittest` suite.
