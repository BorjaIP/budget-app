#!/usr/bin/env bash
# Render the app with synthetic data in a throwaway copy and save screenshots.
# Never touches the real database. Needs docker (official Playwright image) and network on first run.
#
# Usage: scripts/ui_preview.sh <out-dir> [route ...]    (default routes: / /transactions /settings /about)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(realpath -m "${1:?usage: ui_preview.sh <out-dir> [route ...]}")"
shift || true
ROUTES=("$@")
[ "${#ROUTES[@]}" -gt 0 ] || ROUTES=(/ /transactions /settings /about)

PREVIEW="${PREVIEW_DIR:-$HOME/.cache/budget-app-ui-preview}"
FRONT=3100
BACK=8100
IMAGE=mcr.microsoft.com/playwright/python:v1.49.1-noble
LOG="$PREVIEW/reflex.log"

stop_app() { pkill -f "reflex run --env dev --frontend-port $FRONT" 2>/dev/null || true; }
trap stop_app EXIT

mkdir -p "$PREVIEW" "$OUT"
# Refresh sources only; keep .web so the frontend is not rebuilt from scratch every run.
rm -rf "$PREVIEW/dashboard" "$PREVIEW/assets" "$PREVIEW/demo.db"
cp -r "$REPO/dashboard" "$REPO/assets" "$REPO/rxconfig.py" "$PREVIEW/"
find "$PREVIEW/dashboard" -name __pycache__ -type d -prune -exec rm -rf {} +

(cd "$PREVIEW" && PYTHONPATH="$PREVIEW" uv run --project "$REPO" python "$REPO/scripts/seed_demo_data.py" "$PREVIEW/demo.db")

stop_app
: > "$LOG"
(cd "$PREVIEW" && DATABASE_URL="sqlite:///$PREVIEW/demo.db" nohup uv run --project "$REPO" \
  reflex run --env dev --frontend-port "$FRONT" --backend-port "$BACK" > "$LOG" 2>&1 &)

for _ in $(seq 1 220); do
  grep -q "App Running" "$LOG" && break
  sleep 3
done
if ! grep -q "App Running" "$LOG"; then
  tail -n 25 "$LOG"
  echo "the app did not start" >&2
  exit 1
fi
sleep 5

# The image ships the browsers but not the Python package; install it for this run only.
docker run --rm --network host --ipc=host --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$OUT:/out" -v "$REPO/scripts/ui_shots.py:/ui_shots.py:ro" \
  "$IMAGE" sh -c 'pip install -q --user --break-system-packages playwright==1.49.1 && python /ui_shots.py "$@"' \
  sh "http://localhost:$FRONT" /out "${ROUTES[@]}"
