# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, and others) working in this repository.

## Project Overview

Personal budget/expense management app built with **Reflex** (Python full-stack framework that compiles to React). Uses SQLModel as ORM over SQLite (local development) or PostgreSQL (Docker), and a **local** Ollama model for expense categorization (no data leaves the machine).

## Sensitive data (HARD RULE)

- `data/` holds personal bank exports (`.xls`, `.xlsx`, `.csv`), the SQLite database and uploads.
  AI agents MUST NOT read, list, grep, open, copy, print or otherwise inspect anything inside `data/`,
  and MUST NOT paste its contents anywhere (logs, tests, fixtures, commits, prompts to other models).
  Local permission rules in `.claude/settings.json` (not committed) enforce this for file tools. Do not work around them
  with the shell, `python`, `sqlite3`, `pandas`, etc.
- Only the application and the owner's own scripts read `data/`. If you need to understand the data,
  ask the owner for the schema. The code-level schema lives in `dashboard/database/models.py` and
  `dashboard/utils/file_reader.py`.
- Tests and examples use synthetic data created in temporary directories, never the real `data/`.
  `dashboard/database/operations.py` creates `db_manager` at import time and opens the database lazily on
  first use (`data/expenses.db`, relative to the cwd, for the default SQLite URL): tests must
  `monkeypatch.chdir(tmp_path)` before touching it.
- To look at the UI, use `scripts/ui_preview.sh` (it seeds an invented database with
  `scripts/seed_demo_data.py`); never screenshot or open the app running on the real database.
- A script that must run against real data prints aggregates only (counts, percentages, timings),
  never concept text, amounts or dates of individual rows.
- `.env` may hold credentials and settings overrides: never read, print or commit it. Validate the compose
  file with `docker compose ... config --quiet`; plain `config` prints interpolated values.

## Commands

Dependencies are managed with **uv** only. `pyproject.toml` + `uv.lock` are the single source of truth
(there are no `requirements*.txt` files).

```bash
make install      # uv sync (creates/updates .venv)
make up           # install + run the Reflex dev server (hot reload) inside .venv
make docker-up    # build and start the full stack (app + Ollama + PostgreSQL)
make docker-down  # stop the stack

uv run pytest tests/ -q          # unit tests (synthetic data only)
scripts/ui_preview.sh /tmp/shots # screenshots (desktop/mobile, light/dark) of a throwaway copy with synthetic demo data
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
- **Config** (`config.py`): `Settings` (pydantic-settings) reads environment variables and `.env`: `DATABASE_URL` (default `sqlite:///data/expenses.db`; PostgreSQL in Docker), `OLLAMA_BASE_URL`, `uploaded_files_dir`.
- **Database** (`database/`): `DatabaseManager` in `operations.py` wraps SQLModel and creates its engine lazily from `settings.database_url`. `models.py` defines the `Expense` table. Schema changes on existing SQLite databases go through the additive guarded migration in `DatabaseManager._migrate_schema` (SQLite only; there is no Alembic).
- **File processing** (`utils/`): `FileReader` parses uploaded `.xls`/`.xlsx` bank exports with Pandas (`xlrd` for `.xls`, `openpyxl` for `.xlsx`). `FileProcessor` handles the upload-to-database pipeline with deduplication.
- **LLM** (`llm/`): `llm_call.py` calls Ollama (default model `qwen2.5:3b-instruct`) at `settings.ollama_base_url` (env `OLLAMA_BASE_URL`, default `http://localhost:11434`). The prompt (`prompt.py`) asks for `[Category][Subcategory]`; few-shot examples come from rows the user tagged by hand (`category_source = "manual"`), falling back to static examples. `CATEGORY_TAXONOMY` is reviewed by the owner: **never change its categories or subcategories**.
- **UI components** (`components/`), **templates** (`templates/template.py`), **styles** (`styles.py`, Radix UI theme).

### Data flow

1. User uploads an Excel file → `FileProcessor` validates and reads it via `FileReader`.
2. Parsed expenses are inserted into the configured database via `DatabaseManager` (deduplicated by hash).
3. `TableState` loads from the database and renders the expense table.
4. The "Recategorizar" button resets non-manual rows and sends them to the local Ollama model; manual tags are preserved and feed the few-shot prompt.

### Docker

`docker/docker-compose.yaml` runs:

- **ollama**: LLM inference with NVIDIA GPU support (image `latest`), port 11434 published on the host.
- **model-pull**: one-shot job that pulls the categorization model from the Ollama registry, retrying until it succeeds.
- **postgres**: PostgreSQL 17 for the app, reachable only on the compose network (development credentials live in the compose file).
- **app**: this application (`Dockerfile`), ports 3000/8000, configured with `DATABASE_URL` and `OLLAMA_BASE_URL`; uploads are mounted from `data/uploaded_files`.

No VPN container is part of the stack.

## UI conventions

Minimalist look: warm sand grays, a neutral accent, 1px hairline borders, no shadows or gradients,
Geist (self-hosted in `assets/fonts`), sentence case and no emojis.

- Reuse the shared pieces: `components/card.py` (surface), `page_header.py`, `empty_state.py`,
  `notice.py` (inline error with retry) and `icon.py` (Radix Icons; do not use `rx.icon`, it renders Lucide).
- Money and counters use `class_name="num"` (tabular digits) and are right-aligned in tables. Color is
  semantic only: green for income and positive savings, red for expenses, negative savings and errors;
  expenses and income must always be distinguishable at a glance (amounts, totals and chart series).
- Icon-only controls and inputs without a visible label need an accessible name
  (`custom_attrs={"aria-label": ...}`); active navigation sets `aria-current`.
- Loading uses skeletons. Failures are logged with `logging` and shown as `error_notice`; raw exceptions
  never reach the user.
- Reflex 0.10 specifics: `set_<var>` setters are not generated (declare them), responsive enum props use
  `rx.breakpoints(...)`, and decorated pages must be imported in `dashboard/dashboard.py`.
- Check changes with `scripts/ui_preview.sh` (desktop and mobile, light and dark) and keep
  `tests/test_app_compiles.py` green; an HTTP 200 from the dev server does not prove a page exists.

## Conventions

- Conventional Commits. Never stage unrelated work: add explicit paths, not `git add -A`.
- Generated technical artifacts (code, comments, docs, tests) are written in English.
- `odd/` and `.atl/` are local gentle-ai workflow files and are git-ignored.
