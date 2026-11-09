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
