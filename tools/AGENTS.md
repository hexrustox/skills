# Tools

Python tooling for this repo. `tools/pyproject.toml` holds the shared `ruff` and `ty` dev tools.

## Verify

Run from this directory:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
