import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def test_every_page_compiles(tmp_path):
    """Evaluate and compile all pages without writing output or starting servers.

    Page functions run lazily, so an import-only check misses errors such as a
    missing event setter; this catches them in a couple of seconds.
    """
    shutil.copy(REPO_ROOT / "rxconfig.py", tmp_path / "rxconfig.py")
    (tmp_path / "assets").symlink_to(REPO_ROOT / "assets", target_is_directory=True)
    code = "import dashboard.dashboard as d; d.app._compile(dry_run=True, use_rich=False)"
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
    }
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=240
    )
    assert result.returncode == 0, ANSI.sub("", result.stderr + result.stdout)[-1800:]
