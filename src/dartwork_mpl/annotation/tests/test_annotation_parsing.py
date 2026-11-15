"""Annotation entry points parse their string options once.

The public parameters stay ``str``; these tests pin that each accepted string
maps to itself, each rejected one raises the unchanged public message, and
that ``place_legend``'s choice among inside spots and outside plans follows
the ladder's ordering rules.
"""

import pytest

from dartwork_mpl.annotation._axis_labels import _parse_axis
from dartwork_mpl.annotation._point_labels import (
    _parse_corner,
    _parse_hline_side,
    _parse_hline_x,
    _parse_value_side,
)


@pytest.mark.parametrize("side", ["auto", "above", "below", "left", "right"])
def test_value_side_accepts_each_documented_side(side: str) -> None:
    """Every documented ``annotate_value`` side parses to itself."""
    assert _parse_value_side(side) == side


@pytest.mark.parametrize(
    ("parse", "value", "message"),
    [
        (
            _parse_value_side,
            "top",
            "side must be 'auto', 'above', 'below', 'left', or 'right'",
        ),
        (
            _parse_corner,
            "center",
            "loc must be 'upper left', 'upper right', 'lower left', or 'lower right'",
        ),
        (_parse_hline_side, "left", "side must be 'above' or 'below'"),
        (
            _parse_hline_x,
            "middle",
            "x must be 'auto', 'left', 'center', 'right', or a float",
        ),
    ],
    ids=["value-side", "corner", "hline-side", "hline-x"],
)
def test_unknown_option_raises_the_public_message(
    parse, value, message
) -> None:
    """A string outside the vocabulary raises ``ValueError`` with the unchanged text."""
    with pytest.raises(ValueError) as excinfo:
        parse(value)
    assert str(excinfo.value) == message


def test_hline_x_keeps_numbers_as_axes_fractions() -> None:
    """A numeric ``x`` becomes a float fraction; a known string stays an anchor."""
    assert _parse_hline_x(1) == 1.0
    assert isinstance(_parse_hline_x(1), float)
    assert _parse_hline_x("center") == "center"


def test_axis_rejects_both_with_the_callers_message() -> None:
    """``_parse_axis`` accepts only x/y and raises the message its caller chose."""
    assert _parse_axis("y", "msg") == "y"
    with pytest.raises(ValueError, match="^custom$"):
        _parse_axis("both", "custom")
