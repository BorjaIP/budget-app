# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, and others) working in this repository.

## Project Overview

Personal budget/expense management app built with **Reflex** (Python full-stack framework that compiles to React). Uses SQLite for storage, SQLModel as ORM, and a **local** Ollama model for expense categorization (no data leaves the machine).

## Sensitive data (HARD RULE)

- `data/` holds personal bank exports (`.xls`, `.xlsx`, `.csv`), the SQLite database and uploads.
  AI agents MUST NOT read, list, grep, open, copy, print or otherwise inspect anything inside `data/`,
  and MUST NOT paste its contents anywhere (logs, tests, fixtures, commits, prompts to other models).
  Permission rules in `.claude/settings.json` enforce this for file tools. Do not work around them
  with the shell, `python`, `sqlite3`, `pandas`, etc.
- Only the application and the owner's own scripts read `data/`. If you need to understand the data,
  ask the owner for the schema. The code-level schema lives in `dashboard/database/models.py` and
  `dashboard/utils/file_reader.py`.
- Tests and examples use synthetic data created in temporary directories, never the real `data/`.
  `dashboard/database/operations.py` creates `db_manager` at import time, which opens
  `data/expenses.db` relative to the cwd: tests must `monkeypatch.chdir(tmp_path)` before importing it.
- A script that must run against real data prints aggregates only (counts, percentages, timings),
  never concept text, amounts or dates of individual rows.
- `.env` holds VPN credentials: never read, print or commit it. Validate the compose file with
  `docker compose ... config --quiet`; plain `config` prints interpolated secrets.

## Commands

Dependencies are managed with **uv** only. `pyproject.toml` + `uv.lock` are the single source of truth
(there are no `requirements*.txt` files).

```bash
make install      # uv sync (creates/updates .venv)
make up           # install + run the Reflex dev server (hot reload) inside .venv
make docker-up    # build and start the full stack (app + Ollama + VPN)
make docker-down  # stop the stack

uv run pytest tests/ -q          # unit tests (synthetic data only)
uv add 'package<=X.Y.Z'          # add a dependency, pinned with an upper bound (see below)
```

Dependency convention: every dependency in `pyproject.toml` uses `<=` with the version that was
verified to work, as a reference ceiling (for example `pandas<=3.0.6`). Upgrading means bumping that
ceiling after running the tests and the app.

## Architecture

Only `dashboard/` is active. The `budget_app/` directory is a legacy implementation (mostly commented out).

The Reflex app is configured in `rxconfig.py` with `app_name="dashboard"`. Entry point is `dashboard/dashboard.py`.

### Key layers (all under `dashboard/`)

- **Pages** (`pages/`): route handlers. The expenses page is at `expenses/page.py` → `/expenses`.
- **State** (`expenses/state.py`): `TableState`, the Reflex reactive state for pagination, filtering, sorting, uploads, categorization and database access.
- **Database** (`database/`): `DatabaseManager` in `operations.py` wraps SQLModel/SQLite. `models.py` defines the `Expense` table. The database file lives in `data/expenses.db`. Schema changes on existing databases go through the additive guarded migration in `DatabaseManager._migrate_schema` (there is no Alembic).
- **File processing** (`utils/`): `FileReader` parses uploaded `.xls`/`.xlsx` bank exports with Pandas (`xlrd` for `.xls`, `openpyxl` for `.xlsx`). `FileProcessor` handles the upload-to-database pipeline with deduplication.
- **LLM** (`llm/`): `llm_call.py` calls Ollama (default model `qwen2.5:3b-instruct`) at `OLLAMA_BASE_URL` (default `http://localhost:11434`). The prompt (`prompt.py`) asks for `[Category][Subcategory]`; few-shot examples come from rows the user tagged by hand (`category_source = "manual"`), falling back to static examples. `CATEGORY_TAXONOMY` is reviewed by the owner: **never change its categories or subcategories**.
- **UI components** (`components/`), **templates** (`templates/template.py`), **styles** (`styles.py`, Radix UI theme).

### Data flow

1. User uploads an Excel file → `FileProcessor` validates and reads it via `FileReader`.
2. Parsed expenses are inserted into SQLite via `DatabaseManager` (deduplicated by hash).
3. `TableState` loads from the database and renders the expense table.
4. The "Recategorizar" button resets non-manual rows and sends them to the local Ollama model; manual tags are preserved and feed the few-shot prompt.

### Docker

`docker/docker-compose.yaml` runs:

- **gluetun**: VPN container (Private Internet Access); Ollama shares its network namespace, so other containers reach Ollama at `gluetun:11434`.
- **ollama**: LLM inference with NVIDIA GPU support (image `latest`).
- **model-pull**: one-shot job that pulls the categorization model, retrying until the VPN is up.
- **app**: this application (`Dockerfile`), ports 3000/8000, with `data/` mounted at `/app/data`.

Requires `.env` with `OPENVPN_USER` and `OPENVPN_PASSWORD`.

## Conventions

- Conventional Commits. Never stage unrelated work: add explicit paths, not `git add -A`.
- Generated technical artifacts (code, comments, docs, tests) are written in English.
- `odd/` and `.atl/` are local gentle-ai workflow files and are git-ignored.
