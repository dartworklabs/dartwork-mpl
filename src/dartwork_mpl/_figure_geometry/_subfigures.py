"""What a Figure or SubFigure holds, its nested SubFigures included.

matplotlib lists every Axes on the root Figure (``fig.axes``, in the order
they were made) but on a SubFigure only its own, not a nested SubFigure's;
and each (Sub)Figure keeps its legends, suptitle and texts on itself. An
Axes' ``get_position`` is a fraction of its own (Sub)Figure. Callers that
look for a panel's neighbours or for figure-level artists read them here,
so a SubFigure's are seen wherever they sit:

- :func:`figure_tree`: a (Sub)Figure and its nested SubFigures, depth first;
- :func:`figure_axes`: the Axes drawn in a (Sub)Figure, in ``fig.axes``
  order (for the root Figure, ``fig.axes`` itself: its order is the
  ``axes_index`` the checks report);
- :func:`figure_legends`: the figure-level legends of a (Sub)Figure's tree;
- :func:`root_position`: an Axes' position as a fraction of the root Figure;
- :func:`drawn_in_tree`: whether an artist is shown, every SubFigure above
  it shown too (hiding a SubFigure hides what it holds, though matplotlib
  leaves each child's own ``get_visible()`` True).

The lists are structural: they name what a hidden SubFigure holds too. A
caller that wants what is drawn picks with :func:`drawn_in_tree`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.transforms import Bbox

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend


def figure_tree(fig: Figure | SubFigure) -> list[Figure | SubFigure]:
    """``fig``, then each of its SubFigures and theirs, depth first."""
    tree: list[Figure | SubFigure] = [fig]
    for sub in fig.subfigs:
        tree.extend(figure_tree(sub))
    return tree


def _parents(ax: Axes) -> list[Figure | SubFigure]:
    """The (Sub)Figures ``ax`` is drawn in, its own first, up to the root."""
    found: list[Figure | SubFigure] = []
    parent = ax.get_figure(root=False)
    while parent is not None and parent not in found:
        found.append(parent)
        parent = parent.get_figure(root=False)
    return found


def figure_axes(fig: Figure | SubFigure) -> list[Axes]:
    """The Axes drawn in ``fig`` or in a SubFigure nested in it.

    In the root Figure's ``fig.axes`` order. For the root Figure this is
    ``fig.axes`` (every Axes of every SubFigure is on it); for a SubFigure,
    those of them inside it.
    """
    root = fig.get_figure(root=True)
    if root is None or fig is root:
        return list(fig.axes)
    return [ax for ax in root.axes if fig in _parents(ax)]


def figure_legends(fig: Figure | SubFigure) -> list[Legend]:
    """The figure-level legends of ``fig`` and its nested SubFigures."""
    return [legend for member in figure_tree(fig) for legend in member.legends]


def drawn_in_tree(artist: Artist) -> bool:
    """Whether ``artist`` is shown and so is every SubFigure above it.

    ``SubFigure.set_visible(False)`` hides its Axes, legends and texts
    without changing their own flags. The root Figure's own flag is not
    read: a hidden root Figure keeps the answers it had.
    """
    if not artist.get_visible():
        return False
    root = artist.get_figure(root=True)
    holder = artist.get_figure(root=False)
    seen: list[Figure | SubFigure] = []
    while holder is not None and holder is not root and holder not in seen:
        if not holder.get_visible():
            return False
        seen.append(holder)
        holder = holder.get_figure(root=False)
    return True


def root_position(ax: Axes) -> Bbox:
    """``ax.get_position()`` as a fraction of the root Figure.

    An Axes in the root Figure is returned as is; one in a SubFigure is
    carried through its SubFigure's box to the root's.
    """
    position = ax.get_position()
    parent = ax.get_figure(root=False)
    root = ax.get_figure(root=True)
    if parent is None or root is None or parent is root:
        return position
    return position.transformed(parent.transSubfigure).transformed(
        root.transFigure.inverted()
    )
