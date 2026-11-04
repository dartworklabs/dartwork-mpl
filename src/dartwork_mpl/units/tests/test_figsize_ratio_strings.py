"""``dm.figsize`` accepts "W:H" ratio strings and explains pixel input.

Agents and people write screen ratios as ``"16:9"`` and widths as
``"1920px"``. The first is unambiguous (height = width x H / W) and is
accepted; the second has no physical size without a DPI, so the error says
that instead of suggesting the unrelated ``pt`` unit.
"""

from __future__ import annotations

import pytest

import dartwork_mpl as dm
from dartwork_mpl.units import parse_aspect


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        ("16:9", 9 / 16),
        ("4:3", 3 / 4),
        ("3:4", 4 / 3),
        ("1:1", 1.0),
        ("2.39:1", 1 / 2.39),
        (" 16 : 9 ", 9 / 16),
    ],
)
def test_ratio_string_sets_height_from_width(ratio, expected):
    width, height = dm.figsize("16cm", ratio)
    assert width == pytest.approx(16 / 2.54)
    assert height == pytest.approx(width * expected)


def test_ratio_string_matches_the_equivalent_token():
    assert dm.figsize("13cm", "16:9") == pytest.approx(
        dm.figsize("13cm", "slide")
    )
    assert dm.figsize("13cm", "4:3") == pytest.approx(
        dm.figsize("13cm", "standard")
    )


def test_parse_aspect_and_figsize_grid_accept_ratio_strings():
    assert parse_aspect("16:9") == pytest.approx(9 / 16)
    one_panel = dm.figsize_grid("8cm", "4:3")
    assert one_panel == pytest.approx(dm.figsize("8cm", "standard"))


@pytest.mark.parametrize("bad", ["0:9", "16:0", "-16:9", "16:9:1", "16:"])
def test_malformed_or_non_positive_ratio_strings_are_rejected(bad):
    with pytest.raises(ValueError, match="aspect"):
        dm.figsize("13cm", bad)


@pytest.mark.parametrize(
    "ratio",
    [
        "0." + "0" * 307 + "1:10",  # h / w overflows to inf
        "10:0." + "0" * 324 + "1",  # h underflows to 0.0
        "1" + "0" * 300 + ":0." + "0" * 299 + "1",  # h / w underflows to 0.0
    ],
    ids=["overflow", "zero-height", "underflow"],
)
def test_ratio_strings_with_extreme_quotients_are_rejected(ratio):
    with pytest.raises(ValueError, match="positive"):
        dm.figsize("13cm", ratio)
    with pytest.raises(ValueError, match="positive"):
        parse_aspect(ratio)


@pytest.mark.parametrize("width", ["1920px", "1920 px", "800pixels"])
def test_pixel_width_explains_dpi_instead_of_suggesting_pt(width):
    with pytest.raises(ValueError) as excinfo:
        dm.figsize(width, "slide")
    message = str(excinfo.value)
    assert "pt'" not in message
    assert "DPI" in message
    assert "dm.inch(" in message


def test_pixel_height_explains_dpi():
    with pytest.raises(ValueError) as excinfo:
        dm.figsize("13cm", "1080px")
    message = str(excinfo.value)
    assert "DPI" in message
    assert "Did you mean" not in message


def test_other_unit_typos_keep_their_suggestion():
    with pytest.raises(ValueError, match=r"'13cm'"):
        dm.figsize("13centimeters", "standard")
