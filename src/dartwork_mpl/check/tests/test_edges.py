"""One test per rule in ``EDGES``, on facts built by hand (no figure)."""

from __future__ import annotations

from dataclasses import replace

from dartwork_mpl.check.edges import EDGES
from dartwork_mpl.check.findings import Findings
from dartwork_mpl.check.model import (
    Box,
    CanvasUse,
    Facts,
    Frame,
    Hit,
    Inked,
    Inset,
    Legend,
    OnData,
    Panel,
    PolarTheta,
    Text,
    TickOcclusion,
    TickRow,
    TickValues,
)
from dartwork_mpl.check.roles import (
    AxisLabel,
    FreeText,
    PanelLetter,
    Role,
    TickLabel,
    Title,
)
from dartwork_mpl.colorspace import Legibility, Ratio, Rgb
from dartwork_mpl.edgecase import settle
from dartwork_mpl.vocab import X, Y

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
    wide = text("A title wider than its plot", Box(10, 500, 520, 540), Title())
    plot, bar = (
        Frame(object(), 0, Box(20, 50, 450, 480)),
        Box(470, 30, 500, 560),
    )
    beside = Facts(
        CANVAS, PT, texts=(wide,), frames=(plot, Frame(None, 1, bar))
    )
    (f,) = found(beside)
    assert "runs into the plot of axes[1]" in f.message and f.panels == (0, 1)
    twin = Frame(object(), 1, plot.box)
    assert not found(Facts(CANVAS, PT, texts=(wide,), frames=(plot, twin)))


def test_an_inset_label_has_to_cross_the_parent_spine():
    label = text("Load (MW)", Box(100, 200, 140, 300), AxisLabel(), panel=1)
    parent = Panel(object(), 0)
    for spine, expected in (
        (Box(120, 100, 120, 400), ("CROSS_AXES_OVERLAP",)),
        (Box(102, 100, 102, 400), ()),
        (Box(120, 100, 120, 203), ()),
    ):
        inset = Inset(parent, 1, (label,), (spine,))
        facts = Facts(CANVAS, PT, texts=(label,), insets=(inset,))
        assert found(facts).rules == expected


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
    (f,) = found(Facts(CANVAS, PT, ticks=(numbers,)))
    assert f.rule == "MISSING_AXIS_LABEL" and "ax.set_xlabel(" in f.fix
    years = replace(numbers, at=TickValues((2019.0, 2020.0), linear=True))
    assert not found(Facts(CANVAS, PT, ticks=(years,)))
    assert not found(Facts(CANVAS, PT, ticks=(row("Mon", "Tue"),)))
    blank = Facts(CANVAS, PT, ticks=(numbers,), empty=(Panel(object(), 0),))
    assert found(blank).rules == ("EMPTY_AXES",)


def test_VALUE_LABEL_ON_DATA():
    label = text("3.1", INSIDE)
    on = OnData(label, (Hit("line", ""),))
    (f,) = found(Facts(CANVAS, PT, texts=(label,), values=(on,)))
    assert f.rule == "VALUE_LABEL_ON_DATA" and f.artists == (label.handle,)


def test_TEXT_ON_LINE():
    name = text("Apple A7", INSIDE)
    on = OnData(name, (Hit("line", "trend"),))
    (f,) = found(Facts(CANVAS, PT, texts=(name,), struck=(on,)))
    assert f.rule == "TEXT_ON_LINE" and f.artists == (name.handle,)
    assert "'Apple A7'" in f.message


def test_LETTER_ON_DATA():
    letter = text("b", Box(100, 500, 120, 530), PanelLetter())
    on = OnData(letter, (Hit("line", "Signal"),))
    (f,) = found(Facts(CANVAS, PT, texts=(letter,), letters=(on,)))
    assert f.rule == "LETTER_ON_DATA" and f.artists == (letter.handle,)
    assert "'b' sits on lines" in f.message


def test_TEXT_CONTRAST():
    """A text is found when one window of it has lost half its ink: all of
    a white value on pale yellow, or the part of a note on a navy bar."""
    label = text("4.6", INSIDE)
    white, yellow = Rgb(1.0, 1.0, 1.0), Rgb.from_hex("#f9d969")
    faint = Inked(label, Legibility(1.0, 1.0, Ratio(1.39), white, yellow))
    (f,) = found(Facts(CANVAS, PT, texts=(label,), inks=(faint,)))
    assert f.rule == "TEXT_CONTRAST" and "1.39:1" in f.message
    assert "all of its ink" in f.message and "#ffffff on #f9d969" in f.message
    black, navy = Rgb(0.0, 0.0, 0.0), Rgb.from_hex("#0b2a5b")
    partly = Inked(label, Legibility(0.45, 1.0, Ratio(1.43), black, navy))
    (f,) = found(Facts(CANVAS, PT, texts=(label,), inks=(partly,)))
    assert "45% of its ink" in f.message
    plain = Inked(label, Legibility(0.0, 0.0, Ratio(3.2), black, yellow))
    assert not found(Facts(CANVAS, PT, texts=(label,), inks=(plain,)))
    edge = Inked(label, Legibility(0.2, 0.49, Ratio(1.5), black, navy))
    assert not found(Facts(CANVAS, PT, texts=(label,), inks=(edge,)))


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


def test_SMALL_PANEL():
    def ticks(panel: int, *axes: X | Y) -> tuple[TickRow, ...]:
        label = (text("10", Box(0, 0, 20, 10), TickLabel(), panel),)
        return tuple(
            TickRow(object(), panel, w, label, 0, 0.0, True, True) for w in axes
        )

    # em 40 px: 7 tick labels are 280 px
    small = Frame(object(), 0, Box(0, 0, 400, 200))
    (f,) = found(Facts(CANVAS, PT, ticks=ticks(0, X(), Y()), frames=(small,)))
    assert f.rule == "SMALL_PANEL" and f.panels == (0,)
    roomy = Frame(object(), 1, Box(0, 0, 600, 300))
    both = ticks(0, X(), Y()) + ticks(1, X(), Y())
    largest = Facts(CANVAS, PT, ticks=both, frames=(small, roomy))
    assert "SMALL_PANEL" not in found(largest).rules
    colorbar = Facts(CANVAS, PT, ticks=ticks(0, Y()), frames=(small,))
    assert not found(colorbar)


def test_TEXT_TOO_CLOSE():
    title = text("Temperature peaks at noon", INSIDE, Title())
    for label, expected in (
        (text("Today", Box(110, 70, 160, 94)), ("TEXT_TOO_CLOSE",)),
        (text("Today", Box(110, 50, 160, 80)), ()),
        (text("Today", Box(110, 80, 160, 110)), ("OVERLAP",)),
        (text("Today", Box(304, 100, 360, 140)), ("TEXT_TOO_CLOSE",)),
        (text("Today", Box(304, 70, 360, 94)), ()),
        (text("Air temperature", Box(110, 70, 160, 94), AxisLabel()), ()),
    ):
        assert found(Facts(CANVAS, PT, texts=(title, label))).rules == expected

    first = text("Wind", INSIDE)
    for gap, expected in ((10, ("TEXT_TOO_CLOSE",)), (17, ())):
        second = text("Hydro", Box(120, 140 + gap, 320, 175 + gap))
        assert found(Facts(CANVAS, PT, texts=(first, second))).rules == expected

    for aligned in (
        Box(102, 144, 230, 184),  # left
        Box(170, 144, 299, 184),  # right
        Box(145, 144, 255, 184),  # centre
    ):
        second = text("Hydro", aligned)
        assert not found(Facts(CANVAS, PT, texts=(first, second)))
        larger = replace(second, em=44)
        assert found(Facts(CANVAS, PT, texts=(first, larger))).rules == (
            "TEXT_TOO_CLOSE",
        )

    value = text("19.4 TWh", INSIDE)
    name = text("Solar", Box(306, 100, 400, 140))
    assert found(Facts(CANVAS, PT, texts=(value, name))).rules == (
        "TEXT_CROWD",
    )


def test_POLAR_TICK_ON_PLOT():
    """A real intrusion counts, while a graze or an outside corner clears."""
    disc = Box(100, 100, 300, 300)
    for box, expected in (
        (Box(280, 180, 330, 220), ("POLAR_TICK_ON_PLOT",)),
        (Box(289, 180, 330, 220), ()),
        (Box(280, 280, 330, 320), ()),
    ):
        label = text("Camera quality", box, TickLabel())
        theta = PolarTheta(Panel(object(), 0), disc, (label,))
        assert found(Facts(CANVAS, PT, polar_theta=(theta,))).rules == expected


def test_MIXED_MINUS():
    """A Unicode tick on any panel is evidence for the mixed-sign finding."""
    label = text("-12.4%", INSIDE)
    facts = Facts(CANVAS, PT, minus_labels=(label,))
    assert not found(facts)
    tick = text("\u221210", INSIDE, TickLabel(), panel=1)
    (finding,) = found(replace(facts, minus_tick=tick))
    assert finding.rule == "MIXED_MINUS"
    assert finding.panels == (0,) and finding.artists == (label.handle,)


def test_TEXT_MISALIGNMENT_on_forest_values():
    import matplotlib.pyplot as plt

    import dartwork_mpl as dm

    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
        ax.scatter([2, 3, 4], [0, 1, 2])
        ax.set(xlabel="Effect", yticks=[])
        texts = [
            ax.text(
                1.03,
                i,
                text,
                transform=ax.get_yaxis_transform(),
                fontfamily="Inter",
            )
            for i, text in enumerate(
                (" 1.1 [2.4, 16.4]", "88.8 [-3.6, 5.2]", "-111.1 [-5.8, 1.6]")
            )
        ]
        dm.simple_layout(fig)
        assert "TEXT_MISALIGNMENT" in dm.check(fig).rules
        dm.align_texts(texts, "decimal")
        dm.simple_layout(fig)
        assert "TEXT_MISALIGNMENT" not in dm.check(fig).rules
        plt.close(fig)


def test_bar_ends_are_not_a_column():
    import matplotlib.pyplot as plt

    import dartwork_mpl as dm

    with dm.style.context("report"):
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
        bars = ax.barh(
            ["North", "South", "East", "West"], [38.6, 82.7, 61.2, 25.3]
        )
        ax.bar_label(bars, fmt="%.1f", padding=4)
        ax.set(xlabel="Revenue (USD m)", xlim=(0, 100))
        dm.simple_layout(fig)
        assert "TEXT_MISALIGNMENT" not in dm.check(fig).rules
        plt.close(fig)


def test_RADIAL_TICK_COVERED():
    """Light veils clear the check, while a substantially painted box fires."""
    label = text("20", INSIDE, TickLabel())
    for opacity, expected in ((0.2, ()), (0.45, ("RADIAL_TICK_COVERED",))):
        facts = Facts(
            CANVAS, PT, occluded_ticks=(TickOcclusion(label, opacity),)
        )
        assert found(facts).rules == expected


def test_TEXT_AT_EDGE():
    """At ordinary layout margins the text clears, and clipping reports once."""
    for left, expected in (
        (0, ("TEXT_AT_EDGE",)),
        (1, ("TEXT_AT_EDGE",)),
        (12, ()),
        (-10, ("OVERFLOW",)),
    ):
        label = text("Germany", Box(left, 100, 110, 140))
        assert (
            found(Facts(CANVAS, PT, texts=(label,), edge_texts=(label,))).rules
            == expected
        )


def test_UNDERUSED_CANVAS():
    """A strip within a big canvas flags, while a tile or balanced margins clear."""
    big = Box(0, 0, 1500, 1200)
    tile = Box(0, 0, 800, 600)
    for canvas, body, expected in (
        (big, Box(0, 300, 1360, 900), ("UNDERUSED_CANVAS",)),
        (big, Box(150, 150, 1350, 1050), ()),
        (big, Box(255, 210, 1245, 990), ()),
        (tile, Box(20, 180, 780, 420), ()),
    ):
        facts = Facts(
            canvas, PT, canvas_use=CanvasUse(Panel(object(), 0), body)
        )
        assert found(facts).rules == expected
