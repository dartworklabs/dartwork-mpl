"""dm.label_bars: value labels on bars that read like their axis (B3).

Downstream code hand-wrote these labels in 418 files: ten font sizes,
``"bold"`` against the ``dm.fw(1)`` rule, formats that repeat the axis unit.
The helper settles the look, the unit, the decimals and the side. The
expected texts are the approved captures' (review page
``2026-11-06-b3-labels``; ``b3/img/report.json`` entries ``q-A``, ``g-A``,
``g-A-series``, ``h-A``), drawn from the same data as ``b3/scripts/charts.py``.
The observed values are read after a real canvas draw.
"""

from __future__ import annotations

import io

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest
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
