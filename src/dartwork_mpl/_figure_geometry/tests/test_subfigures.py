"""What a Figure or SubFigure holds, nested SubFigures included.

matplotlib lists every Axes on the root Figure (``fig.axes``) but only a
SubFigure's own on the SubFigure, and keeps each (Sub)Figure's legends,
suptitle and texts on that (Sub)Figure alone. The placer and the checks
read panels and figure-level artists through ``_figure_geometry`` so a
SubFigure's neighbours and its legends are seen wherever they sit.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl import _figure_geometry as fg


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _tree():
    """A root Axes, then a SubFigure with its own Axes and a nested one's."""
    fig = plt.figure()
    top = fig.add_subplot(2, 1, 1)
    sub = fig.subfigures(2, 1)[1]
    own = sub.add_subplot(1, 2, 1)
    nested = sub.subfigures(1, 2)[1]
    deep = nested.add_subplot()
    return fig, sub, nested, (top, own, deep)


def test_the_root_figure_holds_exactly_its_axes_list() -> None:
    """For the root, ``fig.axes`` itself: its order is ``axes_index``."""
    fig, _sub, _nested, _axes = _tree()
    assert fg.figure_axes(fig) == fig.axes


def test_a_subfigure_holds_its_nested_subfigures_axes_in_figure_order() -> None:
    fig, sub, nested, (_top, own, deep) = _tree()
    assert sub.axes == [own]  # matplotlib's own list leaves ``deep`` out
    assert fg.figure_axes(sub) == [own, deep]
    assert fg.figure_axes(nested) == [deep]


def test_the_tree_is_the_figure_then_its_subfigures_depth_first() -> None:
    fig, sub, nested, _axes = _tree()
    other = fig.subfigs[0]
    first, second = sub.subfigs  # ``sub.subfigures(1, 2)`` made two
    assert second is nested
    assert fg.figure_tree(fig) == [fig, other, sub, first, nested]
    assert fg.figure_tree(sub) == [sub, first, nested]


def test_figure_legends_are_every_subfigures_too() -> None:
    fig, sub, nested, (top, own, deep) = _tree()
    for ax, name in ((top, "Top"), (own, "Own"), (deep, "Deep")):
        ax.plot([0, 1], [0, 1], label=name)
    root_legend = fig.legend(handles=top.get_lines())
    sub_legend = sub.legend(handles=own.get_lines())
    nested_legend = nested.legend(handles=deep.get_lines())
    assert fg.figure_legends(fig) == [root_legend, sub_legend, nested_legend]
    assert fg.figure_legends(sub) == [sub_legend, nested_legend]


def test_drawn_in_tree_reads_every_subfigure_above_the_artist() -> None:
    """Hiding a SubFigure hides what is in it, though matplotlib leaves
    each child's own ``get_visible()`` True; a grandparent counts too."""
    fig = plt.figure()
    outer = fig.subfigures(1, 2)[1]
    inner = outer.subfigures(1, 1)
    ax = inner.add_subplot()
    title = inner.suptitle("Inner group")
    assert fg.drawn_in_tree(ax)
    assert fg.drawn_in_tree(title)
    outer.set_visible(False)
    assert ax.get_visible()  # matplotlib's own flag stays True
    assert not fg.drawn_in_tree(ax)
    assert not fg.drawn_in_tree(title)
    assert not fg.drawn_in_tree(inner)


def test_a_hidden_root_figure_is_not_read() -> None:
    """The root Figure's own flag is left as before: only SubFigures hide."""
    fig = plt.figure()
    ax = fig.add_subplot()
    fig.set_visible(False)
    assert fg.drawn_in_tree(ax)
    ax.set_visible(False)
    assert not fg.drawn_in_tree(ax)


@pytest.mark.parametrize("hidden", ["holder", "ancestor"])
def test_a_hidden_subfigures_title_and_legend_have_no_extent(
    hidden: str,
) -> None:
    """What a hidden SubFigure holds is not drawn, so it reserves, crops
    and covers nothing; the structural lists still name it."""
    fig = plt.figure()
    left, right = fig.subfigures(1, 2)
    left.subplots()
    holder = right if hidden == "holder" else right.subfigures(1, 1)
    ax = holder.subplots()
    ax.plot([0, 1], [0, 1], label="Series")
    title = holder.suptitle("Hidden group")
    legend = holder.legend()
    right.set_visible(False)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    found = [art for art, _ext in fg.iter_figure_level_extents(fig, renderer)]
    assert title not in found
    assert legend not in found
    assert fg.figure_axes(fig) == fig.axes
    assert legend in fg.figure_legends(fig)


def test_a_hidden_subfigure_does_not_end_the_outside_span() -> None:
    """A panel in a hidden SubFigure is no neighbour: the range above the
    left panel runs to the canvas edge, not to it."""
    fig = plt.figure(figsize=(8, 4))
    left, right = fig.subfigures(1, 2)
    ax = left.subplots()
    right.subplots()
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    shown = fg.outside_span_px(ax, "above", renderer)
    right.set_visible(False)
    hidden = fg.outside_span_px(ax, "above", renderer)
    assert shown[1] < fig.bbox.x1
    assert hidden[1] == pytest.approx(fig.bbox.x1)


def test_figure_level_extents_include_a_subfigures_title_and_legend() -> None:
    fig, sub, _nested, (_top, own, _deep) = _tree()
    own.plot([0, 1], [0, 1], label="Own")
    title = sub.suptitle("Panel group")
    legend = sub.legend()
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    found = [art for art, _ext in fg.iter_figure_level_extents(fig, renderer)]
    assert title in found
    assert legend in found
    root_only = [
        art
        for art, _ext in fg.iter_figure_level_extents(
            fig, renderer, subfigures=False
        )
    ]
    assert title not in root_only
    assert legend not in root_only
