"""figure_legend: one legend for every panel of a figure, outside the panels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from matplotlib.transforms import Bbox

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    get_renderer,
    iter_figure_level_extents,
)
from ._legend_fit import ceil_div, legend_size, probe
from ._legend_outside import OutsidePlan, choose, split_ncols

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend
    from matplotlib.typing import LegendLocType

# Each side's legend ``loc`` and its anchor on the (sub)figure, in figure fraction.
_FIGURE_LOCS: dict[OutsideSide, tuple[LegendLocType, tuple[float, float]]] = {
    "above": ("upper center", (0.5, 1.0)),
    "below": ("lower center", (0.5, 0.0)),
    "right": ("center right", (1.0, 0.5)),
    "left": ("center left", (0.0, 0.5)),
}

_SIDES: dict[str, OutsideSide] = {
    "above": "above",
    "below": "below",
    "right": "right",
    "left": "left",
}


def _entry_names(legend: Legend) -> set[str]:
    """The entry names a legend shows, as given before any wrapping."""
    for name in ("_dm_outside_source", "_dm_best_source"):
        source = getattr(legend, name, None)
        labels = getattr(source, "labels", None)
        if isinstance(labels, list):
            return {str(label) for label in labels}
    return {text.get_text() for text in legend.get_texts()}


def _figure_entries(fig: Figure | SubFigure) -> tuple[list[Any], list[str]]:
    """Every Axes' labelled artists once, by label, in figure order."""
    handles: list[Any] = []
    labels: list[str] = []
    seen: set[str] = set()
    for ax in fig.axes:
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=True):
            if label not in seen:
                seen.add(label)
                handles.append(handle)
                labels.append(label)
    return handles, labels


def _figure_plan(
    fig: Figure | SubFigure,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    legend_kw: dict[str, Any],
    explicit: int | None,
    renderer: RendererBase,
    panels: Bbox,
) -> OutsidePlan:
    """Columns and cost of the figure legend on ``side`` of the panels.

    Above and below: the fewest rows no wider than the (sub)figure.
    Right and left: the fewest columns no taller than the panels. The loss
    is the legend's height (above, below) or width (right, left) as a
    share of the panels'.
    """
    count = max(len(labels), 1)
    along_width = side in ("above", "below")
    limit = fig.bbox.width if along_width else panels.height
    if explicit is not None:
        steps = [explicit]
    elif along_width:
        steps = list(
            dict.fromkeys(ceil_div(count, r) for r in range(1, count + 1))
        )
    else:
        steps = list(range(1, count + 1))
    loc, _anchor = _FIGURE_LOCS[side]
    width = height = float("inf")
    ncols = steps[-1]
    fits = False
    for ncols in steps:
        trial = probe(fig, handles, labels, loc=loc, ncols=ncols, **legend_kw)
        try:
            width, height = legend_size(trial, renderer)
        except BBOX_ERRORS:
            width = height = float("inf")
        fits = (width if along_width else height) <= limit + 0.5
        if fits:
            break
    loss = (
        height / max(panels.height, 1.0)
        if along_width
        else width / max(panels.width, 1.0)
    )
    return OutsidePlan(side, ncols, tuple(labels), width, height, loss, fits)


def _below_suptitle(fig: Figure | SubFigure, renderer: RendererBase) -> float:
    """The (sub)figure fraction just under a suptitle, else 1.0 (the top)."""
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is None:
        return 1.0
    for art, ext in iter_figure_level_extents(
        cast("Figure", fig), renderer, legends=False
    ):
        if art is suptitle:
            return float((ext.y0 - fig.bbox.y0) / fig.bbox.height)
    return 1.0


def _replaced(fig: Figure | SubFigure, names: set[str]) -> list[Legend]:
    """The legends a new figure legend of ``names`` replaces.

    The Axes legends holding only ``names`` and the figure legend an earlier
    call drew. Taken before the new legend exists, removed only once it
    does, so a call that fails leaves every legend as it was.
    """
    found: list[Legend] = []
    for ax in fig.axes:
        legend = ax.get_legend()
        if legend is not None and _entry_names(legend) <= names:
            found.append(legend)
    found.extend(
        legend
        for legend in fig.legends
        if getattr(legend, "_dm_figure_legend", False)
    )
    return found


def _remove(legends: list[Legend]) -> None:
    for legend in legends:
        legend.remove()


def figure_legend(
    fig: Figure | SubFigure, *, loc: str = "best", **kw: Any
) -> Legend | None:
    """One legend for every panel of ``fig``, outside the panels.

    The entries are every Axes' labelled artists, each label once, in
    figure order. The Axes legends that hold only those entries (one per
    panel, a twin pair's, ``dm.place_legend``'s) and a legend an earlier
    call drew are removed once the new legend is drawn; any other legend
    stays, and a call that raises (``bbox_to_anchor`` with a side, say)
    leaves every legend as it was.

    ``loc="best"`` puts the legend above the panels, or right of them when
    that takes clearly less of the panels (at least 10 % and 5 % of their
    size less; the rule of :func:`dartwork_mpl.place_legend`). Above and
    below take the fewest rows no wider than the figure, right and left the
    fewest columns no taller than the panels; ``ncol`` / ``ncols`` in
    ``kw`` overrides the count. ``loc="above"``, ``"below"``, ``"right"``
    or ``"left"`` is that side; any other ``loc`` (with ``kw``) goes to
    ``fig.legend`` unchanged. Above, the legend sits under a
    ``fig.suptitle``. Names are not wrapped.

    :func:`dartwork_mpl.simple_layout` keeps the panels clear of the legend,
    with the preset's ``legend.borderaxespad`` between them. Returns the
    legend, or ``None`` when no Axes has a labelled artist.

    Experimental: the side rule and which panel legends are removed may
    still change.
    """
    handles, labels = _figure_entries(fig)
    replaced = _replaced(fig, set(labels))
    if not handles:
        _remove(replaced)
        return None
    side = _SIDES.get(loc)
    if side is None and loc != "best":
        legend = fig.legend(
            handles, labels, loc=cast("LegendLocType", loc), **kw
        )
        legend._dm_figure_legend = True  # type: ignore[attr-defined]
        _remove(replaced)
        return legend
    legend_kw, explicit = split_ncols(kw)
    for key in ("bbox_to_anchor", "bbox_transform"):
        if key in legend_kw:
            raise ValueError(
                f"figure_legend(loc={loc!r}) anchors the legend itself; "
                f"remove {key}= or pass a matplotlib loc instead"
            )
    renderer = get_renderer(fig)
    boxes = [
        ax.get_window_extent(renderer) for ax in fig.axes if ax.get_visible()
    ]
    panels = Bbox.union(boxes) if boxes else Bbox(fig.bbox.get_points())
    sides: list[OutsideSide] = (
        [side] if side is not None else ["above", "right"]
    )
    plan = choose(
        [
            _figure_plan(
                fig, handles, labels, s, legend_kw, explicit, renderer, panels
            )
            for s in sides
        ]
    )
    where, anchor = _FIGURE_LOCS[plan.side]
    if plan.side == "above":
        anchor = (anchor[0], _below_suptitle(fig, renderer))
    legend = fig.legend(
        handles,
        labels,
        loc=where,
        ncols=plan.ncols,
        bbox_to_anchor=anchor,
        bbox_transform=fig.transSubfigure,
        **legend_kw,
    )
    # simple_layout keeps this gap between the legend and the panels.
    legend._dm_layout_gap_pt = float(legend.borderaxespad) * float(  # type: ignore[attr-defined]
        legend.prop.get_size_in_points()
    )
    legend._dm_figure_legend = True  # type: ignore[attr-defined]
    legend._dm_figure_side = plan.side  # type: ignore[attr-defined]
    _remove(replaced)
    return legend


__all__ = ["figure_legend"]
