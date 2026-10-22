"""``simple_layout`` margins are parsed once into variants and solved by pure arithmetic.

Pins the three margin forms (percent, physical length, bare fraction), the
per-side fallback to ``margin``, the error raised for each bad form, and the
edge solver's sum, clamp and convergence delta, all without drawing.
"""

import math

import pytest

import dartwork_mpl as dm
from dartwork_mpl.layout import (
    _EDGE_EPSILON,
    _FractionMargin,
    _GridEdges,
    _margin_fraction,
    _parse_margin,
    _parse_margins,
    _PercentMargin,
    _PhysicalMargin,
    _Sides,
    _solve_edges,
)

_ZERO = _Sides(0.0, 0.0, 0.0, 0.0)


@pytest.mark.parametrize(
    ("value", "variant", "fraction_of_4in"),
    [
        ("5%", _PercentMargin(5.0), 0.05),
        (" 5% ", _PercentMargin(5.0), 0.05),
        (dm.inch(1), _PhysicalMargin(dm.inch(1)), 0.25),
        ("1in", _PhysicalMargin(dm.inch(1)), 0.25),
        (0.1, _FractionMargin(0.1), 0.1),
        (0, _FractionMargin(0.0), 0.0),
    ],
    ids=["pct", "pct-padded", "length", "unit-string", "float", "int"],
)
def test_each_margin_form_parses_to_its_variant(
    value, variant, fraction_of_4in
) -> None:
    """Each public form maps to one variant, and only a length depends on the extent."""
    margin = _parse_margin(value)

    assert margin == variant
    assert _margin_fraction(margin, 4.0) == pytest.approx(fraction_of_4in)


@pytest.mark.parametrize(
    ("value", "error", "match"),
    [
        (True, TypeError, "got bool"),
        ([1], TypeError, "got list"),
        ("a%", ValueError, "could not convert"),
        ("5xx", ValueError, "could not parse length"),
    ],
)
def test_bad_margin_is_rejected(value, error, match) -> None:
    """A bool or non-margin type raises ``TypeError``; a bad string ``ValueError``."""
    with pytest.raises(error, match=match):
        _parse_margin(value)


def test_unset_sides_fall_back_to_margin() -> None:
    """A per-side ``None`` takes ``margin``; ``margin=None`` means no margin."""
    spec = _parse_margins("2%", ml="1in", mr=None, mt=None, mb=0.1)

    assert spec.left == _PhysicalMargin(dm.inch(1))
    assert spec.right == spec.top == _PercentMargin(2.0)
    assert spec.bottom == _FractionMargin(0.1)
    assert _parse_margins(None, None, None, None, None).left == _FractionMargin(
        0.0
    )


def test_margins_resolve_against_their_own_axis() -> None:
    """Left/right lengths divide by the width, bottom/top by the height."""
    spec = _parse_margins(dm.inch(1), None, None, None, None)

    sides = spec.fractions(4.0, 2.0)

    assert (sides.left, sides.right) == (0.25, 0.25)
    assert (sides.bottom, sides.top) == (0.5, 0.5)


def test_margin_is_parsed_before_the_sides() -> None:
    """With several bad values, ``margin``'s error is the one raised."""
    with pytest.raises(TypeError):
        _parse_margins([1], ml="5xx", mr=None, mt=None, mb=None)


def test_solver_adds_reservation_margin_and_overhang() -> None:
    """Each edge moves inward by reservation + margin + content overhang."""
    step = _solve_edges(
        overhang=_Sides(0.05, 0.02, 0.1, 0.03),
        reserved=_Sides(0.0, 0.0, 0.0, 0.1),
        margins=_Sides(0.01, 0.01, 0.02, 0.02),
        last_edges=None,
        fw_px=400.0,
        fh_px=300.0,
    )

    assert step.edges == _GridEdges(
        left=pytest.approx(0.06),
        right=pytest.approx(0.97),
        bottom=pytest.approx(0.12),
        top=pytest.approx(0.85),
    )
    assert math.isinf(step.delta_px)


def test_solver_keeps_a_valid_rectangle_when_margins_eat_the_figure() -> None:
    """Edges stay in [0, 1] with at least ``_EDGE_EPSILON`` between opposite edges."""
    step = _solve_edges(
        _ZERO, _ZERO, _Sides(0.8, 0.8, 0.8, 0.8), None, 100, 100
    )

    assert step.edges.left == 0.8
    assert step.edges.right == pytest.approx(0.8 + _EDGE_EPSILON)
    assert step.edges.bottom == 0.8
    assert step.edges.top == pytest.approx(0.8 + _EDGE_EPSILON)


def test_solver_delta_is_the_largest_edge_move_in_pixels() -> None:
    """The convergence delta measures each edge move on its own axis's pixels."""
    last = _GridEdges(0.0, 1.0, 0.0, 1.0)

    step = _solve_edges(
        _ZERO,
        _ZERO,
        _Sides(0.01, 0.0, 0.0, 0.02),
        last,
        fw_px=100.0,
        fh_px=200.0,
    )

    assert step.delta_px == pytest.approx(4.0)
