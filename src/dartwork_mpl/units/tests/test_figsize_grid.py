from __future__ import annotations

import pytest

import dartwork_mpl as dm
from dartwork_mpl.units import parse_width


def test_figsize_grid_two_columns_square() -> None:
    width, height = dm.figsize_grid("6cm", "square", ncols=2, gap="1cm")

    panel = parse_width(dm.cm(6))
    gap = parse_width(dm.cm(1))

    assert width == pytest.approx(2 * panel + gap)
    assert height == pytest.approx(panel)


def test_figsize_grid_three_columns_two_rows_arithmetic() -> None:
    width, height = dm.figsize_grid(
        "4cm", "wide", ncols=3, nrows=2, gap="0.5cm"
    )

    panel_width = parse_width(dm.cm(4))
    panel_height = dm.figsize(dm.cm(4), "wide")[1]
    gap = parse_width(dm.cm(0.5))

    assert width == pytest.approx(3 * panel_width + 2 * gap)
    assert height == pytest.approx(2 * panel_height + gap)


def test_figsize_grid_uses_default_gap() -> None:
    width, height = dm.figsize_grid("2cm", "square", ncols=2)

    panel = parse_width(dm.cm(2))
    gap = parse_width("0.6cm")

    assert width == pytest.approx(2 * panel + gap)
    assert height == pytest.approx(panel)


def test_figsize_grid_rejects_invalid_ncols() -> None:
    with pytest.raises(ValueError, match="ncols"):
        dm.figsize_grid("6cm", ncols=0)


def test_figsize_grid_rejects_bare_float_like_figsize() -> None:
    with pytest.raises(TypeError) as grid_error:
        dm.figsize_grid(6.0)  # type: ignore[arg-type]

    with pytest.raises(TypeError) as figsize_error:
        dm.figsize(6.0)  # type: ignore[arg-type]

    assert str(grid_error.value) == str(figsize_error.value)


def test_figsize_grid_numeric_aspect_ratio() -> None:
    width, height = dm.figsize_grid("8cm", 0.5, nrows=2, gap="1cm")

    panel = parse_width(dm.cm(8))
    gap = parse_width(dm.cm(1))

    assert width == pytest.approx(panel)
    assert height == pytest.approx(2 * panel * 0.5 + gap)
