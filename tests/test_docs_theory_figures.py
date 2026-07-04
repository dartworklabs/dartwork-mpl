"""Committed theory-figure SVGs must be deterministic (no embedded timestamp).

``docs/color_system/generate_theory_figures.py`` sets a fixed ``svg.hashsalt``
and ``metadata={"Date": None}`` on every save so a re-render is byte-identical
unless the plotted data actually changed — the docs page's "the pictures are
the proof" claim. A figure added without those controls would bake a wall-clock
timestamp (and churn every clip-path id on each run), so a one-number
correction would surface as a full-file diff. This guards against that
regression cheaply, without running the (slow) generator.
"""

from pathlib import Path

_THEORY = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "color_system"
    / "theory_figures"
)


def test_theory_svgs_have_no_embedded_date() -> None:
    svgs = sorted(_THEORY.glob("theory_*.svg"))
    assert svgs, "no theory-figure SVGs found"
    dated = [
        p.name for p in svgs if "<dc:date" in p.read_text(encoding="utf-8")
    ]
    assert not dated, f"non-deterministic (timestamped) theory SVGs: {dated}"
