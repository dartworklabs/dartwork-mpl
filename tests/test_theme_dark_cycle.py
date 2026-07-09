"""The theme-dark categorical cycle must clear the bg_L-aware gates.

The white v5 cycle is contrast-gated against white and is void on the dark
facecolor. theme-dark ships its own cycle; this is its live gate — every
member is legible on the actual facecolor (WCAG contrast) and the set stays
distinct under normal + deuteranopia + protanopia + tritanopia simulation.
"""

from __future__ import annotations

import re
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
    """theme-dark's cycle clears the shipped *tiered* CVD gate.

    The v5 gate is not a flat ΔE≥10 across all four vision types: tritanopia
    (the rare S-cone deficiency) is held to a realistic lower floor (8) than
    the common red-green floor (10), matching ``gate_cycle``'s design. Assert
    the actual policy via ``gate_cycle`` rather than re-deriving ΔE inline.
    """
    from dartwork_mpl._colors._gates import gate_cycle

    _, hexes = _parse_style()
    g = gate_cycle(hexes)
    # Shipped tiered policy — assert the SAME unrounded floors check_all gates
    # on (common_min_raw / tritan_raw), not the rounded display keys, so this
    # test cannot green a cycle whose true floor rounds up across the gate.
    assert g["common_min_raw"] >= 10.0, g[
        "common_min_raw"
    ]  # normal+protan+deutan
    assert g["tritan_raw"] >= 8.0, g[
        "tritan_raw"
    ]  # rare S-cone deficiency floor
    # Design MARGIN for THIS dark cycle (not the gate) — its members are tuned
    # so even tritan clears well above the 8.0 floor (measured 11.0). Kept as a
    # regression tripwire against a future palette edit eroding that headroom.
    assert g["tritan_raw"] >= 10.0, (
        f"tritan margin {g['tritan_raw']:.2f} < 10.0 (not gate)"
    )
