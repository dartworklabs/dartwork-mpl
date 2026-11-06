"""dm.label_bars: value labels on bars that read like their axis (B3).

Downstream code hand-wrote these labels in 418 files: ten font sizes,
``"bold"`` against the ``dm.fw(1)`` rule, formats that repeat the axis unit.
The helper settles the look, the unit, the decimals and the side. The
expected texts are the approved captures' (review page
``2026-11-06-b3-labels``; ``b3/img/report.json`` entries ``q-A``, ``g-A``,
``g-A-series``, ``h-A``, and for stacks ``s-A``, ``s-A-tot``, ``s-A-seg``),
drawn from the same data as ``b3/scripts/charts.py``. The observed values
are read after a real canvas draw.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import warnings

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest
from matplotlib.figure import Figure
from matplotlib.text import Text

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._colors.contrast import contrast_ratio

MINUS = "\N{MINUS SIGN}"
OFFSET_PT = 3.0

# ---------------------------------------------------------------- the data
QUARTERS = [f"{y}.Q{q}" for y in (23, 24, 25) for q in (1, 2, 3, 4)]
Q_REV = (
    np.array(
        [21.4, 22.1, 23.1, 24.2, 25.0, 26.3, 27.5, 28.8, 29.3, 30.9, 32.4, 33.0]
    )
    * 1e9
)
SEGMENTS = ["Cloud", "Devices", "Ads", "Gaming", "Other"]
G_MARGIN = np.array(
    [
        [24.6, 27.9, 30.2],
        [-3.5, 1.2, 4.8],
        [18.0, 21.5, 23.0],
        [-8.4, -2.1, 3.6],
        [6.0, 5.5, -1.5],
    ]
)
H_NAMES = [
    "Northwind",
    "Contoso",
    "Fabrikam",
    "Tailspin",
    "Wingtip",
    "Litware",
    "Adatum",
    "Proseware",
    "Woodgrove",
    "Lucerne",
]
H_SHARE = np.array([31.0, 22.4, 11.6, 4.2, 3.9, 3.1, 2.4, 1.9, 1.6, 1.2])
S_YEARS = ["FY20", "FY21", "FY22", "FY23", "FY24", "FY25"]
S_PARTS = [
    ("Products", np.array([14.2, 15.1, 15.8, 16.4, 17.9, 19.3]) * 1e9),
    ("Services", np.array([6.1, 7.4, 8.9, 10.6, 12.8, 15.2]) * 1e9),
    ("Licensing", np.array([2.0, 2.2, 2.1, 2.5, 2.6, 3.0]) * 1e9),
]
S_COLORS = ["dc.blue7", "dc.blue4", "dc.blue2"]
# The dense chart (d): 24 months of revenue (charts.py's seeded series).
D_REV = (
    np.array(
        [
            *(820, 860, 860, 858, 904, 906, 979, 1063, 1007, 1027, 1103, 1123),
            *(1138, 1117, 1184, 1243, 1177, 1243, 1204, 1258, 1259, 1357),
            *(1337, 1432),
        ]
    )
    * 1e6
)
D_TICKS = [f"{24 + i // 12}.{i % 12 + 1:02d}" for i in range(24)]
T_YOY = np.array(
    [37.0, 33.4, 29.1, 22.5, 17.2, 12.9, 12.3, 13.2, 17.0, 19.1, 19.6, 18.9]
)
# Korean quarterly revenue in 원 (the B2 axis-unit capture, first value 5,234억).
Q_WON = (
    np.array(
        [5234, 5480, 5830, 6420, 6150, 6690, 7120, 7880, 7540, 8210, 8930, 9650]
    )
    * 1e8
)

# ------------------------------------------------------- approved captures
Q_A = [
    "21.4",
    "22.1",
    "23.1",
    "24.2",
    "25.0",
    "26.3",
    "27.5",
    "28.8",
    "29.3",
    "30.9",
    "32.4",
    "33.0",
]
G_A = [
    "24.6",
    f"{MINUS}3.5",
    "18.0",
    f"{MINUS}8.4",
    "6.0",
    "27.9",
    "1.2",
    "21.5",
    f"{MINUS}2.1",
    "5.5",
    "30.2",
    "4.8",
    "23.0",
    "3.6",
    f"{MINUS}1.5",
]
G_A_SERIES = ["#0f79cf"] * 5 + ["#d3441c"] * 5 + ["#248837"] * 5
H_A = ["31.0", "22.4", "11.6", "4.2", "3.9", "3.1", "2.4", "1.9", "1.6", "1.2"]
# The stacked chart (s): segments container by container, then the totals.
S_A_SEG = [
    "14.2",
    "15.1",
    "15.8",
    "16.4",
    "17.9",
    "19.3",
    "6.1",
    "7.4",
    "8.9",
    "10.6",
    "12.8",
    "15.2",
    "2.0",
    "2.2",
    "2.1",
    "2.5",
    "2.6",
    "3.0",
]
S_A_TOT = ["22.3", "24.7", "26.8", "29.5", "33.3", "37.5"]
# The dense chart (d-A): every label kept, turned vertical.
D_A = [
    "820",
    "860",
    "860",
    "858",
    "904",
    "906",
    "979",
    "1,063",
    "1,007",
    "1,027",
    "1,103",
    "1,123",
    "1,138",
    "1,117",
    "1,184",
    "1,243",
    "1,177",
    "1,243",
    "1,204",
    "1,258",
    "1,259",
    "1,357",
    "1,337",
    "1,432",
]
# d-A-skip: every other label, counted back from the last one.
D_A_SKIP = D_A[1::2]
# The approved measurements (report.json): top limit / largest bar.
D_A_HEADROOM = 1.103
H_A_HEADROOM = 1.069
AUTOSCALE_HEADROOM = 1.1  # the report preset's axes.ymargin


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


# ---------------------------------------------------------------- charts
def _fig(aspect="standard"):
    return plt.subplots(figsize=dm.figsize("12cm", aspect))


def _quarterly(values=Q_REV, *, unit=True):
    fig, ax = _fig()
    x = np.arange(len(values))
    bars = ax.bar(x, values, width=0.62, color="dc.blue6", label="Revenue")
    ax.set_xticks(x, QUARTERS[: len(values)])
    if unit:
        dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
    return fig, ax, bars


def _grouped():
    fig, ax = _fig()
    x = np.arange(len(SEGMENTS))
    w = 0.26
    bars = [
        ax.bar(x + (j - 1) * (w + 0.01), G_MARGIN[:, j], width=w, label=year)
        for j, year in enumerate(["FY23", "FY24", "FY25"])
    ]
    ax.axhline(0, color="black", linewidth=0.3, zorder=1)
    ax.set_xticks(x, SEGMENTS)
    ax.set_ylabel("Operating margin (%)")
    return fig, ax, bars


def _horizontal(values=H_SHARE, names=H_NAMES):
    fig, ax = _fig()
    y = np.arange(len(values))
    bars = ax.barh(y, values, height=0.62, color="dc.blue6")
    ax.set_yticks(y, names[: len(values)])
    ax.invert_yaxis()
    ax.set_xlabel("Market share, 2025 (%)")
    return fig, ax, bars


def _plain(values, **bar_kw):
    fig, ax = _fig()
    bars = ax.bar(np.arange(len(values)), values, **bar_kw)
    return fig, ax, bars


def _stack(ax, parts, positions, *, horizontal=False, **bar_kw):
    """Stack ``parts`` (``(values, bar keywords)``) as callers build stacks.

    Each container starts at the running end of the ones before it: a
    positive value on the positive end, a negative one on the negative end;
    a NaN value adds nothing.
    """
    high = np.zeros(len(positions))
    low = np.zeros(len(positions))
    draw, base = (ax.barh, "left") if horizontal else (ax.bar, "bottom")
    containers = []
    for values, kw in parts:
        values = np.asarray(values, dtype=float)
        start = np.where(values < 0, low, high)
        containers.append(
            draw(positions, values, **{base: start}, **bar_kw, **kw)
        )
        high = high + np.where(values > 0, values, 0.0)
        low = low + np.where(values < 0, values, 0.0)
    return containers


def _stacked():
    """The approved stacked chart (s): three revenue parts over six years."""
    fig, ax = _fig()
    x = np.arange(len(S_YEARS))
    parts = [
        (values, {"color": color, "label": name})
        for (name, values), color in zip(S_PARTS, S_COLORS, strict=True)
    ]
    containers = _stack(ax, parts, x, width=0.6)
    ax.set_xticks(x, S_YEARS)
    dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
    return fig, ax, containers


# ---------------------------------------------------------------- reading
def _texts(texts):
    return [t.get_text() for t in texts]


def _drawn(fig):
    fig.canvas.draw()
    return fig.canvas.get_renderer()


def _offset_px(fig):
    return OFFSET_PT * fig.dpi / 72.0


def _assert_outside(fig, texts, patches, orientation="vertical"):
    """Each label sits 3 pt beyond its bar's end, centred on the bar."""
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    for text, patch in zip(texts, patches, strict=True):
        tb = text.get_window_extent(renderer)
        pb = patch.get_window_extent(renderer)
        if orientation == "vertical":
            assert (tb.x0 + tb.x1) / 2 == pytest.approx(
                (pb.x0 + pb.x1) / 2, abs=0.6
            )
            if patch.get_height() >= 0:
                assert tb.y0 == pytest.approx(pb.y1 + gap, abs=0.6)
            else:
                assert tb.y1 == pytest.approx(pb.y0 - gap, abs=0.6)
        else:
            assert (tb.y0 + tb.y1) / 2 == pytest.approx(
                (pb.y0 + pb.y1) / 2, abs=0.6
            )
            if patch.get_width() >= 0:
                assert tb.x0 == pytest.approx(pb.x1 + gap, abs=0.6)
            else:
                assert tb.x1 == pytest.approx(pb.x0 - gap, abs=0.6)


def _assert_centred(fig, texts, patches):
    """Each label's middle is its bar's middle."""
    renderer = _drawn(fig)
    for text, patch in zip(texts, patches, strict=True):
        tb = text.get_window_extent(renderer)
        pb = patch.get_window_extent(renderer)
        assert (tb.x0 + tb.x1) / 2 == pytest.approx((pb.x0 + pb.x1) / 2, abs=1)
        assert (tb.y0 + tb.y1) / 2 == pytest.approx((pb.y0 + pb.y1) / 2, abs=1)


def _kinds(texts):
    return [t.kind for t in texts]


def _hex(text):
    return mcolors.to_hex(text.get_color())


def _contrast_on_white(text):
    return contrast_ratio(mcolors.to_rgb(text.get_color()), (1.0, 1.0, 1.0))


# ---------------------------------------------------------------- tests
def test_quarterly_matches_approved():
    fig, ax, bars = _quarterly()
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert _texts(texts) == Q_A
    assert ax.get_ylabel() == "Revenue (USD B)"  # the unit stays in the label
    for text in texts:
        assert text.get_fontsize() == pytest.approx(dm.fs(-1))  # 7 pt
        assert text.get_fontweight() == dm.fw(1)  # 300
        assert _hex(text) == "#000000"
        assert text.get_rotation() == 0
    _assert_outside(fig, texts, bars.patches)


def test_negative_bars_label_below_with_minus():
    fig, ax, groups = _grouped()
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == G_A
    patches = [p for bars in groups for p in bars.patches]
    for text, patch in zip(texts, patches, strict=True):
        below = patch.get_height() < 0
        assert text.get_text().startswith(MINUS) == below
        assert text.get_verticalalignment() == ("top" if below else "bottom")
    _assert_outside(fig, texts, patches)


def test_barh_left_for_negatives():
    fig, ax, bars = _horizontal()
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == H_A
    assert {t.get_horizontalalignment() for t in texts} == {"left"}
    _assert_outside(fig, texts, bars.patches, "horizontal")

    fig, ax, bars = _horizontal(np.array([12.5, -4.0, 7.5]))
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["12.5", f"{MINUS}4.0", "7.5"]
    assert [t.get_horizontalalignment() for t in texts] == [
        "left",
        "right",
        "left",
    ]
    assert {t.get_verticalalignment() for t in texts} == {"center"}
    _assert_outside(fig, texts, bars.patches, "horizontal")


def test_axis_unit_max_and_whole():
    dm.style.use("report-kr")
    fig, ax, _ = _plain(Q_WON, width=0.65)
    dm.axis_unit(ax, "y", label="매출 ({unit}원)")
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert ax.get_ylabel() == "매출 (조원)"
    assert _texts(texts)[:3] == ["0.523", "0.548", "0.583"]
    assert _texts(texts)[-1] == "0.965"

    fig, ax, _ = _plain(Q_WON, width=0.65)
    dm.axis_unit(ax, "y", label="매출 ({unit}원)", scale="whole")
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert ax.get_ylabel() == "매출 (억원)"
    assert _texts(texts)[:3] == ["5,234", "5,480", "5,830"]
    assert _texts(texts)[-1] == "9,650"


def test_default_si_suffix_follows_ticks():
    # Labelled before simple_layout installs the library's tick numbers.
    fig, ax, _ = _plain(np.array([12.0, 25.0, 33.0]) * 1e9)
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    ticks = [t.get_text() for t in ax.get_yticklabels() if t.get_text()]
    assert "35G" in ticks
    assert _texts(texts) == ["12G", "25G", "33G"]

    # A later limit change moves the tick unit; the labels follow at the draw.
    ax.set_ylim(0, 5e12)
    fig.canvas.draw()
    assert _texts(texts) == ["0.012T", "0.025T", "0.033T"]

    # format_axis_si: the same unit decision and suffix as its ticks.
    fig, ax, _ = _plain([1200.0, 2500.0, 800.0])
    dm.format_axis_si(ax)
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["1.2k", "2.5k", "0.8k"]

    # The returned texts already hold the axis-wide decision (980 alone
    # would print in no unit), before any draw.
    fig, ax, _ = _plain([980.0, 1200.0])
    dm.format_axis_si(ax)
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["0.98k", "1.20k"]
    fig.canvas.draw()
    assert _texts(texts) == ["0.98k", "1.20k"]


def test_percent_formatter_follows_ticks():
    fig, ax, _ = _plain([0.31, 0.22, 0.12])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["31%", "22%", "12%"]

    fig, ax, _ = _plain([31.0, 22.4, 11.6])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())  # xmax=100
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["31.0%", "22.4%", "11.6%"]


def test_fmt_string_and_callable():
    revenue = np.array([21.4, 38.5, 30.9]) * 1e9
    fig, ax, _ = _quarterly(revenue)
    texts = dm.label_bars(ax, fmt="${}B")
    dm.simple_layout(fig)
    assert _texts(texts) == ["$21.4B", "$38.5B", "$30.9B"]

    # The template wraps the signed number (a callable gives -$3.5B).
    fig, ax, _ = _quarterly(np.array([-3.5, 2.0]) * 1e9)
    texts = dm.label_bars(ax, fmt="${}B")
    assert _texts(texts) == [f"${MINUS}3.5B", "$2.0B"]
    texts = dm.label_bars(
        ax, fmt=lambda v: f"{MINUS if v < 0 else ''}${abs(v)}B"
    )
    assert _texts(texts)[0] == f"{MINUS}$3.5B"

    seen: list[float] = []

    def billions(value):
        seen.append(value)
        return f"{value:.2f} bn"

    fig, ax, _ = _quarterly(revenue)
    texts = dm.label_bars(ax, fmt=billions)
    dm.simple_layout(fig)
    assert _texts(texts) == ["21.40 bn", "38.50 bn", "30.90 bn"]
    assert seen[-3:] == pytest.approx([21.4, 38.5, 30.9])  # in the axis unit

    # A format spec in the template formats the scaled value itself.
    fig, ax, _ = _quarterly(revenue)
    texts = dm.label_bars(ax, fmt="{:.2f}")
    dm.simple_layout(fig)
    assert _texts(texts) == ["21.40", "38.50", "30.90"]


def test_decimals_rule():
    def labels(values, **kw):
        fig, ax, _ = _plain(values)
        texts = dm.label_bars(ax, **kw)
        dm.simple_layout(fig)
        return _texts(texts)

    # One count per call: 18.0 keeps the decimal its neighbours need.
    assert labels([21.4, 18.0, 21.5]) == ["21.4", "18.0", "21.5"]
    # Whole numbers print no meaningless .0.
    assert labels([120.0, 135.0, 150.0]) == ["120", "135", "150"]
    # Three significant digits on the largest |value|.
    assert labels([1234.5678, 980.25]) == ["1,235", "980"]
    assert labels([0.5234, 0.1]) == ["0.523", "0.100"]
    # decimals= fixes the count.
    assert labels([21.4, 18.0], decimals=2) == ["21.40", "18.00"]
    assert labels([21.4, 18.0], decimals=0) == ["21", "18"]

    # Each call settles its own count; one call over both settles one.
    fig, ax = _fig()
    small = ax.bar([0, 1], [1.5, 2.5])
    large = ax.bar([2, 3], [10.0, 20.0])
    assert _texts(dm.label_bars(ax, small)) == ["1.5", "2.5"]
    assert _texts(dm.label_bars(ax, [large])) == ["10", "20"]
    fig, ax = _fig()
    ax.bar([0, 1], [1.5, 2.5])
    ax.bar([2, 3], [10.0, 20.0])
    assert _texts(dm.label_bars(ax)) == ["1.5", "2.5", "10.0", "20.0"]


def test_color_series_option():
    fig, ax, _ = _grouped()
    texts = dm.label_bars(ax, color="series")
    dm.simple_layout(fig)
    assert [_hex(t) for t in texts] == G_A_SERIES
    for text in texts:
        assert _contrast_on_white(text) >= 4.5

    fig, ax, _ = _grouped()
    texts = dm.label_bars(ax, color="dc.red7")
    assert {_hex(t) for t in texts} == {mcolors.to_hex("dc.red7")}
    texts = dm.label_bars(ax, color=np.array([0.5, 0.1, 0.1]))
    assert {_hex(t) for t in texts} == {mcolors.to_hex((0.5, 0.1, 0.1))}

    # A light, translucent series is darkened to a readable ink.
    fig, ax, _ = _plain([3.0, 5.0], color="#c9e8ff", alpha=0.3)
    texts = dm.label_bars(ax, color="series")
    for text in texts:
        assert _contrast_on_white(text) >= 4.5

    # The colour as drawn: a dark bar at alpha 0.3 shows light, and the ink
    # is that light colour darkened, not the opaque colour.
    fig, ax, _ = _plain([3.0, 5.0], color="dc.blue9", alpha=0.3)
    texts = dm.label_bars(ax, color="series")
    r, g, b = mcolors.to_rgb("dc.blue9")
    shown = mcolors.to_hex([0.3 * c + 0.7 for c in (r, g, b)])
    expected = dm.ensure_contrast(shown, "#ffffff")
    assert {_hex(t) for t in texts} == {mcolors.to_hex(expected)}
    assert expected != mcolors.to_hex("dc.blue9")


def test_zero_and_nan_bars():
    fig, ax, bars = _plain([0.0, np.nan, 3.5])
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["0", "3.5"]  # no label for the NaN bar
    assert texts[0].get_verticalalignment() == "bottom"
    _assert_outside(fig, texts, [bars.patches[0], bars.patches[2]])

    fig, ax, _ = _plain([0.0, 0.0])
    assert _texts(dm.label_bars(ax)) == ["0", "0"]


def test_categorical_and_date_positions():
    fig, ax = _fig()
    bars = ax.bar(["Seoul", "Busan", "Incheon"], [3.0, 5.0, 2.0])
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["3", "5", "2"]
    _assert_outside(fig, texts, bars.patches)

    fig, ax = _fig()
    days = np.array(["2024-01-01", "2024-02-01", "2024-03-01"], "datetime64[D]")
    bars = ax.bar(days, [4.0, 6.5, 5.25], width=20)
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["4.00", "6.50", "5.25"]
    _assert_outside(fig, texts, bars.patches)


def test_without_layout():
    fig, ax, bars = _quarterly()
    texts = dm.label_bars(ax)
    fig.savefig(io.BytesIO(), format="png")
    assert _texts(texts) == Q_A
    assert ax.get_ylabel() == "Revenue (USD B)"
    _assert_outside(fig, texts, bars.patches)

    # Labelled before the axis unit exists: the save prints them in it.
    fig, ax, bars = _quarterly(unit=False)
    texts = dm.label_bars(ax)
    dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
    fig.savefig(io.BytesIO(), format="png")
    assert _texts(texts) == Q_A


def test_bars_on_the_twin():
    # Bars on the parent, a line on the twin: labels go on the twin (drawn
    # last, so the line never covers them), placed with the bars' data.
    fig, ax, bars = _quarterly()
    ax2 = ax.twinx()
    ax2.plot(np.arange(12), np.linspace(37, 19, 12), color="dc.orange6")
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert all(t.axes is ax2 for t in texts)
    assert all(t in ax2.texts for t in texts)
    assert not any(t in ax.texts for t in texts)
    assert _texts(texts) == Q_A  # the bar axis's unit, not the twin's
    _assert_outside(fig, texts, bars.patches)

    # Bars on the twin, a line on the parent.
    fig, ax = _fig()
    ax.plot(np.arange(3), [5.0, 7.0, 6.0])
    ax2 = ax.twinx()
    bars = ax2.bar(np.arange(3), [120.0, 135.0, 150.0], alpha=0.5)
    texts = dm.label_bars(ax2)
    dm.simple_layout(fig)
    assert all(t.axes is ax2 for t in texts)
    assert _texts(texts) == ["120", "135", "150"]
    _assert_outside(fig, texts, bars.patches)


def test_returns_texts_and_later_edits_survive():
    fig, ax, bars = _quarterly()
    texts = dm.label_bars(ax)
    assert len(texts) == len(bars.patches)
    assert all(isinstance(t, Text) for t in texts)
    assert _texts(texts) == Q_A  # right before any draw

    texts[0].set_text("Low")
    texts[1].set_color("dc.red7")
    texts[2].set_fontsize(11)
    texts[3].set_fontweight("bold")
    texts[4].set_verticalalignment("center")
    for _ in range(2):
        dm.simple_layout(fig)
    ax.set_ylim(0, 2e12)  # the unit moves to T
    fig.canvas.draw()
    assert texts[0].get_text() == "Low"
    assert _hex(texts[1]) == mcolors.to_hex("dc.red7")
    assert texts[2].get_fontsize() == 11
    assert texts[3].get_fontweight() == "bold"
    assert texts[4].get_verticalalignment() == "center"
    assert texts[5].get_text() == "0.0263"  # the others follow the ticks

    # The call is recorded on the axes for the layout's later passes.
    (family,) = ax._dm_bar_label_families
    assert family.texts == texts
    assert family.containers == [bars]
    assert family.options.crowded == "rotate"
    assert family.options.where == "auto"
    assert family.options.total == "auto"


def test_where_inside_and_center():
    fig, ax, bars = _plain([4.0, -3.0], width=0.6)
    inside = dm.label_bars(ax, where="inside")
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    for text, patch in zip(inside, bars.patches, strict=True):
        tb = text.get_window_extent(renderer)
        pb = patch.get_window_extent(renderer)
        if patch.get_height() >= 0:
            assert tb.y1 == pytest.approx(pb.y1 - gap, abs=0.6)
        else:
            assert tb.y0 == pytest.approx(pb.y0 + gap, abs=0.6)

    fig, ax, bars = _plain([4.0, -3.0], width=0.6)
    centred = dm.label_bars(ax, where="center")
    renderer = _drawn(fig)
    for text, patch in zip(centred, bars.patches, strict=True):
        tb = text.get_window_extent(renderer)
        pb = patch.get_window_extent(renderer)
        assert (tb.y0 + tb.y1) / 2 == pytest.approx((pb.y0 + pb.y1) / 2, abs=1)
        assert (tb.x0 + tb.x1) / 2 == pytest.approx((pb.x0 + pb.x1) / 2, abs=1)


# ------------------------------------------------- reading the saved file
# A label reads when the whole number can be read in the file a user
# keeps: every glyph pixel stands on a background its ink contrasts with,
# and the text box lies on one background (a bar or the plot background),
# not across a bar edge. Checked on the PNG and on the PDF, rasterised.
READ_RATIO = 3.0  # WCAG 2.x, graphics and large text: the floor here
_PROBE = (1.0, 0.0, 1.0)  # a colour no test bar or background takes


def _luminance(rgb):
    rgb = np.asarray(rgb, dtype=float)
    linear = np.where(
        rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4
    )
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def _ratios(ink, grounds):
    """WCAG contrast of ``ink`` against each background pixel."""
    a, b = _luminance(ink), _luminance(grounds)
    return (np.maximum(a, b) + 0.05) / (np.minimum(a, b) + 0.05)


def _raster(fig, fmt, folder):
    """The figure saved as ``fmt`` and read back as pixels (RGB, 0-1).

    A PDF is rasterised by Ghostscript at the figure's dpi, so its pixels
    line up with the figure's display coordinates as a PNG's do.
    """
    path = folder / f"page.{fmt}"
    with matplotlib.rc_context({"savefig.bbox": "standard"}):
        fig.savefig(path, format=fmt, dpi=fig.dpi)
    if fmt == "pdf":
        gs = shutil.which("gs")
        if gs is None:
            pytest.skip(
                "reading the PDF needs Ghostscript (gs) to rasterise it"
            )
        png = folder / "page_pdf.png"
        subprocess.run(
            [
                gs,
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=png16m",
                "-dTextAlphaBits=4",
                "-dGraphicsAlphaBits=4",
                f"-r{fig.dpi:g}",
                f"-sOutputFile={png}",
                str(path),
            ],
            check=True,
        )
        path = png
    return plt.imread(path)[..., :3].astype(float)


def _unreadable(fig, labels, folder, fmt):
    """The drawn labels whose number does not read in the saved ``fmt``.

    Three saves: as drawn; the labels hidden (what lies behind them); the
    labels in a probe colour (where their glyphs are, whatever their ink).
    A label fails when a glyph pixel's background contrasts with its ink
    less than READ_RATIO, or when its text box (2 px in from its edge, for
    antialiasing) lies across more than one background.
    """
    drawn = [t for t in labels if t.get_visible()]
    inks = [t.get_color() for t in drawn]
    renderer = _drawn(fig)
    boxes = [t.get_window_extent(renderer) for t in drawn]
    for t in drawn:
        t.set_visible(False)
    ground = _raster(fig, fmt, folder)
    for t in drawn:
        t.set_visible(True)
        t.set_color(_PROBE)
    probe = _raster(fig, fmt, folder)
    for t, ink in zip(drawn, inks, strict=True):
        t.set_color(ink)
    height = ground.shape[0]
    bad = []
    for t, ink, box in zip(drawn, inks, boxes, strict=True):
        rows = slice(int(height - box.y1), int(np.ceil(height - box.y0)))
        cols = slice(int(box.x0), int(np.ceil(box.x1)))
        behind, glyphs = ground[rows, cols], probe[rows, cols]
        mask = np.abs(glyphs - behind).max(axis=2) > 0.15
        inner = behind[2:-2, 2:-2].reshape(-1, 3)
        spread = float(np.abs(inner - np.median(inner, axis=0)).max())
        worst = float(_ratios(mcolors.to_rgb(ink), behind[mask]).min())
        if not mask.any() or spread > 0.1 or worst < READ_RATIO:
            bad.append((t.get_text(), round(worst, 2), round(spread, 2)))
    return bad


def _assert_readable(fig, labels, folder):
    for fmt in ("png", "pdf"):
        assert _unreadable(fig, labels, folder, fmt) == [], fmt


def _narrow_dark(width, **label_kw):
    """Dark bars narrower than their numbers (the review's C1 data)."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"), dpi=200)
    bars = ax.bar(
        np.arange(6),
        [300, 4100, 520, 610, 12500, 700],
        width=width,
        color="dc.blue9",
    )
    return fig, ax, bars, dm.label_bars(ax, **label_kw)


def test_inside_label_wider_than_its_bar_sits_beyond_it(tmp_path):
    # where="inside" on dark bars narrower than the numbers: white ink on
    # the bar would leave part of each number on the white background
    # (12,500 read as 2,50). A label its bar does not hold sits beyond the
    # bar's end in the text colour instead, and reads in the PNG and PDF.
    fig, ax, bars, labels = _narrow_dark(0.3, where="inside")
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    for label, patch in zip(labels, bars.patches, strict=True):
        assert label.off_bar and not label.on_bar and label.beyond_end
        assert _hex(label) == "#000000"
        box = label.get_window_extent(renderer)
        assert box.y0 == pytest.approx(
            patch.get_window_extent(renderer).y1 + _offset_px(fig), abs=0.6
        )
    _assert_readable(fig, labels, tmp_path)

    # Wide bars hold the numbers across: the tall ones keep them inside in
    # white; the short ones (too short along) put them beyond their ends.
    fig, ax, bars, labels = _narrow_dark(0.85, where="inside")
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    assert [t.get_text() for t in labels if t.on_bar] == ["4,100", "12,500"]
    for label, patch in zip(labels, bars.patches, strict=True):
        box = label.get_window_extent(renderer)
        bar = patch.get_window_extent(renderer)
        if label.on_bar:
            assert _hex(label) == "#ffffff"
            assert bar.x0 - 0.5 <= box.x0 and box.x1 <= bar.x1 + 0.5
            assert box.y1 == pytest.approx(bar.y1 - _offset_px(fig), abs=0.6)
        else:
            assert _hex(label) == "#000000"
            assert box.y0 == pytest.approx(bar.y1 + _offset_px(fig), abs=0.6)
    _assert_readable(fig, labels, tmp_path)


def test_crowded_inside_keeps_a_label_its_row_cannot_hold_outside(tmp_path):
    # crowded="inside" on barh rows thinner than the text: the labels stay
    # beyond the bar ends in the text colour (they used to move onto the
    # rows in white and run past them); a later taller figure that holds
    # them moves them in.
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"), dpi=200)
    values = np.linspace(4000.0, 1500.0, 12)
    ax.barh(np.arange(12), values, height=0.25, color="dc.blue9")
    ax.invert_yaxis()
    ax.set_xlim(0, 4600)
    labels = dm.label_bars(ax, crowded="inside")
    dm.simple_layout(fig)
    _drawn(fig)
    shown = [t for t in labels if t.get_visible()]
    assert shown
    assert all(t.where == "outside" and not t.on_bar for t in shown)
    assert {_hex(t) for t in shown} == {"#000000"}
    _assert_readable(fig, labels, tmp_path)


def test_error_bars_push_labels_past_caps():
    fig, ax = _fig()
    bars = ax.bar([0, 1], [4.0, -3.0], yerr=[1.0, 0.5], capsize=2)
    texts = dm.label_bars(ax)
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    up = ax.transData.transform((0, 5.0))[1]
    down = ax.transData.transform((1, -3.5))[1]
    assert texts[0].get_window_extent(renderer).y0 == pytest.approx(
        up + gap, abs=0.6
    )
    assert texts[1].get_window_extent(renderer).y1 == pytest.approx(
        down - gap, abs=0.6
    )
    assert bars.errorbar is not None


def test_inverted_value_axis_keeps_labels_outside():
    fig, ax, bars = _horizontal(np.array([12.5, -4.0, 7.5]))
    texts = dm.label_bars(ax)
    ax.invert_xaxis()  # mirrored bars, inverted after labelling
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    for text, patch in zip(texts, bars.patches, strict=True):
        tb = text.get_window_extent(renderer)
        pb = patch.get_window_extent(renderer)
        if patch.get_width() >= 0:  # grows leftwards on screen
            assert tb.x1 == pytest.approx(pb.x0 - gap, abs=0.6)
        else:
            assert tb.x0 == pytest.approx(pb.x1 + gap, abs=0.6)


def test_labels_beyond_the_axes_are_not_clipped():
    # A user limit at the bar top puts the label above the axes; it is still
    # drawn whole, as ax.annotate draws it.
    fig, ax, _ = _plain([4.0, 2.0])
    ax.set_ylim(0, 4)
    (top, _low) = dm.label_bars(ax)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="rgba")
    width, height = (int(v) for v in fig.canvas.get_width_height())
    pixels = np.frombuffer(buffer.getvalue(), np.uint8).reshape(
        height, width, 4
    )
    box = top.get_window_extent(fig.canvas.get_renderer())
    assert box.y0 >= ax.get_window_extent().y1  # wholly above the axes
    rows = slice(int(height - box.y1), int(height - box.y0))
    cols = slice(int(box.x0), int(box.x1) + 1)
    assert (pixels[rows, cols, :3].min(axis=2) < 128).any()


def _tight_shape(fig):
    """(height, width) in pixels of a ``bbox_inches="tight"`` PNG save."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    return plt.imread(buffer).shape[:2]


def test_bars_out_of_view_get_no_labels():
    # The reviewer's probe: 12 bars, a view of the first six.
    def chart(label):
        fig, ax, _ = _plain(np.arange(1.0, 13.0))
        ax.set_xlim(-0.5, 5.5)
        return fig, ax, (dm.label_bars(ax) if label else [])

    fig, ax, texts = chart(True)
    renderer = _drawn(fig)
    shown = [t for t in texts if t.get_visible()]
    assert _texts(shown) == ["1", "2", "3", "4", "5", "6"]
    axes_box = ax.get_window_extent(renderer)
    for text in shown:
        box = text.get_window_extent(renderer)
        assert axes_box.x0 <= box.x0 and box.x1 <= axes_box.x1
    hidden = texts[6]
    assert not np.isfinite(hidden.get_tightbbox(renderer).extents).all()
    assert _tight_shape(fig) == _tight_shape(chart(False)[0])

    # Back in view, the labels come back.
    ax.set_xlim(-0.5, 11.5)
    fig.canvas.draw()
    assert all(t.get_visible() for t in texts)


def test_bar_past_a_user_limit_shows_its_value_inside_the_limit():
    # The reviewer's probe: a bar of 40 under a limit of 5 the user set.
    # Its true value sits just inside the limit, on the bar (decision 9-3
    # B); nothing goes off the axes, so a tight save keeps its size.
    def chart(label):
        fig, ax, _ = _plain([3.0, 40.0, 2.0], color="dc.blue9")
        ax.set_ylim(0, 5)
        return fig, ax, (dm.label_bars(ax) if label else [])

    fig, ax, texts = chart(True)
    renderer = _drawn(fig)
    assert [t.get_visible() for t in texts] == [True, True, True]
    assert _texts(texts) == ["3", "40", "2"]
    clipped = texts[1]
    box = clipped.get_window_extent(renderer)
    top = ax.get_window_extent(renderer).y1
    bar = clipped.bar.get_window_extent(renderer)
    assert box.y1 == pytest.approx(top - _offset_px(fig), abs=0.6)
    assert (box.x0 + box.x1) / 2 == pytest.approx(
        (bar.x0 + bar.x1) / 2, abs=0.6
    )
    assert _hex(clipped) == "#ffffff"  # readable on the dark bar
    assert _hex(texts[0]) == "#000000"  # the others keep the text colour
    width, height = fig.canvas.get_width_height()
    for text in texts:
        box = text.get_window_extent(renderer)
        assert box.y0 >= 0
        assert box.y1 <= height
    assert _tight_shape(fig) == _tight_shape(chart(False)[0])

    # An error bar past the limit pushes a visible label only to the edge.
    fig, ax = _fig()
    ax.bar([0, 1], [4.0, 2.0], yerr=[3.0, 0.5])
    ax.set_ylim(0, 5)
    texts = dm.label_bars(ax)
    renderer = _drawn(fig)
    top = ax.get_window_extent(renderer).y1
    assert texts[0].get_visible()
    assert texts[0].get_window_extent(renderer).y0 == pytest.approx(
        top + _offset_px(fig), abs=0.6
    )


# ------------------------------------------- bars past a limit (9-3 B)
# The approved PoC figures of decision 9-3 (review page
# 2026-11-06-b3-followups, b3poc/3-clipped-bar-label/summary.json, B).
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
MONTHS += ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ORDERS = [48, 52, 61, 58, 64, 72, 135, 79, 83, 88, 96, 120]
MARKETS = ["United States", "China", "Japan", "Germany", "India", "UK"]
MARKET_SIZE = [2410, 760, 540, 410, 330, 290]


def _poc_orders(limits=(0, 100)):
    """Monthly orders (k), the caller's 0-100 limit (PoC figure a)."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"), dpi=300)
    ax.bar(MONTHS, ORDERS, color="dc.teal2")
    ax.set_ylim(*limits)
    ax.set_ylabel("Orders (k)")
    return fig, ax, dm.label_bars(ax)


def _poc_markets(limits=(0, 800)):
    """Market size (USD B), the caller's 0-800 limit (PoC figure b)."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", 0.55), dpi=300)
    ax.barh(MARKETS, MARKET_SIZE, color="dc.blue4")
    ax.invert_yaxis()
    ax.set_xlim(*limits)
    ax.set_xlabel("Market size (USD B)")
    return fig, ax, dm.label_bars(ax)


def _contrast_on_bar(label):
    face = mcolors.to_rgb(label.bar.get_facecolor())
    return contrast_ratio(mcolors.to_rgb(label.get_color()), face)


def _inside_edge(fig, ax, label, edge):
    """The label's distance (px) inside the axes ``edge`` it sits at."""
    renderer = _drawn(fig)
    box = label.get_window_extent(renderer)
    view = ax.get_window_extent(renderer)
    return {
        "top": view.y1 - box.y1,
        "bottom": box.y0 - view.y0,
        "right": view.x1 - box.x1,
        "left": box.x0 - view.x0,
    }[edge]


@pytest.mark.parametrize(
    ("build", "clipped", "texts", "contrast", "edge"),
    [
        (_poc_orders, [6, 11], ["135", "120"], 15.22, "top"),
        (_poc_markets, [0], ["2,410"], 10.24, "right"),
    ],
)
def test_bars_past_the_limit_show_their_true_value(
    build, clipped, texts, contrast, edge
):
    fig, ax, labels = build()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dm.simple_layout(fig)
    assert [str(w.message) for w in caught] == []
    renderer = _drawn(fig)
    assert all(t.get_visible() for t in labels)
    assert [labels[i].get_text() for i in clipped] == texts
    for i, label in enumerate(labels):
        assert label.clipped is (i in clipped)
        if i not in clipped:
            continue
        assert _hex(label) == "#000000"
        assert _contrast_on_bar(label) == pytest.approx(contrast, abs=0.02)
        assert _inside_edge(fig, ax, label, edge) == pytest.approx(
            _offset_px(fig), abs=0.6
        )
        box = label.get_window_extent(renderer)
        bar = label.bar.get_window_extent(renderer)
        assert bar.x0 <= box.x0 and box.x1 <= bar.x1
        assert bar.y0 <= box.y0 and box.y1 <= bar.y1
    shown = _shown(fig, labels)
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []
    # The limits stay the caller's.
    assert not (ax.get_autoscaley_on() and ax.get_autoscalex_on())


@pytest.mark.parametrize(
    ("build", "limits", "edge"),
    [
        (_poc_orders, (100, 0), "bottom"),  # inverted: bars grow down
        (_poc_markets, (800, 0), "left"),  # inverted: bars grow left
    ],
)
def test_bars_past_an_inverted_limit(build, limits, edge):
    fig, ax, labels = build(limits)
    dm.simple_layout(fig)
    clipped = [t for t in labels if t.clipped]
    assert _texts(clipped) == (
        ["135", "120"] if build is _poc_orders else ["2,410"]
    )
    for label in clipped:
        assert label.get_visible()
        assert _inside_edge(fig, ax, label, edge) == pytest.approx(
            _offset_px(fig), abs=0.6
        )
    assert _overlapping(_shown(fig, labels)) == []


def test_bar_past_a_log_limit_and_a_negative_one():
    fig, ax = _fig()
    ax.bar(np.arange(4), [3.0, 40.0, 900.0, 12000.0], width=0.6)
    ax.set_yscale("log")
    ax.set_ylim(1, 1000)
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert [t.clipped for t in labels] == [False, False, False, True]
    assert all(t.get_visible() for t in labels)
    assert labels[3].get_text() == "12,000"
    assert _inside_edge(fig, ax, labels[3], "top") == pytest.approx(
        _offset_px(fig), abs=0.6
    )

    # A negative bar past the lower limit: its value inside that limit.
    fig, ax, _ = _plain([-40.0, 3.0])
    ax.set_ylim(-5, 5)
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert [t.clipped for t in labels] == [True, False]
    assert labels[0].get_visible()
    assert labels[0].get_text() == f"{MINUS}40"
    assert _inside_edge(fig, ax, labels[0], "bottom") == pytest.approx(
        _offset_px(fig), abs=0.6
    )


def test_bars_beyond_the_view_have_none_and_a_short_part_labels_off_it():
    # Only bars cut by the limit along their value count: a bar wholly
    # below the view and one starting above it get none. One that shows
    # too little of itself to hold the label keeps its true value, beyond
    # the limit, off the bar, in the text colour (review C1, candidate A).
    fig, ax = _fig()
    ax.bar(
        [0, 1, 2],
        [30.0, 20.0, 40.0],
        bottom=[0.0, 120.0, 98.0],
        color="dc.blue9",
    )
    ax.set_ylim(50, 100)
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    assert [t.get_visible() for t in labels] == [False, False, True]
    assert not any(t.clipped for t in labels[:2])
    short = labels[2]
    assert short.clipped and short.off_bar and not short.on_bar
    assert _hex(short) == "#000000"
    top = ax.get_window_extent(renderer).y1
    assert short.get_window_extent(renderer).y0 == pytest.approx(
        top + _offset_px(fig), abs=0.6
    )

    # The full bar back in view: an outside label in the text colour again.
    fig, ax, _ = _plain([3.0, 40.0], color="dc.blue9")
    ax.set_ylim(0, 5)
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    _drawn(fig)
    assert _hex(labels[1]) == "#ffffff"
    ax.set_ylim(0, 60)
    _drawn(fig)
    assert not labels[1].clipped
    assert _hex(labels[1]) == "#000000"
    _assert_outside(fig, labels, ax.containers[0].patches)


def test_bar_past_the_limit_keeps_explicit_and_series_choices():
    fig, ax, _ = _plain([3.0, 40.0, 50.0], color="dc.blue9")
    ax.set_ylim(0, 5)
    labels = dm.label_bars(ax, color="series")
    series = _hex(labels[0])
    labels[1].set_color("dc.red7")  # the caller's colour wins
    dm.simple_layout(fig)
    _drawn(fig)
    assert [t.clipped for t in labels] == [False, True, True]
    assert _hex(labels[1]) == mcolors.to_hex("dc.red7")
    assert _hex(labels[2]) == "#ffffff"  # on its bar: readable, not series
    assert _hex(labels[0]) == series not in ("#ffffff", "#000000")

    # A stack's total past the limit keeps the plain rule: no label.
    fig, ax = _fig()
    ax.bar([0, 1], [3.0, 30.0])
    ax.bar([0, 1], [1.0, 20.0], bottom=[3.0, 30.0])
    labels = dm.label_bars(ax, total="only")
    ax.set_ylim(0, 10)
    dm.simple_layout(fig)
    _drawn(fig)
    assert [t.get_visible() for t in labels] == [True, False]


def test_labels_go_on_the_axes_drawn_on_top():
    # The twin idiom that keeps the bars' axes on top: zorder, not order.
    fig, ax, _ = _quarterly()
    ax2 = ax.twinx()
    ax2.plot(np.arange(12), np.linspace(37, 19, 12), color="dc.orange6")
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    texts = dm.label_bars(ax)
    assert all(t.axes is ax for t in texts)
    assert not any(t in ax2.texts for t in texts)


def test_bars_from_another_axes_raise():
    fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("12cm", "wide"))
    bars = right.bar([0, 1], [1.0, 2.0])
    with pytest.raises(ValueError, match="twin"):
        dm.label_bars(left, bars)
    assert not hasattr(left, "_dm_bar_label_families")

    # A twin's bars share the plot area: accepted.
    fig, ax = _fig()
    ax.plot([0, 1], [5.0, 6.0])
    ax2 = ax.twinx()
    twin_bars = ax2.bar([0, 1], [120.0, 135.0])
    texts = dm.label_bars(ax, twin_bars)
    assert all(t.axes is ax2 for t in texts)


# ---------------------------------------------------------------- stacks
def test_stack_segments_and_totals_match_approved():
    fig, ax, containers = _stacked()
    texts = dm.label_bars(ax)
    dm.place_legend(ax)
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert _texts(texts) == S_A_SEG + S_A_TOT
    assert _kinds(texts) == ["segment"] * 18 + ["total"] * 6
    for text in texts:
        assert text.get_visible()
        assert text.get_fontsize() == pytest.approx(dm.fs(-1))
        assert text.get_fontweight() == dm.fw(1)
        assert _hex(text) == "#000000"  # dark ink on blue7/4/2; totals
        assert text.get_rotation() == 0
    segments = [p for c in containers for p in c.patches]
    _assert_centred(fig, texts[:18], segments)
    _assert_outside(fig, texts[18:], containers[-1].patches)

    # The stack is recorded for the layout's later passes.
    (family,) = ax._dm_bar_label_families
    (stack,) = family.stacks
    assert stack.containers == containers
    assert all(t.stack is stack for t in texts)


def test_total_only_and_off():
    fig, ax, containers = _stacked()
    texts = dm.label_bars(ax, total="only")
    dm.simple_layout(fig)
    assert _texts(texts) == S_A_TOT
    assert set(_kinds(texts)) == {"total"}
    _assert_outside(fig, texts, containers[-1].patches)

    fig, ax, containers = _stacked()
    texts = dm.label_bars(ax, total=False)
    dm.simple_layout(fig)
    assert _texts(texts) == S_A_SEG
    assert set(_kinds(texts)) == {"segment"}
    _assert_centred(fig, texts, [p for c in containers for p in c.patches])

    # Bars that form no stack keep their edge labels under either option.
    for total in ("only", False):
        fig, ax, _ = _plain([3.0, 5.0])
        texts = dm.label_bars(ax, total=total)
        assert _texts(texts) == ["3", "5"]
        assert set(_kinds(texts)) == {"edge"}


def test_short_segment_label_hidden():
    fig, ax = _fig()
    _stack(ax, [([30.0, 30.0], {}), ([1.0, 12.0], {})], np.arange(2))
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    short = texts[2]
    assert short.get_text() == "1"
    # 1 of 42 on a 12 cm chart: a few points, shorter than a 7 pt label.
    assert not short.get_visible()
    assert short in ax.texts  # hidden, not deleted
    assert not np.isfinite(short.get_tightbbox(renderer).extents).all()
    assert all(t.get_visible() for t in texts if t is not short)

    # A taller figure gives the segment room: the label comes back.
    width, height = fig.get_size_inches()
    fig.set_size_inches(width, 12)
    fig.canvas.draw()
    assert short.get_visible()

    # Measured against the label itself: a smaller label fits again.
    fig.set_size_inches(width, height)
    fig.canvas.draw()
    assert not short.get_visible()
    short.set_fontsize(2)
    fig.canvas.draw()
    assert short.get_visible()
    # Along the value axis as drawn: a long text fits flat, not turned.
    short.set_text("1,000,000")
    fig.canvas.draw()
    assert short.get_visible()
    short.set_rotation(90)
    fig.canvas.draw()
    assert not short.get_visible()


def test_segment_room_after_a_dpi_change():
    # Text and bar both scale with the dpi, so the answer must not change;
    # asked before the next draw, the label is measured at the new dpi,
    # not with the renderer of the last draw.
    fig, ax = _fig()
    ax.set_ylim(0, 100)
    containers = _stack(ax, [([50.0], {}), ([10.0], {})], [0])
    seg = dm.label_bars(ax, total=False)[1]
    renderer = _drawn(fig)
    height = seg.get_window_extent(renderer).height
    unit_px = (
        ax.transData.transform((0, 1))[1] - ax.transData.transform((0, 0))[1]
    )
    containers[1].patches[0].set_height(1.3 * height / unit_px)
    fig.canvas.draw()
    assert seg.get_visible()
    fig.set_dpi(fig.dpi / 2)
    assert seg.get_visible()
    fig.canvas.draw()
    assert seg.get_visible()

    # A plain Figure's canvas has no renderer of its own: matplotlib
    # measures at the figure's current dpi, so a dpi change measures anew.
    fig = Figure(figsize=dm.figsize("12cm", "standard"), dpi=72)
    ax = fig.add_subplot()
    _stack(ax, [([30.0, 30.0], {}), ([1.0, 12.0], {})], np.arange(2))
    short = dm.label_bars(ax)[2]
    fig.savefig(io.BytesIO(), format="png", dpi="figure")
    assert not short.get_visible()
    fig.set_dpi(288)
    assert not short.get_visible()


def test_segment_room_counts_the_inside_inset():
    def chart(where, length=None):
        fig, ax = _fig()
        ax.set_ylim(0, 100)
        containers = _stack(ax, [([50.0], {}), ([10.0], {})], [0])
        if length is not None:
            containers[1].patches[0].set_height(length)
        texts = dm.label_bars(ax, where=where, total=False)
        return fig, ax, texts[1]

    fig, ax, label = chart("center")
    renderer = _drawn(fig)
    height = label.get_window_extent(renderer).height
    unit_px = (
        ax.transData.transform((0, 1))[1] - ax.transData.transform((0, 0))[1]
    )
    # A segment longer than the label, but not by the 3 pt inset.
    length = (height + _offset_px(fig) / 2) / unit_px
    fig, _, centred = chart("center", length)
    fig.canvas.draw()
    assert centred.get_visible()
    fig, _, inside = chart("inside", length)
    fig.canvas.draw()
    assert not inside.get_visible()


def test_stack_bottoms_from_rounded_running_sums():
    # Bottoms read from a table of running totals (0.3) rather than summed
    # bar by bar (0.1 + 0.2 = 0.30000000000000004) still stack.
    fig, ax = _fig()
    ax.bar([0], [0.1])
    ax.bar([0], [0.2], bottom=[0.1])
    ax.bar([0], [0.4], bottom=[0.3])
    assert 0.1 + 0.2 != 0.3
    texts = dm.label_bars(ax)
    assert _kinds(texts) == ["segment"] * 3 + ["total"]
    assert _texts(texts)[-1] == "0.7"


def test_mixed_sign_stack_net_total_side():
    fig, ax = _fig()
    containers = _stack(
        ax,
        [([5.0, 2.0], {}), ([-2.0, -5.0], {}), ([3.0, 1.0], {})],
        np.arange(2),
        width=0.6,
    )
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    seg = [p for c in containers for p in c.patches]
    assert _texts(texts) == [
        "5",
        "2",
        f"{MINUS}2",
        f"{MINUS}5",
        "3",
        "1",
        "6",  # net 5 - 2 + 3
        f"{MINUS}2",  # net 2 - 5 + 1
    ]
    assert _kinds(texts) == ["segment"] * 6 + ["total"] * 2
    _assert_centred(fig, texts[:6], seg)
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    up, down = texts[6:]
    # Net 6 >= 0: beyond the positive end (5 + 3), above it.
    assert up.get_verticalalignment() == "bottom"
    assert up.get_window_extent(renderer).y0 == pytest.approx(
        ax.transData.transform((0, 8.0))[1] + gap, abs=0.6
    )
    # Net -2 < 0: beyond the negative end (-5), below it.
    assert down.get_verticalalignment() == "top"
    assert down.get_window_extent(renderer).y1 == pytest.approx(
        ax.transData.transform((1, -5.0))[1] - gap, abs=0.6
    )


def test_waterfall_is_not_a_stack():
    # A waterfall: one container of floating bars. Plain edge labels.
    fig, ax = _fig()
    bars = ax.bar(
        np.arange(4), [10.0, -3.0, 5.0, -2.0], bottom=[0.0, 10.0, 7.0, 12.0]
    )
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["10", f"{MINUS}3", "5", f"{MINUS}2"]
    assert set(_kinds(texts)) == {"edge"}
    _assert_outside(fig, texts, bars.patches)
    (family,) = ax._dm_bar_label_families
    assert family.stacks == []

    # Bars at the same positions that float above the others: no stack.
    fig, ax = _fig()
    low = ax.bar([0, 1], [4.0, 5.0])
    high = ax.bar([0, 1], [2.0, 2.0], bottom=[6.0, 7.0])
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["4", "5", "2", "2"]
    assert set(_kinds(texts)) == {"edge"}
    _assert_outside(fig, texts, low.patches + high.patches)

    # Overlaid bars from the same base (actual against target): no stack.
    fig, ax = _fig()
    ax.bar([0, 1], [5.0, 6.0])
    ax.bar([0, 1], [3.0, 4.0], width=0.4)
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["5", "6", "3", "4"]
    assert set(_kinds(texts)) == {"edge"}

    # Gap-to-target bars beside the actuals, starting at their tops: other
    # positions, so no stack either.
    fig, ax = _fig()
    actual = ax.bar([0, 1], [3.0, 4.0], width=0.4)
    gap = ax.bar([0.3, 1.3], [1.0, 1.5], bottom=[3.0, 4.0], width=0.2)
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["3.0", "4.0", "1.0", "1.5"]
    assert set(_kinds(texts)) == {"edge"}
    _assert_outside(fig, texts, actual.patches + gap.patches)


def test_bars_that_never_stand_together_are_no_stack():
    # A two-colour waterfall: rises and falls at the same positions, each
    # from the running level, the other colour padded with NaN or zero.
    steps = np.array([10.0, -3.0, 5.0, -2.0])
    level = np.array([0.0, 10.0, 7.0, 12.0])
    for pad in (np.nan, 0.0):
        fig, ax = _fig()
        x = np.arange(4)
        ups = ax.bar(x, np.where(steps > 0, steps, pad), bottom=level)
        downs = ax.bar(x, np.where(steps < 0, steps, pad), bottom=level)
        texts = dm.label_bars(ax)
        dm.simple_layout(fig)
        # Each value once, no totals, no "0" for the padding.
        assert _texts(texts) == ["10", "5", f"{MINUS}3", f"{MINUS}2"]
        assert set(_kinds(texts)) == {"edge"}
        assert ax._dm_bar_label_families[0].stacks == []
        shown = [ups.patches[0], ups.patches[2], downs.patches[1]]
        _assert_outside(fig, texts, [*shown, downs.patches[3]])

    # The highlight idiom: one series split into grey and an accent.
    values = np.array([3.0, 5.0, 4.0, 6.0])
    mask = np.array([False, True, False, False])
    for pad in (np.nan, 0.0):
        fig, ax = _fig()
        ax.bar(np.arange(4), np.where(mask, pad, values), color="0.7")
        ax.bar(np.arange(4), np.where(mask, values, pad), color="dc.red6")
        texts = dm.label_bars(ax)
        assert _texts(texts) == ["3", "4", "6", "5"]
        assert set(_kinds(texts)) == {"edge"}
        assert ax._dm_bar_label_families[0].stacks == []

    # An all-NaN container, then the real one: one plain family.
    fig, ax = _fig()
    ax.bar([0, 1], [np.nan, np.nan])
    bars = ax.bar([0, 1], [3.0, 4.0])
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["3", "4"]
    assert set(_kinds(texts)) == {"edge"}
    (family,) = ax._dm_bar_label_families
    assert family.stacks == []
    _assert_outside(fig, texts, bars.patches)


def test_running_end_tolerance_is_per_bar():
    # 501 is not 1 because another bar is 1e12 tall.
    fig, ax = _fig()
    ax.bar([0, 1], [1e12, 1.0])
    ax.bar([0, 1], [5.0, 5.0], bottom=[1e12, 501.0])
    texts = dm.label_bars(ax)
    assert set(_kinds(texts)) == {"edge"}
    assert ax._dm_bar_label_families[0].stacks == []


def test_inside_ink_by_contrast():
    blue7 = mcolors.to_hex("dc.blue7")
    assert blue7 == "#1686e0"
    on_blue7 = mcolors.to_rgb(blue7)
    assert contrast_ratio((0.0, 0.0, 0.0), on_blue7) == pytest.approx(
        5.52, abs=0.01
    )
    assert contrast_ratio((1.0, 1.0, 1.0), on_blue7) == pytest.approx(
        3.80, abs=0.01
    )

    def chart(**kw):
        fig, ax = _fig()
        parts = [([4.0, 5.0], {"color": "dc.blue7"}), ([3.0, 3.0], kw)]
        _stack(ax, parts, np.arange(2))
        return ax

    # Segments take the more readable of white and the text colour; the
    # totals sit off the bars, in the text colour.
    texts = dm.label_bars(chart(color="dc.blue9"))
    assert [_hex(t) for t in texts] == ["#000000"] * 2 + ["#ffffff"] * 2 + [
        "#000000"
    ] * 2

    # The dark ink is the preset's text colour.
    with matplotlib.rc_context({"text.color": "#212529"}):
        texts = dm.label_bars(chart(color="dc.blue9"))
    assert [_hex(t) for t in texts] == ["#212529"] * 2 + ["#ffffff"] * 2 + [
        "#212529"
    ] * 2

    # The colour as drawn: dc.blue9 at alpha 0.3 shows light, so dark ink.
    texts = dm.label_bars(chart(color="dc.blue9", alpha=0.3))
    assert {_hex(t) for t in texts} == {"#000000"}

    # where="inside" / "center" on plain bars: the same ink; outside labels
    # keep the text colour.
    for where in ("inside", "center"):
        fig, ax, _ = _plain([4.0, 3.0], color=["dc.blue7", "dc.blue9"])
        texts = dm.label_bars(ax, where=where)
        assert [_hex(t) for t in texts] == ["#000000", "#ffffff"]
    fig, ax, _ = _plain([4.0, 3.0], color=["dc.blue7", "dc.blue9"])
    assert {_hex(t) for t in dm.label_bars(ax)} == {"#000000"}

    # An explicit colour wins, totals included.
    texts = dm.label_bars(chart(color="dc.blue9"), color="dc.red7")
    assert {_hex(t) for t in texts} == {mcolors.to_hex("dc.red7")}
    # "series" colours only labels off their own bar: a segment keeps the
    # readable ink, a total (of no single series) the text colour.
    texts = dm.label_bars(chart(color="dc.blue9"), color="series")
    assert [_hex(t) for t in texts] == ["#000000"] * 2 + ["#ffffff"] * 2 + [
        "#000000"
    ] * 2


def _shown_on(text, patch):
    """Contrast of ``text``'s ink against ``patch`` as drawn on white."""
    r, g, b, a = mcolors.to_rgba(patch.get_facecolor())
    shown = tuple(a * c + (1 - a) for c in (r, g, b))
    return contrast_ratio(mcolors.to_rgb(text.get_color()), shown)


def test_series_ink_only_off_the_bar():
    navy = "#0b3d91"
    # A segment and a "center" label under "series" sit on their own bar:
    # readable ink, never the bar's own hue.
    fig, ax = _fig()
    containers = _stack(
        ax, [([4.0], {"color": "dc.blue2"}), ([3.0], {"color": navy})], [0]
    )
    texts = dm.label_bars(ax, color="series")
    for text, bars in zip(texts[:2], containers, strict=True):
        assert _shown_on(text, bars.patches[0]) >= 4.5
    assert _hex(texts[2]) == "#000000"  # the total
    for where in ("center", "inside"):
        fig, ax, bars = _plain([4.0], color=navy)
        (text,) = dm.label_bars(ax, where=where, color="series")
        assert _shown_on(text, bars.patches[0]) >= 4.5
        assert _hex(text) != navy

    # Off the bar the series hue reads on the background: outside labels,
    # a stack's segments placed outside included.
    fig, ax, _ = _plain([4.0], color=navy)
    (text,) = dm.label_bars(ax, color="series")
    assert _hex(text) == navy  # already 4.5:1 on white
    fig, ax = _fig()
    _stack(ax, [([4.0], {"color": "dc.blue2"}), ([3.0], {"color": navy})], [0])
    texts = dm.label_bars(ax, where="outside", color="series")
    assert _hex(texts[1]) == navy
    assert _hex(texts[0]) not in ("#000000", "#ffffff")  # blue2, darkened
    assert _contrast_on_white(texts[0]) >= 4.5
    assert _hex(texts[2]) == "#000000"  # the total


def test_grouped_and_stacked_layout():
    # Two stacked groups side by side, drawn interleaved.
    fig, ax = _fig()
    x = np.arange(3)
    w = 0.35
    left, right = x - w / 2 - 0.01, x + w / 2 + 0.01
    a1 = ax.bar(left, [3.0, 4.0, 5.0], width=w)
    b1 = ax.bar(right, [2.0, 2.0, 2.0], width=w)
    a2 = ax.bar(left, [1.0, 1.0, 1.0], bottom=[3.0, 4.0, 5.0], width=w)
    b2 = ax.bar(right, [6.0, 5.0, 4.0], bottom=[2.0, 2.0, 2.0], width=w)
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    (family,) = ax._dm_bar_label_families
    assert [s.containers for s in family.stacks] == [[a1, a2], [b1, b2]]
    segments = [t for t in texts if t.kind == "segment"]
    totals = [t for t in texts if t.kind == "total"]
    # Container by container: a1, b1, a2, b2.
    assert _texts(segments) == [
        "3",
        "4",
        "5",
        "2",
        "2",
        "2",
        "1",
        "1",
        "1",
        "6",
        "5",
        "4",
    ]
    assert _texts(totals) == ["4", "5", "6", "8", "7", "6"]
    _assert_centred(
        fig, segments, a1.patches + b1.patches + a2.patches + b2.patches
    )
    _assert_outside(fig, totals, a2.patches + b2.patches)

    # Grouped bars (side by side, from one base) form no stack.
    fig, ax, _ = _grouped()
    texts = dm.label_bars(ax)
    assert set(_kinds(texts)) == {"edge"}
    assert ax._dm_bar_label_families[0].stacks == []


def test_stack_where_places_segments():
    def chart():
        fig, ax = _fig()
        parts = [([6.0, 7.0], {}), ([5.0, 4.0], {})]
        return fig, ax, _stack(ax, parts, np.arange(2), width=0.6)

    # "inside": just inside each segment's end; the totals stay outside.
    fig, ax, containers = chart()
    texts = dm.label_bars(ax, where="inside")
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    segments = [p for c in containers for p in c.patches]
    for text, patch in zip(texts[:4], segments, strict=True):
        tb = text.get_window_extent(renderer)
        assert tb.y1 == pytest.approx(
            patch.get_window_extent(renderer).y1 - gap, abs=0.6
        )
    assert _texts(texts[4:]) == ["11", "11"]
    _assert_outside(fig, texts[4:], containers[-1].patches)

    # "outside": at each segment's end, as asked, in the text colour.
    fig, ax, containers = chart()
    texts = dm.label_bars(ax, where="outside", total=False)
    _assert_outside(fig, texts, [p for c in containers for p in c.patches])
    assert {_hex(t) for t in texts} == {"#000000"}

    # A label outside its segment needs no room on it.
    fig, ax = _fig()
    _stack(ax, [([30.0, 30.0], {}), ([1.0, 12.0], {})], np.arange(2))
    texts = dm.label_bars(ax, where="outside", total=False)
    fig.canvas.draw()
    assert all(t.get_visible() for t in texts)


def test_stack_nan_and_zero_segments():
    fig, ax = _fig()
    containers = _stack(
        ax,
        [([3.0, 4.0], {}), ([np.nan, 2.0], {}), ([1.0, 0.0], {})],
        np.arange(2),
        width=0.6,
    )
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    # No label for the NaN segment, which adds nothing to its total, nor
    # for the zero segment beside bars that carry the value.
    assert _texts(texts) == ["3", "4", "2", "1", "4", "6"]
    assert _kinds(texts) == ["segment"] * 4 + ["total"] * 2
    fig.canvas.draw()
    assert all(t.get_visible() for t in texts)
    _assert_outside(
        fig, texts[4:], [containers[2].patches[0], containers[1].patches[1]]
    )

    # Where every bar is zero, the first one keeps its label (no room to
    # show on a stack segment) and the total reads 0.
    fig, ax = _fig()
    _stack(ax, [([0.0, 2.0], {}), ([0.0, 3.0], {})], np.arange(2))
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["0", "2", "3", "0", "5"]
    assert _kinds(texts) == ["segment"] * 3 + ["total"] * 2

    # bottom + values carried the NaN on: the bar above it is not drawn,
    # shows no label, and the total counts what stands.
    fig, ax = _fig()
    ax.bar([0, 1], [3.0, 4.0])
    ax.bar([0, 1], [np.nan, 2.0], bottom=[3.0, 4.0])
    ax.bar([0, 1], [1.0, 1.0], bottom=[np.nan, 6.0])
    texts = dm.label_bars(ax)
    fig.canvas.draw()
    assert _texts(texts) == ["3", "4", "2", "1", "1", "3", "7"]
    assert not texts[3].get_visible()

    # A zero bar a caller put on the negative end: the total still sits
    # beyond the farthest positive end.
    fig, ax = _fig()
    top = ax.bar([0], [5.0])
    ax.bar([0], [-2.0])
    ax.bar([0], [0.0], bottom=[-2.0])
    texts = dm.label_bars(ax)
    assert _texts(texts) == ["5", f"{MINUS}2", "3"]
    assert _kinds(texts)[-1] == "total"
    _assert_outside(fig, texts[-1:], top.patches)


def test_segment_room_reads_the_text_the_draw_writes():
    # barh: the room a label needs is its width, which the tick unit moves.
    fig, ax = _fig()
    parts = [
        ([3e6], {"color": "dc.blue2"}),
        ([1234567.0], {"color": "dc.blue2"}),
    ]
    _stack(ax, parts, [0], horizontal=True, height=0.6)
    seg = dm.label_bars(ax, total=False)[1]
    assert seg.get_text() == "1,234,567"
    renderer = _drawn(fig)

    def width(text):
        probe = ax.text(0, 0, text, fontsize=seg.get_fontsize())
        probe.set_fontweight(seg.get_fontweight())
        extent = probe.get_window_extent(renderer).width
        probe.remove()
        return extent

    # A view in which the segment is narrower than "1,234,567" but wider
    # than "1.23M".
    room = (width("1,234,567") + width("1.23M")) / 2
    ax.set_xlim(0, 1234567.0 * ax.get_window_extent(renderer).width / room)
    fig.canvas.draw()
    assert not seg.get_visible()

    # A draw formats the axis before it asks the label: the label is
    # measured on the text that draw writes.
    dm.format_axis_si(ax, "x")
    ax.xaxis.get_major_formatter().format_ticks(list(ax.get_xticks()))
    assert seg.get_visible()
    fig.canvas.draw()
    assert seg.get_text() == "1.23M"
    assert seg.get_visible()


def test_negative_only_barh_stack():
    fig, ax = _fig()
    containers = _stack(
        ax,
        [([-3.0, -2.0], {}), ([-1.0, -4.0], {})],
        np.arange(2),
        horizontal=True,
        height=0.6,
    )
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == [
        f"{MINUS}{v}" for v in ("3", "2", "1", "4", "4", "6")
    ]
    assert _kinds(texts) == ["segment"] * 4 + ["total"] * 2
    _assert_centred(fig, texts[:4], [p for c in containers for p in c.patches])
    assert {t.get_horizontalalignment() for t in texts[4:]} == {"right"}
    _assert_outside(fig, texts[4:], containers[1].patches, "horizontal")


def test_stack_on_a_twin():
    # Stacked bars on the twin, a line on the parent.
    fig, ax = _fig()
    ax.plot([0, 1], [50.0, 70.0], color="dc.orange6")
    ax2 = ax.twinx()
    containers = _stack(
        ax2, [([3.0, 4.0], {}), ([2.0, 2.0], {})], np.arange(2), width=0.6
    )
    texts = dm.label_bars(ax2)
    dm.simple_layout(fig)
    assert all(t.axes is ax2 for t in texts)
    assert _texts(texts) == ["3", "4", "2", "2", "5", "6"]
    _assert_centred(fig, texts[:4], [p for c in containers for p in c.patches])
    _assert_outside(fig, texts[4:], containers[1].patches)

    # Stacked bars on the parent, a line on the twin: the labels go on the
    # twin, placed with the bars' data.
    fig, ax = _fig()
    containers = _stack(
        ax, [([3.0, 4.0], {}), ([2.0, 2.0], {})], np.arange(2), width=0.6
    )
    ax2 = ax.twinx()
    ax2.plot([0, 1], [50.0, 70.0], color="dc.orange6")
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert all(t.axes is ax2 for t in texts)
    assert _texts(texts) == ["3", "4", "2", "2", "5", "6"]
    _assert_centred(fig, texts[:4], [p for c in containers for p in c.patches])
    _assert_outside(fig, texts[4:], containers[1].patches)


def test_stack_on_an_inverted_value_axis():
    fig, ax = _fig()
    _stack(ax, [([3.0, 4.0], {}), ([2.0, -2.0], {})], np.arange(2), width=0.6)
    texts = dm.label_bars(ax)
    ax.invert_yaxis()  # after labelling
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    gap = _offset_px(fig)
    assert _texts(texts[4:]) == ["5", "2"]
    # Both nets are >= 0: beyond the positive ends (5 and 4), which the
    # inverted axis shows lower on screen.
    for text, end, x in zip(texts[4:], (5.0, 4.0), (0, 1), strict=True):
        assert text.get_verticalalignment() == "top"
        assert text.get_window_extent(renderer).y1 == pytest.approx(
            ax.transData.transform((x, end))[1] - gap, abs=0.6
        )

    # A negative net (2 - 5 + 1) sits beyond the negative end (-5), which
    # the inverted axis shows higher on screen.
    fig, ax = _fig()
    _stack(ax, [([2.0], {}), ([-5.0], {}), ([1.0], {})], [0], width=0.6)
    ax.invert_yaxis()
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    total = texts[-1]
    assert total.get_text() == f"{MINUS}2"
    assert total.get_verticalalignment() == "bottom"
    assert total.get_window_extent(renderer).y0 == pytest.approx(
        ax.transData.transform((0, -5.0))[1] + _offset_px(fig), abs=0.6
    )


def test_invalid_arguments_raise():
    fig, ax, bars = _plain([1.0, 2.0])
    with pytest.raises(ValueError, match="where"):
        dm.label_bars(ax, where="top")
    with pytest.raises(ValueError, match="total"):
        dm.label_bars(ax, total="yes")
    with pytest.raises(ValueError, match="crowded"):
        dm.label_bars(ax, crowded="wrap")
    with pytest.raises(ValueError, match="decimals"):
        dm.label_bars(ax, decimals=-1)
    with pytest.raises(ValueError, match="fmt"):
        dm.label_bars(ax, fmt="no placeholder")
    with pytest.raises(TypeError, match="bars"):
        dm.label_bars(ax, ax.plot([0, 1], [1, 2]))
    assert dm.label_bars(ax, []) == []  # explicitly nothing to label
    fig, ax = _fig()
    ax.plot([0, 1], [1, 2])
    with pytest.raises(ValueError, match="no bars"):
        dm.label_bars(ax)
    assert not hasattr(ax, "_dm_bar_label_families")


def test_exported_as_experimental():
    assert "label_bars" in dm.__all__
    assert "label_bars" in dm.EXPERIMENTAL


# ------------------------------------------------- settling in simple_layout
def _dense(values=D_REV, color="dc.blue6", **label_kw):
    """The approved dense chart (d), labelled and laid out."""
    fig, ax = _fig()
    x = np.arange(len(values))
    bars = ax.bar(x, values, width=0.7, color=color)
    ax.set_xticks(x[::3], D_TICKS[: len(values)][::3])
    dm.axis_unit(
        ax, "y", label="Revenue (USD {unit})", ladder="finance", scale="whole"
    )
    texts = dm.label_bars(ax, **label_kw)
    dm.simple_layout(fig)
    return fig, ax, bars, texts


def _twin_chart(*, label=True):
    """The approved twin chart (t): bars, a growth line on the twin."""
    fig, ax, bars = _quarterly()
    ax2 = ax.twinx()
    ax2.plot(np.arange(12), T_YOY, color="dc.orange6", marker="o", markersize=3)
    ax2.set_ylabel("YoY growth (%)")
    texts = dm.label_bars(ax) if label else []
    return fig, ax, bars, texts


def _shown(fig, texts):
    """``(label, display box)`` of each label drawn."""
    renderer = _drawn(fig)
    return [
        (t, t.get_window_extent(renderer)) for t in texts if t.get_visible()
    ]


def _cover(a, b, tol):
    return (
        min(a.x1, b.x1) - max(a.x0, b.x0) > tol
        and min(a.y1, b.y1) - max(a.y0, b.y0) > tol
    )


def _overlapping(shown, tol=0.5):
    """Pairs of drawn labels whose boxes overlap."""
    return [
        (a.get_text(), b.get_text())
        for i, (a, box_a) in enumerate(shown)
        for b, box_b in shown[i + 1 :]
        if _cover(box_a, box_b, tol)
    ]


def _on_bars(fig, shown, tol=0.8):
    """Labels off their bar (``"outside"``) that cover a bar anyway.

    A label inside the limit its bar runs past (``clipped``) sits on its
    own bar by design: it may cover no other bar.
    """
    renderer = fig.canvas.get_renderer()
    bars = [
        (patch, patch.get_window_extent(renderer))
        for axes in fig.axes
        for patch in axes.patches
        if patch.get_visible()
    ]

    def covers(label, box):
        clipped = getattr(label, "clipped", False)
        if label.where != "outside" and not clipped:
            return False
        return any(
            _cover(box, b, tol)
            for patch, b in bars
            if not (clipped and patch is label.bar)
        )

    return [label.get_text() for label, box in shown if covers(label, box)]


def _inside_axes(ax, shown, tol=0.5):
    box = ax.get_window_extent(ax.get_figure().canvas.get_renderer())
    return all(
        b.x0 >= box.x0 - tol
        and b.x1 <= box.x1 + tol
        and b.y0 >= box.y0 - tol
        and b.y1 <= box.y1 + tol
        for _, b in shown
    )


def test_dense_24_rotated_all_kept_no_overlap():
    # d-A: 24 labels wider than the bar pitch turn vertical; all kept.
    fig, ax, bars, texts = _dense()
    shown = _shown(fig, texts)
    assert _texts(texts) == D_A
    assert len(shown) == 24
    assert {t.get_rotation() for t in texts} == {90.0}
    assert {t.get_horizontalalignment() for t in texts} == {"center"}
    assert {t.get_verticalalignment() for t in texts} == {"bottom"}
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []
    _assert_outside(fig, texts, bars.patches)
    # The top label sits inside the axes, 3 pt from its edge (approved:
    # 12.5 px at 300 dpi), the limit grown by just that (1.103, not 1.15).
    axes_top = ax.get_window_extent(fig.canvas.get_renderer()).y1
    top = max(box.y1 for _, box in shown)
    assert axes_top - top >= 0
    assert axes_top - top == pytest.approx(_offset_px(fig), abs=0.6)
    assert ax.get_ylim()[1] / D_REV.max() == pytest.approx(
        D_A_HEADROOM, abs=0.002
    )
    assert ax.get_autoscaley_on()  # still matplotlib's limit to change


def test_crowded_skip_and_inside():
    # d-A-skip: every other label hidden, counted back from the last bar.
    fig, ax, _bars, texts = _dense(crowded="skip")
    shown = _shown(fig, texts)
    assert [t.get_text() for t, _ in shown] == D_A_SKIP
    assert [t.get_visible() for t in texts] == [i % 2 == 1 for i in range(24)]
    assert {t.get_rotation() for t in texts} == {0.0}
    assert _overlapping(shown) == []
    # A kept label wider than its bar is lifted over the taller bar it
    # spans, never drawn on it.
    assert _on_bars(fig, shown) == []
    renderer = fig.canvas.get_renderer()
    lifted = texts[9]  # 1,027 spans the taller 1,103 to its right
    assert lifted.get_window_extent(renderer).y0 == pytest.approx(
        ax.transData.transform((10, D_REV[10]))[1] + _offset_px(fig), abs=0.6
    )
    hidden = texts[0]
    assert not np.isfinite(hidden.get_tightbbox(renderer).extents).all()
    # The kept labels fit in matplotlib's own margin: no growth.
    assert ax.get_ylim()[1] / D_REV.max() == pytest.approx(
        AUTOSCALE_HEADROOM, abs=0.002
    )

    # d-A-inside: vertical text inside the bar ends, in readable ink.
    fig, ax, bars, texts = _dense(crowded="inside")
    shown = _shown(fig, texts)
    assert len(shown) == 24
    assert {t.get_rotation() for t in texts} == {90.0}
    assert {t.where for t in texts} == {"inside"}
    assert {_hex(t) for t in texts} == {"#000000"}  # approved, on dc.blue6
    assert _overlapping(shown) == []
    renderer = fig.canvas.get_renderer()
    for (_label, box), patch in zip(shown, bars.patches, strict=True):
        bar = patch.get_window_extent(renderer)
        assert bar.x0 - 0.5 <= box.x0 and box.x1 <= bar.x1 + 0.5
        assert box.y1 == pytest.approx(bar.y1 - _offset_px(fig), abs=0.6)
        assert box.y0 >= bar.y0
    assert ax.get_ylim()[1] / D_REV.max() == pytest.approx(
        AUTOSCALE_HEADROOM, abs=0.002
    )

    # On dark bars the inside ink is white; a bar too short for its label
    # keeps the label outside, vertical, in the text colour.
    values = D_REV.copy()
    values[3] = 40e6
    fig, ax, bars, texts = _dense(values, color="dc.blue9", crowded="inside")
    short = texts[3]
    assert short.where == "outside"
    assert _hex(short) == mcolors.to_hex(matplotlib.rcParams["text.color"])
    assert short.get_rotation() == 90.0
    _assert_outside(fig, [short], [bars.patches[3]])
    others = [t for i, t in enumerate(texts) if i != 3]
    assert {t.where for t in others} == {"inside"}
    assert {_hex(t) for t in others} == {"#ffffff"}


def test_barh_thin_rows_skip_alternate():
    # Rows thinner than the text: barh never turns its labels; it hides
    # every other one, keeping the top row (the first one read).
    n = 40
    values = np.linspace(40.0, 2.5, n)
    for crowded in ("rotate", "skip"):
        fig, ax = _fig()
        y = np.arange(n)
        bars = ax.barh(y, values, height=0.9)
        ax.invert_yaxis()
        texts = dm.label_bars(ax, crowded=crowded)
        dm.simple_layout(fig)
        shown = _shown(fig, texts)
        assert {t.get_rotation() for t in texts} == {0.0}
        assert [t.get_visible() for t in texts] == [
            i % 2 == 0 for i in range(n)
        ]
        assert _overlapping(shown) == []
        # A kept label spans the longer row above it: it is pushed past
        # that row's end instead of sitting on it.
        assert _on_bars(fig, shown) == []
        renderer = fig.canvas.get_renderer()
        assert texts[2].get_window_extent(renderer).x0 == pytest.approx(
            bars.patches[1].get_window_extent(renderer).x1 + _offset_px(fig),
            abs=0.6,
        )
        assert _inside_axes(ax, shown)

    # A figure tall enough for every row brings every label back.
    fig.set_size_inches(fig.get_size_inches()[0], 16)
    dm.simple_layout(fig)
    assert all(t.get_visible() for t in texts)
    _assert_outside(fig, texts, bars.patches, "horizontal")


def test_headroom_grows_only_autoscaled_limit():
    # q-A: the labels fit in matplotlib's own margin; the limit stays.
    fig, ax, bars = _quarterly()
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert ax.get_ylim() == pytest.approx((0.0, AUTOSCALE_HEADROOM * 33e9))
    shown = _shown(fig, texts)
    axes_top = ax.get_window_extent(fig.canvas.get_renderer()).y1
    assert axes_top - max(b.y1 for _, b in shown) == pytest.approx(50.4, abs=1)

    # h-A: matplotlib's margin (axes.xmargin 0.05) leaves the top label on
    # the axes edge; the limit grows by the label and 3 pt, no more.
    fig, ax, bars = _horizontal()
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    renderer = fig.canvas.get_renderer()
    right = ax.get_window_extent(renderer).x1
    assert right - max(b.x1 for _, b in shown) == pytest.approx(
        _offset_px(fig), abs=0.6
    )
    assert ax.get_xlim()[0] == 0.0
    assert ax.get_xlim()[1] / H_SHARE.max() == pytest.approx(
        H_A_HEADROOM, abs=0.002
    )
    assert ax.get_autoscalex_on()

    # It grows from matplotlib's autoscaled limit, never from its own last
    # write: another layout finds the same limit.
    grown = ax.get_xlim()
    dm.simple_layout(fig)
    assert ax.get_xlim() == pytest.approx(grown, rel=1e-6)

    # A view the caller set while autoscaling stays on (set_xlim(...,
    # auto=None), set_xbound) is theirs: kept, nothing grows.
    ax.set_xlim(0, 80, auto=None)
    dm.simple_layout(fig)
    assert ax.get_xlim() == (0.0, 80.0)
    assert ax.get_autoscalex_on()


@pytest.mark.parametrize("sign", [1, -1])
@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_headroom_keeps_the_edge_it_does_not_grow(orientation, sign):
    # With no margin the labels need room; only the label side grows. The
    # other edge keeps matplotlib's exact value (a sticky 0, not 4e-16 from
    # a round trip through display space).
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    values = sign * np.array([21.4, 18.0, 21.5, 33.0])
    if orientation == "vertical":
        ax.bar(range(4), values)
        ax.margins(y=0)
    else:
        ax.barh(range(4), values)
        ax.margins(x=0)
    dm.label_bars(ax)
    dm.simple_layout(fig)
    low, high = ax.get_ylim() if orientation == "vertical" else ax.get_xlim()
    if sign > 0:
        assert low == 0.0
        assert high > 33.0
    else:
        assert high == 0.0
        assert low < -33.0
    plt.close(fig)

    # A later explicit limit wins from then on.
    ax.set_xlim(0, 40)
    dm.simple_layout(fig)
    assert ax.get_xlim() == (0.0, 40.0)
    assert not ax.get_autoscalex_on()


def test_user_limits_respected_label_outside_margin_reserved():
    # The caller's limit ends on the top bar: the limit stays, the label
    # sits above the axes and the layout makes room for it in the figure.
    def chart(label):
        fig, ax, bars = _quarterly()
        ax.set_ylim(0, 33e9)
        texts = dm.label_bars(ax) if label else []
        dm.simple_layout(fig)
        return fig, ax, texts

    fig, ax, texts = chart(True)
    assert ax.get_ylim() == (0.0, 33e9)
    assert not ax.get_autoscaley_on()
    renderer = _drawn(fig)
    top = texts[-1].get_window_extent(renderer)
    axes_box = ax.get_window_extent(renderer)
    assert texts[-1].get_visible()
    assert top.y0 == pytest.approx(axes_box.y1 + _offset_px(fig), abs=0.6)
    assert top.y1 <= fig.bbox.height + 0.5  # inside the figure
    bare, bare_ax, _ = chart(False)
    bare_top = bare_ax.get_window_extent(_drawn(bare)).y1
    assert bare_top - axes_box.y1 >= top.height  # the margin reserved


def test_log_value_axis():
    # Review focus 4: on a log value axis the labels sit beyond the bar
    # ends and the headroom is solved in the axis's scale.
    fig, ax = _fig()
    values = [3.0, 40.0, 900.0, 12000.0]
    bars = ax.bar(np.arange(4), values, width=0.6)
    ax.set_yscale("log")
    ax.margins(y=0.02)  # too little room for the top label
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    low, high = ax.get_ylim()
    assert 0 < low < 3.0 and 12000.0 < high < 1e6
    assert _texts(texts) == ["3", "40", "900", "12,000"]
    _assert_outside(fig, texts, bars.patches)
    shown = _shown(fig, texts)
    axes_top = ax.get_window_extent(fig.canvas.get_renderer()).y1
    assert axes_top - max(b.y1 for _, b in shown) == pytest.approx(
        _offset_px(fig), abs=0.6
    )
    dm.simple_layout(fig)
    assert ax.get_ylim() == pytest.approx((low, high))

    # An inverted log axis grows its bottom (where the bars point) instead.
    ax.invert_yaxis()
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    axes_bottom = ax.get_window_extent(fig.canvas.get_renderer()).y0
    assert min(b.y0 for _, b in shown) - axes_bottom == pytest.approx(
        _offset_px(fig), abs=0.6
    )
    # Inverting is no view of the caller's: a taller figure regrows less.
    width, height = fig.get_size_inches()
    fig.set_size_inches(width, height * 1.6)
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    axes_bottom = ax.get_window_extent(fig.canvas.get_renderer()).y0
    assert min(b.y0 for _, b in shown) - axes_bottom == pytest.approx(
        _offset_px(fig), abs=0.6
    )


@pytest.mark.parametrize(
    ("limits", "shown"),
    [
        ((1.0, 100.0), True),  # the middle (31.6) in view, 500.5 is not
        ((100.0, 2000.0), False),  # 500.5 in view, the middle (31.6) is not
    ],
)
def test_centred_label_on_a_log_axis_shows_where_it_sits(limits, shown):
    # A centred label sits at the middle of its bar on screen: on a log
    # axis the geometric middle (31.6 for 1 to 1000), not the data mean.
    fig, ax = _fig()
    bars = ax.bar([0], [999.0], bottom=1.0, width=0.6)
    ax.set_yscale("log")
    ax.set_ylim(*limits)
    (label,) = dm.label_bars(ax, where="center")
    dm.simple_layout(fig)
    renderer = _drawn(fig)

    assert label.get_visible() is shown
    middle = float(ax.transData.transform((0, np.sqrt(1000.0)))[1])
    box = ax.get_window_extent(renderer)
    assert bool(box.y0 <= middle <= box.y1) is shown
    if shown:
        _assert_centred(fig, [label], bars.patches)


@pytest.mark.parametrize(
    ("limits", "shown"),
    [((0.0, 1000.0), True), ((0.0, 400.0), False), ((600.0, 1200.0), False)],
)
def test_centred_label_on_a_linear_axis_shows_while_its_middle_does(
    limits, shown
):
    fig, ax = _fig()
    bars = ax.bar([0], [999.0], bottom=1.0, width=0.6)
    ax.set_ylim(*limits)
    (label,) = dm.label_bars(ax, where="center")
    dm.simple_layout(fig)
    _drawn(fig)

    assert label.get_visible() is shown
    if shown:
        _assert_centred(fig, [label], bars.patches)


def test_repeat_simple_layout_idempotent():
    def state(fig, ax, texts):
        """Limits, Axes box (px) and label boxes (px); what is drawn."""
        renderer = _drawn(fig)
        limits = np.r_[ax.get_xlim(), ax.get_ylim()]
        boxes = np.ravel(
            [ax.get_window_extent(renderer).extents]
            + [t.get_window_extent(renderer).extents for t in texts]
        )
        return limits, boxes, [t.get_visible() for t in texts]

    def grouped():
        fig, ax, _ = _grouped()
        return fig, ax, dm.label_bars(ax)

    def horizontal():
        fig, ax, _ = _horizontal()
        return fig, ax, dm.label_bars(ax)

    def dense(crowded):
        fig, ax, _, texts = _dense(crowded=crowded)
        return fig, ax, texts

    builds = [
        grouped,
        horizontal,
        lambda: dense("rotate"),
        lambda: dense("skip"),
        lambda: dense("inside"),
    ]
    for build in builds:
        fig, ax, texts = build()
        dm.simple_layout(fig)
        first = state(fig, ax, texts)
        for _ in range(2):
            dm.simple_layout(fig)
        again = state(fig, ax, texts)
        # Within the layout's own convergence step (0.5 px); growing again
        # from the grown limit would add another margin each call.
        assert np.allclose(again[0], first[0], rtol=1e-4, atol=0)
        assert np.allclose(again[1], first[1], rtol=0, atol=0.5)
        assert again[2] == first[2]

    # Explicit later edits win over every layout.
    fig, ax, _bars, texts = _dense()
    texts[0].set_rotation(0)
    texts[1].set_horizontalalignment("left")
    texts[2].set_visible(False)
    texts[3].set_color("dc.red7")
    for _ in range(2):
        dm.simple_layout(fig)
    assert texts[0].get_rotation() == 0
    assert texts[1].get_horizontalalignment() == "left"
    assert not texts[2].get_visible()
    assert _hex(texts[3]) == mcolors.to_hex("dc.red7")
    assert texts[4].get_rotation() == 90

    # Room again (a wide figure): the labels turn back and the limit
    # returns to matplotlib's own: nothing compounds.
    fig.set_size_inches(14, fig.get_size_inches()[1])
    dm.simple_layout(fig)
    assert texts[0].get_rotation() == 0
    assert {t.get_rotation() for t in texts[4:]} == {0.0}
    assert ax.get_ylim()[1] / D_REV.max() == pytest.approx(
        AUTOSCALE_HEADROOM, abs=0.002
    )
    assert not texts[2].get_visible()
    assert all(t.get_visible() for t in texts[3:])

    # Labels moved inside come back out, in the text colour.
    fig, ax, _bars, texts = _dense(color="dc.blue9", crowded="inside")
    assert {t.where for t in texts} == {"inside"}
    fig.set_size_inches(14, fig.get_size_inches()[1])
    dm.simple_layout(fig)
    assert {t.where for t in texts} == {"outside"}
    assert {t.get_rotation() for t in texts} == {0.0}
    text_color = mcolors.to_hex(matplotlib.rcParams["text.color"])
    assert {_hex(t) for t in texts} == {text_color}

    # An edit made before any layout wins too.
    fig, ax = _fig()
    ax.bar(np.arange(24), D_REV, width=0.7)
    texts = dm.label_bars(ax)
    texts[0].set_rotation(45)
    texts[1].set_visible(False)
    dm.simple_layout(fig)
    assert texts[0].get_rotation() == 45
    assert not texts[1].get_visible()
    assert texts[2].get_rotation() == 90


def test_crowded_when_wider_than_the_pitch_less_1_5_pt():
    # Bars at a pitch set through the caller's x limits: a label wider than
    # the pitch less 1.5 pt is crowded, one narrower is not.
    fig, ax = _fig()
    ax.bar(np.arange(40), np.full(40, 33.0), width=0.4)
    texts = dm.label_bars(ax)
    width = texts[0].get_window_extent(_drawn(fig)).width  # not turned yet
    dm.simple_layout(fig)
    axes_width = ax.get_window_extent(_drawn(fig)).width
    gap = 1.5 * fig.dpi / 72.0
    for pitch, crowded in (
        (width + 0.5 * gap, True),
        (width + 1.5 * gap, False),
    ):
        ax.set_xlim(-0.5, -0.5 + axes_width / pitch)
        dm.simple_layout(fig)
        renderer = _drawn(fig)
        assert ax.get_window_extent(renderer).width == pytest.approx(
            axes_width, abs=0.01
        )
        assert (texts[0].get_rotation() == 90) is crowded


def test_crowding_reads_each_label_against_its_nearest_bar():
    # Two bars close together, the second one's label wider than their
    # distance: crowded, though the first label (narrow) fits and the
    # second has no bar to its right.
    fig, ax = _fig()
    ax.bar([0.0, 1.0], [1.0, 1000.0], width=0.3)
    texts = dm.label_bars(ax)
    renderer = _drawn(fig)
    narrow, wide = (t.get_window_extent(renderer).width for t in texts)
    dm.simple_layout(fig)
    axes_width = ax.get_window_extent(_drawn(fig)).width
    pitch = (narrow + wide) / 2 + 1.5 * fig.dpi / 72.0
    ax.set_xlim(-0.5, -0.5 + axes_width / pitch)
    dm.simple_layout(fig)
    assert [t.get_rotation() for t in texts] == [90.0, 90.0]

    # In a stack, the widest label at a position decides: the totals here.
    fig, ax = _fig()
    x = np.arange(30.0)
    ax.bar(x, np.full(30, 500.0), width=0.6)
    ax.bar(x, np.full(30, 500.0), bottom=500.0, width=0.6)
    texts = dm.label_bars(ax)
    renderer = _drawn(fig)
    segment = texts[0].get_window_extent(renderer).width  # "500"
    total = texts[-1].get_window_extent(renderer).width  # "1,000"
    assert total > segment
    dm.simple_layout(fig)
    axes_width = ax.get_window_extent(_drawn(fig)).width
    pitch = (segment + total) / 2 + 1.5 * fig.dpi / 72.0
    ax.set_xlim(-0.5, -0.5 + axes_width / pitch)
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in texts} == {90.0}


def test_crowded_lift_stays_in_view_and_off_overlaid_labels():
    # A kept label is lifted over a taller neighbour only up to the view
    # the caller set (1,500 runs past 1,400; "skip" hides its label).
    fig, ax = _fig()
    values = D_REV.copy()
    values[22], values[23] = 1500e6, 1000e6
    ax.bar(np.arange(24), values, width=0.7)
    ax.set_ylim(0, 1400e6)
    texts = dm.label_bars(ax, crowded="skip")
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    assert texts[23].get_visible()
    assert not texts[22].get_visible()
    assert texts[21].get_visible()  # 1,357 spans the 1,500 bar
    top = ax.get_window_extent(renderer).y1
    assert texts[21].get_window_extent(renderer).y0 == pytest.approx(
        top + _offset_px(fig), abs=0.6
    )

    # Bars overlaid on one base (actual inside target) are no stack: a
    # kept position keeps both labels, each at its own bar's end.
    fig, ax = _fig()
    x = np.arange(24)
    target = ax.bar(x, D_REV * 1.1, width=0.8, color="dc.gray3")
    actual = ax.bar(x, D_REV * 0.8, width=0.5, color="dc.blue6")
    texts = dm.label_bars(ax, crowded="skip")
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    assert _overlapping(shown) == []
    renderer = fig.canvas.get_renderer()
    for text, patch in zip(texts[24:], actual.patches, strict=True):
        if text.get_visible():
            assert text.get_window_extent(renderer).y0 == pytest.approx(
                patch.get_window_extent(renderer).y1 + _offset_px(fig), abs=0.6
            )
    assert [t.get_visible() for t in texts[:24]] == [
        t.get_visible() for t in texts[24:]
    ]
    assert target.patches  # drawn under the actual bars


def test_crowded_stack_keeps_outside_segments_on_their_own_bars():
    # where="outside" on a stack stays literal per segment (Task 3 ruling):
    # crowding never lifts a lower segment's label off its segment end; the
    # top segment's label, beyond the stack, clears taller neighbours.
    fig, ax = _fig()
    x = np.arange(24)
    base = ax.bar(x, D_REV * 0.6, width=0.7)
    ax.bar(x, D_REV * 0.4, bottom=D_REV * 0.6, width=0.7)
    texts = dm.label_bars(ax, where="outside", total=False, crowded="skip")
    dm.simple_layout(fig)
    renderer = _drawn(fig)
    for text, patch in zip(texts[:24], base.patches, strict=True):
        if text.get_visible():
            assert text.get_window_extent(renderer).y0 == pytest.approx(
                patch.get_window_extent(renderer).y1 + _offset_px(fig), abs=0.6
            )
    tops = _shown(fig, texts[24:])
    assert len(tops) == 12
    assert _on_bars(fig, tops) == []


def test_grown_span_is_the_least_room_for_every_label():
    from dartwork_mpl.annotation._bar_label_settle import grown_span

    # A 1000 px axes; anchors and needs in px, +1 up, -1 down.
    assert grown_span(0.0, 1000.0, [(900.0, 50.0, 1)]) is None  # fits
    wants = [(990.0, 30.0, 1), (950.0, 120.0, 1), (40.0, 60.0, -1)]
    low, high = grown_span(0.0, 1000.0, wants)
    span = high - low
    room = [
        ((high - a) if side > 0 else (a - low)) / span * 1000.0 - need
        for a, need, side in wants
    ]
    assert min(room) == pytest.approx(0.0, abs=1e-9)  # the least widening
    assert all(r >= -1e-9 for r in room)  # and every label fits
    assert low <= 0.0 and high >= 1000.0
    # The label that decides moves as the span grows: 995 decides at
    # today's span, 650 (a longer label) once the view has widened.
    wants = [(995.0, 40.0, 1), (650.0, 375.0, 1)]
    low, high = grown_span(0.0, 1000.0, wants)
    assert (low, high) == pytest.approx((0.0, 1040.0))
    # Labels as long as the axes cannot be helped.
    assert grown_span(0.0, 1000.0, [(990.0, 1000.0, 1)]) is None


def test_crowding_pitch_reads_every_bar_on_the_axes():
    # One call per container of interleaved bars: a call's own bars stand
    # two slots apart, but its labels are crowded by the other call's bars.
    fig, ax = _fig()
    x = np.arange(24)
    first = ax.bar(x[0::2], D_REV[0::2], width=0.7)
    second = ax.bar(x[1::2], D_REV[1::2], width=0.7)
    texts = dm.label_bars(ax, first) + dm.label_bars(ax, second)
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    assert len(shown) == 24
    assert {t.get_rotation() for t in texts} == {90.0}
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []

    # Bars left unlabelled crowd the labels all the same.
    fig, ax = _fig()
    labelled = ax.bar(x[0::2], D_REV[0::2], width=0.7)
    ax.bar(x[1::2], D_REV[1::2], width=0.7, color="dc.gray4")
    texts = dm.label_bars(ax, labelled)
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    assert {t.get_rotation() for t in texts} == {90.0}
    assert _on_bars(fig, shown) == []


@pytest.mark.parametrize(
    ("layout", "n"),
    [
        ("grouped barh", 14),  # rows thinner than the text, two per row
        ("grouped bar", 20),  # still overlapping once turned vertical
        ("interleaved bar", 48),  # one call per alternate bar
    ],
)
def test_overlap_selection_spans_separate_calls(layout, n):
    # One label_bars call per series: each call's own labels stand apart,
    # but the two calls' labels meet. The last overlap check sees every
    # call labelling the plot area, so none overlap and none sit on a bar.
    fig, ax = _fig()
    pos = np.arange(n, dtype=float)
    values = np.linspace(40.0, 12.0, n)
    if layout == "grouped barh":
        first = ax.barh(pos - 0.2, values, height=0.4)
        second = ax.barh(pos + 0.2, values, height=0.4)
        ax.invert_yaxis()
    elif layout == "grouped bar":
        first = ax.bar(pos - 0.2, values, width=0.4)
        second = ax.bar(pos + 0.2, values, width=0.4)
    else:
        first = ax.bar(pos[0::2], values[0::2], width=0.8)
        second = ax.bar(pos[1::2], values[1::2], width=0.8)
    texts = dm.label_bars(ax, first) + dm.label_bars(ax, second)
    dm.simple_layout(fig)
    shown = _shown(fig, texts)

    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []
    assert len(shown) >= len(texts) // 2  # every other position kept
    assert _inside_axes(ax, shown)
    visible = [t.get_visible() for t in texts]
    dm.simple_layout(fig)  # a repeat layout makes the same choice
    assert [t.get_visible() for t in texts] == visible


def test_separate_calls_that_fit_are_left_alone():
    # Two calls whose labels do not meet: nothing hidden, nothing turned.
    fig, ax = _fig()
    pos = np.arange(4, dtype=float)
    first = ax.bar(pos - 0.2, [3, 4, 5, 6], width=0.4)
    second = ax.bar(pos + 0.2, [2, 3, 4, 5], width=0.4)
    texts = dm.label_bars(ax, first) + dm.label_bars(ax, second)
    dm.simple_layout(fig)
    assert all(t.get_visible() for t in texts)
    assert {t.get_rotation() for t in texts} == {0.0}
    _assert_outside(fig, texts, [*first.patches, *second.patches])


# ------------------------------------------- overlapping series (9-2 B)
# The approved PoC figures of decision 9-2 (review page
# 2026-11-06-b3-followups, b3poc/2-overlapping-series/summary.json, B):
# same data, size and preset (report, 300 dpi).
PLAN_TEXTS = ["63", "88", "63", "75", "77", "86", "64", "74", "75"]
ACTUAL_TEXTS = ["65", "86", "65", "73", "73", "84", "63", "77", "75"]
POC_ROWS = [0, 2, 4, 5, 6, 8, 9, 10, 12]  # the rows summary.json lists
H_2024 = ["92", "75", "78", "90", "72", "83", "86"]
H_2024 += ["52", "43", "56", "55", "88", "91", "40"]
H_2025 = ["96", "82", "80", "97", "73", "87", "93"]
H_2025 += ["55", "46", "59", "61", "91", "99", "44"]


def _poc_grouped_bar(per_series=False):
    """14 weeks of Plan vs Actual, grouped bars, 9 cm (PoC figure b)."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"), dpi=300)
    rng = np.random.default_rng(3)
    x = np.arange(14)
    a = rng.uniform(60, 95, 14).round()
    b = (a + rng.uniform(-4, 4, 14).round()).clip(40, 99)
    plan = ax.bar(x - 0.2, a, 0.4, color="dc.gray4", label="Plan")
    actual = ax.bar(x + 0.2, b, 0.4, color="dc.orange3", label="Actual")
    ax.set_xticks(x, [f"W{i + 1}" for i in x])
    ax.set_ylabel("Output (units)")
    ax.legend(loc="upper left", ncols=2)
    if per_series:
        dm.label_bars(ax, plan)
        dm.label_bars(ax, actual)
    else:
        dm.label_bars(ax)
    return fig, ax, plan, actual


def _poc_grouped_barh(aspect=1.15):
    """14 regions, 2024 vs 2025, one call per series, thin rows (PoC a)."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", aspect), dpi=300)
    regions = ["Korea", "Japan", "China", "India", "Vietnam", "Indonesia"]
    regions += ["Australia", "Germany", "France", "UK", "Spain", "Brazil"]
    regions += ["Mexico", "Canada"]
    rng = np.random.default_rng(7)
    a = rng.integers(40, 96, 14)
    b = a + rng.integers(1, 9, 14)
    y = np.arange(14)
    first = ax.barh(y + 0.19, a, 0.38, color="dc.gray4", label="2024")
    second = ax.barh(y - 0.19, b, 0.38, color="dc.teal2", label="2025")
    ax.set_yticks(y, regions)
    ax.invert_yaxis()
    ax.set_xlabel("Revenue (USD M)")
    ax.legend(loc="lower right")
    dm.label_bars(ax, first)
    dm.label_bars(ax, second)
    return fig, ax, first, second


def _labels_of(ax, container):
    """The labels of ``container``'s bars, bar by bar."""
    found = [t for t in ax.texts if getattr(t, "container", None) is container]
    return sorted(found, key=lambda t: t.index)


def _layout_warnings(fig):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dm.simple_layout(fig)
    return [
        w for w in caught if "hidden where they would overlap" in str(w.message)
    ]


@pytest.mark.parametrize("per_series", [False, True])
def test_overlapping_series_alternate_by_bar_index(per_series):
    # PoC figure b, B: the first series keeps its labels on even bar
    # indices, the second on odd ones (7/14 each); neither vanishes.
    fig, ax, plan, actual = _poc_grouped_bar(per_series)
    assert _layout_warnings(fig) == []  # alternating is no loss to report
    plan_labels, actual_labels = _labels_of(ax, plan), _labels_of(ax, actual)
    assert [plan_labels[i].get_text() for i in POC_ROWS] == PLAN_TEXTS
    assert [actual_labels[i].get_text() for i in POC_ROWS] == ACTUAL_TEXTS
    _drawn(fig)
    assert [t.get_visible() for t in plan_labels] == [
        i % 2 == 0 for i in range(14)
    ]
    assert [t.get_visible() for t in actual_labels] == [
        i % 2 == 1 for i in range(14)
    ]
    shown = _shown(fig, plan_labels + actual_labels)
    assert len(shown) == 14
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []
    visible = [t.get_visible() for t in plan_labels + actual_labels]
    dm.simple_layout(fig)  # a repeat layout makes the same choice
    assert [t.get_visible() for t in plan_labels + actual_labels] == visible


def test_grouped_barh_alternates_across_calls():
    # PoC figure a (one label_bars call per series): the rows hold one
    # label each, so the series alternate as in figure b, 7/14 each, and
    # nothing is lost. Turns run in reading order: the top row first, and
    # in each row the bar read first (2025, drawn above 2024 on this
    # inverted axis). summary.json's B shows 2024 14/14 and 2025 0/14
    # here: the PoC numbered each call's container 0, so both calls looked
    # like one series; with the series told apart (PoC rerun, b3impl
    # report) the same candidate alternates too (review I5: the user sees
    # the three versions again).
    fig, ax, first, second = _poc_grouped_barh()
    assert _layout_warnings(fig) == []
    labels_2024, labels_2025 = _labels_of(ax, first), _labels_of(ax, second)
    assert _texts(labels_2024) == H_2024
    assert _texts(labels_2025) == H_2025
    _drawn(fig)
    assert [t.get_visible() for t in labels_2025] == [
        i % 2 == 0 for i in range(14)
    ]
    assert [t.get_visible() for t in labels_2024] == [
        i % 2 == 1 for i in range(14)
    ]
    shown = _shown(fig, labels_2024 + labels_2025)
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []
    assert {t.get_rotation() for t in labels_2024 + labels_2025} == {0.0}


def test_thin_rows_keep_the_series_mains_rule_keeps_and_warn():
    # The same rows at 9 x 7.2 cm: one label per row still meets the next
    # row's, so the turns would lose labels. Decision 12-2 A: the plain
    # overlap rule decides, the path main takes, so the series main keeps
    # stays. That rule walks from the top row down and keeps, in each row,
    # the label of the bar drawn uppermost on screen; no year order, no
    # series name. The layout says labels were hidden.
    fig, ax, first, second = _poc_grouped_barh(aspect=0.8)
    caught = _layout_warnings(fig)
    assert len(caught) == 1
    message = str(caught[0].message)
    assert "14 of 28" in message
    assert "taller figure" in message
    assert "crowded='skip'" in message
    labels_2024, labels_2025 = _labels_of(ax, first), _labels_of(ax, second)
    renderer = _drawn(fig)
    for pair in zip(labels_2024, labels_2025, strict=True):
        upper, lower = sorted(
            pair,
            key=lambda t: t.bar.get_window_extent(renderer).y0,
            reverse=True,
        )
        assert upper.get_visible()
        assert not lower.get_visible()
    shown = _shown(fig, labels_2024 + labels_2025)
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []
    assert {t.get_rotation() for t in labels_2024 + labels_2025} == {0.0}

    # A taller figure brings every label back, and the warning goes.
    fig.set_size_inches(fig.get_size_inches()[0], 9)
    assert _layout_warnings(fig) == []
    assert all(t.get_visible() for t in labels_2024 + labels_2025)


def test_hidden_label_warning_follows_the_rule():
    # One series of thin rows (the barh fallback): warned under the
    # default rule, silent under crowded="skip", which asks for it.
    values = np.linspace(40.0, 2.5, 40)
    for crowded, expected in (("rotate", 1), ("inside", 1), ("skip", 0)):
        fig, ax = _fig()
        ax.barh(np.arange(40), values, height=0.9)
        ax.invert_yaxis()
        texts = dm.label_bars(ax, crowded=crowded)
        caught = _layout_warnings(fig)
        assert len(caught) == expected, crowded
        hidden = sum(not t.get_visible() for t in texts)
        assert hidden > 0
        if expected:
            assert f"{hidden} of 40" in str(caught[0].message)

    # Labels that all fit: no warning.
    fig, ax, _ = _quarterly()
    dm.label_bars(ax)
    assert _layout_warnings(fig) == []


def test_three_series_take_turns():
    # Three series count down: the first at bar index 0, the last at 1,
    # the middle one at 2, ... (series -i mod 3), so the kept labels stand
    # at least a bar width short of the pitch apart; 8 of 24 each.
    fig, ax = _fig()
    x = np.arange(24, dtype=float)
    values = np.linspace(40.0, 12.0, 24)
    containers = [
        ax.bar(x + (j - 1) * 0.27, values * (1 - 0.1 * j), width=0.27)
        for j in range(3)
    ]
    dm.label_bars(ax)
    assert _layout_warnings(fig) == []
    for j, container in enumerate(containers):
        labels = _labels_of(ax, container)
        assert [t.get_visible() for t in labels] == [
            (j + i) % 3 == 0 for i in range(24)
        ], j
    shown = _shown(fig, list(ax.texts))
    assert _overlapping(shown) == []
    assert _on_bars(fig, shown) == []


def _review_grouped(
    n,
    groups,
    width,
    *,
    horizontal=False,
    values="scan",
    reverse=False,
    per_series=False,
):
    """The independent review's grouped charts (b3review scan / probes).

    ``values="scan"``: its seeded random values (scan_overlaps.py);
    ``"linear"``: falling values per series (probe_bars.py grouped_n).
    ``reverse`` labels the series in the reverse of their drawing order.
    """
    matplotlib.rcdefaults()
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"), dpi=150)
    x = np.arange(groups, dtype=float)
    w = 0.8 / n
    rng = np.random.default_rng(groups * 10 + n)
    containers = []
    for j in range(n):
        if values == "scan":
            data = rng.uniform(40, 99, groups).round()
        else:
            data = np.linspace(40.0, 12.0, groups) * (1 - 0.07 * j)
        pos = x + (j - (n - 1) / 2) * w
        draw = ax.barh if horizontal else ax.bar
        containers.append(draw(pos, data, w))
    if horizontal:
        ax.invert_yaxis()
    order = containers[::-1] if reverse else containers
    if per_series:
        for container in order:
            dm.label_bars(ax, container)
    else:
        dm.label_bars(ax, order)
    return fig, ax, containers


def _kept_per_series(fig, ax, containers):
    _drawn(fig)
    return [sum(t.get_visible() for t in _labels_of(ax, c)) for c in containers]


@pytest.mark.parametrize(
    ("n", "width", "on_main"),
    [
        (2, "7cm", [8, 8]),  # the turns would keep 12/1
        (3, "17cm", [12, 12, 12]),  # the turns would keep 16/8/8
    ],
)
def test_turns_never_keep_fewer_labels_than_the_plain_rule(n, width, on_main):
    # Review I1: where taking turns would lose labels for room or keep fewer
    # of them, the plain rule decides, as on main (bd2b61f8, same figures:
    # 8/8 and 12/12/12). Labels it hides are lost for room: warned.
    fig, ax, containers = _review_grouped(n, 24, width)
    caught = _layout_warnings(fig)
    assert _kept_per_series(fig, ax, containers) == on_main
    assert _overlapping(_shown(fig, list(ax.texts))) == []
    assert len(caught) == 1


@pytest.mark.parametrize(
    ("n", "width", "horizontal", "reverse", "per_series", "kept"),
    [
        (3, "12cm", False, True, False, [8, 8, 8]),
        (3, "12cm", False, True, True, [8, 8, 8]),
        (4, "12cm", False, True, False, [6, 6, 6, 6]),
        (3, "17cm", True, False, False, [8, 8, 8]),  # barh, inverted y
        (3, "17cm", True, True, True, [8, 8, 8]),
    ],
)
def test_series_turns_follow_the_screen_not_the_calls(
    n, width, horizontal, reverse, per_series, kept
):
    # Review I2: series are ranked in reading order on screen, so labelling
    # them in reverse, or barh on an inverted y axis, takes the same turns
    # (main: 0/0/24, 0/0/0/24 and 24/0/0 here) with no warning.
    fig, ax, containers = _review_grouped(
        n,
        24,
        width,
        horizontal=horizontal,
        values="linear",
        reverse=reverse,
        per_series=per_series,
    )
    assert _layout_warnings(fig) == []
    assert _kept_per_series(fig, ax, containers) == kept
    assert _overlapping(_shown(fig, list(ax.texts))) == []


def test_a_replacing_turn_stays_clear_of_the_label_kept_before():
    # Review M3: a label that takes the turn from the last kept one at its
    # bar index must also clear the one kept before that, even when it is
    # wider; otherwise the last kept one stays.
    from types import SimpleNamespace

    from dartwork_mpl.annotation._bar_label_settle import keep_apart

    def position(index, low, high):
        label = SimpleNamespace(index=index)
        return SimpleNamespace(labels=[label], low=low, high=high)

    wide = position(1, 40.0, 99.5)  # its turn first, reaches 99.5
    narrow = position(1, 70.0, 88.0)
    before = position(0, 100.0, 120.0)
    positions = [wide, narrow, before]  # in screen order
    turns = {id(wide): 0, id(narrow): 1, id(before): 0}
    assert keep_apart(positions, 2.0, turns) == [before, narrow]
    # With room for it, the wide label takes its turn.
    wide.high = 97.0
    assert keep_apart(positions, 2.0, turns) == [before, wide]
    # The plain rule keeps the last on screen, then what clears it.
    assert keep_apart(positions, 2.0) == [before, narrow]


def test_stacked_series_keep_the_overlap_rule():
    # Totals (stacks) are no plain series: the overlap rule hides from the
    # last position on screen, as before, so the left stacks lose theirs.
    fig, ax = _fig()
    x = np.arange(20, dtype=float)
    low, high = np.linspace(40, 12, 20), np.linspace(30, 20, 20)
    ax.bar(x - 0.2, low, width=0.4)
    left = ax.bar(x - 0.2, high, bottom=low, width=0.4)
    ax.bar(x + 0.2, low * 0.9, width=0.4)
    right = ax.bar(x + 0.2, high, bottom=low * 0.9, width=0.4)
    texts = dm.label_bars(ax, total="only")
    dm.simple_layout(fig)
    _drawn(fig)
    assert {t.kind for t in texts} == {"total"}
    assert [t.get_visible() for t in texts if t.bar in left.patches] == [
        False
    ] * 20
    assert [t.get_visible() for t in texts if t.bar in right.patches] == [
        True
    ] * 20


def _room_to_own_edge(fig, texts, along):
    """Each drawn label's distance (px) to its own Axes' far edge."""
    renderer = _drawn(fig)
    room = []
    for text in texts:
        if not text.get_visible():
            continue
        box = text.get_window_extent(renderer)
        edge = text.bar_axes.get_window_extent(renderer)
        room.append(edge.y1 - box.y1 if along == "y" else edge.x1 - box.x1)
    return room


def test_shared_value_axis_grows_for_each_panel():
    # Panels sharing a value axis sit at other places on screen: each
    # label's room is read in its own panel; the limit grows just enough.
    gap = None
    fig, (top, low) = plt.subplots(
        2, 1, sharey=True, figsize=dm.figsize("12cm", "standard")
    )
    top.bar(np.arange(6), [10.0, 12.0, 9.0, 11.0, 13.0, 10.0])
    low.bar(np.arange(6), [20.0, 25.0, 31.0, 28.0, 30.0, 27.0])
    texts = dm.label_bars(top) + dm.label_bars(low)
    dm.simple_layout(fig)
    gap = _offset_px(fig)
    room = _room_to_own_edge(fig, texts, "y")
    assert min(room) == pytest.approx(gap, abs=0.6)  # the least growth
    assert all(r >= gap - 0.6 for r in room)  # every label inside its panel

    fig, (left, right) = plt.subplots(
        1, 2, sharex=True, figsize=dm.figsize("12cm", "standard")
    )
    left.barh(np.arange(5), [20.0, 35.0, 40.0, 25.0, 30.0])
    right.barh(np.arange(5), [50.0, 70.0, 88.0, 60.0, 45.0])
    texts = dm.label_bars(left) + dm.label_bars(right)
    dm.simple_layout(fig)
    room = _room_to_own_edge(fig, texts, "x")
    assert min(room) == pytest.approx(gap, abs=0.6)
    assert all(r >= gap - 0.6 for r in room)
    assert left.get_xlim()[1] < 88.0 * 1.3

    fig, axes = plt.subplots(
        2, 2, sharey=True, figsize=dm.figsize("12cm", "standard")
    )
    texts = []
    for i, ax in enumerate(axes.flat):
        ax.bar(np.arange(4), np.array([10.0, 14.0, 12.0, 11.0]) * (1 + 0.6 * i))
        texts += dm.label_bars(ax)
    dm.simple_layout(fig)
    room = _room_to_own_edge(fig, texts, "y")
    assert min(room) == pytest.approx(gap, abs=0.6)
    assert all(r >= gap - 0.6 for r in room)

    # Panels of other heights: the label's room scales with its panel.
    fig, (small, large) = plt.subplots(
        2,
        1,
        sharey=True,
        figsize=dm.figsize("12cm", "standard"),
        gridspec_kw={"height_ratios": [1, 3]},
    )
    # The tallest bar in the larger panel, read against the smaller one.
    small.bar(np.arange(6), [10.0, 12.0, 9.0, 11.0, 13.0, 10.0])
    large.bar(np.arange(6), [20.0, 25.0, 31.0, 28.0, 30.0, 27.0])
    for ax in (small, large):
        ax.margins(y=0.02)  # too little room in either panel
    texts = dm.label_bars(small) + dm.label_bars(large)
    dm.simple_layout(fig)
    room = _room_to_own_edge(fig, texts, "y")
    assert min(room) == pytest.approx(gap, abs=0.6)
    assert all(r >= gap - 0.6 for r in room)


def test_bounds_set_while_autoscaling_are_kept():
    # set_ybound keeps autoscaling on; the view it sets is still explicit.
    fig, ax, _ = _quarterly()
    dm.label_bars(ax)
    ax.set_ybound(0, 60e9)
    dm.simple_layout(fig)
    assert ax.get_ylim() == (0.0, 60e9)
    assert ax.get_autoscaley_on()

    fig, ax, _ = _quarterly()
    dm.label_bars(ax)
    dm.simple_layout(fig)
    ax.set_ybound(0, 60e9)
    for _ in range(2):
        dm.simple_layout(fig)
    assert ax.get_ylim() == (0.0, 60e9)

    # New data after a layout: matplotlib autoscales anew, and the labels'
    # room grows from there again.
    fig, ax, _ = _horizontal()
    ax.margins(x=0)
    dm.label_bars(ax)
    dm.simple_layout(fig)
    grown = ax.get_xlim()
    longest = ax.barh([10], [40.0])
    texts = dm.label_bars(ax, longest)
    dm.simple_layout(fig)
    assert ax.get_xlim()[1] > max(grown[1], 40.0)
    right = ax.get_window_extent(_drawn(fig)).x1
    box = texts[0].get_window_extent(fig.canvas.get_renderer())
    assert right - box.x1 == pytest.approx(_offset_px(fig), abs=0.6)


def test_outside_segments_put_the_total_beyond_the_top_label():
    # where="outside" on a stack: the top segment's label sits at the
    # stack's end, and the total goes 3 pt beyond that label.
    fig, ax = _fig()
    x = np.arange(6)
    base = np.array([14.0, 15.0, 16.0, 16.0, 18.0, 19.0])
    ax.bar(x, base, width=0.6)
    ax.bar(x, [6.0, 7.0, 9.0, 11.0, 13.0, 15.0], bottom=base, width=0.6)
    texts = dm.label_bars(ax, where="outside")
    dm.simple_layout(fig)
    shown = _shown(fig, texts)
    assert len(shown) == 18
    assert _overlapping(shown) == []
    renderer = fig.canvas.get_renderer()
    tops = texts[6:12]
    totals = [t for t in texts if t.kind == "total"]
    for top_label, total in zip(tops, totals, strict=True):
        assert total.get_window_extent(renderer).y0 == pytest.approx(
            top_label.get_window_extent(renderer).y1 + _offset_px(fig), abs=0.6
        )
    assert _inside_axes(ax, shown)

    # The top label hidden by the caller: the total comes back to the end.
    tops[0].set_visible(False)
    renderer = _drawn(fig)
    end = ax.transData.transform((0, 20.0))[1]
    assert totals[0].get_window_extent(renderer).y0 == pytest.approx(
        end + _offset_px(fig), abs=0.6
    )


def test_validate_figure_clean_on_six_charts():
    def q():
        fig, ax, _ = _quarterly()
        return fig, ax, dm.label_bars(ax)

    def g():
        fig, ax, _ = _grouped()
        texts = dm.label_bars(ax)
        dm.place_legend(ax)
        return fig, ax, texts

    def s():
        fig, ax, _ = _stacked()
        texts = dm.label_bars(ax)
        dm.place_legend(ax)
        return fig, ax, texts

    def h():
        fig, ax, _ = _horizontal()
        return fig, ax, dm.label_bars(ax)

    def d():
        fig, ax = _fig()
        x = np.arange(24)
        ax.bar(x, D_REV, width=0.7, color="dc.blue6")
        ax.set_xticks(x[::3], D_TICKS[::3])
        dm.axis_unit(
            ax,
            "y",
            label="Revenue (USD {unit})",
            ladder="finance",
            scale="whole",
        )
        return fig, ax, dm.label_bars(ax)

    def t():
        fig, ax, _, texts = _twin_chart()
        dm.place_legend(ax)
        return fig, ax, texts

    # The one finding allowed is about series colours, not labels: g's
    # default palette draws a grayscale INFO note, as in the approved
    # capture (a palette matter outside B3). Every other finding counts.
    palette_only = "GRAYSCALE_SAFETY"
    for name, build in {"q": q, "g": g, "s": s, "h": h, "d": d, "t": t}.items():
        fig, ax, texts = build()
        dm.simple_layout(fig)
        found = dm.validate_figure(fig, quiet=True)
        label_findings = [
            w.check_id for w in found if w.check_id != palette_only
        ]
        assert label_findings == [], name
        palette = [w for w in found if w.check_id == palette_only]
        assert len(palette) == (1 if name == "g" else 0), name
        assert all(str(w.severity).endswith("INFO") for w in palette), name
        shown = _shown(fig, texts)
        assert len(shown) == len(texts), name
        assert _overlapping(shown) == [], name
        assert _on_bars(fig, shown) == [], name
        assert _inside_axes(ax, shown), name


# ---------------------------------------------------------------- lifecycle
def test_label_bars_again_replaces_earlier_labels():
    fig, ax, bars = _quarterly()
    first = dm.label_bars(ax)
    second = dm.label_bars(ax, fmt="${}B")
    assert not any(t in ax.texts for t in first)
    assert all(t.axes is None for t in first)
    assert [t for t in ax.texts if t in second] == second
    assert len(ax.texts) == len(second)
    (family,) = ax._dm_bar_label_families
    assert family.texts == second
    dm.simple_layout(fig)
    assert second[-1].get_text() == "$33.0B"

    # Only the containers the later call names change hands.
    fig, ax, groups = _grouped()
    every = dm.label_bars(ax)
    again = dm.label_bars(ax, groups[1], color="series")
    assert len(ax.texts) == 15
    old, new = ax._dm_bar_label_families
    assert old.containers == [groups[0], groups[2]]
    assert len(old.texts) == 10 and new.texts == again
    assert all(t.axes is None for t in every[5:10])
    dm.simple_layout(fig)
    assert _texts(old.texts) == G_A[:5] + G_A[10:]

    # A stack's totals go with any of its containers, the base included
    # (the totals sit on the top container's bars).
    fig, ax, containers = _stacked()
    dm.label_bars(ax)
    base = dm.label_bars(ax, containers[0])
    (old, new) = ax._dm_bar_label_families
    assert {t.kind for t in old.texts} == {"segment"}
    assert {t.container for t in old.texts} == set(containers[1:])
    assert {t.kind for t in new.texts} == {"edge"} and new.texts == base
    assert len(ax.texts) == 18


def test_cleared_axes_drop_their_labels():
    fig, ax, _ = _quarterly()
    dm.label_bars(ax)
    ax.cla()
    dm.simple_layout(fig)
    assert ax._dm_bar_label_families == []
    bars = ax.bar(np.arange(3), [1.0, 2.0, 3.0])
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == ["1", "2", "3"]
    _assert_outside(fig, texts, bars.patches)

    # Bars cleared under labels kept on a twin: the labels go too.
    fig, ax, _bars, texts = _twin_chart()
    ax2 = texts[0].axes
    ax.cla()
    dm.simple_layout(fig)
    assert not any(t in ax2.texts for t in texts)
    assert ax._dm_bar_label_families == []


def test_twin_created_later_rehosts_labels():
    # Labelled before the twin existed: the layout moves the same labels
    # onto the twin drawn last, explicit edits and all.
    fig, ax, bars = _quarterly()
    texts = dm.label_bars(ax)
    texts[0].set_color("dc.red7")
    texts[1].set_text("Low")
    ax2 = ax.twinx()
    ax2.plot(np.arange(12), T_YOY, color="dc.orange6")
    dm.simple_layout(fig)
    assert all(t.axes is ax2 for t in texts)
    assert all(t in ax2.texts for t in texts)
    assert not any(t in ax.texts for t in texts)
    assert _hex(texts[0]) == mcolors.to_hex("dc.red7")
    assert texts[1].get_text() == "Low"
    assert _texts(texts[2:]) == Q_A[2:]
    _assert_outside(fig, texts, bars.patches)
    shown = _shown(fig, texts)
    assert _inside_axes(ax, shown)

    # The bars' axes raised on top again: the labels move back.
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    dm.simple_layout(fig)
    assert all(t.axes is ax for t in texts)
    _assert_outside(fig, texts, bars.patches)
