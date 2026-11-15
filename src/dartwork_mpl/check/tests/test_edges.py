"""One test per rule in ``EDGES``, on facts built by hand (no figure)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dartwork_mpl.axis import X
from dartwork_mpl.check.edges import EDGES
from dartwork_mpl.check.findings import Findings
from dartwork_mpl.check.model import (
    Box,
    Contrast,
    Corner,
    Facts,
    Hit,
    Legend,
    Panel,
    Text,
    TickRow,
    ValueLabel,
)
from dartwork_mpl.check.roles import AxisLabel, FreeText, Role, TickLabel, Title
from dartwork_mpl.edgecase import settle

CANVAS = Box(0, 0, 1000, 600)
PT = 300 / 72


FREE = FreeText()


def text(s: str, box: Box, role: Role = FREE, panel: int | None = 0) -> Text:
    return Text(object(), s, role, panel, box, em=40.0)


def row(*labels: str, **kw: object) -> TickRow:
    texts = tuple(
        text(s, Box(100 + 80 * i, 50, 150 + 80 * i, 80), TickLabel())
        for i, s in enumerate(labels)
    )
    base = {
        "handle": object(),
        "panel": 0,
        "axis": X(),
        "labels": texts,
        "span": 800.0,
        "need": 300.0,
        "closest": 1.0,
        "overlaps": 0,
        "deepest": 0.0,
        "names": False,
        "labelled": True,
        "labelled_elsewhere": False,
    }
    return TickRow(**{**base, **kw})  # type: ignore[arg-type]


def rules(facts: Facts) -> list[str]:
    return [f.rule for f in settle(facts, Findings(), EDGES).plan]


def facts(**kw: object) -> Facts:
    return Facts(canvas=CANVAS, px_per_pt=PT, **kw)  # type: ignore[arg-type]


INSIDE = Box(100, 100, 300, 140)


def test_every_rule_has_a_unique_name():
    names = [e.name for e in EDGES]
    assert len(names) == len(set(names)) == 18


def test_OVERFLOW_cut_at_the_edge():
    assert "OVERFLOW" in rules(
        facts(texts=(text("Nuclear", Box(900, 300, 1010, 340)),))
    )
    assert "OVERFLOW" not in rules(facts(texts=(text("ok", INSIDE),)))


def test_TEXT_AT_EDGE_flush_is_one_info():
    flush = (
        text("a", Box(0, 500, 20, 540)),
        text("Nuclear", Box(900, 300, 1000, 340)),
    )
    found = settle(facts(texts=flush), Findings(), EDGES).plan.of(
        "TEXT_AT_EDGE"
    )
    assert len(found) == 1 and "left: 'a'" in found[0].message
    assert str(found[0].severity) == "INFO"


def test_OVERLAP_within_one_axes():
    a, b = text("Peak", INSIDE), text("Trough", Box(250, 110, 400, 150))
    assert "OVERLAP" in rules(facts(texts=(a, b)))
    assert "OVERLAP" not in rules(
        facts(texts=(a, text("x", Box(400, 100, 450, 140))))
    )


def test_OVERLAP_counts_an_axis_name_on_its_tick_labels():
    name = text("Visitors", Box(140, 40, 200, 90), AxisLabel())
    assert "OVERLAP" in rules(facts(texts=(name,), ticks=(row("10", "20"),)))


def test_CROSS_AXES_OVERLAP_title_on_neighbour_ticks():
    title = text("Lower", Box(100, 60, 200, 90), Title(), panel=1)
    assert "CROSS_AXES_OVERLAP" in rules(
        facts(texts=(title,), ticks=(row("1", "2"),))
    )


def test_TEXT_CROWD_value_beside_a_name():
    value = text("19.4 TWh", Box(700, 500, 860, 540))
    name = text("Solar", Box(889, 500, 980, 540))
    assert "TEXT_CROWD" in rules(facts(texts=(value, name)))
    far = text("Solar", Box(920, 500, 990, 540))
    assert "TEXT_CROWD" not in rules(facts(texts=(value, far)))
    both_names = text("Wind", Box(889, 500, 980, 540))
    assert "TEXT_CROWD" not in rules(
        facts(texts=(text("Hydro", value.box), both_names))
    )


def _legend(
    box: Box, covers: tuple[Hit, ...] = (), panel: int | None = 0
) -> Legend:
    return Legend(
        object(), panel, box, ("A", "B"), Box(100, 100, 500, 400), 0.0, covers
    )


def test_LEGEND_OVERFLOW_too_big_or_off_canvas():
    assert "LEGEND_OVERFLOW" in rules(
        facts(legends=(_legend(Box(100, 100, 400, 300)),))
    )
    assert "LEGEND_OVERFLOW" in rules(
        facts(legends=(_legend(Box(950, 100, 1100, 150)),))
    )
    assert "LEGEND_OVERFLOW" not in rules(
        facts(legends=(_legend(Box(400, 350, 490, 390)),))
    )


def test_LEGEND_OVERLAP_over_a_title():
    title = text("Sales", Box(200, 400, 300, 430), Title())
    legend = _legend(Box(150, 390, 350, 420))
    assert "LEGEND_OVERLAP" in rules(facts(texts=(title,), legends=(legend,)))


def test_LEGEND_ON_DATA_reports_what_it_covers():
    legend = _legend(Box(400, 350, 490, 390), (Hit("marker", "Samples"),))
    found = settle(facts(legends=(legend,)), Findings(), EDGES).plan.of(
        "LEGEND_ON_DATA"
    )
    assert "covers markers ('Samples')" in found[0].message


def test_VALUE_LABEL_ON_DATA_per_axes():
    on = ValueLabel(text("12", INSIDE), (Hit("line", "Revenue"),))
    off = ValueLabel(text("15", INSIDE), ())
    found = settle(facts(values=(on, off)), Findings(), EDGES).plan
    assert "1 of 2 value labels" in found.of("VALUE_LABEL_ON_DATA")[0].message


def test_VALUE_LABEL_DECIMAL_whole_numbers_with_decimals():
    labels = (text("120.0", INSIDE), text("135.0", INSIDE))
    assert "VALUE_LABEL_DECIMAL" in rules(facts(texts=labels))
    real = (text("88.9%", INSIDE), text("90.0%", INSIDE))
    assert "VALUE_LABEL_DECIMAL" not in rules(facts(texts=real))


def test_TICK_OVERLAP():
    assert "TICK_OVERLAP" in rules(
        facts(ticks=(row("a", "b", overlaps=2, deepest=4.0),))
    )


def test_TICK_CROWD_needs_both_fill_and_closeness():
    assert "TICK_CROWD" in rules(
        facts(ticks=(row("a", "b", need=900.0, closest=0.1),))
    )
    assert "TICK_CROWD" not in rules(
        facts(ticks=(row("a", "b", need=900.0, closest=0.6),))
    )


def test_TICK_CORNER_OVERLAP():
    x, y = text("-3", INSIDE, TickLabel()), text("-3", INSIDE, TickLabel())
    corner = Corner(0, 1, 3.0, x, y, "lower left")
    assert "TICK_CORNER_OVERLAP" in rules(facts(corners=(corner,)))


@pytest.mark.parametrize(
    ("labels", "fires"),
    [
        (("2.0", "4.0", "6.0"), True),  # whole numbers with decimals
        (("0.5", "1", "1.5"), True),  # mixed places
        (("1.0", "1.0", "1.5"), True),  # twins
        (("0.12500", "0.25000", "0.37500"), True),  # excess precision
        (
            ("-1.0M", "-0.5M", "0", "0.5M", "1.0M"),
            False,
        ),  # a bare 0 has no unit
        (("0", "0.5", "1.0"), False),
        (("Q1", "Q2", "Q3"), False),
    ],
)
def test_TICK_DECIMAL(labels: tuple[str, ...], fires: bool):
    assert ("TICK_DECIMAL" in rules(facts(ticks=(row(*labels),)))) is fires


def test_MISSING_AXIS_LABEL_only_for_numbers_named_nowhere():
    assert "MISSING_AXIS_LABEL" in rules(
        facts(ticks=(row("1", labelled=False),))
    )
    for kw in (
        {"names": True},
        {"labelled_elsewhere": True},
        {"labelled": True},
    ):
        r = row("1", **{"labelled": False, **kw})
        assert "MISSING_AXIS_LABEL" not in rules(facts(ticks=(r,)))


def test_TEXT_CONTRAST_grouped_by_colours():
    faint = Contrast(text("note", INSIDE), 1.6, False, "#dddddd", "#ffffff")
    found = settle(facts(contrast=(faint, faint)), Findings(), EDGES).plan
    assert str(found.of("TEXT_CONTRAST")[0].severity) == "WARNING"
    fine = replace(faint, ratio=7.0)
    assert "TEXT_CONTRAST" not in rules(facts(contrast=(fine,)))


def test_EMPTY_AXES():
    assert "EMPTY_AXES" in rules(
        facts(panels=(Panel(object(), 1, INSIDE, True),))
    )


def test_MARGIN_ASYMMETRY():
    assert "MARGIN_ASYMMETRY" in rules(facts(content=Box(40, 40, 700, 560)))
    assert "MARGIN_ASYMMETRY" not in rules(facts(content=Box(40, 40, 960, 560)))
