"""Color-system fixtures shared by the colour slice's colocated tests.

Applies to every test below ``src/dartwork_mpl/_colors/`` (build, verify and
the authority tests); all users of these fixtures live there. The
repository-wide bootstrap and state isolation live in the root
``conftest.py`` (ADR 0005).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from dartwork_mpl._colors.construction._catalog import CatalogSnapshot

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SSOT_PATH = (
    _REPO_ROOT
    / "docs/superpowers/specs/assets"
    / "2026-07-03-color-system-v5/color_v5_ssot.json"
)


@pytest.fixture(scope="session")
def v5_ssot() -> dict:
    """설계 확정 SSOT (스펙 §7 — 구현이 이 값을 재생산해야 함)."""
    return json.loads(_SSOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def candidate_catalog(
    tmp_path_factory: pytest.TempPathFactory,
) -> CatalogSnapshot:
    """Compile current source once into a deeply immutable color snapshot.

    Golden comparisons and mutation gates share these real compiler outputs;
    tests of changed compiler inputs still invoke the compiler independently.

    Under pytest-xdist every worker is its own session, so a plain session
    fixture would compile the candidate once per worker (~1 min each). The
    first worker compiles and publishes ``to_json()`` into the run's shared
    temp root; the others wait on the lock and rebuild the snapshot with
    ``from_payload``. That round trip is exact: the rebuilt snapshot compares
    equal field by field, with identical container types and JSON bytes.
    """
    from dartwork_mpl._colors.construction._catalog import (
        CatalogSnapshot,
        compile_candidate_snapshot,
    )

    if "PYTEST_XDIST_WORKER" not in os.environ:
        return compile_candidate_snapshot()
    try:
        import fcntl
    except ImportError:  # no POSIX lock: each worker compiles for itself
        return compile_candidate_snapshot()

    shared_root = tmp_path_factory.getbasetemp().parent
    published = shared_root / "candidate_catalog.json"
    with (shared_root / "candidate_catalog.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if published.is_file():
                return CatalogSnapshot.from_payload(
                    json.loads(published.read_text(encoding="utf-8"))
                )
            snapshot = compile_candidate_snapshot()
            partial = published.with_suffix(".partial")
            partial.write_text(snapshot.to_json(), encoding="utf-8")
            partial.replace(published)
            return snapshot
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
