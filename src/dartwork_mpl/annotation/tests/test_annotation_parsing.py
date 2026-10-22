"""Annotation entry points parse their string options once, and legend trials rank as documented.

The public parameters stay ``str``; these tests pin that each accepted string
maps to itself, each rejected one raises the unchanged public message, and
that ``place_legend``'s choice among trial placements (and the attributes it
reports) follows the scoring rules.
"""

import math

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.annotation import (
    _best_trial,
    _mark_placement,
    _MeasuredLegend,
    _parse_axis,
    _parse_corner,
    _parse_hline_side,
    _parse_hline_x,
    _parse_value_side,
    _UnmeasuredLegend,
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


def test_best_trial_picks_lowest_score_and_earliest_on_tie() -> None:
    """The lowest penalty wins; equal penalties keep the earlier candidate."""
    first = _MeasuredLegend("upper right", 1, score=0.5, collision_free=False)
    tied = _MeasuredLegend("upper left", 1, score=0.5, collision_free=False)
    worse = _MeasuredLegend("lower left", 1, score=0.9, collision_free=False)

    assert _best_trial([worse, first, tied]) is first


def test_unmeasured_trial_ranks_after_any_measured_one() -> None:
    """An unmeasurable placement is chosen only when nothing was measured."""
    unmeasured = _UnmeasuredLegend("upper right", 1)
    measured = _MeasuredLegend(
        "lower center", 3, score=1e9, collision_free=False
    )

    assert _best_trial([unmeasured, measured]) is measured
    assert (
        _best_trial([unmeasured, _UnmeasuredLegend("upper left", 2)])
        is unmeasured
    )


def test_mark_placement_reports_score_and_collision_state() -> None:
    """The legend carries the documented attributes; unmeasured reads False and inf."""
    fig, ax = plt.subplots()
    ax.plot([0, 1], label="a")
    legend = ax.legend()
    try:
        _mark_placement(
            legend,
            _MeasuredLegend("upper left", 2, score=0.25, collision_free=True),
        )
        assert legend._dm_collision_free is True
        assert legend._dm_collision_score == 0.25

        _mark_placement(legend, _UnmeasuredLegend("upper left", 2))
        assert legend._dm_collision_free is False
        assert math.isinf(legend._dm_collision_score)
    finally:
        plt.close(fig)
