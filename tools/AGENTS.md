# Tools

Python tooling for this repo. `tools/pyproject.toml` holds the shared `ruff` and `ty` dev tools. The `creating-skills` port and its standard-library test suite live under `tools/skills/creating-skills`.

## Verify

Run from this directory. Done when all four exit 0:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python -m unittest discover -s skills/creating-skills/tests -t skills/creating-skills`

The `-t` argument makes `scripts` importable from the test modules.
