"""LEGEND_ON_DATA: a legend drawn over data, a text, another legend or another panel.

``LEGEND_OVERLAP`` compares a legend with titles, axis labels, tick labels
and figure text. This check compares it with what the reader reads values
from. It takes every visible Axes legend and figure legend and reports, per
legend, what its box meets:

* data in any plot box (an Axes and its ``twinx`` / ``twiny`` partners),
  measured as VALUE_LABEL_ON_DATA measures it: bars, drawn line segments at
  their width, markers and scatter points at their size, clipped to the
  plot box. A legend over another panel's data counts too;
* the texts inside any Axes (``ax.texts``: value labels, annotations,
  line-end labels), by window extent;
* another legend's box;
* another panel's plot box, even where that panel draws no data: an Axes
  legend reaching into a neighbouring Axes is drawn over or under it.

Contact up to half a point is a touch, not a cover. A legend inside its own
Axes is drawn over the panels that Axes sits on (an Axes added on top of
another with ``fig.add_axes``), so those do not count. Images, meshes,
contours and filled areas are not data here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple, TypeAlias, TypedDict

import numpy as np

from ..._figure_geometry import same_position_axes
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix
from .value_label_on_data import _clip, _measure, _segments_hit, _window

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend
    from matplotlib.transforms import Bbox

    from .value_label_on_data import _Data

__all__ = ["check_legend_on_data"]

Covered: TypeAlias = Literal["bar", "line", "marker", "text", "legend", "panel"]

_TOUCH_PT = 0.5
_NAME_CHARS = 30  # names in the message and detail are cut to this length
_MAX_NAMES = 3
_MAX_LABELS = 5


class LegendOnDataDetail(TypedDict):
    """The legend of ``legend_axes`` (``None``: a figure legend) covers ``covered``.

    ``legend_labels`` holds the legend's first five entry texts, so a
    figure legend can be told apart; ``artists`` names up to three covered
    artists (series labels, text, ``legend of axes[i]``, ``axes[i]``);
    ``panels`` lists the ``fig.axes`` indices whose plot box holds the
    covered data.
    """

    legend_axes: int | None
    legend_labels: list[str]
    covered: list[Covered]
    artists: list[str]
    panels: list[int]


class _Hit(NamedTuple):
    kind: Covered
    name: str


class _PlotBox(NamedTuple):
    """One rectilinear plot box: the first Axes' index, its owners and frame."""

    axes_index: int
    owners: list[Axes]
    frame: Bbox


class _Placed(NamedTuple):
    """A visible legend, the ``fig.axes`` index it belongs to, and its box."""

    axes_index: int | None
    legend: Legend
    box: Bbox


def _cut(name: str) -> str:
    return name.strip()[:_NAME_CHARS]


def _legends(fig: Figure, renderer: RendererBase) -> list[_Placed]:
    found: list[tuple[int | None, Legend]] = []
    for index, ax in enumerate(fig.axes):
        legend = ax.get_legend()
        if ax.get_visible() and legend is not None and legend.get_visible():
            found.append((index, legend))
    found.extend(
        (None, legend) for legend in fig.legends if legend.get_visible()
    )
    placed: list[_Placed] = []
    for owner, legend in found:
        try:
            box = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if box.width > 0 and box.height > 0:
            placed.append(_Placed(owner, legend, box))
    return placed


def _plot_boxes(fig: Figure, renderer: RendererBase) -> list[_PlotBox]:
    """One entry per rectilinear plot box; twins share their first Axes' entry."""
    seen: set[int] = set()
    boxes: list[_PlotBox] = []
    for index, ax in enumerate(fig.axes):
        if not ax.get_visible() or ax.name != "rectilinear" or id(ax) in seen:
            continue
        owners = same_position_axes(ax)
        seen.update(id(owner) for owner in owners)
        try:
            frame = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        boxes.append(_PlotBox(index, owners, frame))
    return boxes


def _meets(a: Bbox, b: Bbox, touch: float) -> bool:
    return bool(
        min(a.x1, b.x1) - max(a.x0, b.x0) > touch
        and min(a.y1, b.y1) - max(a.y0, b.y0) > touch
    )


def _within(inner: Bbox, outer: Bbox) -> bool:
    return bool(
        inner.x0 >= outer.x0
        and inner.y0 >= outer.y0
        and inner.x1 <= outer.x1
        and inner.y1 <= outer.y1
    )


def _data_hits(box: Bbox, data: _Data, frame: Bbox, touch: float) -> list[_Hit]:
    """Bars, lines and markers of one plot box that ``box`` covers."""
    found: list[_Hit] = []
    if len(data.bars.box):
        x0, y0, x1, y1 = data.bars.box.T
        meets = np.minimum(box.x1, x1) - np.maximum(box.x0, x0) > touch
        meets &= np.minimum(box.y1, y1) - np.maximum(box.y0, y0) > touch
        found += [
            _Hit("bar", data.bars.names[i]) for i in np.flatnonzero(meets)
        ]
    clipped = _clip(box, frame)
    if clipped is None:
        return found
    lined: set[int] = set()
    for line in data.lines:
        # The stroke reaches ``half`` past its path; contact within
        # ``touch`` of the legend's edge is a touch.
        reach = clipped.padded(line.half - touch)
        if reach.width > 0 and reach.height > 0 and _segments_hit(line, reach):
            found.append(_Hit("line", line.name))
            lined.add(line.key)
    for marks in data.markers:
        if marks.key in lined or not len(marks.xy):
            continue
        run = _window(marks.xy[:, 0], marks.reach, clipped.x0, clipped.x1)
        x, y = marks.xy[run, 0], marks.xy[run, 1]
        nx = np.clip(x, clipped.x0, clipped.x1)
        ny = np.clip(y, clipped.y0, clipped.y1)
        r = np.maximum(marks.r[run] - touch, 0.0)
        if np.any((x - nx) ** 2 + (y - ny) ** 2 < r**2):
            found.append(_Hit("marker", marks.name))
    return found


def _text_hits(
    fig: Figure, box: Bbox, renderer: RendererBase, touch: float
) -> list[_Hit]:
    found: list[_Hit] = []
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        for text in ax.texts:
            if not text.get_visible() or not text.get_text().strip():
                continue
            try:
                extent = text.get_window_extent(renderer)
            except BBOX_ERRORS:
                continue
            if _meets(box, extent, touch):
                found.append(_Hit("text", _cut(text.get_text())))
    return found


class _Measured:
    """Each plot box's data, measured the first time a legend meets the box."""

    def __init__(self, fig: Figure, renderer: RendererBase) -> None:
        self._fig = fig
        self._renderer = renderer
        self._data: dict[int, _Data] = {}

    def of(self, plot: _PlotBox) -> _Data:
        if plot.axes_index not in self._data:
            self._data[plot.axes_index] = _measure(
                plot.owners, plot.frame, self._renderer, self._fig
            )
        return self._data[plot.axes_index]


def _hits(
    fig: Figure,
    placed: _Placed,
    legends: list[_Placed],
    boxes: list[_PlotBox],
    measured: _Measured,
    renderer: RendererBase,
    touch: float,
) -> tuple[list[_Hit], list[int]]:
    box = placed.box
    own: set[int] = set()
    own_frame: Bbox | None = None
    if placed.axes_index is not None:
        ax = fig.axes[placed.axes_index]
        own = {id(a) for a in same_position_axes(ax)}
        try:
            own_frame = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            own_frame = None
    inside_own = own_frame is not None and _within(box, own_frame)
    hits: list[_Hit] = []
    panels: list[int] = []
    for plot in boxes:
        if not _meets(box, plot.frame, touch):
            continue
        mine = bool(own & {id(owner) for owner in plot.owners})
        if (
            not mine
            and inside_own
            and own_frame is not None
            and _within(own_frame, plot.frame)
        ):
            continue  # drawn over the panel its own Axes sits on
        if placed.axes_index is not None and not mine:
            hits.append(_Hit("panel", f"axes[{plot.axes_index}]"))
        found = _data_hits(box, measured.of(plot), plot.frame, touch)
        if found:
            hits += found
            panels.append(plot.axes_index)
    hits += _text_hits(fig, box, renderer, touch)
    for other in legends:
        if other.legend is not placed.legend and _meets(box, other.box, touch):
            owner = (
                "figure legend"
                if other.axes_index is None
                else f"legend of axes[{other.axes_index}]"
            )
            hits.append(_Hit("legend", owner))
    return hits, panels


@register_check("LEGEND_ON_DATA", order=46)
def check_legend_on_data(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Flag legends drawn over data, texts, other legends or other panels."""
    legends = _legends(fig, renderer)
    if not legends:
        return []
    touch = _TOUCH_PT * fig.dpi / 72.0
    boxes = _plot_boxes(fig, renderer)
    measured = _Measured(fig, renderer)
    warnings: list[VisualWarning] = []
    for placed in legends:
        hits, panels = _hits(
            fig, placed, legends, boxes, measured, renderer, touch
        )
        if not hits:
            continue
        kinds: list[Covered] = sorted({hit.kind for hit in hits})
        names = list(dict.fromkeys(hit.name for hit in hits))
        labels = [_cut(text.get_text()) for text in placed.legend.get_texts()][
            :_MAX_LABELS
        ]
        owner = (
            "Figure legend"
            if placed.axes_index is None
            else f"Legend of axes[{placed.axes_index}]"
        )
        shown = ", ".join(repr(name) for name in names[:_MAX_NAMES])
        more = ", ..." if len(names) > _MAX_NAMES else ""
        warnings.append(
            VisualWarning(
                severity=Severity.WARNING,
                check_id="LEGEND_ON_DATA",
                message=(
                    f"{owner} covers "
                    f"{', '.join(kind + 's' for kind in kinds)} "
                    f"({shown}{more})"
                ),
                detail=wire(
                    LegendOnDataDetail(
                        legend_axes=placed.axes_index,
                        legend_labels=labels,
                        covered=kinds,
                        artists=names[:_MAX_NAMES],
                        panels=panels,
                    )
                ),
            )
        )
    return warnings


@register_fix("LEGEND_ON_DATA")
def _fix_legend_on_data(_warning: VisualWarning) -> list[str]:
    """Placements that keep a legend off the data."""
    return [
        "# Inside where it covers nothing, else outside its Axes\n"
        "dm.place_legend(ax)\ndm.simple_layout(fig)",
        "# Panels sharing one set of series: one legend for the figure\n"
        "dm.figure_legend(fig)\ndm.simple_layout(fig)",
        "# Many lines: name them at their ends instead of a legend\n"
        "dm.label_line_ends(ax)\ndm.simple_layout(fig)",
    ]
