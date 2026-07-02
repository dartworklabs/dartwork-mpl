"""Numeric asset-count claims in docs must equal the mechanical count (G4).

"16 curated colormaps" survived in the flagship colormap page while 56
shipped; the font pages predate the #370 corpus expansion. Each entry
pairs a claim-regex with the callable that computes the true number —
and the regex MUST match, so rewording a claim can't silently disable
its check.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_ASSET = _REPO / "src" / "dartwork_mpl" / "asset"


def _n_cmaps() -> int:
    return len(list((_ASSET / "cmap").glob("*.txt")))


def _n_font_files() -> int:
    return len(
        [
            p
            for p in (_ASSET / "font").iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        ]
    )


def _n_presets() -> int:
    presets = json.loads(
        (_ASSET / "mplstyle" / "presets.json").read_text(encoding="utf-8")
    )
    return len(presets)


def _n_curated_palettes() -> int:
    pkg = json.loads(
        (_ASSET / "color" / "dc_palettes.json").read_text(encoding="utf-8")
    )
    # The unnamed "" key is the default prop-cycle repoint (dc.0..7),
    # not one of the curated named palettes.
    return len([k for k in pkg if k])


def _n_basic_templates() -> int:
    return len(list((_ASSET / "prompt" / "05-templates").glob("*.py")))


_CLAIMS: list[tuple[str, str, Callable[[], int]]] = [
    (
        "docs/color_system/colormaps.md",
        r"ships \*\*(\d+) curated colormaps\*\*",
        _n_cmaps,
    ),
    (
        "docs/color_system/colormaps.md",
        r"Explore all (\d+) built-in colormaps",
        _n_cmaps,
    ),
    (
        "docs/fonts/index.md",
        r"bundles \*\*(\d+) text font files across \d+ families\*\*",
        _n_font_files,
    ),
    (
        "docs/usage_guide/styles.md",
        r"giving \*\*(\d+) presets\*\* total",
        _n_presets,
    ),
    (
        "docs/color_system/categorical-palettes.md",
        r"curated (\d+)-palette system",
        _n_curated_palettes,
    ),
    (
        "docs/color_system/colors.md",
        r"\*\*(\d+)-palette categorical system\*\*",
        _n_curated_palettes,
    ),
    ("llms.txt", r"(\d+) ready-to-use scripts", _n_basic_templates),
    ("CLAUDE.md", r"(\d+) ready-to-use plot templates", _n_basic_templates),
]


@pytest.mark.parametrize(
    ("relpath", "claim_re", "counter"),
    _CLAIMS,
    ids=[f"{c[0]}~{i}" for i, c in enumerate(_CLAIMS)],
)
def test_count_claim_matches_reality(
    relpath: str, claim_re: str, counter: Callable[[], int]
) -> None:
    text = (_REPO / relpath).read_text(encoding="utf-8")
    m = re.search(claim_re, text)
    assert m, (
        f"{relpath}: claim regex {claim_re!r} not found — if the prose "
        f"was reworded, update the regex so the check stays live"
    )
    actual = counter()
    assert int(m.group(1)) == actual, (
        f"{relpath}: claims {m.group(1)}, mechanical count is {actual}"
    )
