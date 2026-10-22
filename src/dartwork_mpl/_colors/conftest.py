"""Color-system fixtures shared by the colour slice's colocated tests.

Applies to every test below ``src/dartwork_mpl/_colors/`` (build, verify and
the authority tests); all users of these fixtures live there. The
repository-wide bootstrap and state isolation live in the root
``conftest.py`` (ADR 0005).
"""

from __future__ import annotations

import json
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
def candidate_catalog() -> CatalogSnapshot:
    """Compile current source once into a deeply immutable color snapshot.

    Golden comparisons and mutation gates share these real compiler outputs;
    tests of changed compiler inputs still invoke the compiler independently.
    """
    from dartwork_mpl._colors.construction._catalog import (
        compile_candidate_snapshot,
    )

    return compile_candidate_snapshot()
