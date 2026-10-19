"""Smoke matrix exercising every dartwork-mpl style preset.

For every preset listed in ``dm.style.presets_dict()`` we apply the
preset, build a trivially clean chart (single line plot + axis
labels), save PNG+PDF to a temporary directory, and assert that:

    1. ``dm.style.use(preset)`` does not raise.
    2. ``dm.save_formats`` writes both files with > 1 KB each.
    3. ``dm.validate_figure`` reports no WARNING-level findings on
       the trivially clean chart (INFO findings — e.g. EMPTY_AXES on
       a zero-data axes — are not emitted here because the chart has
       data).
    4. PDF text embeds TrueType fonts rather than Type 3 glyph programs.

Why a separate file: the existing ``tests/test_style.py`` covers
preset *loading* but not the round-trip through ``save_formats`` and
``validate_figure``. This matrix proves that every advertised preset
actually produces a savable, validation-clean figure end-to-end.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity

_MIN_FILE_BYTES: int = 1024


def _assert_embedded_truetype(pdf_path: Path) -> None:
    """Inspect emitted font dictionaries for embedded TrueType descendants.

    Matplotlib writes font dictionaries outside compressed content streams,
    so these PDF names inspect the exported artifact without a PDF dependency.
    """
    pdf = pdf_path.read_bytes()
    subtypes = re.findall(rb"/Subtype\s*/(Type3|Type0|CIDFontType2)\b", pdf)
    assert subtypes, "PDF contains no inspectable text fonts"
    assert b"Type3" not in subtypes, subtypes
    assert b"Type0" in subtypes, subtypes
    assert b"CIDFontType2" in subtypes, subtypes
    assert re.search(rb"/FontFile2\s+\d+\s+0\s+R\b", pdf), (
        "PDF does not reference an embedded TrueType font program"
    )


def _all_preset_names() -> list[str]:
    """Return every preset name registered in presets.json."""
    return sorted(dm.style.presets_dict().keys())


@pytest.mark.parametrize("preset", _all_preset_names())
def test_preset_applies_without_bad_values(
    preset: str, caplog: pytest.LogCaptureFixture
) -> None:
    """``style.use`` must not trip matplotlib's rcParams validator.

    matplotlib logs (not raises) a ``Bad value`` warning for an
    unresolvable token in a style file and then *silently skips* the
    key — e.g. a renamed ``dc.*`` palette in a prop_cycle ships the
    default tab colors while every test stays green. Gate on the log
    record so that class fails loudly (prefix-agnostic — it validates
    every rcParams key, not just colors).
    """
    import logging

    with caplog.at_level(logging.WARNING, logger="matplotlib"):
        dm.style.use(preset)
    bad = [
        r.getMessage() for r in caplog.records if "Bad value" in r.getMessage()
    ]
    assert not bad, f"{preset}: matplotlib rejected style values: {bad}"


@pytest.mark.parametrize("preset", _all_preset_names())
def test_preset_round_trip(preset: str, tmp_path: Path) -> None:
    """Export Latin, math, and Korean preset text with embedded TrueType."""
    dm.style.use(preset)

    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([1, 2, 3, 4], [1, 4, 9, 16])
    ax.set_ylabel("값" if preset.endswith("-kr") else "Value")
    ax.set_xlabel(r"Index ($\alpha$)")

    dm.simple_layout(fig, margin=dm.inch(0.08))

    out_stem = str(tmp_path / f"preset_{preset}")
    dm.save_formats(fig, out_stem, formats=("png", "pdf"), validate=False)

    png_path = Path(f"{out_stem}.png")
    pdf_path = Path(f"{out_stem}.pdf")
    assert png_path.exists(), f"{preset}: PNG not written"
    assert pdf_path.exists(), f"{preset}: PDF not written"
    assert png_path.stat().st_size > _MIN_FILE_BYTES, (
        f"{preset}: PNG suspiciously small ({png_path.stat().st_size} bytes)"
    )
    assert pdf_path.stat().st_size > _MIN_FILE_BYTES, (
        f"{preset}: PDF suspiciously small ({pdf_path.stat().st_size} bytes)"
    )
    _assert_embedded_truetype(pdf_path)

    warnings = dm.validate_figure(fig, quiet=True)
    severe = [w for w in warnings if w.severity == Severity.WARNING]
    assert severe == [], (
        f"{preset}: WARNING-level findings on a trivial chart — "
        f"{[(w.check_id, w.message) for w in severe]}"
    )

    plt.close(fig)


@pytest.mark.parametrize("style_name", ["dmpl", "dmpl_light"])
def test_legacy_style_embeds_truetype(style_name: str, tmp_path: Path) -> None:
    """Standalone legacy styles must embed the same PDF font format."""
    dm.style.stack([style_name])
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_xlabel("Index")
    dm.simple_layout(fig)
    stem = tmp_path / style_name
    dm.save_formats(fig, str(stem), formats=("pdf",), validate=False)
    _assert_embedded_truetype(stem.with_suffix(".pdf"))
    plt.close(fig)


def test_explicit_type3_override_is_respected(tmp_path: Path) -> None:
    """Normal matplotlib rc overrides remain effective during PDF export."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_xlabel("Index")
    dm.simple_layout(fig)
    with plt.rc_context({"pdf.fonttype": 3}):
        dm.save_formats(
            fig, str(tmp_path / "type3"), formats=("pdf",), validate=False
        )
    pdf = (tmp_path / "type3.pdf").read_bytes()
    assert re.search(rb"/Subtype\s*/Type3\b", pdf)
    assert not re.search(rb"/Subtype\s*/CIDFontType2\b", pdf)
    plt.close(fig)
