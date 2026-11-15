"""Realistic charts through the public surface: the labels as drawn."""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm


@pytest.fixture(autouse=True)
def _report():
    dm.style.use("report")
    yield
    plt.close("all")


def _boxes(fig, texts):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    return [t.get_window_extent(renderer) for t in texts]


def test_bar_labels_print_like_the_ticks_above_the_bars_with_headroom():
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    bars = ax.bar(list("ABCDE"), [42.5, 37.1, 51.8, 29.4, 46.0])
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    assert [t.get_text() for t in labels] == [
        "42.5",
        "37.1",
        "51.8",
        "29.4",
        "46.0",
    ]
    plot = ax.get_window_extent()
    for box, bar in zip(_boxes(fig, labels), bars, strict=True):
        assert box.y0 > bar.get_window_extent().y1  # beyond the end
        assert box.y1 < plot.y1  # the value axis grew to hold it
    ylim = ax.get_ylim()
    dm.simple_layout(fig)
    assert ax.get_ylim() == pytest.approx(ylim)  # nothing compounds


def test_negative_bars_and_barh_put_labels_past_the_end():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    ax.bar(list("AB"), [12, -7])
    bx.barh(list("AB"), [120, 135])
    up, down = dm.label_bars(ax)
    right = dm.label_bars(bx)
    dm.simple_layout(fig)
    assert down.get_text() == "\N{MINUS SIGN}7"
    a, b = _boxes(fig, [up, down])
    assert b.y1 < ax.transData.transform((0, -7))[1] < a.y0
    for box, bar in zip(_boxes(fig, right), bx.patches, strict=True):
        assert box.x0 > bar.get_window_extent().x1


@pytest.mark.parametrize(
    ("format_axis", "values", "texts"),
    [
        (
            dm.format_axis_millions,
            [1.25e6, 12.5e6, 0.03e6],
            ["1.2M", "12.5M", "<0.1M"],
        ),
        (
            dm.format_axis_currency,
            [800, -800, 0],
            ["$800", "\N{MINUS SIGN}$800", "$0"],
        ),
    ],
)
def test_labels_take_the_tick_unit(format_axis, values, texts):
    fig, ax = plt.subplots()
    ax.bar(list("ABC"), values)
    format_axis(ax, axis="y")
    assert [t.get_text() for t in dm.label_bars(ax)] == texts


def test_stacked_bars_label_segments_and_totals_in_readable_ink():
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    bottom = np.zeros(3)
    for values, color in (([18, 22, 27], "0.1"), ([24, 23, 21], "0.9")):
        ax.bar(list("ABC"), values, bottom=bottom, color=color)
        bottom += values
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    texts = [t.get_text() for t in labels]
    assert texts == ["18", "22", "27", "24", "23", "21", "42", "45", "48"]
    assert labels[0].get_color() == "white"  # on the dark segment
    assert labels[3].get_color() != "white"
    totals = _boxes(fig, labels[6:])
    assert all(b.y0 > ax.transData.transform((0, 40))[1] for b in totals)


def test_crowded_labels_turn_and_what_still_meets_is_hidden_with_a_warning():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    labels = dm.label_bars(ax, ax.bar(range(30), np.linspace(1000, 9999, 30)))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dm.simple_layout(fig)
    assert {t.get_rotation() for t in labels} == {90.0}
    shown = [t for t in labels if t.get_visible()]
    assert labels[-1] in shown and 0 < len(shown) < len(labels)
    assert any("bar value labels are hidden" in str(w.message) for w in caught)


def test_skip_hides_without_a_warning_and_relabelling_replaces():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    bars = ax.bar(range(30), np.linspace(1000, 9999, 30))
    dm.label_bars(ax, bars)
    labels = dm.label_bars(ax, bars, crowded="skip", fmt="{} u")
    assert len(ax.texts) == len(labels) == 30
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dm.simple_layout(fig)
    assert not [w for w in caught if "dm.label_bars" in str(w.message)]
    assert {t.get_rotation() for t in labels} == {0.0}
    assert labels[0].get_text() == "1,000 u"


def test_twin_bars_put_their_labels_on_the_axes_drawn_last():
    fig, ax = plt.subplots()
    ax.bar(list("ABC"), [3, 4, 5])
    twin = ax.twinx()
    twin.plot([0, 1, 2], [9, 1, 5])
    labels = dm.label_bars(ax)
    assert all(t.axes is twin for t in labels)


def test_a_value_label_takes_the_first_free_side():
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3], [1, 3, 2, 4])
    ax.set_ylim(0, 4)
    peak = dm.annotate_value(ax, 1, 3, "peak")
    end = dm.annotate_value(ax, 3, 4, "end")
    assert peak.xyann == (0.0, 3.0)  # above, clear
    assert end.xyann[0] != 0.0  # the top of the plot: sideways, not below
    assert peak.get_fontsize() == pytest.approx(dm.fs(-1))


def test_corner_and_reference_line_labels():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.scatter([0.03], [0.97])
    note = dm.annotate_corner(ax, "n = 5")
    assert note.xy == (1.0, 1.0)  # a point takes the upper left
    ax.plot([0.2, 0.6], [0.5, 0.5])
    target = dm.label_hline(ax, 0.5, "Target")
    assert target.xy[0] == pytest.approx(0.6, abs=0.01)
    assert target.get_horizontalalignment() == "right"


def test_panel_letters_sit_on_the_title_baseline_and_align_per_column():
    dm.style.use("scientific")
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize(dm.col2, "standard"))
    for ax in axes.flat:
        ax.plot([0, 1], [0, 1])
    axes[0, 0].set_title("Response")
    axes[0, 0].set_ylabel("Amplitude (mV)")
    letters = dm.label_axes(axes)
    dm.simple_layout(fig)
    assert [t.get_text() for t in letters] == ["a", "b", "c", "d"]
    a, b, c, _d = _boxes(fig, letters)
    title = _boxes(fig, [axes[0, 0].title])[0]
    assert a.x0 == pytest.approx(c.x0)  # one column, one left edge
    assert a.y0 == pytest.approx(b.y0)  # one row, one baseline
    assert a.x1 < title.x0 or a.y0 >= title.y0 - 3


def test_line_end_names_replace_the_legend_and_stay_apart():
    fig, ax = plt.subplots()
    x = np.arange(5)
    for name, last in (("a", 5.0), ("b", 5.05), ("c", 1.0)):
        ax.plot(x, [1, 2, 3, 4, last], label=name)
    ax.legend()
    names = dm.label_line_ends(ax)
    dm.simple_layout(fig)
    assert ax.get_legend() is None
    a, b, _c = _boxes(fig, names)
    assert a.y1 <= b.y0 + 0.5 or b.y1 <= a.y0 + 0.5


def test_a_note_sits_under_the_plot():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    note = dm.add_note(fig, "Source: test")
    dm.simple_layout(fig)
    (box,) = _boxes(fig, [note])
    assert box.y1 < ax.xaxis.get_tightbbox(fig.canvas.get_renderer()).y0
    assert note.get_fontsize() == pytest.approx(dm.fs(-1))
