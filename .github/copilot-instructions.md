# Copilot Instructions for pym2v

Practical instructions for Copilot-based edits and automation in this repository. Include commands, architecture overview, and repository-specific conventions Copilot should follow.

## Build, test, and lint (quick commands)

Prefer Taskfile tasks where available (Taskfile.yml lives at the repo root):

```bash
# Quick setup (creates .env from .env.example, installs tools, syncs deps)
task setup

# Run linters (pre-commit + ruff)
task lint

# Run full test suite
task test
```

Direct uv commands (used by CI and Taskfile):

```bash
# Install dependencies (all groups + extras)
uv sync --all-groups --all-extras

# Run a single test file
uv run pytest tests/test_api.py

# Run a single test by name or expression
uv run pytest -k "test_get_machines"

# Run all tests
uv run pytest

# Run linters directly
uv tool run pre-commit run --all-files

# Build and serve docs locally
uv run mkdocs serve

# Test release flow (uses .env and testpypi index)
task test-release
```

Hints:
- `.env.example` exists in the project root; use `task create-env-file` or `task setup` to copy it to `.env`.
- See `pyproject.toml` and `Taskfile.yml` for CI, linting and test options (pytest markers, ruff rules, coverage thresholds).

## High-level architecture

This package is a thin Python client for the Eurogard m2v industrial IoT platform. Key files and responsibilities:

- `src/pym2v/api.py` — EurogardAPI: the primary client wrapper. Uses `httpx` + `httpx-auth` and exposes sync/async methods to fetch machines, measurement metadata, and historical frames.
- `src/pym2v/settings.py` — pydantic-settings based configuration (env prefix: `EUROGARD_`).
- `src/pym2v/logger.py` — small logging helper for consistent formatting.
- `src/pym2v/*` — helpers for data transformation; frames are returned as `polars` DataFrames.
- `tests/` — pytest tests; network interactions are mocked (see `conftest.py`).
- Docs: `mkdocs.yml` + `docs/` with mkdocstrings pointing at `src/`.

Data flow (common developer mental model):
1. Instantiate `EurogardAPI()` → Client + OAuth2 auth is prepared.
2. Query machines and measurement names.
3. Request historical data via `get_frame_from_names()` (returns `pl.DataFrame`) or `get_long_frame_from_names()` which batches long ranges.
4. Async variant `aget_frame_from_names()` exists for concurrent fetching.

## Key conventions (do not change lightly)

- Python version: >=3.12, <3.14 (see `pyproject.toml`).
- Type hints required; package is `py.typed`.
- Docstrings follow Google style; ruff enforces docstring rules.
- Use `SecretStr` (pydantic) for secrets; access via `.get_secret_value()` only when needed.
- Retry logic: tenacity is used for transient API errors (see decorated functions in `api.py`).
- DataFrames: polars is the canonical API (not pandas). Returned frames include a `timestamp` column.
- Tests: tests mock `httpx` client; use the `api` pytest fixture. Marker `local` is available; CI runs with `-m "not local"` by default.
- Linting: pre-commit + ruff. `task lint` is the canonical entrypoint.
- Releases: use `uv version` and `task bump-version` / `task create-git-tag` as in Taskfile.
- Docs: mkdocs + mkdocstrings; handlers configured in `mkdocs.yml` (paths: `src`).

Repo conventions for automation/agents
- When creating commits programmatically, include this trailer at the end of the commit message exactly as shown:

  Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>

- Prefer Taskfile tasks for multi-step operations so CI mirrors local actions.

## Where to look for more details
- `README.md` — usage examples and basic setup.
- `CONTRIBUTING.md` — contributor workflow (uses Taskfile and uv).
- `Taskfile.yml` — canonical developer tasks (setup, lint, test, release helpers).
- `pyproject.toml` — ruff, pytest, coverage and dependency groups.
- `.github/workflows/` — CI and docs publishing workflows.

----

If you'd like this file adjusted (more/less detail, examples for a Copilot agent to run specific flows), say which areas to expand.
