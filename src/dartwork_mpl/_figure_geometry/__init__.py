"""Figure measurement mechanism shared by layout, annotation and validation.

Platform code (ADR 0005): it knows matplotlib's renderer and artist extents
and nothing about any capability, and it imports no slice. Not part of the
public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from matplotlib.text import Text

__all__ = [
    "BBOX_ERRORS",
    "axes_text_artists",
    "axes_titles",
    "get_renderer",
    "iter_figure_level_extents",
]

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.transforms import Bbox

#: Exceptions matplotlib may raise from ``get_window_extent`` /
#: ``get_tightbbox`` on artists in degenerate states (NaN-only data,
#: zero-area fonts, renderers that refuse the call). Single source for
#: both the layout engine and the validation checks — the two used to
#: carry identical private copies.
BBOX_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    AttributeError,
)


def get_renderer(fig: Figure | SubFigure) -> RendererBase:
    """Return ``fig.canvas.get_renderer()`` with the type-ignore centralised.

    Matplotlib's ``FigureCanvasBase`` does not declare ``get_renderer`` —
    only the backend subclasses (``FigureCanvasAgg`` etc.) do. mypy
    flags every call site with ``attr-defined``. Routing through this
    helper keeps the suppression in one place.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
        Figure (or SubFigure) whose canvas exposes a renderer (true
        for every backend dartwork-mpl supports). SubFigure delegates
        its canvas to the parent Figure, so the same call works.

    Returns
    -------
    matplotlib.backend_bases.RendererBase
        The renderer used by ``fig``'s canvas.
    """
    return fig.canvas.get_renderer()  # type: ignore[attr-defined,no-any-return]


def iter_figure_level_extents(
    fig: Figure, renderer: RendererBase, *, legends: bool = True
) -> Iterator[tuple[Any, Bbox]]:
    """Yield ``(artist, window_extent)`` for each figure-level artist.

    Figure-level artists — ``fig.suptitle`` / ``fig.supxlabel`` /
    ``fig.supylabel`` (the private ``_sup*`` attributes), ``fig.text``
    entries, and ``fig.legend`` legends — live on the Figure, not on any
    Axes, so per-axes extent walks never see them. Three sites previously
    re-derived this candidate list plus the identical guard triplet:
    ``layout._figure_artist_reservations``, ``layout.tight_crop``, and the
    ``OVERFLOW`` visual check. This is their single source.

    matplotlib stores the sup-title / sup-labels in ``fig.texts`` *as well
    as* the ``_sup*`` attributes, so candidates are de-duplicated by
    identity — a bbox counted twice is harmless for the callers'
    ``min`` / ``max`` / ``Bbox.union`` math, but yielding each artist once
    keeps the contract clear.

    The guard, applied to every candidate:

    * skip invisible artists;
    * skip text artists whose text is empty or whitespace-only — a blank
      suptitle / footnote reserves no space and must not extend a
      bounding box (this unifies a prior inconsistency: reservations and
      OVERFLOW already skipped blank text, ``tight_crop`` did not);
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
        Include ``fig.legends``. The OVERFLOW check passes ``False`` —
        figure legends are the LEGEND_OVERFLOW check's responsibility.
        Default ``True``.

    Yields
    ------
    tuple[matplotlib.artist.Artist, matplotlib.transforms.Bbox]
        Each qualifying artist and its display-space window extent.
    """
    seen: set[int] = set()
    candidates: list[Any] = []
    for art in (
        getattr(fig, "_suptitle", None),
        getattr(fig, "_supxlabel", None),
        getattr(fig, "_supylabel", None),
        *fig.texts,
        *(fig.legends if legends else ()),
    ):
        if art is None or id(art) in seen:
            continue
        seen.add(id(art))
        candidates.append(art)

    for art in candidates:
        if not art.get_visible():
            continue
        # Only text artists carry ``get_text``; legends don't, so they are
        # never dropped for "empty text".
        get_text = getattr(art, "get_text", None)
        if get_text is not None and not get_text().strip():
            continue
        try:
            ext = art.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        yield art, ext


# ``ax.title`` is only the centre title. ``ax.set_title(..., loc="left")``
# and ``loc="right"`` write to these private attributes instead, so a walk
# over ``ax.title`` alone never sees a left-aligned headline.
_TITLE_ATTRS: dict[Literal["center", "left", "right"], str] = {
    "center": "title",
    "left": "_left_title",
    "right": "_right_title",
}


def axes_titles(ax: Axes) -> dict[str, Text]:
    """Return the title Text artists of ``ax`` keyed by ``set_title``'s ``loc``.

    This is the one place that reads matplotlib's private title
    attributes. Each is read with ``getattr`` and kept only while its text
    matches the public ``ax.get_title(loc=...)``, so a matplotlib that
    renames or repurposes them yields fewer titles instead of wrong ones.
    """
    titles: dict[str, Text] = {}
    for loc, attr in _TITLE_ATTRS.items():
        text = getattr(ax, attr, None)
        if not isinstance(text, Text):
            continue
        try:
            public = ax.get_title(loc=loc)
        except (TypeError, ValueError, AttributeError):
            continue
        if text.get_text() == public:
            titles[loc] = text
    return titles


def axes_text_artists(ax: Axes) -> list[Text]:
    """Return ``ax.texts``, the three titles and the x/y axis labels."""
    titles = axes_titles(ax).values()
    return [*ax.texts, *titles, ax.xaxis.label, ax.yaxis.label]
