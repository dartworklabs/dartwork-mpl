"""Realistic charts through the public surface: the labels as drawn."""

from __future__ import annotations

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
            dm.format_axis_myriad,
            [1.25e8, 12.5e8, 0.5e8],
            ["1.2억", "12.5억", "0.5억"],
        )
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


def test_crowded_labels_turn_and_what_still_meets_is_hidden():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    labels = dm.label_bars(ax, ax.bar(range(30), np.linspace(1000, 9999, 30)))
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in labels} == {90.0}
    shown = [t for t in labels if t.get_visible()]
    assert labels[-1] in shown and 0 < len(shown) < len(labels)


def test_a_value_label_takes_the_first_free_side():
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3], [1, 3, 2, 4])
    ax.set_ylim(0, 4)
    peak = dm.annotate_value(ax, 1, 3, "peak")
    end = dm.annotate_value(ax, 3, 4, "end")
    assert peak.xyann == (0.0, 3.0)  # above, clear
    assert end.xyann[0] != 0.0  # the top of the plot: sideways, not below
    assert peak.get_fontsize() == pytest.approx(dm.fs(-1))


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


def test_a_value_label_the_caller_hid_or_turned_stays_so() -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "wide"))
    ax.bar([str(i) for i in range(12)], [1000 * i + 12345 for i in range(12)])
    labels = dm.label_bars(ax)
    dm.simple_layout(fig)
    shown = [t for t in labels if t.get_visible()]
    shown[0].set_visible(False)
    shown[1].set_rotation(45)
    dm.simple_layout(fig)
    assert not shown[0].get_visible()
    assert shown[1].get_rotation() == 45


def test_a_panel_letter_the_caller_moved_stays_where_they_put_it() -> None:
    fig, axes = plt.subplots(1, 2)
    letters = dm.label_axes(axes)
    dm.simple_layout(fig)
    letters[0].xyann = (5.0, 5.0)
    dm.simple_layout(fig)
    assert tuple(letters[0].xyann) == (5.0, 5.0)


def test_a_line_name_the_caller_moved_stays_where_they_put_it() -> None:
    fig, ax = plt.subplots()
    x = np.linspace(0, 1, 10)
    ax.plot(x, x, label="up")
    ax.plot(x, x + 0.01, label="close")
    names = dm.label_line_ends(ax)
    dm.simple_layout(fig)
    names[0].xyann = (20.0, -10.0)
    dm.simple_layout(fig)
    assert tuple(names[0].xyann) == (20.0, -10.0)
