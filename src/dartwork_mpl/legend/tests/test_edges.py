"""Each named legend edge case: when it fires and what it changes."""

from __future__ import annotations

from dataclasses import replace

from dartwork_mpl.edgecase import settle
from dartwork_mpl.legend import decide
from dartwork_mpl.legend.edges import EDGES
from dartwork_mpl.legend.model import (
    AnchorFacts,
    Box,
    Columns,
    Entries,
    EntryFacts,
    EntryPlan,
    FigureFacts,
    FigurePlan,
    Hits,
    Inside,
    Loc,
    Outside,
    Owner,
    Request,
    Side,
    Size,
    Span,
    TitleBox,
    TitleFacts,
    TitlePad,
)
from dartwork_mpl.legend.tests.test_decide import AXES, CORNER, facts, size_of


def _settled(f, plan):
    return settle(f, plan, EDGES)


def test_polar_frame_ink_counts_the_frame_as_data():
    def frame(box: Box) -> Hits:  # an angle label in the upper right
        return Hits(int(box.overlaps(CORNER["upper right"])))

    f = facts(frame=frame)
    result = _settled(f, decide.place(f))
    assert result.fired == ("polar-frame-ink",)
    assert result.plan == Inside(Loc.UPPER_LEFT, Columns(1))


def test_overlong_entry_names_break_to_the_side():
    def wrap(entries: Entries, width) -> Entries:
        return Entries(tuple(t.replace(" ", "\n") for t in entries.labels))

    def wide(entries: Entries, columns: Columns) -> Size:
        lines = max(t.count("\n") + 1 for t in entries.labels)
        return Size(600.0 / lines, 15.0 * lines)

    f = replace(
        facts(n=1, request=Request(Side.BELOW), wrap=wrap, size_of=wide),
        entries=Entries(("a long name",)),
    )
    plain = decide.place(f)
    assert isinstance(plain, Outside) and not plain.fits
    result = _settled(f, plain)
    assert result.fired == ("overlong-entry-names",)
    assert isinstance(result.plan, Outside) and result.plan.fits
    assert result.plan.entries == Entries(("a\nlong\nname",))


def test_overlong_entry_names_leave_a_fitting_legend_above_alone():
    f = facts(request=Request(Side.ABOVE))
    assert _settled(f, decide.place(f)).fired == ()


def _twins(**second) -> EntryFacts:
    bars = Owner(Entries(("Rain",)), (0.0, 0), legend=Entries(("Rain",)))
    line = Owner(Entries(("Temp", "Rain")), (0.0, 1), **second)
    return EntryFacts((bars, line))


def test_twin_merge_puts_every_entry_on_the_twin_drawn_last():
    f = _twins()
    result = _settled(f, decide.entries(f))
    assert result.fired == ("twin-merge",)
    assert result.plan == EntryPlan(host=1, picks=((0, 0), (1, 0)), remove=(0,))


def test_explicit_legend_kept_when_it_is_not_what_the_artists_draw():
    f = _twins(legend=Entries(("Temperature (C)",)))
    result = _settled(f, decide.entries(f))
    assert result.fired == ("twin-merge", "explicit-legend-kept")
    assert isinstance(result.plan, EntryPlan) and result.plan.leave == 1


def _anchor(length: float, span: Span) -> AnchorFacts:
    tick = Box(-30, 290, -4, 310)  # the top y tick label, left of the Axes
    return AnchorFacts(Side.ABOVE, AXES, Size(length, 20), span, (tick,))


def test_outside_on_canvas_moves_a_wide_legend_back_in():
    f = _anchor(500.0, Span(-40.0, 600.0))  # centred: -50 to 450
    result = _settled(f, decide.anchor(f))
    assert result.fired == ("outside-on-canvas",)
    assert result.plan.shift == 10.0  # its left end on the span's
    assert result.plan.clearance == 10.0  # over the tick label it spans


def test_outside_on_canvas_leaves_a_short_centred_legend():
    f = _anchor(100.0, Span(-40.0, 600.0))
    assert _settled(f, decide.anchor(f)).fired == ()


def test_title_over_above_legend_lifts_the_titles_over_it():
    title = TitleBox(Box(150, 305, 250, 320), base_y=300.0, pad=5.0)
    f = TitleFacts((title,), (Box(100, 302, 300, 330),), gap=6.0)
    result = _settled(f, decide.title_pad(f))
    assert result.fired == ("title-over-above-legend",)
    assert result.plan == TitlePad(36.0)
    beside = replace(f, legends_above=(Box(260, 302, 400, 330),))
    assert _settled(beside, decide.title_pad(beside)).plan == TitlePad()


def test_figure_legend_past_suplabels_goes_under_the_suptitle():
    f = FigureFacts(
        None,
        None,
        Entries(("a",)),
        Box(0, 0, 500, 400),
        5.0,
        size_of,
        label_edges={Side.ABOVE: 0.93},
    )
    result = _settled(f, decide.figure_place(f))
    assert result.fired == ("figure-legend-past-suplabels",)
    assert result.plan == FigurePlan(Side.ABOVE, Columns(1), (0.5, 0.93))
