# Feature: local categorization via Ollama, dockerized deployment

## Objective

Categorization of expenses must run entirely on local hardware (no frontier
model reads user financial data), via Ollama in Docker (kept behind the
existing Gluetun/PIA VPN — needed because the user's ISP blocks model
downloads without it). The app itself gets a Dockerfile so `docker compose up`
runs app + Ollama together. The "Recategorizar" button must work end-to-end
against this stack.

## Why

- User explicitly rejected any frontier/cloud LLM touching their bank data.
- Current hardware (GTX 1650 SUPER, 4GB VRAM, 9.7GB RAM in WSL2) makes the
  current `mistral:7b-instruct-v0.2-q3_K_M` borderline; a smaller instruct
  model suits this closed-set classification task better and leaves headroom.
- VPN wrapper (Gluetun) stays: user needs it to pull models past ISP blocking,
  not for privacy of the app itself.

## Constraints

- Do NOT modify `CATEGORY_TAXONOMY` in `dashboard/llm/llm_call.py:8-60` — user
  reviewed and finalized these categories/subcategories already.
- Keep Gluetun/PIA VPN wrapping around the Ollama service.
- No test runner exists yet in this repo (no `tests/`, no pytest declared) →
  Strict TDD resolves to **false** (fails closed per no-runner rule). Add
  pytest as a dev dependency and cover new pure-logic functions with plain
  tests, but this is not gated by red/green/refactor.
- Delivery strategy: `single-pr` per user ("no hay presupuesto, pusheo a
  master"), single feature branch, work-unit commits.

## Scope

1. Swap Ollama model to `qwen2.5:3b-instruct` (fits 4GB VRAM, good multilingual
   instruction-following for short structured outputs); bump the `ollama`
   image tag in `docker/docker-compose.yaml` from pinned `0.6.3` to `latest`.
2. Add `category_source: Optional[str]` (`"manual" | "llm"`) to `Expense` /
   `ExpenseBase` in `dashboard/database/models.py`, and set it correctly in
   `dashboard/database/operations.py::update_category` based on caller intent
   (manual edit in `state.py:283` vs LLM assignment in `state.py:371`).
3. Fix `dashboard/llm/prompt.py` to request `[Categoria][Subcategoria]` (two
   brackets) instead of a single ambiguous tag, and build the few-shot section
   dynamically from real `category_source="manual"` rows instead of the 3
   hardcoded examples, falling back to the current static examples when there
   isn't enough manually-tagged data yet.
4. Make the Ollama base URL configurable via `OLLAMA_BASE_URL` env var in
   `dashboard/llm/llm_call.py` (default `http://localhost:11434` for local
   dev), since in Docker the app must reach Ollama via the `gluetun` service
   (Ollama runs with `network_mode: service:gluetun`, so it has no DNS name of
   its own — other containers reach it via `gluetun:11434`).
5. Add `Dockerfile` for the Reflex app (uv-based, matches `pyproject.toml`).
6. Update `docker/docker-compose.yaml`: add the app service on the same
   network as `gluetun`, wire `OLLAMA_BASE_URL=http://gluetun:11434`, bump
   Ollama image tag, add a one-shot init step to `ollama pull
   qwen2.5:3b-instruct` automatically on `docker compose up`.
7. Update `Makefile` with a target to run the dockerized stack (keep existing
   `make up`/`make install` for local non-docker dev as-is).
8. Add minimal pytest coverage for the new pure functions (prompt/few-shot
   builder, response parsing) — add `pytest` as a dev dependency via
   `uv add --dev pytest`.

## Tasks

- [x] T1 — Explore codebase, hardware, confirm scope (this session)
- [x] T2 — Model + docker-compose changes (image tag, model, VPN kept, app
      service, network wiring, OLLAMA_BASE_URL, auto-pull init step)
- [x] T3 — `category_source` field + `update_category` provenance wiring
- [x] T4 — Prompt fix (two-bracket output) + dynamic few-shot builder using
      manually-tagged examples + parsing update
- [x] T5 — App `Dockerfile`
- [x] T6 — `Makefile` docker target
- [x] T7 — pytest dev dependency + unit tests for prompt/few-shot builder and
      response parser
- [ ] T8 — Manual verification: `docker compose up` builds & serves; button
      "Recategorizar" categorizes against local Ollama — **not done in this
      sandbox** (no internet-heavy Docker build, no real Ollama pull, no UI
      click available here). Left for the user to run manually.

## Verification (per task)

- `uv run python -c "import ast; ast.parse(open('dashboard/llm/llm_call.py').read())"` (or run the new pytest suite once added) for logic changes.
- `docker compose -f docker/docker-compose.yaml --env-file .env config` to validate compose syntax after edits.
- Manual: `make docker-up` (new target), confirm 3 containers up, confirm Ollama pull runs, click "Recategorizar" in the running app.

## Progress

T2-T7 implemented in a single commit (see below). Also discovered along the
way: the SQLModel table is actually named `expense` (singular), not
`expenses` — the additive migration in `DatabaseManager._migrate_schema`
reads `Expense.__tablename__` rather than hardcoding a name, and was verified
against the real local `expenses.db` (column `category_source` confirmed
added via `PRAGMA table_info`). Also found and fixed a pre-existing ambiguity
in single-bracket fallback parsing: "Transporte" is both a top-level category
and a subcategory of "Viajes" — precedence now checks top-level category
match first.

Verified in this sandbox:
- `uv run pytest tests/ -q` → 13 passed.
- `uv run python -c "from dashboard.llm import llm_call; ..."` → imports OK,
  including a live run of the new schema migration against the real
  `expenses.db`.
- `docker compose -f docker/docker-compose.yaml --env-file .env config` →
  valid, resolved config printed (compose auto-added implicit
  `depends_on`/`condition` entries because of `network_mode: service:gluetun`
  on `ollama`; this is expected/harmless).

NOT verified (no internet-heavy build / real GPU/Ollama available here):
- Docker image actually builds (`docker compose up --build`).
- `model-pull` one-shot container actually pulls `qwen2.5:3b-instruct`.
- The `app` container starts, serves 3000/8000, and reaches Ollama at
  `gluetun:11434`.
- Clicking "Recategorizar" end-to-end against a live local Ollama.

Commit: see `git log -1` on `feature/local-categorization-docker` for the
hash (single commit covering T2-T7).
