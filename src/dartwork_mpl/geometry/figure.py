"""What a Figure holds, its nested SubFigures included, and its own artists.

matplotlib lists every Axes on the root Figure (``fig.axes``, in the order
they were made) but on a SubFigure only its own, and each (Sub)Figure keeps
its legends, suptitle and texts on itself. Hiding a SubFigure hides what it
holds, though matplotlib leaves each child's own ``get_visible()`` True. The
lists here are structural; :func:`drawn_in_tree` picks what is drawn.
"""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

from matplotlib.text import Text

from .renderer import BBOX_ERRORS

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend
    from matplotlib.text import Annotation
    from matplotlib.transforms import Bbox


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
    return bool(artist.get_visible() and holders_shown(artist))


def holders_shown(artist: Artist) -> bool:
    """Whether every SubFigure above ``artist`` is shown (its own flag aside).

    The root Figure's flag is not read. Without SubFigures: always.
    """
    root = artist.get_figure(root=True)
    holder = artist.get_figure(root=False)
    seen: list[Figure | SubFigure] = []
    while holder is not None and holder is not root and holder not in seen:
        if not holder.get_visible():
            return False
        seen.append(holder)
        holder = holder.get_figure(root=False)
    return True


def iter_figure_level_extents(
    fig: Figure | SubFigure,
    renderer: RendererBase,
    *,
    legends: bool = True,
    subfigures: bool = True,
) -> Iterator[tuple[Text | Legend, Bbox]]:
    """Yield ``(artist, window_extent)`` for each figure-level artist.

    Figure-level artists — ``fig.text`` entries, ``fig.suptitle`` /
    ``fig.supxlabel`` / ``fig.supylabel`` (which matplotlib makes with
    ``fig.text``, so they are in ``fig.texts``), and ``fig.legend`` legends
    — live on the Figure, not on any Axes, so per-axes extent walks never
    see them. The layout's edge reservations and the ``OVERFLOW`` check
    share this walk.

    The guard, applied to every candidate:

    * skip invisible artists, and those of a hidden SubFigure
      (:func:`drawn_in_tree`);
    * skip text artists whose text is empty or whitespace-only — a blank
      suptitle / footnote reserves no space and must not extend a
      bounding box;
    * swallow :data:`BBOX_ERRORS` from ``get_window_extent``;
    * drop zero-area extents — uninformative, and they poison the
      downstream ``min`` / ``max`` / ``Bbox.union`` math.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure whose figure-level artists to walk.
    renderer : matplotlib.backend_bases.RendererBase
        Renderer used to measure extents (from :func:`get_renderer`).
    legends : bool, optional
        Include ``fig.legends``. The OVERFLOW check passes ``False``: it
        reads the legends' entry texts itself.
        Default ``True``.
    subfigures : bool, optional
        Also walk each SubFigure nested in ``fig`` (:func:`figure_tree`),
        which keeps its own suptitle, texts and legends. The layout's edge
        reservations pass ``False``: they size the root grid. Default
        ``True``.

    Yields
    ------
    tuple[matplotlib.artist.Artist, matplotlib.transforms.Bbox]
        Each qualifying artist and its display-space window extent.
    """
    seen: set[int] = set()
    candidates: list[Text | Legend] = []
    for member in figure_tree(fig) if subfigures else [fig]:
        for art in (*member.texts, *(member.legends if legends else ())):
            if id(art) in seen:
                continue
            seen.add(id(art))
            candidates.append(art)

    for art in candidates:
        if not drawn_in_tree(art):  # a hidden SubFigure hides its own
            continue
        # A legend has no text of its own, so it is never dropped for
        # "empty text".
        if isinstance(art, Text) and not art.get_text().strip():
            continue
        try:
            ext = art.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        yield art, ext


# The panel letters placed on each root Figure, each with its panel. The
# slice that places them records them; any slice may read them.
_PANEL_LETTERS: weakref.WeakKeyDictionary[
    Figure, list[tuple[Axes, Annotation]]
] = weakref.WeakKeyDictionary()


def record_panel_letters(
    fig: Figure, members: Sequence[tuple[Axes, Annotation]]
) -> None:
    """Remember the letters placed on the root Figure ``fig``."""
    _PANEL_LETTERS.setdefault(fig, []).extend(members)


def panel_letters(fig: Figure | SubFigure) -> list[tuple[Axes, Annotation]]:
    """The automatic panel letters on ``fig``'s root, each with its panel."""
    return list(_PANEL_LETTERS.get(fig.get_figure(root=True), []))
