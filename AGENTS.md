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
- **Config** (`config.py`): `Settings` (pydantic-settings) reads environment variables and `.env`: `DATABASE_URL` (default `sqlite:///data/expenses.db`; PostgreSQL in Docker), `OLLAMA_BASE_URL`, `LOG_LEVEL`, `uploaded_files_dir`.
- **Database** (`database/`): `DatabaseManager` in `operations.py` wraps SQLModel and creates its engine lazily from `settings.database_url`. `models.py` defines the `Expense` table. Schema changes on existing SQLite databases go through the additive guarded migration in `DatabaseManager._migrate_schema` (SQLite only; there is no Alembic).
- **File processing** (`utils/`): `FileReader` parses uploaded `.xls`/`.xlsx` bank exports with Pandas (`xlrd` for `.xls`, `openpyxl` for `.xlsx`). `FileProcessor` handles the upload-to-database pipeline with deduplication.
- **LLM** (`llm/`): `llm_call.py` calls Ollama (default model `qwen2.5:3b-instruct`) at `settings.ollama_base_url` (env `OLLAMA_BASE_URL`, default `http://localhost:11434`) in two constrained steps: first the category among the names in the user's taxonomy, then the subcategory of that category (or none). Answers are restricted with Ollama structured outputs, so they are always valid. Prompts live in `prompt.py`; nothing in code names a category.
- **Taxonomy** (`taxonomy.py`, `database/taxonomy_repository.py`, `taxonomy_state.py`, page `/categories`): the categories and subcategories are user data (tables `category`, `subcategory`, each with an optional description that is sent to the model). `DEFAULT_TAXONOMY` is the owner's original list: it seeds a new database and is what "Restaurar originales" brings back; the owner reviewed it, so do not edit it casually. An expense has a category and an optional subcategory; without a valid subcategory it stays in its category, without a valid category it is Otros / General (reserved: it cannot be renamed or deleted). Renaming follows through expenses, merchant labels and budgets; deleting a category sends its expenses to Otros / General. Each category is for expenses or for income (`kind`; the owner's default income category is Nómina); a movement is classified only among the categories of its own kind, decided by the sign of its amount, plus Otros, and merchant memory never crosses kinds. Never hard-code category names in logic or UI: read them from the repository (`db_manager.taxonomy.load()`) or `TaxonomyState`.
- **UI components** (`components/`), **templates** (`templates/template.py`), **styles** (`styles.py`, Radix UI theme).

### Categorization pipeline

`expenses/state.py::categorize_pending_expenses` is a background event (it keeps running when the user changes
page; blocking database calls run in threads). Each movement goes through, cheapest first:

1. **Merchant memory** (`MerchantLabel`, `llm/merchant.py::merchant_key`): a merchant the user already corrected
   is reused with `category_source="memory"`. No model call, always the same answer. A manual correction is saved
   with `DatabaseManager.learn_from_correction`, which also applies it to the merchant's non-manual rows.
2. **Similarity** (`llm/retrieval.py`, character 3-gram TF-IDF cosine): a labeled movement at least 0.85 similar,
   with no close rival of another category, is reused with `category_source="similar"`.
3. **Model, two constrained steps** (`llm/llm_call.py`): the 8 most similar labeled merchants go in the prompt (plus
   the generic examples while there are fewer than 20 labels), temperature 0. With more than 30 categories
   `llm/shortlist.py` offers only the plausible ones (those of similar labels, the most used, unused ones whose
   name or description matches) so the result does not degrade as the taxonomy grows. The answer stores
   `category_confidence` (product of both steps' probabilities, from Ollama `logprobs`).

Rows without category, or from the model below `LLM_CONFIDENCE_THRESHOLD` (default 0.6, not calibrated), are the
"Por revisar" queue. When a run ends, a global dialog (`components/categorization_results.py`) summarizes it and
lists the doubtful merchants one by one (correct the badge, or "Está bien", which stores a hand-made label).
A progress strip shows on every page while it runs. Manual rows are never overwritten.

New columns on `expense` go through `DatabaseManager._ADDED_COLUMNS` (works on SQLite and PostgreSQL).
`scripts/eval_similarity.py` measures similarity strategies on the owner's own labels (aggregates only).
Background and references: `docs/categorization-strategy.md`.

### Logging

The `dashboard` logger writes to stdout (`docker logs budget-app`). At `INFO` a categorization run logs only
aggregates (`RunStats.summary()`: counts, fallbacks to Otros/General, errors, average ms, top categories) and
warns on every fallback. Concepts and raw model answers come from bank data and are logged only with
`LOG_LEVEL=DEBUG`; never paste those logs anywhere.

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
- The overview period (`dashboard/periods.py`: Mes, 3 meses, 12 meses, Año, Todo, or a year) is anchored on the
  newest date in the data; category rows and the "sin categorizar" notice drill down into Gastos via
  `TableState.drill_down`.
- Charts follow the `data-visualization` skill: start bar axes at zero, give every chart a text alternative
  (`chart_summary`), mark benchmarks (dashed average line) and do not rely on color alone (income carries a `+`).
- Check changes with `scripts/ui_preview.sh` (desktop and mobile, light and dark) and keep
  `tests/test_app_compiles.py` green; an HTTP 200 from the dev server does not prove a page exists.

## Conventions

- Conventional Commits. Never stage unrelated work: add explicit paths, not `git add -A`.
- Generated technical artifacts (code, identifiers, file names, routes, comments, docs, tests) are written in English;
  only text the user sees in the UI is Spanish (and data values such as the category names).
- `odd/` and `.atl/` are local gentle-ai workflow files and are git-ignored.
