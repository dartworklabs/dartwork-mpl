"""A pure file stays pure when it runs: importing it loads no matplotlib.

``test_domain_rules`` (D2) reads a domain file's own imports. This test runs
them: every ``model.py``, ``decide.py`` and ``edges.py`` and every module in
``boundaries.DECISIONS`` is imported in a fresh interpreter, and the test
fails if ``matplotlib`` is then in ``sys.modules``. A pure file that imports
a platform package which imports matplotlib fails here, though its own
source names no matplotlib.

The packages enclosing the file (the package root and its slice or platform
package) are stood in for by empty packages, so their initializers, the shell
around the file, do not run. Everything the file imports runs as it is: its
siblings, and every other package with its initializer.
"""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from . import boundaries

PKG_DIR = Path(__file__).resolve().parents[2] / "src" / "dartwork_mpl"
DOMAIN_FILES = frozenset({"model.py", "decide.py", "edges.py"})

PROBE = """
import importlib, sys, types
root, target = sys.argv[1:]
parts = target.split(".")
for end in range(1, len(parts)):
    stand_in = types.ModuleType(".".join(parts[:end]))
    stand_in.__path__ = ["/".join([root, *parts[1:end]])]
    sys.modules[stand_in.__name__] = stand_in
importlib.import_module(target)
print("matplotlib" in sys.modules)
"""


def pure_modules() -> list[str]:
    """Every domain file and DECISIONS module, by dotted name."""
    found = set(boundaries.DECISIONS)
    for path in PKG_DIR.rglob("*.py"):
        rel = path.relative_to(PKG_DIR)
        if path.name in DOMAIN_FILES and not boundaries.is_test(rel):
            if rel.parts[: len(("guide", "assets"))] == ("guide", "assets"):
                continue
            found.add(".".join(("dartwork_mpl", *rel.with_suffix("").parts)))
    return sorted(found)


def loads_matplotlib(module: str) -> bool:
    """Whether importing ``module`` alone loads matplotlib."""
    run = subprocess.run(
        [sys.executable, "-c", PROBE, str(PKG_DIR), module],
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode:
        pytest.fail(f"{module} does not import alone:\n{run.stderr}")
    return run.stdout.strip() == "True"


def test_pure_files_load_no_matplotlib() -> None:
    modules = pure_modules()
    assert modules, "no pure files found"
    with ThreadPoolExecutor() as pool:
        loads = list(pool.map(loads_matplotlib, modules))
    impure = [m for m, load in zip(modules, loads, strict=True) if load]
    assert not impure, (
        "these pure files load matplotlib when imported: " + ", ".join(impure)
    )
