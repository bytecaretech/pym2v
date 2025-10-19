# Contributing

1. Install uv
1. Install project dependencies: `uv sync`
1. Install pre-commit hooks: `uv run pre-commit install`
1. Create a dedicated development branch: `git checkout -b <hyphen-delimited-branch-name>`
1. Add your changes
1. Run linters: `uv run pre-commit run --all-files`
1. Run tests: `uv run pytest`
1. Commit changes and open a pull request
