"""One test per rule in ``EDGES``, on facts built by hand (no figure)."""

from __future__ import annotations

from dartwork_mpl.check.edges import EDGES
from dartwork_mpl.check.findings import Findings
from dartwork_mpl.check.model import (
    Box,
    Facts,
    Hit,
    Inked,
    Legend,
    OnData,
    Panel,
    Text,
    TickRow,
)
from dartwork_mpl.check.roles import AxisLabel, FreeText, Role, TickLabel, Title
from dartwork_mpl.colorspace import Hex, Ratio
from dartwork_mpl.edgecase import settle
from dartwork_mpl.vocab import X

CANVAS = Box(0, 0, 1000, 600)
PT = 300 / 72
INSIDE = Box(100, 100, 300, 140)
FREE = FreeText()


def text(s: str, box: Box, role: Role = FREE, panel: int = 0) -> Text:
    return Text(object(), s, role, panel, box, em=40.0)


def row(
    *labels: str, overlaps: int = 0, numbers: bool = False, panel: int = 0
) -> TickRow:
    texts = tuple(
        text(s, Box(100 + 80 * i, 50, 150 + 80 * i, 80), TickLabel())
        for i, s in enumerate(labels)
    )
    return TickRow(
        object(), panel, X(), texts, overlaps, 4.0 * overlaps, numbers, False
    )


def found(facts: Facts) -> Findings:
    return settle(facts, Findings(), EDGES).plan


def test_OVERFLOW_cut_at_the_edge():
    cut = Facts(CANVAS, PT, texts=(text("Nuclear", Box(900, 300, 1010, 340)),))
    assert found(cut).rules == ("OVERFLOW",)
    assert not found(Facts(CANVAS, PT, texts=(text("ok", INSIDE),)))


def test_OVERLAP_within_one_axes():
    a, b = text("Peak", INSIDE), text("Trough", Box(250, 110, 400, 150))
    assert "OVERLAP" in found(Facts(CANVAS, PT, texts=(a, b))).rules
    apart = text("x", Box(400, 100, 450, 140))
    assert not found(Facts(CANVAS, PT, texts=(a, apart)))
    name = text("Visitors", Box(140, 40, 200, 90), AxisLabel())
    on_ticks = Facts(CANVAS, PT, texts=(name,), ticks=(row("10", "20"),))
    assert "OVERLAP" in found(on_ticks).rules


def test_CROSS_AXES_OVERLAP_title_on_neighbour_ticks():
    title = text("Lower", Box(100, 60, 200, 90), Title(), panel=1)
    facts = Facts(CANVAS, PT, texts=(title,), ticks=(row("1", "2"),))
    assert "CROSS_AXES_OVERLAP" in found(facts).rules


def test_TEXT_CROWD_value_beside_a_name():
    value = text("19.4 TWh", Box(700, 500, 860, 540))
    name = text("Solar", Box(889, 500, 980, 540))
    assert "TEXT_CROWD" in found(Facts(CANVAS, PT, texts=(value, name))).rules
    far = text("Solar", Box(920, 500, 990, 540))
    assert not found(Facts(CANVAS, PT, texts=(value, far)))
    two_names = (text("Hydro", value.box), text("Wind", name.box))
    assert not found(Facts(CANVAS, PT, texts=two_names))


def test_LEGEND_ON_DATA_reports_what_it_covers():
    box = Box(100, 500, 300, 560)
    legend = Legend(object(), 0, ("A",), (Hit("marker", "Samples"),), box)
    (f,) = found(Facts(CANVAS, PT, legends=(legend,)))
    assert f.rule == "LEGEND_ON_DATA"
    assert "covers markers ('Samples')" in f.message
    clear = Legend(object(), 0, ("A",), (), box)
    title = text("Phones lead", Box(150, 540, 400, 580), Title())
    (f,) = found(Facts(CANVAS, PT, texts=(title,), legends=(clear,)))
    assert "covers titles ('Phones lead')" in f.message
    twin = Legend(object(), 1, ("B",), (), Box(100, 520, 280, 560))
    (f,) = found(Facts(CANVAS, PT, legends=(clear, twin)))
    assert "covers legends" in f.message and f.artists == (twin.handle,)


def test_TICK_OVERLAP():
    assert found(
        Facts(CANVAS, PT, ticks=(row("a", "b", overlaps=2),))
    ).rules == ("TICK_OVERLAP",)


def test_EMPTY_AXES():
    (f,) = found(Facts(CANVAS, PT, empty=(Panel(object(), 5),)))
    assert f.rule == "EMPTY_AXES" and f.panels == (5,)


def test_MISSING_AXIS_LABEL():
    numbers = row("1", "2", numbers=True)
    assert found(Facts(CANVAS, PT, ticks=(numbers,))).rules == (
        "MISSING_AXIS_LABEL",
    )
    assert not found(Facts(CANVAS, PT, ticks=(row("Mon", "Tue"),)))
    blank = Facts(CANVAS, PT, ticks=(numbers,), empty=(Panel(object(), 0),))
    assert found(blank).rules == ("EMPTY_AXES",)


def test_VALUE_LABEL_ON_DATA():
    label = text("3.1", INSIDE)
    on = OnData(label, (Hit("line", ""),))
    (f,) = found(Facts(CANVAS, PT, texts=(label,), values=(on,)))
    assert f.rule == "VALUE_LABEL_ON_DATA" and f.artists == (label.handle,)


def test_TEXT_CONTRAST():
    label = text("4.6", INSIDE)
    white, yellow = Hex("#ffffff"), Hex("#f9d969")
    faint = Inked(label, white, yellow, Ratio(1.39))
    (f,) = found(Facts(CANVAS, PT, texts=(label,), inks=(faint,)))
    assert f.rule == "TEXT_CONTRAST" and "1.39:1" in f.message
    plain = Inked(label, Hex("#000000"), yellow, Ratio(3.2))
    assert not found(Facts(CANVAS, PT, texts=(label,), inks=(plain,)))


def test_VALUE_LABEL_DECIMAL():
    counts = [
        text(s, Box(100 * i, 100, 100 * i + 50, 140))
        for i, s in enumerate(("12.0", "31.0"), 1)
    ]
    assert found(Facts(CANVAS, PT, texts=tuple(counts))).rules == (
        "VALUE_LABEL_DECIMAL",
    )
    mixed = (counts[0], text("31.5", Box(300, 100, 350, 140)))
    assert not found(Facts(CANVAS, PT, texts=mixed))
