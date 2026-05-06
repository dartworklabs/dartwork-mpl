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

Why a separate file: the existing ``tests/test_style.py`` covers
preset *loading* but not the round-trip through ``save_formats`` and
``validate_figure``. This matrix proves that every advertised preset
actually produces a savable, validation-clean figure end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity

_MIN_FILE_BYTES: int = 1024


def _all_preset_names() -> list[str]:
    """Return every preset name registered in presets.json."""
    return sorted(dm.style.presets_dict().keys())


@pytest.mark.parametrize("preset", _all_preset_names())
def test_preset_round_trip(preset: str, tmp_path: Path) -> None:
    """Apply ``preset``, build a trivial chart, save PNG+PDF, validate."""
    dm.style.use(preset)

    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([1, 2, 3, 4], [1, 4, 9, 16])
    ax.set_ylabel("Value")
    ax.set_xlabel("Index")

    dm.auto_layout(fig)

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

    warnings = dm.validate_figure(fig, quiet=True)
    severe = [w for w in warnings if w.severity == Severity.WARNING]
    assert severe == [], (
        f"{preset}: WARNING-level findings on a trivial chart — "
        f"{[(w.check_id, w.message) for w in severe]}"
    )

    plt.close(fig)
