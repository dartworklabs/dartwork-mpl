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
import re
import shutil
import subprocess

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
from tests.support.mpl_observe import drawn_renderer

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


pytestmark = pytest.mark.usefixtures("report_preset")


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


def _offset_px(fig):
    return OFFSET_PT * fig.dpi / 72.0


def _assert_outside(fig, texts, patches, orientation="vertical"):
    """Each label sits 3 pt beyond its bar's end, centred on the bar."""
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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


FIXED_UNIT = {
    # name: (install, values, labels)
    "millions-1": (
        lambda ax: dm.format_axis_millions(ax, decimals=1),
        [1.25e6, 2.05e6, -0.8e6, 0.0, 3.4e6],
        ["1.25M", "2.05M", f"{MINUS}0.80M", "0", "3.40M"],
    ),
    "billions-2": (
        lambda ax: dm.format_axis_billions(ax, decimals=2),
        [12.4e9, 8.0e9, -3.5e9, 0.0, 15.0e9],
        ["12.4B", "8.0B", f"{MINUS}3.5B", "0", "15.0B"],
    ),
    "currency": (
        lambda ax: dm.format_axis_currency(ax),
        [1250.0, 2050.0, -800.0, 0.0, 3400.0],
        ["$1,250", "$2,050", f"{MINUS}$800", "$0", "$3,400"],
    ),
    "currency-small": (
        lambda ax: dm.format_axis_currency(ax),
        [4.25, 3.8, -1.5, 0.0, 6.1],
        ["$4.25", "$3.80", f"{MINUS}$1.50", "$0", "$6.10"],
    ),
    "currency-suffix-2": (
        lambda ax: dm.format_axis_currency(
            ax, symbol="€", position="suffix", decimals=2
        ),
        [12.5, 20.55, -8.0, 0.0, 34.0],
        ["12.5€", "20.6€", f"{MINUS}8.0€", "0€", "34.0€"],
    ),
}


def _affixes(text):
    """The sign and symbols around the digits: ``("-$", "")`` for -$800."""
    found = re.fullmatch(r"(\D*)[\d,.]+(\D*)", text.replace(MINUS, "-"))
    assert found is not None, text
    return found.groups()


@pytest.mark.parametrize("name", list(FIXED_UNIT))
def test_fixed_unit_formatters_print_like_their_ticks(name):
    """Ticks written each alone in one fixed unit (``decimals=n`` of
    millions / billions, ``format_axis_currency``) give the labels that
    unit, the currency on its side, the sign before both and the ticks'
    zero rule (bare ``0``; ``$0``, ``0€``). The decimals are the label
    rule's: the ticks' fixed count sizes tick text only."""
    install, values, expected = FIXED_UNIT[name]
    fig, ax, _ = _plain(values)
    install(ax)
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == expected
    # Sign, currency and unit sit where a tick at that value puts them.
    tick = ax.yaxis.get_major_formatter()
    assert [_affixes(t) for t in expected] == [
        _affixes(tick(v)) for v in values
    ]


def test_fixed_unit_labels_follow_and_explicit_wins():
    values = [1.25e6, 2.05e6, -0.8e6, 0.0, 3.4e6]

    # A formatter set after the call: the labels follow at the draw.
    fig, ax, _ = _plain(values)
    texts = dm.label_bars(ax)
    assert _texts(texts)[0] == "1,250,000"
    dm.format_axis_millions(ax, decimals=1)
    fig.canvas.draw()
    assert _texts(texts)[0] == "1.25M"

    # The same labels as under the axis-wide millions (decimals=None).
    fig, ax, _ = _plain(values)
    dm.format_axis_millions(ax)
    texts = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert _texts(texts) == FIXED_UNIT["millions-1"][2]

    # decimals= fixes the count, the unit stays the ticks'.
    fig, ax, _ = _plain(values)
    dm.format_axis_millions(ax, decimals=1)
    texts = dm.label_bars(ax, decimals=2)
    dm.simple_layout(fig)
    assert _texts(texts) == ["1.25M", "2.05M", f"{MINUS}0.80M", "0.00", "3.40M"]

    # fmt= writes the text: a template around the number in the tick unit,
    # a callable that gets that number; no tick suffix or currency added.
    fig, ax, _ = _plain(values)
    dm.format_axis_millions(ax, decimals=1)
    texts = dm.label_bars(ax, fmt="{} mn")
    assert _texts(texts)[:3] == ["1.25 mn", "2.05 mn", f"{MINUS}0.80 mn"]
    seen: list[float] = []
    dm.label_bars(ax, fmt=lambda v: seen.append(v) or "x")
    assert seen[:5] == pytest.approx([1.25, 2.05, -0.8, 0.0, 3.4])

    fig, ax, _ = _plain([1250.0, -800.0, 0.0])
    dm.format_axis_currency(ax)
    texts = dm.label_bars(ax, fmt="USD {}")
    assert _texts(texts) == ["USD 1,250", f"USD {MINUS}800", "USD 0"]


def _millions_1(ax):
    dm.format_axis_millions(ax, decimals=1)


def _billions_bn_1(ax):
    dm.format_axis_billions(ax, suffix="bn", decimals=1)


def _euro_suffix_2(ax):
    dm.format_axis_currency(ax, symbol="€", position="suffix", decimals=2)


@pytest.mark.parametrize(
    ("install", "values", "asked", "expected"),
    [
        # decimals= with fewer and more places than the ticks' fixed count.
        (
            _millions_1,
            [1.25e6, -0.04e6, 0.0],
            {"decimals": 0},
            ["1M", "0", "0"],
        ),
        (
            _millions_1,
            [1.25e6, -0.04e6, 0.0],
            {"decimals": 3},
            ["1.250M", f"{MINUS}0.040M", "0.000"],
        ),
        (
            _billions_bn_1,
            [12.4e9, -3.6e9, 0.0],
            {"decimals": 0},
            ["12bn", f"{MINUS}4bn", "0"],
        ),
        (
            dm.format_axis_currency,
            [4.25, -0.3, 0.0],
            {"decimals": 2},
            ["$4.25", f"{MINUS}$0.30", "$0.00"],
        ),
        (
            _euro_suffix_2,
            [12.4, -0.04, 0.0],
            {"decimals": 0},
            ["12€", "0€", "0€"],
        ),
        (
            _euro_suffix_2,
            [12.4, -0.04, 0.0],
            {"decimals": 3},
            ["12.400€", f"{MINUS}0.040€", "0.000€"],
        ),
        # A format spec in fmt formats the value in the tick unit itself.
        (
            _millions_1,
            [1.25e6, -0.04e6, 0.0],
            {"fmt": "{:.3f} mn"},
            ["1.250 mn", f"{MINUS}0.040 mn", "0.000 mn"],
        ),
    ],
    ids=[
        "millions-1-asked-0",
        "millions-1-asked-3",
        "billions-bn-1-asked-0",
        "currency-0-asked-2",
        "euro-2-asked-0",
        "euro-2-asked-3",
        "millions-1-fmt-spec",
    ],
)
def test_asked_precision_wins_over_the_ticks(install, values, asked, expected):
    """The precision the caller gives the labels wins over the formatter's
    fixed count, fewer places or more: the formatter's count is only a
    default when nothing is asked. The unit, currency side and zero rule
    stay the ticks'."""
    fig, ax, _ = _plain(values)
    install(ax)
    texts = dm.label_bars(ax, **asked)
    dm.simple_layout(fig)
    assert _texts(texts) == expected


# Boundary charts: zero, negatives, small non-zero values that round to
# zero, currency on either side, the user's suffix (``bn``, ``백만``, ``""``).
BOUNDARY = {
    # name: (preset, install, values)
    "millions-1-small": (
        "report",
        _millions_1,
        [1.25e6, 0.03e6, -0.04e6, 0.0, -0.8e6, 3.4e6],
    ),
    "millions-1-wide": (
        "report",
        _millions_1,
        [12.5e6, 0.03e6, -0.04e6, 0.0, -2.6e6, 8.1e6],
    ),
    "billions-bn-1": (
        "report",
        _billions_bn_1,
        [12.4e9, 0.02e9, -0.03e9, 0.0, -3.5e9, 8.0e9],
    ),
    "millions-baekman-1": (
        "report-kr",
        lambda ax: dm.format_axis_millions(ax, suffix="백만", decimals=1),
        [2.4e6, 0.03e6, -0.04e6, 0.0, -1.1e6, 5.6e6],
    ),
    "millions-empty-1": (
        "report",
        lambda ax: dm.format_axis_millions(ax, suffix="", decimals=1),
        [1.25e6, 0.03e6, -0.04e6, 0.0, -0.8e6, 3.4e6],
    ),
    "currency-prefix-0": (
        "report",
        dm.format_axis_currency,
        [4.25, 0.4, -0.3, 0.0, -1.5, 6.1],
    ),
    "currency-suffix-2": (
        "report",
        _euro_suffix_2,
        [12.5, 0.03, -0.04, 0.0, -8.0, 34.0],
    ),
}
# Nothing asked: the label rule in the tick unit (three significant digits
# on the largest value), so a small value shows while the largest leaves
# room for it (0.03M beside 3.4M) and reads 0 when it does not (beside
# 12.5M, or €0.03 beside €34).
BOUNDARY_DEFAULT = {
    "millions-1-small": [
        "1.25M",
        "0.03M",
        f"{MINUS}0.04M",
        "0",
        f"{MINUS}0.80M",
        "3.40M",
    ],
    "millions-1-wide": ["12.5M", "0", "0", "0", f"{MINUS}2.6M", "8.1M"],
    "billions-bn-1": ["12.4bn", "0", "0", "0", f"{MINUS}3.5bn", "8.0bn"],
    "millions-baekman-1": [
        "2.40백만",
        "0.03백만",
        f"{MINUS}0.04백만",
        "0",
        f"{MINUS}1.10백만",
        "5.60백만",
    ],
    "millions-empty-1": [
        "1.25",
        "0.03",
        f"{MINUS}0.04",
        "0",
        f"{MINUS}0.80",
        "3.40",
    ],
    "currency-prefix-0": [
        "$4.25",
        "$0.40",
        f"{MINUS}$0.30",
        "$0",
        f"{MINUS}$1.50",
        "$6.10",
    ],
    "currency-suffix-2": ["12.5€", "0€", "0€", "0€", f"{MINUS}8.0€", "34.0€"],
}
# label_bars(decimals=2): the asked count wins over the ticks'.
BOUNDARY_ASKED = {
    "millions-1-small": [
        "1.25M",
        "0.03M",
        f"{MINUS}0.04M",
        "0.00",
        f"{MINUS}0.80M",
        "3.40M",
    ],
    "millions-1-wide": [
        "12.50M",
        "0.03M",
        f"{MINUS}0.04M",
        "0.00",
        f"{MINUS}2.60M",
        "8.10M",
    ],
    "billions-bn-1": [
        "12.40bn",
        "0.02bn",
        f"{MINUS}0.03bn",
        "0.00",
        f"{MINUS}3.50bn",
        "8.00bn",
    ],
    "millions-baekman-1": [
        "2.40백만",
        "0.03백만",
        f"{MINUS}0.04백만",
        "0.00",
        f"{MINUS}1.10백만",
        "5.60백만",
    ],
    "millions-empty-1": [
        "1.25",
        "0.03",
        f"{MINUS}0.04",
        "0.00",
        f"{MINUS}0.80",
        "3.40",
    ],
    "currency-prefix-0": [
        "$4.25",
        "$0.40",
        f"{MINUS}$0.30",
        "$0.00",
        f"{MINUS}$1.50",
        "$6.10",
    ],
    "currency-suffix-2": [
        "12.50€",
        "0.03€",
        f"{MINUS}0.04€",
        "0.00€",
        f"{MINUS}8.00€",
        "34.00€",
    ],
}


@pytest.mark.parametrize("name", list(BOUNDARY))
def test_fixed_unit_boundaries_default_and_asked(name):
    preset, install, values = BOUNDARY[name]
    dm.style.use(preset)
    for asked, expected in (
        ({}, BOUNDARY_DEFAULT[name]),
        ({"decimals": 2}, BOUNDARY_ASKED[name]),
    ):
        fig, ax, _ = _plain(values)
        install(ax)
        texts = dm.label_bars(ax, **asked)
        dm.simple_layout(fig)
        assert _texts(texts) == expected, asked


# Bar shapes on the fixed-unit paths (the 2026-11-07 review's measured
# texts): barh reads the x formatter, axis="both", log value axes, and
# NaN / infinite bars (no label; the rest unchanged).
SHAPED = {
    # name: (values, install, shape, default, decimals=2)
    "barh-millions-1-x": (
        [1.25e6, -0.8e6, 0.0, 3.4e6],
        lambda ax: dm.format_axis_millions(ax, axis="x", decimals=1),
        "barh",
        ["1.25M", f"{MINUS}0.80M", "0", "3.40M"],
        ["1.25M", f"{MINUS}0.80M", "0.00", "3.40M"],
    ),
    "barh-currency-x": (
        [1250.0, -800.0, 0.0],
        lambda ax: dm.format_axis_currency(ax, axis="x"),
        "barh",
        ["$1,250", f"{MINUS}$800", "$0"],
        ["$1,250.00", f"{MINUS}$800.00", "$0.00"],
    ),
    # The value axis of barh is x: a formatter on y alone leaves it plain.
    "barh-currency-y-only": (
        [1250.0, -800.0, 0.0],
        lambda ax: dm.format_axis_currency(ax, axis="y"),
        "barh",
        ["1,250", f"{MINUS}800", "0"],
        ["1,250.00", f"{MINUS}800.00", "0.00"],
    ),
    "bar-currency-both": (
        [1250.0, -800.0, 0.0],
        lambda ax: dm.format_axis_currency(ax, axis="both"),
        "bar",
        ["$1,250", f"{MINUS}$800", "$0"],
        ["$1,250.00", f"{MINUS}$800.00", "$0.00"],
    ),
    "barh-millions-1-both": (
        [1.25e6, -0.8e6, 0.0],
        lambda ax: dm.format_axis_millions(ax, axis="both", decimals=1),
        "barh",
        ["1.25M", f"{MINUS}0.80M", "0"],
        ["1.25M", f"{MINUS}0.80M", "0.00"],
    ),
    # One count per call on a log axis: 1e4 reads 0 beside 4.5e7 (the
    # spec's round-to-zero rule; a log-axis rule is a follow-up).
    "log-millions-1": (
        [1e4, 2e5, 3.4e6, 4.5e7],
        _millions_1,
        "log",
        ["0", "0.2M", "3.4M", "45.0M"],
        ["0.01M", "0.20M", "3.40M", "45.00M"],
    ),
    "log-currency": (
        [3.0, 45.0, 1250.0, 98000.0],
        dm.format_axis_currency,
        "log",
        ["$3", "$45", "$1,250", "$98,000"],
        ["$3.00", "$45.00", "$1,250.00", "$98,000.00"],
    ),
    "nan-millions-1": (
        [1.25e6, np.nan, -0.8e6, 3.4e6],
        _millions_1,
        "bar",
        ["1.25M", f"{MINUS}0.80M", "3.40M"],
        ["1.25M", f"{MINUS}0.80M", "3.40M"],
    ),
    "nan-currency": (
        [1250.0, np.nan, -800.0],
        dm.format_axis_currency,
        "bar",
        ["$1,250", f"{MINUS}$800"],
        ["$1,250.00", f"{MINUS}$800.00"],
    ),
    "inf-millions-1": (
        [1.25e6, np.inf, 3.4e6],
        _millions_1,
        "bar",
        ["1.25M", "3.40M"],
        ["1.25M", "3.40M"],
    ),
    "inf-currency": (
        [1250.0, -np.inf, 800.0],
        dm.format_axis_currency,
        "bar",
        ["$1,250", "$800"],
        ["$1,250.00", "$800.00"],
    ),
}


# matplotlib's own transform warns on an infinite bar, before any label.
@pytest.mark.filterwarnings(
    "ignore:invalid value encountered in dot:RuntimeWarning"
)
@pytest.mark.parametrize("name", list(SHAPED))
def test_fixed_unit_labels_on_other_bar_shapes(name):
    values, install, shape, default, asked = SHAPED[name]
    for keywords, expected in (({}, default), ({"decimals": 2}, asked)):
        fig, ax = _fig()
        draw = ax.barh if shape == "barh" else ax.bar
        draw(np.arange(len(values)), values)
        if shape == "log":
            ax.set_yscale("log")
        install(ax)
        texts = dm.label_bars(ax, **keywords)
        dm.simple_layout(fig)
        assert _texts(texts) == expected, keywords


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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    drawn_renderer(fig)
    shown = [t for t in labels if t.get_visible()]
    assert shown
    assert all(t.where == "outside" and not t.on_bar for t in shown)
    assert {_hex(t) for t in shown} == {"#000000"}
    _assert_readable(fig, labels, tmp_path)


def test_error_bars_push_labels_past_caps():
    fig, ax = _fig()
    bars = ax.bar([0, 1], [4.0, -3.0], yerr=[1.0, 0.5], capsize=2)
    texts = dm.label_bars(ax)
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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


def test_bar_past_a_user_limit_has_no_label_off_the_axes():
    # The reviewer's probe: a bar of 40 under a limit of 5 the user set.
    def chart(label):
        fig, ax, _ = _plain([3.0, 40.0, 2.0])
        ax.set_ylim(0, 5)
        return fig, ax, (dm.label_bars(ax) if label else [])

    fig, ax, texts = chart(True)
    renderer = drawn_renderer(fig)
    assert [t.get_visible() for t in texts] == [True, False, True]
    width, height = fig.canvas.get_width_height()
    for text in texts:
        if text.get_visible():
            box = text.get_window_extent(renderer)
            assert box.y0 >= 0
            assert box.y1 <= height
    assert _tight_shape(fig) == _tight_shape(chart(False)[0])

    # An error bar past the limit pushes a visible label only to the edge.
    fig, ax = _fig()
    ax.bar([0, 1], [4.0, 2.0], yerr=[3.0, 0.5])
    ax.set_ylim(0, 5)
    texts = dm.label_bars(ax)
    renderer = drawn_renderer(fig)
    top = ax.get_window_extent(renderer).y1
    assert texts[0].get_visible()
    assert texts[0].get_window_extent(renderer).y0 == pytest.approx(
        top + _offset_px(fig), abs=0.6
    )


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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)

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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
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
    """Labels off their bar (``"outside"``) that cover a bar anyway."""
    renderer = fig.canvas.get_renderer()
    bars = [
        patch.get_window_extent(renderer)
        for axes in fig.axes
        for patch in axes.patches
        if patch.get_visible()
    ]
    return [
        label.get_text()
        for label, box in shown
        if label.where == "outside" and any(_cover(box, b, tol) for b in bars)
    ]


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
    renderer = drawn_renderer(fig)
    top = texts[-1].get_window_extent(renderer)
    axes_box = ax.get_window_extent(renderer)
    assert texts[-1].get_visible()
    assert top.y0 == pytest.approx(axes_box.y1 + _offset_px(fig), abs=0.6)
    assert top.y1 <= fig.bbox.height + 0.5  # inside the figure
    bare, bare_ax, _ = chart(False)
    bare_top = bare_ax.get_window_extent(drawn_renderer(bare)).y1
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
    renderer = drawn_renderer(fig)

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
    drawn_renderer(fig)

    assert label.get_visible() is shown
    if shown:
        _assert_centred(fig, [label], bars.patches)


def test_repeat_simple_layout_idempotent():
    def state(fig, ax, texts):
        """Limits, Axes box (px) and label boxes (px); what is drawn."""
        renderer = drawn_renderer(fig)
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
    width = (
        texts[0].get_window_extent(drawn_renderer(fig)).width
    )  # not turned yet
    dm.simple_layout(fig)
    axes_width = ax.get_window_extent(drawn_renderer(fig)).width
    gap = 1.5 * fig.dpi / 72.0
    for pitch, crowded in (
        (width + 0.5 * gap, True),
        (width + 1.5 * gap, False),
    ):
        ax.set_xlim(-0.5, -0.5 + axes_width / pitch)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
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
    renderer = drawn_renderer(fig)
    narrow, wide = (t.get_window_extent(renderer).width for t in texts)
    dm.simple_layout(fig)
    axes_width = ax.get_window_extent(drawn_renderer(fig)).width
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
    renderer = drawn_renderer(fig)
    segment = texts[0].get_window_extent(renderer).width  # "500"
    total = texts[-1].get_window_extent(renderer).width  # "1,000"
    assert total > segment
    dm.simple_layout(fig)
    axes_width = ax.get_window_extent(drawn_renderer(fig)).width
    pitch = (segment + total) / 2 + 1.5 * fig.dpi / 72.0
    ax.set_xlim(-0.5, -0.5 + axes_width / pitch)
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in texts} == {90.0}


def test_crowded_lift_stays_in_view_and_off_overlaid_labels():
    # A kept label is lifted over a taller neighbour only up to the view
    # the caller set (1,432 runs past 1,400: its own label is gone).
    fig, ax = _fig()
    ax.bar(np.arange(24), D_REV, width=0.7)
    ax.set_ylim(0, 1400e6)
    texts = dm.label_bars(ax, crowded="skip")
    dm.simple_layout(fig)
    renderer = drawn_renderer(fig)
    assert not texts[23].get_visible()
    assert texts[22].get_visible()  # 1,337 spans the 1,432 bar
    top = ax.get_window_extent(renderer).y1
    assert texts[22].get_window_extent(renderer).y0 == pytest.approx(
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
    renderer = drawn_renderer(fig)
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


def _room_to_own_edge(fig, texts, along):
    """Each drawn label's distance (px) to its own Axes' far edge."""
    renderer = drawn_renderer(fig)
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
    right = ax.get_window_extent(drawn_renderer(fig)).x1
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
    renderer = drawn_renderer(fig)
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
