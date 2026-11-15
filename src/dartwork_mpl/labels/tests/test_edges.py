"""Each named edge case of the labels: when it fires and what it changes."""

from __future__ import annotations

from dataclasses import replace

from dartwork_mpl.edgecase import settle
from dartwork_mpl.labels import decide, edges
from dartwork_mpl.labels.model import (
    BarOptions,
    HiddenFacts,
    Ink,
    InkFacts,
    Letters,
    Panel,
    PanelsFacts,
    Title,
    ValueFacts,
)
from dartwork_mpl.labels.stacks import BarRun, BarsFacts


def _text(value: float, decimals: int, *, precise=False, sign="-"):
    facts = ValueFacts(value, decimals, False, precise, sign)
    return settle(facts, decide.bar_text(facts), edges.TEXT)


def test_tiny_value_bound():
    settled = _text(0.03, 1)
    assert settled.fired == ("tiny-value-bound",)
    assert (settled.plan.lead, settled.plan.value) == ("<", 0.1)
    assert _text(-0.04, 1).plan.lead == ">"
    assert _text(0.03, 1, precise=True).fired == ()  # decimals= prints 0.0


def test_signed_steps():
    assert _text(30, 0, sign="+").plan.lead == "+"
    assert _text(30, 0, sign="+").fired == ("signed-steps",)
    assert _text(-15, 0, sign="+").fired == ()
    assert _text(0.0, 0, sign="+").fired == ()  # zero takes no sign
    assert _text(0.03, 1, sign="+").fired == ("tiny-value-bound",)


def _run(starts, lengths, host="ax"):
    n = len(starts)
    return BarRun(
        tuple(range(n)),
        tuple(starts),
        tuple(lengths),
        tuple(lengths),
        (host, "vertical"),
    )


def _bars(*runs, total="auto"):
    facts = BarsFacts(runs, total)
    return settle(facts, decide.plain_labels(facts), edges.BARS)


def test_stacked_segments_totals():
    settled = _bars(_run((0, 0), (5, 6)), _run((5, 6), (2, 3)))
    assert settled.fired == ("stacked-segments-totals",)
    kinds = [(p.run, p.index, p.kind, p.value) for p in settled.plan.labels]
    assert kinds == [
        (0, 0, "segment", 5),
        (0, 1, "segment", 6),
        (1, 0, "segment", 2),
        (1, 1, "segment", 3),
        (1, 0, "total", 7),
        (1, 1, "total", 9),
    ]
    only = _bars(_run((0, 0), (5, 6)), _run((5, 6), (2, 3)), total="only")
    assert {p.kind for p in only.plan.labels} == {"total"}
    # A highlight split into two containers: no stack, no '0' on the padding.
    split = _bars(_run((0, 0, 0), (5, 0, 7)), _run((0, 0, 0), (0, 6, 0)))
    assert [(p.run, p.index) for p in split.plan.labels] == [
        (0, 0),
        (0, 2),
        (1, 1),
    ]
    # Floating bars (a waterfall) and grouped bars stay plain.
    assert _bars(_run((0,), (5,)), _run((9,), (2,))).fired == ()


def _ink(on_bar: bool, kind="edge", **options):
    facts = InkFacts(
        BarOptions(**options), kind, on_bar, Ink("white"), Ink("#123456")
    )
    return settle(facts, decide.ink(facts), edges.INK)


def test_inside_readable_ink():
    assert _ink(True).plan == Ink("white")
    assert _ink(True).fired == ("inside-readable-ink",)
    assert _ink(True, color="red").plan == Ink(
        "red"
    )  # the caller's colour wins
    assert _ink(False).plan == Ink()


def test_series_colour():
    assert _ink(False, color="series").plan == Ink("#123456")
    assert _ink(False, color="series").fired == ("series-colour",)
    assert _ink(False, kind="total", color="series").plan == Ink()
    assert _ink(True, color="series").plan == Ink("white")


def test_warn_hidden_labels():
    def note(columns: int, rows: int):
        facts = HiddenFacts(10, columns, rows)
        settled = settle(facts, decide.notice(facts), edges.HIDDEN)
        assert settled.fired == (
            ("warn-hidden-labels",) if columns + rows else ()
        )
        return settled.plan.text

    assert note(0, 0) is None
    assert "4 of 10" in note(4, 0) and "a wider figure" in note(4, 0)
    assert "a taller figure" in note(0, 3)


def _panel(
    x,
    *,
    cell=None,
    outer=None,
    ylabel=None,
    bare=False,
    neighbour=None,
    titles=(),
):
    return Panel(
        corner=(x, 100.0),
        width=8.0,
        descent=2.0,
        gap=4.0,
        cell=cell,
        outer_cell=outer or cell,
        ylabel_x0=ylabel,
        guess_x0=x - 30,
        bare=bare,
        neighbour_x1=neighbour,
        titles=titles,
        top=100.0,
        decos=(),
    )


def test_panel_colorbar_column():
    nested = ((9, 0), (9, 0))
    facts = PanelsFacts(
        (_panel(100, cell=nested, outer=((1, 0), (1, 1))),), 1.0, False
    )
    settled = settle(facts, facts, edges.CELLS)
    assert settled.fired == ("panel-colorbar-column",)
    assert settled.plan.panels[0].cell == ((1, 0), (1, 1))


def test_panel_inner_shared_y():
    row = ((1, 0), (1, 1)), ((1, 0), (1, 2))
    facts = PanelsFacts(
        (
            _panel(100, cell=((1, 0), (1, 0)), ylabel=60),
            _panel(250, cell=row[0], bare=True, neighbour=240),
            _panel(400, cell=row[1], bare=True, neighbour=390),
        ),
        1.0,
        False,
    )
    lefts = decide.letter_lefts(facts)
    assert lefts.lefts == (60, 210, 360)  # the spine distance reaches 240
    settled = settle(facts, lefts, edges.LEFTS)
    assert settled.fired == ("panel-inner-shared-y",)
    assert settled.plan.lefts == (60, 250, 400)


def test_panel_left_title():
    title = Title("left", 72, 130, 110)
    facts = PanelsFacts((_panel(100, ylabel=70, titles=(title,)),), 1.0, False)
    settled = settle(facts, Letters((70,), ()), edges.LEFTS)
    assert settled.fired == ("panel-left-title",)
    assert settled.plan.lefts == (72 - 4 - 8,)
    clear = replace(title, x0=200, x1=260, loc="center")
    far = replace(facts, panels=(replace(facts.panels[0], titles=(clear,)),))
    assert settle(far, Letters((70,), ()), edges.LEFTS).fired == ()
