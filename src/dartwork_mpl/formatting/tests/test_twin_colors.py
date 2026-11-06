"""Series colours on ``twinx`` / ``twiny`` pairs (spec 2026-11-06, decision ④).

On a twin pair whose sides each draw one colour, ``dm.simple_layout`` paints
each side's spine and tick marks in that colour as it shows (alpha composited,
at least 3:1 against the background) and its tick labels and axis label in the
same hue darkened to 4.5:1. Single axes, multi-colour sides, sides sharing one
colour and every colour the user set stay as they are;
``dm.config.twin_colors = "neutral"`` turns it off.

The observed values are the colours of the artists matplotlib draws after a
real canvas draw: the spine of every axes on that side (a twin's own copy of
the left spine sits over its partner's), the tick marks and tick labels of the
side's ticks, and the axis label. Contrast is checked with the WCAG formula
written out here, independent of the library's helpers.
"""

from __future__ import annotations

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting import apply_twin_colors

X = np.arange(12)
REVENUE = np.array(
    [21.4, 22.1, 23.1, 24.2, 25.0, 26.3, 27.5, 28.8, 29.3, 30.9, 32.4, 33.0]
)
GROWTH = np.array(
    [37.1, 33.4, 29.1, 22.5, 17.2, 12.9, 12.3, 13.2, 17.0, 19.1, 19.6, 18.9]
)

BLACK = "#000000"
# dc.blue6 bars: 3.03:1 on white already, so the spine keeps it; text 4.5:1.
BAR_LINE, BAR_TEXT = "#2d99f0", "#0f79cf"
# dc.orange6 line: 2.39:1 on white, so the spine darkens to 3:1; text 4.5:1.
LINE_LINE, LINE_TEXT = "#f06d00", "#c15800"


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _luminance(color: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in mcolors.to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(foreground: str, background: str = "#ffffff") -> float:
    high, low = sorted(
        (_luminance(foreground), _luminance(background)), reverse=True
    )
    return (high + 0.05) / (low + 0.05)


def _hex(color) -> str:
    return mcolors.to_hex(color, keep_alpha=False)


def _side(ax: Axes, side: str) -> dict[str, object]:
    """Drawn colours of one side of ``ax``: spines, tick marks, labels."""
    ax.figure.canvas.draw()
    axis = ax.yaxis if side in ("left", "right") else ax.xaxis
    first = side in ("left", "bottom")
    ticks = axis.get_major_ticks()
    marks = {
        _hex((t.tick1line if first else t.tick2line).get_markeredgecolor())
        for t in ticks
    }
    texts = {_hex((t.label1 if first else t.label2).get_color()) for t in ticks}
    group = [
        other
        for other in ax.figure.axes
        if other.get_position().bounds == ax.get_position().bounds
    ]
    spines = {
        _hex(other.spines[side].get_edgecolor())
        for other in group
        if other.spines[side].get_visible()
    }
    assert len(marks) == 1 and len(texts) == 1 and len(spines) <= 1
    return {
        "spine": spines.pop() if spines else None,  # a hidden spine draws none
        "ticks": marks.pop(),
        "ticklabels": texts.pop(),
        "label": _hex(axis.label.get_color()),
    }


def _neutral() -> dict[str, object]:
    return dict.fromkeys(("spine", "ticks", "ticklabels", "label"), BLACK)


def _bar_line_twin(bar_color="dc.blue6", line_color="dc.orange6", **bar_kw):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.bar(X, REVENUE, color=bar_color, label="Revenue", **bar_kw)
    ax.set_ylabel("Revenue (USD B)")
    ax2 = ax.twinx()
    ax2.plot(X, GROWTH, color=line_color, marker="o", label="YoY growth")
    ax2.set_ylabel("YoY growth (%)")
    return fig, ax, ax2


def test_bar_and_line_twin_get_series_colours():
    fig, ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)

    left, right = _side(ax, "left"), _side(ax2, "right")
    assert left == {
        "spine": BAR_LINE,
        "ticks": BAR_LINE,
        "ticklabels": BAR_TEXT,
        "label": BAR_TEXT,
    }
    assert right == {
        "spine": LINE_LINE,
        "ticks": LINE_LINE,
        "ticklabels": LINE_TEXT,
        "label": LINE_TEXT,
    }
    for colors in (left, right):
        assert _ratio(colors["spine"]) >= 3.0
        assert _ratio(colors["ticklabels"]) >= 4.5
    # The shared x axis is no one series' scale.
    assert _side(ax, "bottom") == _neutral()


def test_single_axes_untouched():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.bar(X, REVENUE, color="dc.blue6")
    ax.set_ylabel("Revenue (USD B)")
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 0
    assert _side(ax, "left") == _neutral()
    assert _side(ax, "bottom") == _neutral()


def test_multi_hue_side_stays_neutral():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.bar(X - 0.2, REVENUE, width=0.4, color="dc.blue6", label="2024")
    ax.bar(X + 0.2, REVENUE * 0.9, width=0.4, color="dc.amber7", label="2025")
    ax2 = ax.twinx()
    ax2.plot(X, GROWTH, color="dc.green5", label="Growth")
    dm.simple_layout(fig)

    assert _side(ax, "left") == _neutral()
    right = _side(ax2, "right")
    assert right["spine"] != BLACK and right["ticklabels"] != BLACK


def test_same_hue_both_neutral():
    fig, ax, ax2 = _bar_line_twin(bar_color="C0", line_color="C0")
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 0
    assert _side(ax, "left") == _neutral()
    assert _side(ax2, "right") == _neutral()


@pytest.mark.parametrize(
    ("bar_color", "line_color"),
    [
        ("dc.blue6", "dc.blue7"),  # OKLab distance 0.057
        ("dc.blue6", "dc.indigo6"),  # 0.074
        ("dc.blue6", "dc.blue6"),  # one colour, alpha apart
    ],
)
def test_near_hues_both_neutral(bar_color, line_color):
    """Two series closer than 0.10 in OKLab cannot tell the scales apart."""
    fig, ax, ax2 = _bar_line_twin(
        bar_color=bar_color, line_color=line_color, alpha=0.5
    )
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 0
    assert _side(ax, "left") == _neutral()
    assert _side(ax2, "right") == _neutral()


def test_distinct_shades_stay_coloured():
    """dc.blue6 bars and a dc.blue9 line are 0.17 apart in OKLab."""
    fig, ax, ax2 = _bar_line_twin(line_color="dc.blue9")
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 2
    assert _side(ax, "left")["ticklabels"] == BAR_TEXT
    assert _side(ax2, "right")["ticklabels"] == _hex("dc.blue9")


@pytest.mark.parametrize("data_on", ["parent", "twin"])
@pytest.mark.parametrize("partner", ["empty", "reference line only"])
def test_partner_without_data_is_not_a_pair(data_on, partner):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax2 = ax.twinx()
    drawn, other = (ax, ax2) if data_on == "parent" else (ax2, ax)
    drawn.bar(X, REVENUE, color="dc.blue6")
    other.set_ylim(0, 50)  # a second scale for the same bars
    if partner == "reference line only":
        other.axhline(25, color="dc.orange6")
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 0
    assert _side(ax, "left") == _neutral()
    assert _side(ax2, "right") == _neutral()


def test_light_alpha_series_spine_reaches_3_to_1():
    fig, ax, ax2 = _bar_line_twin(bar_color="#c9e8ff", alpha=0.3)
    dm.simple_layout(fig)

    left = _side(ax, "left")
    assert 3.0 <= _ratio(left["spine"]) < 3.2
    assert left["ticks"] == left["spine"]
    assert 4.5 <= _ratio(left["ticklabels"]) < 4.7
    assert left["label"] == left["ticklabels"]
    # Still the bars' blue: the hue moves less than a few degrees.
    bar_hue = mcolors.rgb_to_hsv(mcolors.to_rgb("#c9e8ff"))[0]
    for color in (left["spine"], left["ticklabels"]):
        assert (
            abs(mcolors.rgb_to_hsv(mcolors.to_rgb(color))[0] - bar_hue) < 0.02
        )


def test_alpha_series_spine_is_the_colour_as_drawn():
    """A translucent series that still reaches 3:1 shows as composited."""
    fig, ax, ax2 = _bar_line_twin(bar_color="#1864b0", alpha=0.7)
    dm.simple_layout(fig)

    drawn = tuple(0.7 * c + 0.3 for c in mcolors.to_rgb("#1864b0"))
    assert _ratio(_hex(drawn)) >= 3.0  # so no darkening is due
    left = _side(ax, "left")
    assert left["spine"] == left["ticks"] == _hex(drawn)
    assert _ratio(left["ticklabels"]) >= 4.5


def test_explicit_colours_win():
    fig, ax, ax2 = _bar_line_twin()
    violet, rose = _hex("dc.violet8"), _hex("dc.rose8")
    green, cyan = _hex("dc.green5"), _hex("dc.cyan8")
    ax.tick_params(axis="y", colors=violet)  # left tick marks and labels
    ax.set_ylabel("Revenue (USD B)", color=rose)
    ax2.tick_params(axis="y", labelcolor=green)  # right tick labels only
    ax2.spines["right"].set_color(cyan)

    for _ in range(2):
        dm.simple_layout(fig)

    assert _side(ax, "left") == {
        "spine": BAR_LINE,
        "ticks": violet,
        "ticklabels": violet,
        "label": rose,
    }
    assert _side(ax2, "right") == {
        "spine": cyan,
        "ticks": LINE_LINE,
        "ticklabels": green,
        "label": LINE_TEXT,
    }


def test_explicit_colour_after_layout_survives():
    fig, ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)
    ax2.yaxis.label.set_color("dc.violet8")
    ax2.tick_params(axis="y", colors="dc.violet8")
    dm.simple_layout(fig)

    right = _side(ax2, "right")
    assert right["label"] == right["ticks"] == right["ticklabels"]
    assert right["label"] == _hex("dc.violet8")
    assert right["spine"] == LINE_LINE


def test_default_colour_set_after_layout_survives():
    """Black set after a layout is the user's, though black is the default."""
    fig, _ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)
    ax2.yaxis.label.set_color("black")
    ax2.tick_params(axis="y", colors="black")
    ax2.spines["right"].set_color("black")
    dm.simple_layout(fig)
    dm.simple_layout(fig)

    assert _side(ax2, "right") == _neutral()
    assert apply_twin_colors(fig) == 1  # the bar side only


def test_cleared_axes_colours_again():
    """``Axes.clear()`` resets colours itself; that is not a user's choice."""
    fig, ax, _ax2 = _bar_line_twin()
    dm.simple_layout(fig)
    ax.cla()  # resets the axis label and offset text, keeps the rest
    ax.bar(X, REVENUE, color="dc.green6")
    ax.set_ylabel("Revenue (USD B)")
    dm.simple_layout(fig)
    dm.simple_layout(fig)

    left = _side(ax, "left")
    assert left["spine"] == left["ticks"]
    assert left["ticklabels"] == left["label"]
    assert _hex(ax.yaxis.get_offset_text().get_color()) == left["label"]
    green = mcolors.rgb_to_hsv(mcolors.to_rgb("dc.green6"))[0]
    for color in (left["spine"], left["label"]):
        assert abs(mcolors.rgb_to_hsv(mcolors.to_rgb(color))[0] - green) < 0.03


def test_neutral_option():
    fig, ax, ax2 = _bar_line_twin()
    with dm.config.override(twin_colors="neutral"):
        dm.simple_layout(fig)
        assert apply_twin_colors(fig) == 0
    assert _side(ax, "left") == _neutral()
    assert _side(ax2, "right") == _neutral()


def test_neutral_after_series_restores_defaults():
    fig, ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)
    dm.config.twin_colors = "neutral"
    dm.simple_layout(fig)

    assert _side(ax, "left") == _neutral()
    assert _side(ax2, "right") == _neutral()


def test_unknown_option_is_named():
    fig, _ax, _ax2 = _bar_line_twin()
    with (
        dm.config.override(twin_colors="loud"),
        pytest.raises(ValueError, match="config.twin_colors"),
    ):
        dm.simple_layout(fig)


def test_repeat_layout_idempotent():
    fig, ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)
    first = (_side(ax, "left"), _side(ax2, "right"))
    dm.simple_layout(fig)
    dm.simple_layout(fig)

    assert (_side(ax, "left"), _side(ax2, "right")) == first
    assert apply_twin_colors(fig) == 2


def test_side_that_stops_qualifying_reverts():
    fig, ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)
    ax2.plot(X, GROWTH / 2, color="dc.green5", label="QoQ growth")
    dm.simple_layout(fig)

    assert _side(ax2, "right") == _neutral()
    assert _side(ax, "left")["spine"] == BAR_LINE


def test_reference_lines_do_not_count():
    fig, ax, ax2 = _bar_line_twin()
    ax.axhline(25, color="black", linewidth=0.5)
    ax.axvspan(2, 4, color="dc.gray2")
    dm.simple_layout(fig)

    assert _side(ax, "left")["spine"] == BAR_LINE


def test_twiny_pair_colours_x_sides():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.barh(X, REVENUE, color="dc.blue6")
    ax.set_xlabel("Revenue (USD B)")
    ax2 = ax.twiny()
    ax2.plot(GROWTH, X, color="dc.orange6", marker="o")
    ax2.set_xlabel("YoY growth (%)")
    dm.simple_layout(fig)

    assert _side(ax, "bottom")["ticklabels"] == BAR_TEXT
    assert _side(ax2, "top")["ticklabels"] == LINE_TEXT
    assert _side(ax, "left") == _neutral()


def test_twinx_and_twiny_on_one_parent():
    """A scale shared by two series stays neutral; each own scale colours."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(X, REVENUE, color="dc.blue6")
    tx = ax.twinx()
    tx.plot(X, GROWTH, color="dc.orange6")
    ty = ax.twiny()
    ty.plot(X * 2, REVENUE, color="dc.green6")
    dm.simple_layout(fig)

    # Blue and green read on the left scale, blue and orange on the bottom.
    assert _side(ax, "left") == _neutral()
    assert _side(ax, "bottom") == _neutral()
    assert _side(tx, "right")["ticklabels"] == LINE_TEXT
    green_text = _side(ty, "top")["ticklabels"]
    assert green_text != BLACK and _ratio(green_text) >= 4.5
    assert apply_twin_colors(fig) == 2


def test_twin_of_twin():
    """``t.twiny()`` shares the twin's y: its line reads on the right too."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(X, REVENUE, color="dc.blue6")
    t = ax.twinx()
    t.plot(X, GROWTH, color="dc.orange6")
    t3 = t.twiny()
    t3.plot(X * 2, GROWTH / 2, color="dc.green6")
    dm.simple_layout(fig)

    assert _side(t, "right") == _neutral()
    assert _side(ax, "left")["ticklabels"] == BAR_TEXT
    assert _side(t3, "top")["ticklabels"] not in (BLACK, BAR_TEXT)


def test_partner_series_in_the_same_hue_on_a_multi_hue_side():
    """Green bars on the left make a green right scale ambiguous."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.bar(X - 0.2, REVENUE, width=0.4, color="dc.blue6")
    ax.bar(X + 0.2, REVENUE * 0.9, width=0.4, color="dc.green5")
    ax2 = ax.twinx()
    ax2.plot(X, GROWTH, color="dc.green5")
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 0
    assert _side(ax2, "right") == _neutral()


def test_two_twin_groups_and_a_single_axes():
    fig, axs = plt.subplots(1, 3, figsize=dm.figsize("17cm", "wide"))
    pairs = []
    for ax, (bars, line) in zip(
        axs[:2],
        [("dc.blue6", "dc.orange6"), ("dc.green6", "dc.violet6")],
        strict=True,
    ):
        ax.bar(X, REVENUE, color=bars)
        twin = ax.twinx()
        twin.plot(X, GROWTH, color=line)
        pairs.append((ax, twin, bars, line))
    axs[2].plot(X, REVENUE, color="dc.red6")
    dm.simple_layout(fig)

    assert apply_twin_colors(fig) == 4
    for ax, twin, bars, line in pairs:
        left, right = _side(ax, "left"), _side(twin, "right")
        for colors, series in ((left, bars), (right, line)):
            hue = mcolors.rgb_to_hsv(mcolors.to_rgb(series))[0]
            shown = mcolors.rgb_to_hsv(mcolors.to_rgb(colors["ticklabels"]))
            assert abs(shown[0] - hue) < 0.03
    assert _side(axs[2], "left") == _neutral()


def test_dark_background_lightens_text():
    dm.style.use("dark")
    fig, ax, ax2 = _bar_line_twin()
    dm.simple_layout(fig)

    background = _hex(ax.get_facecolor())
    for colors in (_side(ax, "left"), _side(ax2, "right")):
        assert _ratio(colors["spine"], background) >= 3.0
        assert _ratio(colors["ticklabels"], background) >= 4.5
        assert colors["ticklabels"] == colors["label"]
