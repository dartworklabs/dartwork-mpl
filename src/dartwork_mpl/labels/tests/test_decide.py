"""The labels' pure decisions on hand-made facts."""

from __future__ import annotations

import pytest

from dartwork_mpl.colorspace import Legibility, Ratio, Rgb
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
    DrawnOver,
    Halo,
    Ink,
    InkFacts,
    Inside,
    Leave,
    OwnAlpha,
    Panel,
    PanelsFacts,
    Recolour,
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


BLACK, WHITE, GREY = Rgb(0.0, 0.0, 0.0), Rgb(1.0, 1.0, 1.0), Rgb(0.3, 0.3, 0.3)
NAVY, PALE = Rgb.from_hex("#0b2a5b"), Rgb.from_hex("#b4c4fe")
RED = Rgb.from_hex("#fb5b5e")


def _reads(lowest: float, low: float = 0.0, worst: float = 0.0) -> Legibility:
    """A reading: its faintest ink at ``lowest``:1, ``low`` of the ink
    under 3:1 and ``worst`` of it in the worst window."""
    return Legibility(low, worst, Ratio(lowest), BLACK, WHITE)


def _facts(
    drawn: Legibility,
    *inks: tuple[Rgb, Legibility],
    home: Rgb = WHITE,
    size: float = 8.0,
    alpha: float = 1.0,
) -> InkFacts:
    """A text as it is painted, and how each ink it may take would read."""
    return InkFacts(drawn, tuple(Ink(c, r) for c, r in inks), home, size, alpha)


@pytest.mark.parametrize(
    ("facts", "plan"),
    [
        # black on white: nothing to do
        (
            _facts(
                _reads(15.0), (BLACK, _reads(15.0)), (WHITE, _reads(1.0, 1, 1))
            ),
            Leave(),
        ),
        # grey numbers on a mid band read (3.1:1): the author's colour,
        # though black would read better
        (
            _facts(_reads(3.1), (GREY, _reads(3.1)), (BLACK, _reads(4.6))),
            Leave(),
        ),
        # every part reads, though faint specks cross it
        (
            _facts(
                _reads(2.5, 0.05, 0.3),
                (BLACK, _reads(2.5, 0.05, 0.3)),
                (WHITE, _reads(1.0, 0.6, 1)),
            ),
            Leave(),
        ),
        # all of it lost on a dark band: the paper colour reads
        (
            _facts(
                _reads(1.3, 1, 1),
                (GREY, _reads(1.3, 1, 1)),
                (BLACK, _reads(2.0, 1, 1)),
                (WHITE, _reads(9.0)),
            ),
            Recolour(WHITE),
        ),
        # a red note lost only where it crosses a dark wedge stays red
        (
            _facts(
                _reads(1.9, 0.18, 1),
                (RED, _reads(1.9, 0.18, 1)),
                (BLACK, _reads(4.4)),
            ),
            Halo(WHITE, pytest.approx(1.12)),
        ),
        # ... a grey one takes the black that reads on both
        (
            _facts(
                _reads(1.9, 0.18, 1),
                (GREY, _reads(1.9, 0.18, 1)),
                (BLACK, _reads(4.4)),
            ),
            Recolour(BLACK),
        ),
        # ... and a red one lost on all it stands on takes it too
        (
            _facts(
                _reads(1.9, 0.9, 1),
                (RED, _reads(1.9, 0.9, 1)),
                (BLACK, _reads(4.4)),
            ),
            Recolour(BLACK),
        ),
        # across canvas and navy: no one colour, an outline of the canvas
        (
            _facts(
                _reads(1.4, 0.45, 1),
                (BLACK, _reads(1.4, 0.45, 1)),
                (WHITE, _reads(1.0, 0.55, 1)),
            ),
            Halo(WHITE, pytest.approx(1.12)),
        ),
        # a colour that loses one whole window to a thin band is no answer,
        # however little of the text that window is
        (
            _facts(
                _reads(1.0, 0.01, 1),
                (BLACK, _reads(1.0, 0.01, 1)),
                (WHITE, _reads(1.0, 0.99, 1)),
            ),
            Halo(WHITE, pytest.approx(1.12)),
        ),
    ],
)
def test_a_text_takes_the_least_that_makes_it_read(
    facts: InkFacts, plan: object
):
    """Nothing while it reads; else the one colour that reads everywhere;
    else an outline."""
    assert decide.mend(facts) == plan


def test_a_halo_is_the_colour_the_text_reads_best_on_and_never_hairline():
    """Black over pale, mid and dark segments is outlined in the pale one,
    where it then disappears; grey that reads on nothing behind it takes
    the colour furthest from it, white or black when its own inks are all
    close. The outline is 0.14 em of the text, so it grows with it, and a
    tiny text's is never under 0.6 pt."""
    crossing = _reads(2.4, 0.46, 1.0)
    black = _facts(
        crossing, (BLACK, crossing), (WHITE, _reads(1.2, 0.5, 1)), home=PALE
    )
    assert decide.mend(black) == Halo(PALE, pytest.approx(1.12))
    grey = _facts(crossing, (GREY, crossing), (BLACK, crossing), home=NAVY)
    assert decide.plate(grey) == WHITE
    big = _facts(crossing, *((i.colour, i.reading) for i in black.inks),
                 home=PALE, size=20.0)  # fmt: skip
    assert decide.mend(big) == Halo(PALE, pytest.approx(2.8))
    tiny = _facts(crossing, *((i.colour, i.reading) for i in black.inks),
                  home=PALE, size=3.0)  # fmt: skip
    assert decide.mend(tiny) == Halo(PALE, 0.6)


def test_what_did_not_read_once_drawn_gets_the_next_step_then_none():
    """A colour that did not read on the drawn figure is followed by an
    outline; after an outline the text is left as it was."""
    lost = _reads(1.3, 1, 1)
    facts = _facts(lost, (GREY, lost), (WHITE, _reads(9.0)))
    assert decide.after(facts, Recolour(WHITE)) == Halo(
        WHITE, pytest.approx(1.12)
    )
    assert decide.after(facts, Halo(WHITE, pytest.approx(1.12))) == Leave()


def test_what_is_in_the_way_is_the_texts_alpha_or_something_over_it():
    """An outline reads under any opaque ink, so a text nothing helps is
    either translucent or drawn over."""
    lost = _reads(1.3, 1, 1)
    faint = _facts(lost, (GREY, lost), alpha=0.27)
    assert decide.in_the_way(faint) == OwnAlpha(0.27)
    assert decide.in_the_way(_facts(lost, (GREY, lost))) == DrawnOver()
