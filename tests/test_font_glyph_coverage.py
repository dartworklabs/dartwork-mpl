"""Render-based glyph-coverage guard for the scientific/report symbol set.

Import-smoke and the eager-registration contract prove the bundled fonts
*resolve*, but not that a plain-text scientific string actually *renders*
without tofu. matplotlib's per-glyph fallback for plain text is driven by
``font.family`` (an explicit family list), not ``font.sans-serif`` — a
regression to the generic ``sans-serif`` alias, or a dropped bundled
fallback face, silently reopens the tofu this test catches.

Two guards:

1. a curated scientific/report character set renders with ZERO
   "Glyph … missing" warnings under the primary text presets;
2. a mathtext expression renders without exception AND without
   missing-glyph warnings under every preset in the registry.

Kept fast with tiny in-memory SVG buffers.
"""

from __future__ import annotations

import io
import warnings

import matplotlib
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm

matplotlib.use("Agg")  # headless-safe; must precede any figure creation

# The guaranteed plain-text symbol set: arrows, relational / set / calculus
# operators, units, Greek, mathematical-alphanumeric, and dingbats. Every
# glyph here must be covered by the bundled fallback chain (Roboto/Inter,
# then Paperlogy/Noto Sans CJK/Pretendard, then Noto Sans Math, then Noto
# Sans Symbols 1/2). See docs/fonts/math_and_symbols.md.
_BASE_CURATED = "→ ← ↑ ↓ ⇒ ± × ÷ ≈ ≠ ≤ ≥ ∑ ∏ √ ∞ ∂ ∫ ℃ ‰ µ Ω α β γ σ 𝜎 𝑥 ⚠ ✓ ★"  # noqa: RUF001
_UNIQUELY_SERVED_CURATED = (
    "\u2624",  # ☤ U+2624 uniquely served by Noto Sans Symbols.
    "\u2625",  # ☥ U+2625 uniquely served by Noto Sans Symbols.
    "\u263f",  # ☿ U+263F uniquely served by Noto Sans Symbols.
    "\u2646",  # ♆ U+2646 uniquely served by Noto Sans Symbols.
    "\u26a1",  # ⚡ U+26A1 uniquely served by Noto Sans Symbols 2.
    "\u2622",  # ☢ U+2622 uniquely served by Noto Sans Symbols 2.
    "\u23fb",  # ⏻ U+23FB uniquely served by Noto Sans Symbols 2.
    "\u2bd1",  # ⯑ U+2BD1 uniquely served by Noto Sans Symbols 2.
)
CURATED = " ".join((_BASE_CURATED, *_UNIQUELY_SERVED_CURATED))

# A representative mathtext expression exercising superscripts, subscripts,
# relations, radicals, operators, and fractions.
MATHTEXT = r"$x^2 + \alpha_i \geq \sqrt{\beta} \cdot \sum_n \frac{1}{n^2}$"

# Presets whose PLAIN-text symbol coverage is guaranteed by the chain.
PLAIN_PRESETS = ("scientific", "report-kr", "report")


def _missing_glyph_warnings(preset: str, text: str) -> list[str]:
    """Render ``text`` under ``preset`` into an in-memory SVG, returning
    any matplotlib "Glyph … missing" warning messages captured."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    try:
        ax.text(0.5, 0.5, text, ha="center", va="center")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig.savefig(io.BytesIO(), format="svg")
    finally:
        plt.close(fig)
    return [
        str(w.message) for w in caught if "missing from font" in str(w.message)
    ]


@pytest.mark.parametrize("preset", PLAIN_PRESETS)
def test_plain_text_curated_set_has_no_tofu(preset: str) -> None:
    """The curated symbol set renders with no missing-glyph warnings."""
    missing = _missing_glyph_warnings(preset, CURATED)
    assert not missing, (
        f"preset {preset!r} produced {len(missing)} missing-glyph "
        f"warning(s) for the curated set:\n  " + "\n  ".join(missing)
    )


@pytest.mark.parametrize("preset", sorted(dm.style.presets))
def test_mathtext_renders_cleanly_every_preset(preset: str) -> None:
    """mathtext renders without exception and without missing glyphs under
    every registered preset."""
    try:
        missing = _missing_glyph_warnings(preset, MATHTEXT)
    except Exception as exc:  # surface a render exception as a failure
        pytest.fail(f"mathtext raised under preset {preset!r}: {exc!r}")
    assert not missing, (
        f"preset {preset!r} produced {len(missing)} missing-glyph "
        f"warning(s) for mathtext:\n  " + "\n  ".join(missing)
    )


def test_registry_has_the_expected_preset_count() -> None:
    """Guard that the mathtext loop above actually covers all 14 presets —
    a shrunk registry would make the parametrization pass vacuously."""
    assert len(dm.style.presets) == 14, (
        f"expected 14 presets, registry has {len(dm.style.presets)}"
    )
