"""Shared pytest fixtures for the dartwork-mpl test suite.

Why this file exists
--------------------
Many tests apply matplotlib styles via ``dm.style.use(...)`` or mutate
``plt.rcParams`` / open figures as a side effect. Without isolation,
that state leaks across tests and produces order-dependent failures
("works alone, fails in suite") or silent style cross-contamination.

This conftest adds a single ``autouse`` fixture that runs **after**
each test to:

1. Close every open figure (prevents figure-leak warnings and
   accumulated memory in long suites).
2. Reset ``rcParams`` to matplotlib's compiled-in defaults so the next
   test starts from a known baseline.

Tests that *intentionally* depend on a specific style should call
``dm.style.use(...)`` themselves; the reset only happens between tests.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = str(_REPO_ROOT / "src")
_METADATA_ROOT = _REPO_ROOT / ".pytest_cache" / "dartwork_mpl_metadata"


def _pyproject_version() -> str:
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if match is None:
        raise RuntimeError("Could not find project.version in pyproject.toml")
    return match.group(1)


def _ensure_source_tree_metadata() -> str:
    version = _pyproject_version()
    _METADATA_ROOT.mkdir(parents=True, exist_ok=True)
    for old in _METADATA_ROOT.glob("dartwork_mpl-*.dist-info"):
        if old.name != f"dartwork_mpl-{version}.dist-info":
            shutil.rmtree(old)
    dist_info = _METADATA_ROOT / f"dartwork_mpl-{version}.dist-info"
    dist_info.mkdir(exist_ok=True)
    metadata = dist_info / "METADATA"
    metadata.write_text(
        f"Metadata-Version: 2.1\nName: dartwork-mpl\nVersion: {version}\n",
        encoding="utf-8",
    )
    return str(_METADATA_ROOT)


_METADATA_PATH = _ensure_source_tree_metadata()
# Source-tree test runs use ``src`` ahead of site-packages. Mirror that for
# package metadata and subprocesses so a shared venv's stale editable install
# cannot leak a different ``dartwork-mpl`` version or package path into tests.
if _METADATA_PATH not in sys.path:
    sys.path.insert(0, _METADATA_PATH)
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)
_PYTHONPATH_PARTS = [
    part for part in os.environ.get("PYTHONPATH", "").split(os.pathsep) if part
]
for path in (_SRC_PATH, _METADATA_PATH):
    if path not in _PYTHONPATH_PARTS:
        _PYTHONPATH_PARTS.insert(0, path)
os.environ["PYTHONPATH"] = os.pathsep.join(_PYTHONPATH_PARTS)

_SSOT_PATH = (
    _REPO_ROOT
    / "docs/superpowers/specs/assets"
    / "2026-07-03-color-system-v5/color_v5_ssot.json"
)


@pytest.fixture(scope="session")
def v5_ssot() -> dict:
    """설계 확정 SSOT (스펙 §7 — 구현이 이 값을 재생산해야 함)."""
    return json.loads(_SSOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _matplotlib_state_isolation() -> Iterator[None]:
    """Close figures, reset rcParams, and restore ``dm.config``.

    Yields control to the test, then performs cleanup unconditionally.
    """
    # Snapshot the process-global ``dm.config`` singleton so a test that
    # mutates it (directly, or forgetting ``config.override()``) can't
    # leak into later tests. Fields are re-applied onto the singleton on
    # teardown — never rebound — because consumers hold references to
    # the instance itself.
    from dataclasses import fields

    from dartwork_mpl.config import config as _dm_config

    snapshot = {f.name: getattr(_dm_config, f.name) for f in fields(_dm_config)}
    yield
    for name, value in snapshot.items():
        setattr(_dm_config, name, value)
    # Close all figures created during the test to prevent leaks.
    plt.close("all")
    # Restore matplotlib's compiled-in defaults so style mutations from
    # one test don't bleed into the next.
    mpl.rcdefaults()
