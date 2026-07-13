import subprocess
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"

FORBIDDEN = ("pygame", "import random", "from random",
             "import time", "from time", "datetime", "urandom")


def test_sim_sources_have_no_forbidden_imports():
    for f in SIM.rglob("*.py"):
        src = f.read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            assert bad not in src, f"{f.name} references {bad!r}"


def test_importing_sim_does_not_load_pygame():
    code = ("import sys; import sim.match; "
            "sys.exit(1 if any(m.startswith('pygame') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
