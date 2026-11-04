# Tools

Python tooling for this repo: a uv workspace rooted here. `validate-skill/` is its only member package.

Shared dev tools (ruff, ty) belong in this root `pyproject.toml`; runtime dependencies belong in `validate-skill/pyproject.toml`. The root is `package = false`.

## Verify

Run from this directory. Done when all four exit 0:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python -m unittest discover -s validate-skill/tests`

If a tool is unavailable, report that check as unverified instead of skipping it silently.
