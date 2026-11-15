"""An Axes' titles and drawn tick labels, and the Axes it shares a box or a scale with."""

from __future__ import annotations

import matplotlib.pyplot as plt

from dartwork_mpl import geometry as g

BOX = (0.1, 0.1, 0.8, 0.8)


def test_every_title_is_found_by_its_loc() -> None:
    _fig, ax = plt.subplots()
    ax.set_title("Left headline", loc="left")
    ax.set_title("Right note", loc="right")
    titles = g.axes_titles(ax)
    assert {loc: t.get_text() for loc, t in titles.items()} == {
        "center": "",
        "left": "Left headline",
        "right": "Right note",
    }


def test_only_the_ticks_in_view_draw_their_labels() -> None:
    fig, ax = plt.subplots()
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_xlim(0.5, 9.5)
    fig.canvas.draw()
    texts = [t.get_text() for t in g.drawn_tick_labels(ax, "x")]
    assert texts == ["2", "4", "6", "8"]
    ax.xaxis.set_visible(False)
    assert g.drawn_tick_labels(ax, "x") == []
    ax.xaxis.set_visible(True)
    ax.axis("off")
    assert g.drawn_tick_labels(ax, "x") == []


def test_twinx_and_twiny_share_one_axis_each_in_one_box() -> None:
    _fig, ax = plt.subplots()
    right, top = ax.twinx(), ax.twiny()
    assert g.shared_axes(ax, "x") == [ax, right]
    assert g.shared_axes(ax, "y") == [ax, top]
    assert g.same_position_axes(ax) == [ax, right, top]


def test_one_box_and_one_scale_are_separate_questions() -> None:
    fig = plt.figure()
    first, second = fig.add_axes(BOX), fig.add_axes(BOX)
    assert g.same_position_axes(first) == [first, second]
    assert g.shared_axes(first, "x") == [first]
    second.set_visible(False)
    assert g.same_position_axes(first) == [first]


def test_shared_panels_are_in_figure_order_each_in_its_own_box() -> None:
    _fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)
    flat = list(axs.flat)
    assert g.shared_axes(flat[3], "x") == flat
    assert all(g.same_position_axes(ax) == [ax] for ax in flat)


def test_an_inset_stands_alone() -> None:
    _fig, ax = plt.subplots()
    inset = ax.inset_axes((0.5, 0.5, 0.4, 0.4))
    assert g.shared_axes(inset, "x") == [inset]
    assert g.same_position_axes(ax) == [ax]
