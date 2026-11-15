"""The labels' pure decisions on hand-made facts."""

from __future__ import annotations

import pytest

from dartwork_mpl.labels import decide
from dartwork_mpl.labels.model import (
    Center,
    Column,
    CrowdFacts,
    Edge,
    HeadroomFacts,
    Higher,
    Inside,
    Lower,
    Outside,
    Panel,
    PanelsFacts,
    Pixels,
    Room,
    Segment,
    Span,
    Spot,
    StackTotal,
    Title,
    TotalsToo,
    Tries,
    Try,
    ValueFacts,
    parse_bar_options,
    placement,
)
from dartwork_mpl.labels.stacks import BarRun, BarsFacts


def _spots(*spans: tuple[float, float]) -> tuple[Spot, ...]:
    return tuple(Spot((lo + hi) / 2, Span(lo, hi)) for lo, hi in spans)


@pytest.mark.parametrize(
    ("centres", "spans", "crowded"),
    [
        ((0, 20, 40), ((-5, 5), (15, 25), (35, 45)), False),  # 10 px in 20
        ((0, 20, 40), ((-9.5, 9.5), (10.5, 29.5), (30.5, 49.5)), True),
        ((0,), ((-50, 50),), False),  # one bar: no pitch
    ],
)
def test_a_label_wider_than_the_pitch_less_the_gap_is_crowded(
    centres, spans, crowded
):
    facts = CrowdFacts(_spots(*spans), centres, Pixels(2.0))
    assert decide.crowded(facts) is crowded


def test_overlapping_positions_are_hidden_from_the_last():
    spots = _spots((0, 12), (10, 22), (20, 32), (30, 42))
    shown = decide.keep_apart(CrowdFacts(spots, (6, 16, 26, 36), Pixels(1.0)))
    assert shown.flags == (False, True, False, True)


@pytest.mark.parametrize(
    ("rooms", "view"),
    [
        ((), None),
        ((Room(50, 20, Higher()),), None),  # 50 + 20 inside 100
        ((Room(95, 10, Higher()),), Span(0, 1000 / 90 * 9.5)),
        ((Room(5, 10, Lower()),), Span(-500 / 90, 100)),
        ((Room(50, 200, Higher()),), None),  # longer than the axes: no widening
    ],
)
def test_headroom_grows_only_as_far_as_the_labels_need(rooms, view):
    grown = decide.headroom(HeadroomFacts(Span(0, 100), rooms)).view
    if view is None:
        assert grown is None
    else:
        assert grown is not None
        assert (grown.low, grown.high) == pytest.approx((view.low, view.high))


@pytest.mark.parametrize(
    ("value", "decimals", "fixed"), [(21.4, 1, False), (0.0, 2, True)]
)
def test_bar_text_is_the_value_at_the_call_decimals(value, decimals, fixed):
    text = decide.bar_text(ValueFacts(value, decimals, fixed))
    assert (text.value, text.decimals, text.fixed, text.lead) == (
        value,
        decimals,
        fixed,
        "",
    )


def test_every_finite_bar_gets_a_plain_label():
    run = BarRun(
        (0, 1, 2),
        (0, 0, 0),
        (3, float("nan"), 5),
        (3, float("nan"), 5),
        ("ax", "vertical"),
    )
    plan = decide.plain_labels(BarsFacts((run,), TotalsToo()))
    assert [(p.index, p.kind, p.value) for p in plan.labels] == [
        (0, Edge(), 3),
        (2, Edge(), 5),
    ]


def _tries(*pairs: tuple[float, float]) -> Tries:
    return Tries(tuple(Try(o, c) for o, c in pairs))


@pytest.mark.parametrize(
    ("pairs", "side"),
    [
        (((0, 0), (0, 0), (0, 0), (0, 0)), 0),  # above is free
        (((0, 5), (0, 0), (0, 0), (0, 0)), 1),  # below next
        (((3, 0), (0, 0), (0, 9), (0, 0)), 3),  # above leaves: never below
        (((3, 1), (0, 5), (4, 0), (0, 2)), 3),  # none free: least inside
        (((3, 1), (0, 0), (4, 0), (5, 2)), 0),  # all outside: least overall
    ],
)
def test_value_side_takes_the_first_free_side(pairs, side):
    assert decide.value_side(_tries(*pairs)).index == side


def test_first_free_falls_back_to_the_least_covered():
    assert decide.first_free(_tries((0, 4), (0, 0))).index == 1
    assert decide.first_free(_tries((0, 4), (2, 1))).index == 1


def _panel(x: float, *, cell=None, ylabel=None, title=None, top=100.0) -> Panel:
    titles = () if title is None else (Title(title),)
    return Panel(
        corner=(x, 100.0),
        width=8.0,
        descent=2.0,
        cell=cell,
        ylabel_x0=ylabel,
        guess_x0=x - 30,
        titles=titles,
        top=top,
        decos=(),
    )


def test_letters_take_the_column_s_outer_name_and_the_title_baseline():
    panels = (
        _panel(100, cell=((1, 0), (1, 0)), ylabel=70, title=112),
        _panel(100, cell=((1, 1), (1, 0)), ylabel=60),
        _panel(300, cell=((1, 0), (1, 1))),
    )
    facts = PanelsFacts(panels, 1.0, False)
    letters = decide.align_letters(facts, decide.letter_lefts(facts))
    # A column takes its leftmost name; an unnamed panel keeps its row's
    # spine distance; an untitled letter rises to its row's baseline.
    assert letters.lefts == (60, 60, 260)
    assert letters.baselines == (112, 104, 112)


def test_letters_without_any_name_go_where_a_name_would_be():
    facts = PanelsFacts((_panel(100),), 1.0, False)
    assert decide.letter_lefts(facts).lefts == (70,)


def test_spread_keeps_order_and_the_mean_of_a_crowded_group():
    out = decide.spread(Column((10.0, 11.0, 40.0), 6.0)).centres
    assert out == pytest.approx((7.5, 13.5, 40.0))


def _no_colour(value: object) -> tuple[float, float, float, float]:
    raise ValueError(value)


def test_options_parse_once_and_name_a_bad_keyword():
    options = parse_bar_options(
        where="auto",
        total="auto",
        crowded="rotate",
        decimals=None,
        fmt="{:.1f} GWh",
        color="series",
        sign="+",
        to_rgba=_no_colour,
    )
    assert options.series
    assert options.plus
    assert placement(Segment(), options.where) == Center()
    assert placement(StackTotal(), Inside()) == Outside()
    for bad in (
        {"where": "top"},
        {"decimals": -1},
        {"fmt": "GWh"},
        {"color": "nope"},
    ):
        kw = {
            **{
                "where": "auto",
                "total": "auto",
                "crowded": "rotate",
                "decimals": None,
                "fmt": None,
                "color": None,
                "sign": "-",
            },
            **bad,
        }
        with pytest.raises(ValueError, match=next(iter(bad))):
            parse_bar_options(**kw, to_rgba=_no_colour)
