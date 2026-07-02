"""Palette family taxonomy parity (G13).

``FAMILY`` in ``build_dc_palettes.py`` is the taxonomy SSOT; the
explorer data's per-palette ``fam:`` labels and the docs' family-count
claims must agree with it. (Before this guard the explorer had a
one-palette "Vivid" family while the palette actually *named* vivid
sat in "Spectrum" — an incoherent rail the docs' "11 families" claim
contradicted.)
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "docs" / "_static" / "scripts"


def _family_map() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location(
        "_bdc_family", _SCRIPTS / "build_dc_palettes.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.FAMILY)


def _explorer_fams() -> dict[str, str]:
    js = (_SCRIPTS / "categorical_explorer_data.js").read_text(encoding="utf-8")
    pairs = re.findall(
        r'^\s*([a-z_]+):\s*\{ name:"[^"]*", fam:"([^"]+)"', js, re.M
    )
    return dict(pairs)


def test_explorer_fams_match_family_ssot_per_palette() -> None:
    family = _family_map()
    explorer = _explorer_fams()
    assert set(explorer) == set(family), (
        f"palette set drift: only-explorer="
        f"{sorted(set(explorer) - set(family))}, "
        f"only-FAMILY={sorted(set(family) - set(explorer))}"
    )
    mismatched = {
        name: (explorer[name], family[name])
        for name in family
        if explorer[name] != family[name]
    }
    assert not mismatched, f"fam label drift (explorer, SSOT): {mismatched}"


def test_family_count_matches_docs_claim() -> None:
    family = _family_map()
    n_families = len(set(family.values()))
    doc = (
        _REPO / "docs" / "color_system" / "categorical-palettes.md"
    ).read_text(encoding="utf-8")
    m = re.search(r"(\d+)\s+families", doc)
    assert m, "family-count claim not found in categorical-palettes.md"
    assert int(m.group(1)) == n_families, (
        f"docs claim {m.group(1)} families; FAMILY SSOT has {n_families}"
    )
