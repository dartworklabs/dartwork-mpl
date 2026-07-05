"""Colormap assets must be reproducible by their sole writer (G1).

The OKLCH gamut-mapping fix (#240) post-dated the 2026-03 asset
generation, leaving 24 of the committed maps unreproducible (channel
deltas up to 0.41) — the exact drift class
``test_palette_sources_consistency`` guards for palettes. This test
regenerates every map into a temp dir and compares numerically
(``np.allclose`` rather than byte equality — real drift is 1e-1 scale;
strict bytes would be hostage to cross-platform float formatting).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
_GENERATOR = _REPO / "scripts" / "generate_cmaps.py"
_ASSET = _REPO / "src" / "dartwork_mpl" / "asset" / "cmap"


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("cmap_regen")
    spec = importlib.util.spec_from_file_location("_gen_cmaps", _GENERATOR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_gen_cmaps"] = mod
    try:
        spec.loader.exec_module(mod)
        mod.CMAP_DIR = out
        mod.main()
    finally:
        sys.modules.pop("_gen_cmaps", None)
    return out


def test_filename_sets_equal(regenerated: Path) -> None:
    committed = {p.name for p in _ASSET.glob("*.txt")}
    regen = {p.name for p in regenerated.glob("*.txt")}
    assert committed == regen, (
        f"missing_from_regen={sorted(committed - regen)}, "
        f"extra_in_regen={sorted(regen - committed)}"
    )


def test_every_map_numerically_reproducible(regenerated: Path) -> None:
    stale = []
    for committed_file in sorted(_ASSET.glob("*.txt")):
        a = np.loadtxt(committed_file)
        b = np.loadtxt(regenerated / committed_file.name)
        if a.shape != b.shape or not np.allclose(a, b, atol=1e-8):
            delta = float(np.abs(a - b).max()) if a.shape == b.shape else None
            stale.append((committed_file.name, delta))
    assert not stale, (
        f"committed cmap assets not reproducible by generate_cmaps.py: "
        f"{stale} — rerun scripts/generate_cmaps.py and commit (note any "
        f"visual change in the CHANGELOG)"
    )
