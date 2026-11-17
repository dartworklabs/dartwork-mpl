"""The labels' pure decisions on hand-made facts."""

from __future__ import annotations

import pytest

from dartwork_mpl.labels import decide
from dartwork_mpl.labels.bar_geometry import (
    BeyondEnd,
    CrowdFacts,
    HeadroomFacts,
    Higher,
    Lower,
    Pixels,
    Room,
    Spot,
)
from dartwork_mpl.labels.model import (
    Column,
    Inside,
    Panel,
    PanelsFacts,
    Run,
    Title,
    Tries,
    Try,
)
from dartwork_mpl.labels.stacks import BarRun, BarsFacts
from dartwork_mpl.vocab import Span


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


def test_every_finite_bar_gets_a_plain_label():
    run = BarRun(
        (0, 1, 2),
        (0, 0, 0),
        (3, float("nan"), 5),
        (3, float("nan"), 5),
        ("ax", "vertical"),
    )
    plan = decide.plain_labels(BarsFacts((run,)))
    assert [(p.index, p.kind, p.value) for p in plan.labels] == [
        (0, BeyondEnd(), 3),
        (2, BeyondEnd(), 5),
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


def _panel(
    x: float,
    *,
    cell=None,
    title=None,
    top=100.0,
    plot=200.0,
    joined=None,
    apart=None,
) -> Panel:
    titles = () if title is None else (Title(title),)
    return Panel(
        corner=(x, 100.0),
        width=8.0,
        height=10.0,
        descent=2.0,
        size=10.0,
        cell=cell,
        titles=titles,
        top=top,
        decos=(),
        plot_width=plot,
        joined=joined,
        apart=apart,
    )


@pytest.mark.parametrize(
    ("runs", "where"),
    [
        # letter 8 + gap 5 + title: a run fits while it is no wider than
        # its plot (200 px), in every panel.
        (((None, None), (None, None)), Run()),
        (((187.0, None), (100.0, None)), Run()),  # 8 + 5 + 187 = 200
        (((100.0, None), (188.0, None)), Inside(1)),
        (((100.0, 80.0), (None, None)), Run()),  # with a right title
        (((120.0, 80.0), (None, None)), Inside(0)),
    ],
)
def test_one_placement_for_the_figure(runs, where):
    panels = tuple(
        _panel(300.0 * i, joined=j, apart=a) for i, (j, a) in enumerate(runs)
    )
    assert decide.placement(PanelsFacts(panels, 1.0)) == where


def test_a_run_starts_at_the_spine_on_the_title_baseline():
    panels = (
        _panel(100, cell=((1, 0), (1, 0)), title=112, joined=60.0),
        _panel(300, cell=((1, 0), (1, 1))),
    )
    facts = PanelsFacts(panels, 1.0)
    letters = decide.place_letters(facts, Run())
    assert letters.lefts == (100, 300)
    # An untitled letter rises to its row's title baseline.
    assert letters.baselines == (112, 112)
    assert letters.titles == (100 + 8 + 5, None)


def test_inside_letters_sit_in_from_the_plot_corner():
    facts = PanelsFacts((_panel(100, title=112, joined=60.0),), 1.0)
    letters = decide.place_letters(facts, Inside(0))
    assert letters.lefts == (104,)
    assert letters.baselines == (100 - 4 - 8,)
    assert letters.titles == (None,)


def test_spread_keeps_order_and_the_mean_of_a_crowded_group():
    out = decide.spread(Column((10.0, 11.0, 40.0), 6.0)).centres
    assert out == pytest.approx((7.5, 13.5, 40.0))
