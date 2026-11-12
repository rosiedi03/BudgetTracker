# Budget Tracker — Backend

FastAPI backend for the Budget Tracker app. Dependencies and the Python version are managed with [uv](https://docs.astral.sh/uv/).

## Prerequisites

- **uv**: install it with your package manager or by following the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).
- **Python 3.14**: you don't need to install it yourself. uv reads `.python-version` and downloads the correct interpreter automatically.

## Setup

Run every command below from this `backend/` directory.

```sh
uv sync
```

This creates a `.venv/` virtual environment and installs all dependencies, including dev tools like pytest, at the exact versions pinned in `uv.lock`. You don't need to activate the venv. Prefix commands with `uv run` and they'll use it automatically.

## Running the server

```sh
uv run fastapi dev
```

The app's location (`budgettracker.main:app`) is set in `pyproject.toml` under `[tool.fastapi]`, so you don't need to pass a path. Dev mode auto-reloads when you save a file.

Once it's running:

- API: <http://127.0.0.1:8000>
- Interactive API docs (Swagger UI): <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

## Running tests

```sh
uv run pytest
```

## Managing dependencies

Don't use `pip install`. Use uv so `pyproject.toml` and `uv.lock` stay in sync:

```sh
uv add <package>          # runtime dependency
uv add --dev <package>    # dev-only dependency (testing, linting, etc.)
uv remove <package>
```

Commit both `pyproject.toml` and `uv.lock` after changing dependencies. Teammates then run `uv sync` to pick up the changes.

## Project layout

```
backend/
├── pyproject.toml          # project metadata, dependencies, tool config
├── uv.lock                 # pinned dependency versions (commit this)
├── src/
│   └── budgettracker/      # the application package
│       ├── __init__.py
│       └── main.py         # FastAPI app and routes
└── tests/
    └── test_main.py
```

Code lives in an installable package under `src/`, so imports use the package name, for example `from budgettracker.main import app`.
