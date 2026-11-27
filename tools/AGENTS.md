# tools

Python tooling for this repo. `tools/pyproject.toml` holds the shared `ruff` and `ty` dev tools; `uv.lock` is the workspace lock file. Each package keeps its own `AGENTS.md` with commands that run from its directory.

## Verify

```sh
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
