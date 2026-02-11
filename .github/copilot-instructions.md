# Copilot Instructions for pym2v

## Build, Test, and Lint

```bash
# Install dependencies
uv sync

# Run all tests with coverage
uv run pytest

# Run a single test file
uv run pytest tests/test_api.py

# Run a single test by name
uv run pytest -k "test_get_machines"

# Run linters (ruff + pre-commit hooks)
uv run pre-commit run --all-files

# Build docs locally
uv run mkdocs serve
```

## Architecture

This is a Python wrapper for the Eurogard m2v industrial IoT platform API. The package uses OAuth2 authentication with resource owner password credentials flow.

### Core Components

- **`EurogardAPI`** (`src/pym2v/api.py`): Main client class using `httpx.Client` with `httpx-auth` for OAuth2. Methods return raw dicts or polars DataFrames.

- **`Settings`** (`src/pym2v/settings.py`): Pydantic Settings based configuration loaded from environment variables (prefix: `EUROGARD_`) or `.env` file.

- **Logger** (`src/pym2v/logger.py`): Stdlib logging wrapper with consistent formatting.

### Data Flow

1. Create `EurogardAPI()` → httpx client with OAuth2 auth is initialized
2. Get machines/routers → returns paginated dict with `entities` list
3. Get measurements for a machine UUID → returns measurement metadata
4. Fetch historical data → `get_frame_from_names()` returns polars DataFrame, `get_long_frame_from_names()` handles large time ranges by batching

### Async Support

`aget_frame_from_names()` provides native async fetching using `httpx.AsyncClient`. Semaphore for rate limiting is configurable via `max_concurrent_requests` constructor parameter.

## Conventions

- **Docstrings**: Google style, enforced by ruff (`D` rules)
- **Type hints**: Required throughout; package is `py.typed`
- **Secrets**: Use `SecretStr` from pydantic for sensitive values; access via `.get_secret_value()`
- **Retries**: API calls that may fail use tenacity with exponential backoff (see `@retry` decorator on `get_historical_data`)
- **Testing**: All API tests mock the httpx client; use the `api` fixture from `conftest.py`
- **Timestamps**: Use `datetime` objects directly; API conversion to milliseconds is handled internally
- **Intervals**: Use `timedelta` objects directly
- **DataFrames**: Use polars, not pandas. DataFrame methods return `pl.DataFrame` with a `timestamp` column
