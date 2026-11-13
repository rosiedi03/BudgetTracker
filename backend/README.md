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

## API conventions (for frontend work)

The interactive docs at `/docs` list every endpoint and field. A few rules apply everywhere:

- **Money** is a JSON string with exactly two decimal places: `"12.50"`. Requests accept a string or a number (`"12.50"` or `12.5`), but amounts must be positive, at most `99999999.99`, and have no fractions of a cent. Parse responses with a decimal-safe approach, not floating-point math.
- **Percentages** are JSON numbers rounded to one decimal place: `45.5`. Shares under 0.05% round to `0.0`. If a percentage is `0.0` but its matching amount isn't zero, display it as `<0.1%`. Rounded percentages may not add up to exactly 100.

## Tests and checks

Run all four before committing; each should finish with no errors.

```sh
uv run pytest               # tests
uv run ruff check           # lint (add --fix to auto-fix what it can)
uv run ruff format --check  # formatting (run without --check to reformat files)
uv run pyright              # type checking
```

Lint and type-checker settings live in `pyproject.toml` under `[tool.ruff]` and `[tool.pyright]`. The first `pyright` run downloads its own copy of Node.js, so it needs internet access once.

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
│       ├── main.py         # creates the app; startup, middleware, router wiring
│       ├── db.py           # database engine, sessions, startup seeding
│       ├── models.py       # database tables (SQLAlchemy models)
│       ├── deps.py         # shared endpoint dependencies (current user)
│       ├── budgets.py      # saving and looking up monthly budgets
│       ├── schemas/        # request/response shapes; money.py handles amounts and cents
│       └── routers/        # endpoints, one module per area
└── tests/
    ├── conftest.py         # shared fixtures (test database, users, adding transactions)
    └── helpers.py          # shared constants and types (seeded category ids, fixture types)
```

The database is a SQLite file, `budgettracker.db`, created in the directory you start the server
from. Set `BUDGETTRACKER_DATABASE_URL` to use a different location. There are no migrations: after a
model changes, delete the `.db` file and restart.

Code lives in an installable package under `src/`, so imports use the package name, for example `from budgettracker.main import app`.
