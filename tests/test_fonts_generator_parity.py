"""Both font-gallery generators must see every bundled family (G-fonts).

``docs/fonts/generate_assets.py`` builds the all-families SVG preview
embedded in ``fonts/utilities.md``; ``docs/fonts/generate_html_specimens.py``
builds the per-family HTML specimens embedded in ``fonts/families.md``.
Each groups the bundled font files into families with the same
``split("-")[0]`` rule, but they historically diverged on the file
*filter*: the specimens builder collected ``.ttf`` and ``.otf`` while the
asset builder collected ``.ttf`` only. That silently dropped the two
OpenType families — Pretendard (9 ``.otf`` weights) and the Noto Sans CJK
subset (1 ``.otf``) — from the all-families preview, contradicting the
advertised "16 families" and the Pretendard profile that sits right next
to it. This test pins both collectors to the exact family set derived
from every bundled ``.ttf``/``.otf`` file, so a filter regression in
either one fails loudly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_REPO = Path(__file__).resolve().parents[1]
_FONT_DIR = _REPO / "src" / "dartwork_mpl" / "asset" / "font"
_ASSETS = _REPO / "docs" / "fonts" / "generate_assets.py"
_SPECIMENS = _REPO / "docs" / "fonts" / "generate_html_specimens.py"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bundled_families() -> set[str]:
    """Family set derived directly from every bundled font file."""
    return {
        p.stem.split("-")[0]
        for p in _FONT_DIR.iterdir()
        if p.suffix.lower() in {".ttf", ".otf"}
    }


def test_both_generators_collect_every_bundled_family() -> None:
    expected = _bundled_families()
    assets = _load(_ASSETS, "_ga_parity")
    specimens = _load(_SPECIMENS, "_ghs_parity")

    ga_fams = set(assets._collect_fonts())
    ghs_fams = set(specimens._collect_fonts())

    assert ga_fams == expected, (
        "generate_assets._collect_fonts() is missing "
        f"{sorted(expected - ga_fams)} — likely a .ttf-only filter "
        "dropping OpenType families from the all-families preview"
    )
    assert ghs_fams == expected, (
        "generate_html_specimens._collect_fonts() is missing "
        f"{sorted(expected - ghs_fams)}"
    )
    assert ga_fams == ghs_fams, (
        "the two font-gallery generators disagree on the family set: "
        f"assets-only={sorted(ga_fams - ghs_fams)}, "
        f"specimens-only={sorted(ghs_fams - ga_fams)}"
    )


def test_opentype_families_are_not_dropped() -> None:
    """Regression guard: Pretendard and Noto Sans CJK ship as ``.otf``."""
    assets = _load(_ASSETS, "_ga_otf")
    fams = set(assets._collect_fonts())
    for otf_family in ("Pretendard", "NotoSansCJK"):
        assert otf_family in fams, (
            f"{otf_family} (OpenType) was dropped from the all-families "
            "preview — check the file-extension filter in "
            "generate_assets._collect_fonts()"
        )
