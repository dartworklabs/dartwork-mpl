"""Annotation entry points parse their string options once, and legend placements rank as documented.

The public parameters stay ``str``; these tests pin that each accepted string
maps to itself, each rejected one raises the unchanged public message, and
that ``place_legend``'s choice among inside spots and outside plans follows
the ladder's ordering rules.
"""

import pytest

from dartwork_mpl.annotation._axis_labels import _parse_axis
from dartwork_mpl.annotation._legend_fit import InsideSpot, wrap_label
from dartwork_mpl.annotation._legend_outside import (
    OutsidePlan,
    choose,
    split_ncols,
)
from dartwork_mpl.annotation._place_legend import first_free
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


# ------------------------------------------------------------ inside spots
def _spot(loc: str, ncol: int = 1, met: int = 0, over: float = 0.0, tall=0.0):
    return InsideSpot(loc, ncol, met=met, overflow=over, tall=tall)


def test_a_spot_is_free_only_clear_of_ink_and_inside_the_axes() -> None:
    assert _spot("upper right").free
    assert not _spot("upper right", met=1).free
    assert not _spot("upper right", over=0.01).free


def test_the_first_free_spot_wins_in_ladder_order() -> None:
    """Fewest columns first, then the spot order; taken spots are skipped."""
    spots = [
        _spot("upper right", met=2),
        _spot("upper left"),
        _spot("upper right", ncol=2),
    ]
    assert first_free(spots) is spots[1]
    assert first_free([_spot("upper right", met=1)]) is None


def test_a_tall_one_column_legend_goes_last() -> None:
    tall = _spot("upper right", tall=0.2)
    wide = _spot("upper right", ncol=2)
    assert first_free([tall, wide]) is wide
    assert first_free([tall]) is tall


def test_the_least_covering_spot_ranks_by_artists_then_overflow() -> None:
    spots = [
        _spot("upper right", met=2),
        _spot("upper left", met=1, over=0.3),
        _spot("lower left", met=1, over=0.1),
    ]
    assert min(spots, key=InsideSpot.rank) is spots[2]


# ------------------------------------------------------------ outside plans
def _plan(side, loss: float, fits: bool = True, ncols: int = 1) -> OutsidePlan:
    return OutsidePlan(side, ncols, ("a",), 10.0, 10.0, loss, fits)


@pytest.mark.parametrize(
    ("loss", "fits", "level"),
    [(0.6, True, 2), (0.61, True, 1), (1.0, True, 0), (0.1, False, 0)],
)
def test_a_plan_level_is_its_fit(loss: float, fits: bool, level: int) -> None:
    assert _plan("above", loss, fits).level == level


def test_above_stays_unless_another_side_clearly_costs_less() -> None:
    """A later side needs 10 % less loss and 5 % of the plot less."""
    above = _plan("above", 0.30)
    assert choose([above, _plan("right", 0.26)]) is above  # 13 % less, 4 pts
    assert choose([above, _plan("right", 0.28)]) is above  # 2 pts
    right = _plan("right", 0.24)
    assert choose([above, right]) is right  # 20 % less, 6 pts
    small = _plan("above", 0.04)
    assert choose([small, _plan("right", 0.0)]) is small  # 4 pts only


def test_a_better_fit_wins_whatever_it_costs() -> None:
    above = _plan("above", 0.7)  # fits, but takes 70 %
    right = _plan("right", 0.65)
    assert choose([above, right]) is above  # same level, 7 % less
    overflowing = _plan("above", 0.2, fits=False)
    assert choose([overflowing, _plan("right", 0.9)]).side == "right"


def test_a_large_share_needs_the_relative_gain_too() -> None:
    """6 points less of the plot is not enough when it is under 10 % less."""
    above = _plan("above", 0.9)
    assert choose([above, _plan("right", 0.84)]) is above  # 6.7 % less
    right = _plan("right", 0.8)
    assert choose([above, right]) is right  # 11 % and 10 points less


# ------------------------------------------------------------ wrapping
def _chars(text: str) -> float:
    return float(len(text))


def test_a_bracketed_unit_is_one_word() -> None:
    """``(2019 = 100)`` moves to the next line whole, never split at a space."""
    text = "Seoul region index (2019 = 100)"
    assert wrap_label(text, 24, _chars) == "Seoul region index\n(2019 = 100)"
    assert wrap_label(text, 12, _chars) == "Seoul region\nindex\n(2019 = 100)"


def test_wrapping_is_greedy_and_leaves_what_it_cannot_break() -> None:
    assert wrap_label("one two three four", 9, _chars) == "one two\nthree\nfour"
    assert wrap_label("short", 3, _chars) == "short"  # one word
    assert wrap_label("fits as is", 10, _chars) == "fits as is"
    assert wrap_label("two\nlines given", 4, _chars) == "two\nlines given"
    assert wrap_label(r"$\alpha$ is math", 4, _chars) == r"$\alpha$ is math"


def test_split_ncols_reads_either_spelling() -> None:
    assert split_ncols({"ncol": 2, "frameon": False}) == ({"frameon": False}, 2)
    assert split_ncols({"ncols": "3"}) == ({}, 3)
    assert split_ncols({}) == ({}, None)
