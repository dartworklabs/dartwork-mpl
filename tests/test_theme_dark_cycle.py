"""The theme-dark categorical cycle must clear the bg_L-aware gates.

The white v5 cycle is contrast-gated against white and is void on the dark
facecolor. theme-dark ships its own cycle; this is its live gate — every
member is legible on the actual facecolor (WCAG contrast) and the set stays
distinct under normal + deuteranopia + protanopia + tritanopia simulation.
"""

from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path

import matplotlib
import matplotlib.colors as mcolors

matplotlib.use("Agg")

_STYLE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "mplstyle"
    / "theme-dark.mplstyle"
)


def _parse_style() -> tuple[str, list[str]]:
    """Return (facecolor, cycle-hex-list) from theme-dark.mplstyle."""
    import dartwork_mpl  # noqa: F401 — register the dc.* tokens

    text = _STYLE.read_text(encoding="utf-8")
    face = re.search(r'axes\.facecolor:\s*"?(#[0-9a-fA-F]{6})"?', text).group(1)
    cyc_line = re.search(
        r"axes\.prop_cycle:\s*cycler\('color',\s*\[([^\]]+)\]", text
    ).group(1)
    tokens = re.findall(r"'([^']+)'", cyc_line)
    mapping = mcolors.get_named_colors_mapping()
    hexes = [mcolors.to_hex(mapping[t]) for t in tokens]
    return face, hexes


def _rel_lum(hexs: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = mcolors.to_rgb(hexs)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(a: str, b: str) -> float:
    lo, hi = sorted((_rel_lum(a), _rel_lum(b)))
    return (hi + 0.05) / (lo + 0.05)


def test_cycle_members_legible_on_facecolor() -> None:
    face, hexes = _parse_style()
    assert len(hexes) == 7
    for h in hexes:
        assert _contrast(h, face) >= 3.5, (
            f"{h} contrast {_contrast(h, face):.2f} on {face}"
        )


def test_cycle_cvd_safe() -> None:
    from dartwork_mpl.colors._metrics import (
        cvd_rgb,
        de2000_hex,
        hex_from_rgb,
        rgb_from_hex,
    )

    _, hexes = _parse_style()

    def sim(h: str, kind: str) -> str:
        return (
            h
            if kind == "normal"
            else hex_from_rgb(cvd_rgb(rgb_from_hex(h), kind))
        )

    worst = min(
        de2000_hex(sim(a, k), sim(b, k))
        for k in ("normal", "deutan", "protan", "tritan")
        for a, b in combinations(hexes, 2)
    )
    assert worst >= 10.0, f"worst-case CVD min ΔE00 {worst:.2f} < 10 gate"
