"""What a Figure holds through its SubFigures, and its figure-level artists."""

from __future__ import annotations

import matplotlib.pyplot as plt

from dartwork_mpl import geometry as g


def _found(fig, **kwargs) -> list:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    return [a for a, _ in g.iter_figure_level_extents(fig, renderer, **kwargs)]


def test_suptitle_texts_and_legends_count_once_and_blanks_not() -> None:
    fig, ax = plt.subplots()
    (line,) = ax.plot([1, 2, 3], label="s")
    title = fig.suptitle("Title")
    note = fig.text(0.5, 0.01, "footnote")
    legend = fig.legend(handles=[line], loc="upper right")
    label = fig.supxlabel("shared x")  # also kept in fig.texts
    fig.text(0.1, 0.1, "   ")
    fig.text(0.2, 0.2, "hidden").set_visible(False)
    assert _found(fig) == [title, label, note, legend]
    assert _found(fig, legends=False) == [title, label, note]


def _tree():
    """A root Axes, then a SubFigure with its own Axes and a nested one's."""
    fig = plt.figure()
    top = fig.add_subplot(2, 1, 1)
    sub = fig.subfigures(2, 1)[1]
    own = sub.add_subplot(1, 2, 1)
    nested = sub.subfigures(1, 2)[1]
    deep = nested.add_subplot()
    return fig, sub, nested, (top, own, deep)


def test_a_subfigure_holds_its_nested_subfigures_axes_and_legends() -> None:
    fig, sub, nested, (top, own, deep) = _tree()
    assert g.figure_axes(fig) == fig.axes
    assert sub.axes == [own]  # matplotlib's own list leaves ``deep`` out
    assert g.figure_axes(sub) == [own, deep]
    for ax in (top, own, deep):
        ax.plot([0, 1], label="s")
    legends = [f.legend() for f in (fig, sub, nested)]
    assert g.figure_legends(fig) == legends
    assert g.figure_legends(sub) == legends[1:]


def test_a_hidden_subfigure_hides_what_it_holds() -> None:
    """matplotlib leaves each child's own ``get_visible()`` True; a
    grandparent counts too, the root Figure's own flag does not."""
    fig, sub, nested, (_top, own, deep) = _tree()
    title = nested.suptitle("Inner group")
    own.plot([0, 1], label="s")
    legend = sub.legend()
    assert title in _found(fig) and legend in _found(fig)
    assert title not in _found(fig, subfigures=False)
    sub.set_visible(False)
    assert deep.get_visible() and not g.drawn_in_tree(deep)
    assert not g.holders_shown(title)
    assert title not in _found(fig) and legend not in _found(fig)
    sub.set_visible(True)
    fig.set_visible(False)
    assert g.drawn_in_tree(deep)
