# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal budget/expense management app built with **Reflex 0.7.8** (Python full-stack framework that compiles to React). Uses SQLite for storage, SQLModel as ORM, and optionally integrates with Ollama for LLM-powered expense categorization.

## Commands

```bash
# Install dependencies (uses uv package manager)
pip install -r requirements/requirements.txt

# Run the Reflex development server (hot-reload enabled)
reflex run

# Start Docker services (Ollama LLM behind VPN)
docker compose -f docker/docker-compose.yaml --env-file .env up -d

# Type checking
mypy --install-types --non-interactive src/budget_app tests
```

There is no test suite configured yet.

## Architecture

**Two app directories exist but only `dashboard/` is active.** The `budget_app/` directory is a legacy implementation (mostly commented out).

The Reflex app is configured in `rxconfig.py` with `app_name="dashboard"`. Entry point is `dashboard/dashboard.py`.

### Key Layers (all under `dashboard/`)

- **Pages** (`pages/`): Route handlers for `/`, `/settings`, `/about`. The expenses page is at `expenses/page.py` → `/expenses`.
- **State** (`expenses/state.py`): `TableState` — Reflex reactive state managing pagination, filtering, sorting, file uploads, and database interaction.
- **Database** (`database/`): `DatabaseManager` in `operations.py` wraps SQLModel/SQLite operations. Models in `models.py` define `Expense` table. Database file is `expenses.db` at project root.
- **File Processing** (`utils/`): `FileReader` parses uploaded `.xls`/`.xlsx` bank export files using Pandas. `FileProcessor` handles the upload-to-database pipeline with deduplication.
- **LLM** (`llm/llm_call.py`): Async calls to Ollama (`mistral:7b-instruct-v0.2-q3_K_M`) at `localhost:11434` for auto-categorizing expenses using a Spanish category taxonomy.
- **UI Components** (`components/`): Navbar, sidebar. Templates in `templates/template.py` provide page wrapper with layout.
- **Styles** (`styles.py`): Centralized style definitions and Radix UI theme config.

### Data Flow

1. User uploads Excel file → `FileProcessor` validates and reads via `FileReader` (Pandas)
2. Parsed expenses inserted into SQLite via `DatabaseManager`
3. `TableState` loads from database and renders in the expense table view
4. Optionally, expenses are sent to Ollama for category assignment

### Docker Setup

`docker/docker-compose.yaml` runs two services:
- **Gluetun**: VPN container (Private Internet Access) — exposes port 11434
- **Ollama**: LLM inference with NVIDIA GPU support, networked through Gluetun

Requires `.env` with `OPENVPN_USER` and `OPENVPN_PASSWORD`.
