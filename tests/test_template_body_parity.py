"""Template body parity: asset SSOT ↔ gallery copies (G6).

The gallery pages declare the bundled assets as their "Source", yet all
18 basic-tier bodies had silently diverged (the gallery migrated to
curated ``dc.*`` colors; the assets kept ``oc.*``). The advanced tier's
0/18 divergence proves parity is the intended invariant — this test
enforces it for both tiers after normalizing the intentional deltas
(module docstring; the asset's trailing ``dm.save_formats`` call, which
sphinx-gallery replaces with live rendering).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_ASSET = _REPO / "src" / "dartwork_mpl" / "asset" / "prompt" / "05-templates"
_GALLERY = _REPO / "docs" / "examples_source" / "09_ai_templates"
_GALLERY_ADV = _REPO / "docs" / "examples_source" / "09_ai_templates_advanced"

_STEMS = sorted(p.stem for p in _ASSET.glob("*.py"))
_ADV_STEMS = sorted(p.stem for p in (_ASSET / "advanced").glob("*.py"))


def _gallery_file(gallery_dir: Path, stem: str, suffix: str = "") -> Path:
    # test_drift.py quirk: the docs file for ``plot_3d`` is
    # ``plot_3d{suffix}.py``, not ``plot_plot_3d{suffix}.py``.
    name = (
        f"{stem}{suffix}.py" if stem == "plot_3d" else f"plot_{stem}{suffix}.py"
    )
    return gallery_dir / name


def _normalize(src: str) -> list[str]:
    # Strip the module docstring (single- or multi-line).
    m = re.match(r'\s*("""|\'\'\')(?:.|\n)*?\1\s*\n', src)
    if m:
        src = src[m.end() :]
    lines = []
    for line in src.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("dm.save_formats("):
            continue
        lines.append(line.rstrip())
    return lines


@pytest.mark.parametrize("stem", _STEMS)
def test_basic_template_matches_gallery(stem: str) -> None:
    asset = _normalize((_ASSET / f"{stem}.py").read_text(encoding="utf-8"))
    gallery = _normalize(
        _gallery_file(_GALLERY, stem).read_text(encoding="utf-8")
    )
    assert asset == gallery, (
        f"{stem}: asset body diverged from its gallery copy — sync them "
        f"in the same PR (gallery declares the asset as its Source)"
    )


@pytest.mark.parametrize("stem", _ADV_STEMS)
def test_advanced_template_matches_gallery(stem: str) -> None:
    asset = _normalize(
        (_ASSET / "advanced" / f"{stem}.py").read_text(encoding="utf-8")
    )
    gallery = _normalize(
        _gallery_file(_GALLERY_ADV, stem).read_text(encoding="utf-8")
    )
    assert asset == gallery, f"{stem} (advanced): asset ↔ gallery drift"


def test_both_tiers_have_eighteen() -> None:
    assert len(_STEMS) == 18
    assert len(_ADV_STEMS) == 18
