import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_ROUTES = {"/", "/expenses", "/budgets", "/categories", "/settings"}


def _registered_routes(cwd: Path) -> set[str]:
    code = (
        "import json, dashboard.dashboard;"
        "from reflex_base.registry import RegistrationContext;"
        "pages = RegistrationContext.ensure_context().decorated_pages;"
        "print(json.dumps(sorted(str(kwargs.get('route', fn.__name__)) for fn, kwargs in pages)))"
    )
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr[-800:]
    keys = json.loads(result.stdout.strip().splitlines()[-1])
    normalized = set()
    for key in keys:
        route = key.strip("/")
        normalized.add("/" if route in ("", "index") else f"/{route}")
    return normalized


def test_app_registers_every_page(tmp_path):
    """A running dev server answers 200 for unknown routes, so check the registry itself."""
    registered = _registered_routes(tmp_path)

    assert EXPECTED_ROUTES <= registered, f"missing routes: {EXPECTED_ROUTES - registered}"
