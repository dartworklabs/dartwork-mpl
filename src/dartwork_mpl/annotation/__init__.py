"""Axes-based annotation helper module.

Provides ``label_axes`` for adding standard alphabetic sub-labels to figure
panels, ``annotate_value`` / ``annotate_corner`` / ``label_hline`` for compact
in-axes labels, ``label_bars`` for value labels on bars, ``place_legend`` for
axes legends, and ``arrow_axis`` for drawing bidirectional Low-High arrow
axes.
"""

from __future__ import annotations

__all__ = [
    "add_note",
    "annotate_corner",
    "annotate_value",
    "arrow_axis",
    "label_axes",
    "label_bars",
    "label_hline",
    "label_line_ends",
    "make_offset",
    "optimize_legend",
    "place_legend",
    "wrap_axis_label",
    "wrap_axis_labels",
]

import inspect
import re
import string
import warnings
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, cast

import matplotlib as mpl
import numpy as np
from matplotlib import cbook
from matplotlib.axes import Axes
from matplotlib.colors import to_hex, to_rgba
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.offsetbox import DrawingArea, TextArea
from matplotlib.text import Text
from matplotlib.transforms import Bbox, ScaledTranslation

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    anchor_outside,
    axes_titles,
    get_renderer,
    same_position_axes,
    spread_line_end_labels,
)
from ..scale import fs, fw
from ._bar_label_geometry import host_axes
from ._bar_labels import label_bars
from ._optimize_legend import optimize_legend

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.typing import LegendLocType

HorizontalAlign = Literal["left", "center", "right"]
VerticalAlign = Literal[
    "bottom", "baseline", "center", "center_baseline", "top"
]

# Internal vocabularies. The public parameters stay ``str``; each entry point
# parses its string once into one of these and the helpers take only them.
_ValueSide = Literal["above", "below", "right", "left"]
_Corner = Literal["upper left", "upper right", "lower left", "lower right"]
_HlineSide = Literal["above", "below"]
_HlineAnchor = Literal["left", "center", "right"]
_Axis = Literal["x", "y"]
_LegendCandidate = Literal[
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "upper center",
    "lower center",
]


def _parse_value_side(side: str) -> _ValueSide | Literal["auto"]:
    """Return ``annotate_value``'s ``side`` as its literal; raise ``ValueError`` if unknown."""
    match side:
        case "auto" | "above" | "below" | "left" | "right":
            return side
        case _:
            raise ValueError(
                "side must be 'auto', 'above', 'below', 'left', or 'right'"
            )


def _parse_corner(loc: str) -> _Corner:
    """Return ``annotate_corner``'s ``loc`` as its literal; raise ``ValueError`` if unknown."""
    match loc:
        case "upper left" | "upper right" | "lower left" | "lower right":
            return loc
        case _:
            raise ValueError(
                "loc must be 'upper left', 'upper right', 'lower left', "
                "or 'lower right'"
            )


def _parse_hline_side(side: str) -> _HlineSide:
    """Return ``label_hline``'s ``side`` as its literal; raise ``ValueError`` if unknown."""
    match side:
        case "above" | "below":
            return side
        case _:
            raise ValueError("side must be 'above' or 'below'")


def _parse_hline_x(x: str | float) -> _HlineAnchor | Literal["auto"] | float:
    """Return ``label_hline``'s ``x`` as an anchor literal, ``"auto"`` or an axes fraction.

    Raises ``ValueError`` for any other string.
    """
    if not isinstance(x, str):
        return float(x)
    match x:
        case "auto" | "left" | "center" | "right":
            return x
        case _:
            raise ValueError(
                "x must be 'auto', 'left', 'center', 'right', or a float"
            )


def _parse_axis(axis: str, message: str) -> _Axis:
    """Return ``"x"`` or ``"y"``; raise ``ValueError(message)`` for anything else."""
    match axis:
        case "x" | "y":
            return axis
        case _:
            raise ValueError(message)


def _auto_panel_labels(n: int) -> list[str]:
    """Spreadsheet-style panel labels: a, b, ..., z, aa, ab, ....

    ``string.ascii_lowercase[:n]`` silently truncated at 26, dropping
    labels for any grid larger than 26 panels; this extends past z.
    """
    labels: list[str] = []
    for i in range(n):
        chars = ""
        k = i
        while True:
            chars = string.ascii_lowercase[k % 26] + chars
            k = k // 26 - 1
            if k < 0:
                break
        labels.append(chars)
    return labels


# Gap between a panel label and the title it precedes, in label font sizes.
_PANEL_LABEL_GAP_EM = 0.5


def _shown_title(ax: Axes, loc: str) -> Text | None:
    """Return the ``loc`` title of ``ax`` when it is visible and not blank."""
    title = axes_titles(ax).get(loc)
    if title is None or not title.get_visible() or not title.get_text().strip():
        return None
    return title


def _title_in_the_way(ax: Axes, label: Text, gap_pt: float) -> Text | None:
    """Return the title of ``ax`` that ``label`` must sit before, if any.

    A left title always: the label belongs on its line, so every panel of a
    grid reads the same. A centre or right title only when ``label`` at its
    default spot would come within ``gap_pt`` of it (measured after a
    draw); then the leftmost such title.
    """
    left = _shown_title(ax, "left")
    if left is not None:
        return left
    others = [
        title
        for loc in ("center", "right")
        if (title := _shown_title(ax, loc)) is not None
    ]
    if not others:
        return None
    fig, renderer = _renderer_for_axes(ax)
    gap_px = gap_pt * fig.dpi / 72.0
    try:
        box = label.get_window_extent(renderer)
    except BBOX_ERRORS:
        return None
    hits: list[tuple[float, Text]] = []
    for title in others:
        try:
            ext = title.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if (
            box.x1 + gap_px > ext.x0
            and box.x0 < ext.x1 + gap_px
            and box.y1 > ext.y0
            and box.y0 < ext.y1
        ):
            hits.append((ext.x0, title))
    return min(hits, key=lambda hit: hit[0])[1] if hits else None


#: Properties ``label_axes`` sets on the label itself. Passing any spelling of
#: these used to collide inside ``ax.text`` (``ha``, ``va``, ``transform``) or be
#: accepted and then overridden without a word (the full alignment names).
_LABEL_AXES_OWNED_KWARGS = frozenset(
    {"ha", "horizontalalignment", "transform", "va", "verticalalignment"}
)

#: What the agent most likely meant, for the arguments #483 saw in real loops.
_LABEL_AXES_KWARG_HINTS = {
    "fmt": (
        "There is no format string: pass finished strings with labels=, "
        "for example labels=[f'({c})' for c in 'abc']. "
    ),
    "loc": "Use x= and y=, which are Axes-relative, for placement. ",
    "xy": "Use x= and y=, which are Axes-relative, for placement. ",
}

_LABEL_AXES_NATIVE_ESCAPE = (
    "For a different placement API, write the text yourself with "
    "ax.text(x, y, label, transform=ax.transAxes)."
)


#: ``Axes.text`` arguments of its own, which are not ``Text`` setters and so
#: would be misread as unsupported. Taken from the signature rather than listed,
#: so the check cannot drift from the matplotlib in use. Today: ``fontdict``.
_AXES_TEXT_OWN_PARAMETERS = frozenset(
    name
    for name, parameter in inspect.signature(Axes.text).parameters.items()
    if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    and name not in {"self", "x", "y", "s"}
)


def _label_kwarg_is_accepted(name: str) -> bool:
    """Report whether the label call takes ``name``, resolving matplotlib aliases."""
    if name in _AXES_TEXT_OWN_PARAMETERS:
        return True
    try:
        canonical = next(iter(cbook.normalize_kwargs({name: None}, Text)))
    except TypeError:
        return False
    return callable(getattr(Text, f"set_{canonical}", None))


def _reject_unusable_label_kwargs(kwargs: dict[str, Any]) -> None:
    """Fail named, before any label exists, for kwargs that cannot be honoured."""
    for name in kwargs:
        if name in _LABEL_AXES_OWNED_KWARGS:
            raise TypeError(
                f"label_axes() sets {name!r} on the panel labels itself, so "
                f"passing {name!r} cannot take effect. Position the labels with "
                f"x= and y= (both Axes-relative). {_LABEL_AXES_NATIVE_ESCAPE}"
            )
        if not _label_kwarg_is_accepted(name):
            raise AttributeError(
                f"label_axes() does not support {name!r}. It takes labels=, x=, "
                f"y=, fontsize=, fontweight= and any matplotlib Text property "
                f"(color=, rotation=, fontstyle=, ...). "
                f"{_LABEL_AXES_KWARG_HINTS.get(name, '')}"
                f"{_LABEL_AXES_NATIVE_ESCAPE}"
            )


def label_axes(
    axes: list[Axes] | np.ndarray[Any, Any],
    labels: list[str] | None = None,
    fontsize: float | None = None,
    fontweight: str = "normal",
    x: float | str = "auto",
    y: float | None = None,
    **kwargs: Any,
) -> list[Text]:
    """Add standardized identification labels (a, b, c, ...) to subplot panels.

    Commonly used in academic papers and reports to annotate multiple panels
    of a figure, placing labels at the left edge or top corner of each Axes.

    Parameters
    ----------
    axes : list[Axes] | np.ndarray
        List or array of Axes objects to label.
    labels : list[str] | None, optional
        Custom text labels. If None, lowercase letters (a, b, c, ...)
        are assigned automatically.
    fontsize : float | None, optional
        Font size for the labels. If ``None`` (default), resolves to
        ``fs(1)`` so panel labels track the active preset's base font
        size instead of a fixed point value.
    fontweight : str, optional
        Font weight for the labels. Default is "normal".
    x : float | str, optional
        Horizontal position in Axes-relative coordinates (may exceed 0.0-1.0).
        If "auto", the optimal x position is determined based on whether
        a y-axis label is present (-0.18 or -0.02). With ``"auto"`` and a
        title in the way, the label is placed before the title instead: on
        the title's line, its right edge half a label font size left of
        the title's start, following the title wherever it moves (a later
        ``simple_layout``, a legend above). A left title
        (``set_title(..., loc="left")``) is always in the way, so every
        panel of a grid reads ``a  Title``; a centre or right title only
        when the label at its default spot would touch it. Set the titles
        before calling this; their text, size and weight are not changed.
    y : float | None, optional
        Vertical position in Axes-relative coordinates. ``None`` (default)
        is 1.05, or the title's line when the label is placed before a
        title. A given ``y`` is kept in both cases.
    **kwargs
        Additional text properties passed to ``ax.text()`` (``ax.annotate``
        for a label placed before a title). An argument this helper cannot
        honour is reported by name: one ``Text`` does not accept raises
        ``AttributeError``, and a property the helper sets itself
        (``transform``, and either spelling of the alignments) raises
        ``TypeError``. ``fontdict`` reaches ``ax.text`` but not
        ``ax.annotate``, so it fails on a panel whose label moves onto a
        title's line; passing the properties directly (``color=``,
        ``fontsize=``) works on both paths.

    Returns
    -------
    list
        List of created Text objects.
    """
    _reject_unusable_label_kwargs(kwargs)

    if fontsize is None:
        fontsize = fs(1)

    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = _auto_panel_labels(len(axes))

    texts: list[Text] = []
    for ax, label in zip(axes, labels, strict=False):
        if x == "auto":
            has_ylabel = ax.get_ylabel().strip() != ""
            x_pos = -0.18 if has_ylabel else -0.02
        else:
            x_pos = float(x)

        t = ax.text(
            x_pos,
            1.05 if y is None else y,
            label,
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va="bottom",
            ha="left",
            **kwargs,
        )
        if x == "auto":
            size_pt = t.get_fontproperties().get_size_in_points()
            gap_pt = _PANEL_LABEL_GAP_EM * size_pt
            title = _title_in_the_way(ax, t, gap_pt)
            if title is not None:
                t.remove()
                t = ax.annotate(
                    label,
                    xy=(0.0, 0.0 if y is None else y),
                    xycoords=title if y is None else (title, "axes fraction"),
                    xytext=(-gap_pt, 0.0),
                    textcoords="offset points",
                    fontsize=fontsize,
                    fontweight=fontweight,
                    va="bottom",
                    ha="right",
                    annotation_clip=False,
                    **kwargs,
                )
        texts.append(t)

    return texts


def _renderer_for_axes(ax: Axes) -> tuple[Figure | SubFigure, RendererBase]:
    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    fig.canvas.draw()
    return fig, get_renderer(fig)


def _padded_bbox(
    x0: float, y0: float, x1: float, y1: float, pad: float
) -> Bbox:
    return Bbox.from_extents(x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _overlap_area(a: Bbox, b: Bbox) -> float:
    width = min(a.x1, b.x1) - max(a.x0, b.x0)
    height = min(a.y1, b.y1) - max(a.y0, b.y0)
    if width <= 0 or height <= 0:
        return 0.0
    return float(width * height)


def _intersection_area(a: Bbox, b: Bbox) -> float:
    return _overlap_area(a, b)


def _outside_area(inner: Bbox, outer: Bbox) -> float:
    area = max(float(inner.width * inner.height), 0.0)
    return area - _intersection_area(inner, outer)


def _bbox_inside(bbox: Bbox, container: Bbox, tol_px: float = 0.5) -> bool:
    return bool(
        bbox.x0 >= container.x0 - tol_px
        and bbox.x1 <= container.x1 + tol_px
        and bbox.y0 >= container.y0 - tol_px
        and bbox.y1 <= container.y1 + tol_px
    )


def _collision_area(bbox: Bbox, obstacles: list[Bbox]) -> float:
    return sum(_overlap_area(bbox, obstacle) for obstacle in obstacles)


def _line_segment_bboxes(ax: Axes, pad_px: float = 2.0) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for line in ax.lines:
        if not line.get_visible():
            continue
        xy = np.asarray(line.get_xydata(), dtype=float)
        if len(xy) < 2:
            continue
        points = line.get_transform().transform(xy)
        points = points[np.isfinite(points).all(axis=1)]
        if len(points) < 2:
            continue
        for left, right in pairwise(points):
            bboxes.append(
                _padded_bbox(
                    float(min(left[0], right[0])),
                    float(min(left[1], right[1])),
                    float(max(left[0], right[0])),
                    float(max(left[1], right[1])),
                    pad_px,
                )
            )
    return bboxes


def _patch_bboxes(ax: Axes) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for patch in ax.patches:
        if not patch.get_visible():
            continue
        try:
            bbox = (
                patch.get_path()
                .transformed(patch.get_transform())
                .get_extents()
            )
        except (RuntimeError, ValueError, AttributeError):
            continue
        if bbox.width > 0 and bbox.height > 0:
            bboxes.append(bbox)
    return bboxes


def _collection_bboxes(ax: Axes, pad_px: float = 6.0) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for collection in ax.collections:
        if not collection.get_visible():
            continue
        try:
            offsets = collection.get_offsets()
            points = collection.get_offset_transform().transform(offsets)
        except (RuntimeError, ValueError, AttributeError):
            continue
        if len(points) == 0:
            continue
        points = points[np.isfinite(points).all(axis=1)]
        for x, y in points:
            bboxes.append(
                _padded_bbox(float(x), float(y), float(x), float(y), pad_px)
            )
    return bboxes


def _text_bboxes(texts: list[Text], renderer: Any) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            bbox = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if bbox.width > 0 and bbox.height > 0:
            bboxes.append(bbox)
    return bboxes


def _data_occupancy_bboxes(ax: Axes, renderer: Any | None = None) -> list[Bbox]:
    bboxes = [*_line_segment_bboxes(ax), *_patch_bboxes(ax)]
    bboxes.extend(_collection_bboxes(ax))
    if renderer is not None:
        bboxes.extend(_text_bboxes(list(ax.texts), renderer))
    return bboxes


def _set_annotation_offset(text: Text, offset: tuple[float, float]) -> None:
    text.set_position(offset)
    if hasattr(text, "xyann"):
        text.xyann = offset


def _annotation_side_spec(
    side: _ValueSide, offset_pt: float
) -> tuple[tuple[float, float], HorizontalAlign, VerticalAlign]:
    """Return the point offset and alignment that put a label on ``side`` of its point."""
    offset = float(offset_pt)
    match side:
        case "above":
            return (0.0, offset), "center", "bottom"
        case "below":
            return (0.0, -offset), "center", "top"
        case "right":
            return (offset, 0.0), "left", "center"
        case "left":
            return (-offset, 0.0), "right", "center"


def _apply_annotation_side(
    text: Text, side: _ValueSide, offset_pt: float
) -> None:
    """Move ``text`` to ``side`` of its anchor point, ``offset_pt`` points away."""
    offset, ha, va = _annotation_side_spec(side, offset_pt)
    text.set_horizontalalignment(ha)
    text.set_verticalalignment(va)
    _set_annotation_offset(text, offset)


def _annotation_extent(
    text: Text, fig: Figure | SubFigure, renderer: RendererBase
) -> Bbox | None:
    fig.canvas.draw()
    try:
        return text.get_window_extent(renderer)
    except BBOX_ERRORS:
        return None


def annotate_value(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    *,
    side: str = "auto",
    offset_pt: float = 3.0,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Annotate one data value with a compact point-offset label.

    ``side="auto"`` evaluates above, below, right, then left. Above/below are
    used only when the rendered label stays inside the axes spine and avoids
    same-axes data/text. If vertical placement would leave the spine region,
    the label moves horizontally from the data point instead of flipping to the
    opposite vertical side. Explicit ``side="left"`` / ``"right"`` is
    supported, including ``arrowprops``; all offsets are single-axis point
    offsets so arrows remain straight horizontal or vertical connectors.

    The label is one weight step heavier than the preset's base weight
    (``fontweight=fw(1)``) so a data value reads apart from captions;
    pass ``fontweight`` (or ``weight``) to override. ``fontsize`` defaults
    to one step below the base, ``fs(-1)``, the size every value label
    takes (7 pt under ``report``, 16.9 pt under ``presentation``).
    """
    if fontsize is None:
        fontsize = fs(-1)
    requested = _parse_value_side(side)
    if "fontweight" not in kw and "weight" not in kw:
        kw["fontweight"] = fw(1)

    existing_texts = list(ax.texts)
    initial_side: _ValueSide = "above" if requested == "auto" else requested
    offset, ha, va = _annotation_side_spec(initial_side, offset_pt)

    ann = ax.annotate(
        text,
        xy=(x, y),
        xycoords="data",
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )

    if requested != "auto":
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann

    obstacles = [
        *_line_segment_bboxes(ax),
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]
    scores: list[tuple[float, _ValueSide]] = []

    vertical_sides: tuple[_ValueSide, ...] = ("above", "below")
    for candidate in vertical_sides:
        _apply_annotation_side(ann, candidate, offset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        if outside <= 0 and collision <= 0:
            return ann
        if outside > 0:
            break

    horizontal_sides: tuple[_ValueSide, ...] = ("right", "left")
    for candidate in horizontal_sides:
        _apply_annotation_side(ann, candidate, offset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        if outside <= 0 and collision <= 0:
            return ann

    if scores:
        _score, best_side = min(scores, key=lambda item: item[0])
        _apply_annotation_side(ann, best_side, offset_pt)
        fig.canvas.draw()

    return ann


_CORNER_SPECS: dict[
    _Corner,
    tuple[
        tuple[float, float], tuple[float, float], HorizontalAlign, VerticalAlign
    ],
] = {
    "upper left": ((0.0, 1.0), (1.0, -1.0), "left", "top"),
    "upper right": ((1.0, 1.0), (-1.0, -1.0), "right", "top"),
    "lower left": ((0.0, 0.0), (1.0, 1.0), "left", "bottom"),
    "lower right": ((1.0, 0.0), (-1.0, 1.0), "right", "bottom"),
}


def _corner_order(loc: _Corner) -> list[_Corner]:
    """Return the corners to try: ``loc`` first, then the rest in reading order."""
    order: list[_Corner] = [
        "upper left",
        "upper right",
        "lower left",
        "lower right",
    ]
    if loc == "upper left":
        return order
    return [loc, *[candidate for candidate in order if candidate != loc]]


def _apply_corner(text: Text, loc: _Corner, inset_pt: float) -> None:
    """Align ``text`` to corner ``loc`` and inset it ``inset_pt`` points inward."""
    _anchor, offset_direction, ha, va = _CORNER_SPECS[loc]
    text.set_horizontalalignment(ha)
    text.set_verticalalignment(va)
    _set_annotation_offset(
        text,
        (
            offset_direction[0] * float(inset_pt),
            offset_direction[1] * float(inset_pt),
        ),
    )


def add_note(fig: Figure, text: str, **kw: Any) -> Text:
    """Add a source or note line under the plot, in the preset's note style.

    One call for "add a source note" / "그림 아래에 출처를 적어줘", so every
    agent draws the same line: the figure's lower-left corner, left-aligned,
    one step below the preset font (``dm.fs(-1)``) in the preset text colour.
    :func:`dartwork_mpl.simple_layout` keeps the axes, tick labels and axis
    labels above it with the preset's ``axes.labelpad`` between them. A
    ``fontsize=``, ``color=`` or other ``Text`` keyword the user names wins::

        dm.add_note(fig, "Source: internal web logs")
        dm.simple_layout(fig)

    Returns the :class:`~matplotlib.text.Text`.
    """

    style: dict[str, Any] = {"ha": "left", "va": "bottom", "fontsize": fs(-1)}
    style.update(kw)
    note = fig.text(0.0, 0.0, text, **style)
    # simple_layout reserves this gap above the note (layout slice reads it).
    note._dm_layout_gap_pt = float(mpl.rcParams["axes.labelpad"])  # type: ignore[attr-defined]
    return note


def _last_point(line: Any) -> tuple[float, float] | None:
    """The last finite (x, y) of a line in drawing order, as data floats."""
    x = np.asarray(line.convert_xunits(line.get_xdata()), dtype=float)
    y = np.asarray(line.convert_yunits(line.get_ydata()), dtype=float)
    if x.size == 0 or x.shape != y.shape:
        return None
    finite = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
    if finite.size == 0:
        return None
    i = finite[-1]
    return float(x[i]), float(y[i])


def label_line_ends(
    ax: Axes, lines: Any = None, *, gap_pt: float | None = None, **kw: Any
) -> list[Text]:
    """Name each line at its last point instead of a legend, in one style.

    One call for "label the line ends instead of a legend" / "범례 대신 선
    끝에 이름을", so every caller draws the same labels:

    - the line's label, left-aligned ``gap_pt`` (default the preset's
      ``axes.labelpad``) right of its last finite point, vertically centred;
    - the preset text size and weight;
    - the line's colour, darkened or lightened only as far as text needs to
      read on the axes background (:func:`dartwork_mpl.ensure_contrast`,
      4.5:1);
    - labels that would overlap move apart vertically, keeping their order.

    The axes' legend is removed and the axis limits stay;
    :func:`dartwork_mpl.simple_layout` makes room for the labels. ``lines``
    picks the lines (default: every visible line whose label does not start
    with ``_``). A ``fontsize=``, ``color=`` or other ``Text`` keyword wins::

        dm.label_line_ends(ax)
        dm.simple_layout(fig)

    Returns the labels in the order of ``lines``.
    """
    import matplotlib.colors as mcolors

    from .._colors.contrast import ensure_contrast

    if lines is None:
        lines = [
            ln
            for ln in ax.get_lines()
            if ln.get_visible() and not str(ln.get_label()).startswith("_")
        ]
    gap = float(mpl.rcParams["axes.labelpad"] if gap_pt is None else gap_pt)
    background = mcolors.to_rgba(ax.patch.get_facecolor())
    if not ax.patch.get_visible() or background[3] == 0:
        background = mcolors.to_rgba(ax.figure.get_facecolor())
    legend = ax.get_legend()
    if legend is not None:
        legend.remove()

    placed: list[tuple[Text, tuple[float, float]]] = []
    for line in lines:
        end = _last_point(line)
        if end is None:
            continue
        style: dict[str, Any] = {
            "color": ensure_contrast(line.get_color(), background),
            "ha": "left",
            "va": "center",
            "annotation_clip": False,
        }
        style.update(kw)
        label = ax.annotate(
            str(line.get_label()),
            xy=end,
            xycoords="data",
            xytext=(gap, 0.0),
            textcoords="offset points",
            **style,
        )
        placed.append((label, end))
    if len(placed) < 2:
        return [t for t, _ in placed]

    _fig, renderer = _renderer_for_axes(ax)
    spread_line_end_labels(
        ax, [t for t, _ in placed], [e for _, e in placed], gap, renderer
    )
    return [t for t, _ in placed]


def annotate_corner(
    ax: Axes,
    text: str,
    *,
    loc: str = "upper left",
    inset_pt: float = 3.0,
    avoid_overlap: bool = True,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Place narrative text tightly inside an axes corner.

    The anchor is in axes-fraction coordinates with a point inset toward the
    plot interior, so multi-line text stays attached to the selected spine
    corner. With ``avoid_overlap=True`` the helper measures rendered data and
    existing text, then tries corners in upper-left, upper-right, lower-left,
    lower-right order (starting with an explicit ``loc`` when provided).
    """
    if fontsize is None:
        fontsize = fs(-2)
    corner = _parse_corner(loc)

    existing_texts = list(ax.texts)
    anchor, offset_direction, ha, va = _CORNER_SPECS[corner]
    ann = ax.annotate(
        text,
        xy=anchor,
        xycoords="axes fraction",
        xytext=(
            offset_direction[0] * float(inset_pt),
            offset_direction[1] * float(inset_pt),
        ),
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if not avoid_overlap:
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann
    obstacles = [
        *_line_segment_bboxes(ax),
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]

    scores: list[tuple[float, _Corner]] = []
    for candidate in _corner_order(corner):
        anchor, _offset_direction, _ha, _va = _CORNER_SPECS[candidate]
        ann.xy = anchor
        _apply_corner(ann, candidate, inset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        if outside <= 0 and collision <= 0:
            return ann

    if scores:
        _score, best_loc = min(scores, key=lambda item: item[0])
        anchor, _offset_direction, _ha, _va = _CORNER_SPECS[best_loc]
        ann.xy = anchor
        _apply_corner(ann, best_loc, inset_pt)
        fig.canvas.draw()
    return ann


def _display_x_to_data(ax: Axes, display_x: float, y: float) -> float:
    display_y = ax.transData.transform((ax.get_xlim()[0], y))[1]
    return float(ax.transData.inverted().transform((display_x, display_y))[0])


def _axes_fraction_to_data_x(ax: Axes, fraction: float, y: float) -> float:
    fig, renderer = _renderer_for_axes(ax)
    del fig
    axes_bbox = ax.get_window_extent(renderer)
    display_x = axes_bbox.x0 + axes_bbox.width * float(fraction)
    return _display_x_to_data(ax, display_x, y)


def _visible_hline_span(ax: Axes, y: float) -> tuple[float, float]:
    fig, renderer = _renderer_for_axes(ax)
    del fig
    axes_bbox = ax.get_window_extent(renderer)
    target_y = ax.transData.transform((ax.get_xlim()[0], y))[1]
    display_xs: list[float] = []
    tolerance = 2.0

    for line in ax.lines:
        if not line.get_visible():
            continue
        xy = np.asarray(line.get_xydata(), dtype=float)
        if len(xy) < 2:
            continue
        try:
            points = line.get_transform().transform(xy)
        except (RuntimeError, ValueError, AttributeError):
            continue
        points = points[np.isfinite(points).all(axis=1)]
        for left, right in pairwise(points):
            if (
                abs(float(left[1]) - target_y) > tolerance
                or abs(float(right[1]) - target_y) > tolerance
            ):
                continue
            x0 = max(min(float(left[0]), float(right[0])), axes_bbox.x0)
            x1 = min(max(float(left[0]), float(right[0])), axes_bbox.x1)
            if x1 >= x0:
                display_xs.extend([x0, x1])

    if not display_xs:
        return (
            _display_x_to_data(ax, axes_bbox.x0, y),
            _display_x_to_data(ax, axes_bbox.x1, y),
        )

    left_data = _display_x_to_data(ax, min(display_xs), y)
    right_data = _display_x_to_data(ax, max(display_xs), y)
    return (left_data, right_data)


def _hline_x_spec(
    ax: Axes, y: float, x: _HlineAnchor | float
) -> tuple[float, HorizontalAlign]:
    """Return the data x and alignment for a label at anchor ``x`` of the line at ``y``.

    A float ``x`` is an axes fraction; an anchor attaches to the visible
    line's left end, right end or midpoint.
    """
    left, right = _visible_hline_span(ax, y)
    match x:
        case "left":
            return left, "left"
        case "right":
            return right, "right"
        case "center":
            return (left + right) / 2.0, "center"
        case float():
            return _axes_fraction_to_data_x(ax, x, y), "center"


def label_hline(
    ax: Axes,
    y: float,
    text: str,
    *,
    x: str | float = "right",
    side: str = "above",
    gap_pt: float = 2.0,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Place a label tightly against a horizontal reference line.

    ``x="left"`` / ``"right"`` attaches to the visible horizontal line
    endpoint inside the axes; ``"center"`` is available when central placement
    is intentional. ``x="auto"`` measures both endpoints and chooses the less
    obstructed side. Float ``x`` values keep the legacy axes-fraction meaning.
    Vertical movement uses a single-axis point offset so the label stays
    attached to the reference line rather than drifting diagonally.
    """
    if fontsize is None:
        fontsize = fs(-2)
    line_side = _parse_hline_side(side)
    anchor = _parse_hline_x(x)

    va = "bottom" if line_side == "above" else "top"
    offset = (0.0, float(gap_pt) if line_side == "above" else -float(gap_pt))
    existing_texts = list(ax.texts)
    x_pos, ha = _hline_x_spec(ax, y, "right" if anchor == "auto" else anchor)
    ann = ax.annotate(
        text,
        xy=(x_pos, y),
        xycoords="data",
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if anchor != "auto":
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann
    obstacles = [
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]
    scores: list[tuple[float, _HlineAnchor]] = []
    end_anchors: tuple[_HlineAnchor, ...] = ("right", "left")
    for candidate in end_anchors:
        x_pos, ha = _hline_x_spec(ax, y, candidate)
        ann.xy = (x_pos, y)
        ann.set_horizontalalignment(ha)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        score = _outside_area(bbox, axes_bbox) + _collision_area(
            bbox, obstacles
        )
        scores.append((score, candidate))
        if score <= 0:
            return ann

    if scores:
        _score, best_side = min(scores, key=lambda item: item[0])
        x_pos, ha = _hline_x_spec(ax, y, best_side)
        ann.xy = (x_pos, y)
        ann.set_horizontalalignment(ha)
        fig.canvas.draw()
    return ann


def _legend_for_loc(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    loc: str,
    legend_kw: dict[str, Any],
) -> Legend:
    """Draw (replacing any existing) the axes legend at matplotlib location ``loc``."""
    # A caller's loc is passed through unchanged; Matplotlib validates it.
    return ax.legend(
        handles, labels, loc=cast("LegendLocType", loc), **legend_kw
    )


@dataclass(frozen=True)
class _MeasuredLegend:
    """A trial legend placement whose rendered box was measured.

    ``score`` is the overlap/outside penalty (lower is better) and
    ``collision_free`` says the box touches no data and stays inside the axes.
    """

    loc: _LegendCandidate
    ncol: int
    score: float
    collision_free: bool


@dataclass(frozen=True)
class _UnmeasuredLegend:
    """A trial legend placement whose rendered box could not be measured."""

    loc: _LegendCandidate
    ncol: int


_LegendTrial: TypeAlias = _MeasuredLegend | _UnmeasuredLegend


def _trial_score(trial: _LegendTrial) -> float:
    """Return the trial's penalty; an unmeasured trial ranks last (``inf``)."""
    match trial:
        case _MeasuredLegend(score=score):
            return score
        case _UnmeasuredLegend():
            return float("inf")


def _best_trial(trials: list[_LegendTrial]) -> _LegendTrial:
    """Return the lowest-penalty trial, the earliest one on a tie.

    ``trials`` must be non-empty (``ValueError`` otherwise).
    """
    return min(trials, key=_trial_score)


def _mark_placement(legend: Legend, trial: _LegendTrial) -> None:
    """Set the documented ``_dm_collision_free`` / ``_dm_collision_score`` attributes.

    An unmeasured placement reports ``False`` and ``inf``.
    """
    match trial:
        case _MeasuredLegend(score=score, collision_free=collision_free):
            pass
        case _UnmeasuredLegend():
            score, collision_free = float("inf"), False
    legend._dm_collision_free = collision_free  # type: ignore[attr-defined]
    legend._dm_collision_score = score  # type: ignore[attr-defined]


def _score_legend_candidate(
    legend_bbox: Bbox, data_bboxes: list[Bbox], axes_bbox: Bbox, ncol: int
) -> float:
    area = max(float(legend_bbox.width * legend_bbox.height), 1.0)
    overlap = sum(_overlap_area(legend_bbox, bbox) for bbox in data_bboxes)
    outside = _outside_area(legend_bbox, axes_bbox)
    height_ratio = float(legend_bbox.height / max(axes_bbox.height, 1.0))
    tall_penalty = 0.0
    if ncol == 1 and height_ratio > 0.55:
        tall_penalty = height_ratio - 0.55
    return (overlap / area) + 4.0 * (outside / area) + tall_penalty


def _legend_candidate_ncols(
    labels: list[str], legend_kw: dict[str, Any]
) -> list[int]:
    explicit = legend_kw.get("ncol", legend_kw.get("ncols"))
    if explicit is not None:
        return [int(explicit)]
    max_ncol = min(3, max(len(labels), 1))
    return list(range(1, max_ncol + 1))


# The legend's own anchor point (matplotlib ``loc``) for each outside side:
# the legend edge that faces the Axes touches the anchor.
_OUTSIDE_LEGEND_LOCS: dict[OutsideSide, LegendLocType] = {
    "above": "lower center",
    "below": "upper center",
    "right": "center left",
    "left": "center right",
}


def _parse_outside_side(loc: str) -> OutsideSide | None:
    """Return ``loc`` as an outside side, or ``None`` for a matplotlib ``loc``."""
    match loc:
        case "above" | "below" | "right" | "left":
            return loc
        case _:
            return None


def _outside_ncols(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    legend_kw: dict[str, Any],
    renderer: RendererBase,
) -> int:
    """Return the column count for an outside legend on ``side`` of ``ax``.

    Right and left legends are one column. Above and below, the fewest
    rows whose rendered legend is no wider than the Axes win: one row when
    it fits, otherwise two, and so on; a single column when nothing fits.
    ``legend_kw`` must not hold ``ncol`` / ``ncols``.
    """
    if side in ("right", "left"):
        return 1
    try:
        axes_width = ax.get_window_extent(renderer).width
    except BBOX_ERRORS:
        return 1
    count = len(labels)
    tried: set[int] = set()
    for rows in range(1, count + 1):
        ncols = -(-count // rows)  # ceil(count / rows)
        if ncols in tried:
            continue
        tried.add(ncols)
        legend = ax.legend(
            handles,
            labels,
            loc=_OUTSIDE_LEGEND_LOCS[side],
            ncols=ncols,
            **legend_kw,
        )
        try:
            width = legend.get_window_extent(renderer).width
        except BBOX_ERRORS:
            continue
        if width <= axes_width:
            return ncols
    return 1


def _place_outside_legend(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    kw: dict[str, Any],
) -> Legend:
    """Draw the legend of ``ax`` outside ``side``, past its tick and axis labels."""
    for key in ("bbox_to_anchor", "bbox_transform"):
        if key in kw:
            raise ValueError(
                f"place_legend(loc={side!r}) anchors the legend itself; "
                f"remove {key}= or pass a matplotlib loc instead"
            )
    legend_kw = dict(kw)
    explicit = legend_kw.pop("ncols", None)
    explicit = legend_kw.pop("ncol", explicit)
    _fig, renderer = _renderer_for_axes(ax)
    ncols = (
        int(explicit)
        if explicit is not None
        else _outside_ncols(ax, handles, labels, side, legend_kw, renderer)
    )
    legend = ax.legend(
        handles,
        labels,
        loc=_OUTSIDE_LEGEND_LOCS[side],
        ncols=ncols,
        **legend_kw,
    )
    anchor_outside(legend, ax, side, renderer)
    return legend


def _may_go_outside(kw: dict[str, Any]) -> bool:
    """Whether a ``best`` legend may fall back outside (no caller anchor)."""
    return "bbox_to_anchor" not in kw and "bbox_transform" not in kw


def _covers_data(ax: Axes, legend: Legend, renderer: Any) -> bool:
    """Whether the drawn ``legend`` box overlaps data of ``ax`` or its twins."""
    ax.figure.canvas.draw()
    try:
        bbox = legend.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    return _collision_area(bbox, _pair_occupancy_bboxes(ax, renderer)) > 0


def _pair_occupancy_bboxes(ax: Axes, renderer: Any) -> list[Bbox]:
    """Data occupancy of ``ax`` and every twin drawn in the same box."""
    return [
        bbox
        for owner in same_position_axes(ax)
        for bbox in _data_occupancy_bboxes(owner, renderer)
    ]


def _legend_entries(ax: Axes) -> tuple[list[Any], list[str]]:
    """The labelled artists of ``ax`` as legend handles and labels."""
    handles, labels = ax.get_legend_handles_labels()
    return list(handles), list(labels)


_EntrySignature: TypeAlias = tuple[str, tuple[type, ...]]
"""One legend entry: its text and the artist types its handle draws."""

# What reading a legend's offset boxes or building a probe legend can raise on
# a handle or handler matplotlib lays out unexpectedly: a missing attribute or
# child (AttributeError, IndexError) or a rejected argument (TypeError,
# ValueError). Anything else is a bug and propagates.
_UNREADABLE = (AttributeError, IndexError, TypeError, ValueError)


def _entry_signatures(legend: Legend) -> list[_EntrySignature]:
    """Each drawn entry of ``legend``, in legend order: text and handle artist types.

    Read through the public ``get_children`` of the legend's offset boxes:
    an entry is the box that holds a handle area and a text. A tuple handle
    draws several artists where a plain one draws one, and a custom handler
    draws its own types, so the signature tells a rebuildable entry from one
    that is not. A legend with no readable entry gives ``[]``.
    """
    found: list[_EntrySignature] = []

    def walk(node: Any) -> None:
        children = node.get_children()
        areas = [c for c in children if isinstance(c, DrawingArea)]
        texts = [c for c in children if isinstance(c, TextArea)]
        if areas and texts:
            found.append(
                (
                    texts[0].get_text(),
                    tuple(type(a) for a in areas[0].get_children()),
                )
            )
            return
        for child in children:
            if child.__class__.__module__ == "matplotlib.offsetbox":
                walk(child)

    walk(legend.get_children()[0])
    return found


def _probe_signatures(
    host: Axes,
    handles: list[Any],
    labels: list[str],
    handler_map: dict[Any, Any],
) -> list[_EntrySignature]:
    """What plain ``handles`` draw through ``handler_map``, via a detached legend."""
    probe = Legend(host, handles, labels, handler_map=handler_map)
    return _entry_signatures(probe)


def _rebuildable(
    legend: Legend, host: Axes, candidates: list[tuple[list[Any], list[str]]]
) -> bool:
    """Whether ``legend`` is what plain artists would draw, entry for entry.

    ``candidates`` are the (handles, labels) the legend may have been built
    from: the whole pair's artists (a hand merge, or the merged legend) or one
    Axes' own. The legend is rebuildable when its entries equal, position by
    position and in count, what some candidate draws through the legend's own
    ``handler_map``. Fails safe: an empty or unreadable legend, or any
    ``_UNREADABLE`` error while reading it or the probe, is not rebuildable.
    """
    handler_map: dict[Any, Any] = dict(legend.get_legend_handler_map())
    try:
        drawn = _entry_signatures(legend)
        if not drawn:
            return False
        return any(
            handles
            and drawn == _probe_signatures(host, handles, labels, handler_map)
            for handles, labels in candidates
        )
    except _UNREADABLE:
        return False


def _legend_settings(
    legend: Legend | None, default: Legend | None
) -> dict[str, Any]:
    """The settings of ``legend`` a rebuilt legend repeats, as ``Legend`` keywords.

    Only what the public ``Legend`` API reads, and only what differs from
    ``default`` (a fresh legend of the same entries under the current
    preset), so an untouched default stays a default and follows a later
    style change. ``ncols`` has no public getter: pass it to ``place_legend``
    to keep it.
    """
    if legend is None or default is None:
        return {}
    kept: dict[str, Any] = {}
    title = legend.get_title()
    if title.get_text():
        kept["title"] = title.get_text()
    if title.get_fontproperties() != default.get_title().get_fontproperties():
        kept["title_fontproperties"] = title.get_fontproperties().copy()
    default_map = Legend.get_default_handler_map()
    custom = {
        key: handler
        for key, handler in legend.get_legend_handler_map().items()
        if default_map.get(key) is not handler
    }
    if custom:
        kept["handler_map"] = custom
    if legend.get_frame_on() != default.get_frame_on():
        kept["frameon"] = legend.get_frame_on()
    if legend.get_alignment() != default.get_alignment():
        kept["alignment"] = legend.get_alignment()
    if legend.markerscale != default.markerscale:
        kept["markerscale"] = legend.markerscale
    if legend.get_draggable():
        kept["draggable"] = True
    texts, defaults = legend.get_texts(), default.get_texts()
    if texts and defaults:
        if texts[0].get_fontproperties() != defaults[0].get_fontproperties():
            kept["prop"] = texts[0].get_fontproperties().copy()
        colors = {to_rgba(t.get_color()) for t in texts}
        if len(colors) == 1 and colors != {to_rgba(defaults[0].get_color())}:
            kept["labelcolor"] = to_hex(texts[0].get_color(), keep_alpha=True)
    return kept


def _caller_wins(kept: dict[str, Any], kw: dict[str, Any]) -> dict[str, Any]:
    """Kept settings under the caller's keywords; a caller size drops the kept font."""
    merged = {**kept, **kw}
    if "fontsize" in kw and "prop" not in kw:
        merged.pop("prop", None)
    if "title_fontsize" in kw and "title_fontproperties" not in kw:
        merged.pop("title_fontproperties", None)
    return merged


def _merge_twin_legends(
    ax: Axes,
) -> tuple[Axes, list[Any], list[str], dict[str, Any], Legend | None]:
    """One legend for a twin pair: every partner's entries, on the top axes.

    The legend goes on the top twin (the Axes drawn last), so no partner's
    data is drawn over it; the partners' own legends are removed after their
    settings (title, ``handler_map`` and so on) are read for the rebuild. A
    single Axes returns itself and its own entries.

    The last item is a legend to leave untouched: one that is not what the
    pair's own artists would draw (tuple handles, custom handlers, explicit
    labels). The explicit legend wins and nothing is removed.
    """
    owners = same_position_axes(ax)
    host = host_axes(ax)
    parent = host.get_figure(root=False)
    order = parent.axes if parent is not None else owners
    handles: list[Any] = []
    labels: list[str] = []
    seen: set[str] = set()
    for owner in sorted(owners, key=order.index):
        for handle, label in zip(*_legend_entries(owner), strict=True):
            if label not in seen:
                seen.add(label)
                handles.append(handle)
                labels.append(label)
    existing = [
        legend for o in owners if (legend := o.get_legend()) is not None
    ]
    for owner in owners:
        legend = owner.get_legend()
        if legend is None:
            continue
        own = _legend_entries(owner)
        if not _rebuildable(legend, host, [(handles, labels), own]):
            return host, handles, labels, {}, legend
    source = host.get_legend() or next(iter(existing), None)
    default = Legend(host, handles, labels) if handles else None
    settings = _legend_settings(source, default)
    for owner in owners:
        legend = owner.get_legend()
        if owner is not host and legend is not None:
            legend.remove()
    return host, handles, labels, settings, None


def _place_untouched(legend: Legend, loc: str, kw: dict[str, Any]) -> Legend:
    """Follow an explicit placement on a legend that cannot be rebuilt.

    A matplotlib ``loc`` and ``bbox_to_anchor`` move it through ``set_loc`` /
    ``set_bbox_to_anchor``. A side (``"above"``...) and any other keyword
    need a rebuild: warn and leave the legend as it is.
    """
    ignored = sorted(
        k for k in kw if k not in {"bbox_to_anchor", "bbox_transform"}
    )
    if _parse_outside_side(loc) is not None:
        warnings.warn(
            f"place_legend(loc={loc!r}) needs to rebuild the legend, but its "
            "handles cannot be rebuilt faithfully (tuple handles, a custom "
            "handler or explicit labels); the legend is left as it is",
            UserWarning,
            stacklevel=3,
        )
        return legend
    if ignored:
        warnings.warn(
            f"place_legend left an explicit legend untouched; ignored {ignored}",
            UserWarning,
            stacklevel=3,
        )
    if loc != "best":
        legend.set_loc(cast("LegendLocType", loc))
    if "bbox_to_anchor" in kw:
        legend.set_bbox_to_anchor(
            kw["bbox_to_anchor"], kw.get("bbox_transform")
        )
    return legend


def _outside_fallback(
    ax: Axes, handles: list[Any], labels: list[str], kw: dict[str, Any]
) -> Legend:
    """Put the legend above ``ax`` because every in-axes spot covers data."""
    legend = _place_outside_legend(ax, handles, labels, "above", kw)
    legend._dm_collision_free = True  # type: ignore[attr-defined]
    legend._dm_collision_score = 0.0  # type: ignore[attr-defined]
    legend._dm_outside_fallback = True  # type: ignore[attr-defined]
    return legend


def place_legend(ax: Axes, *, loc: str = "best", **kw: Any) -> Legend | None:
    """Place or reposition an axes legend.

    ``loc="best"`` delegates to matplotlib for simple line-only axes. When the
    axes contains bars/collections/text obstacles or a tall legend, it scores
    four corners plus upper/lower center across one to three columns and
    selects the least obstructed in-axes location. When every in-axes
    location would cover data, the legend goes outside, above the axes (the
    ``loc="above"`` placement below), so no caller has to pick a side; a
    ``bbox_to_anchor`` / ``bbox_transform`` in ``kw`` keeps it inside. The
    returned Legend receives ``_dm_collision_free`` and
    ``_dm_collision_score`` attributes; ``_dm_outside_fallback`` is True when
    the legend went outside for that reason.

    ``loc="above"``, ``"below"``, ``"right"`` or ``"left"`` puts the legend
    outside the axes, centred on that side, past the side's tick labels and
    axis label (and a ``twinx`` / ``twiny`` partner's) by the preset's
    ``legend.borderaxespad`` gap. Above and below it takes one row when that
    row fits the axes width, otherwise the fewest rows that fit (rows are
    chosen for the axes width at call time); right and left it is one
    column. ``ncol`` / ``ncols`` in ``kw`` overrides the count, and
    ``bbox_to_anchor`` / ``bbox_transform`` raise ``ValueError`` because the
    side sets the anchor. :func:`dartwork_mpl.simple_layout` re-anchors such
    a legend to the labels present when it runs, makes room for it, and
    raises the axes titles above an ``"above"`` legend.
    ``dm.optimize_legend(ax, outside=True)`` also places a legend outside,
    at the top of the right side with its own font size and frame; prefer
    ``loc="right"`` here, which keeps the preset's legend style.

    A ``twinx`` / ``twiny`` pair gets one legend: the entries of every twin,
    on the twin drawn last (so no partner's data covers it), and the
    partners' own legends are removed. "Last" is by Axes zorder, then figure
    order, so the ``ax.set_zorder(twin.get_zorder() + 1)`` idiom puts the
    legend on ``ax``.

    The rebuilt legend keeps what the existing legend's public API reads: its
    title, ``handler_map``, ``frameon``, ``alignment``, ``markerscale``,
    ``draggable``, and the font properties (size, weight, family) of its title
    and entries and their colour, each only where it differs from the preset;
    keywords passed here win (a ``fontsize`` replaces the kept entry font).
    ``ncols`` cannot be read back, so pass it again.

    A legend that is not what the pair's own artists would draw (tuple
    handles, a custom handler, explicit labels) cannot be rebuilt faithfully
    and is returned untouched: the explicit legend wins, decided by the
    artist types each entry draws, not by its label. An explicit matplotlib
    ``loc`` or ``bbox_to_anchor`` still moves it (``set_loc`` /
    ``set_bbox_to_anchor``); ``loc="above"`` and the other sides, or any
    other keyword, need a rebuild, so they raise a ``UserWarning`` and the
    legend stays as it is. Any other ``loc`` is passed to
    ``ax.legend`` unchanged.
    """
    ax, handles, labels, kept, untouched = _merge_twin_legends(ax)
    if untouched is not None:
        return _place_untouched(untouched, loc, kw)
    if not handles:
        return None
    kw = _caller_wins(kept, kw)

    side = _parse_outside_side(loc)
    if side is not None:
        return _place_outside_legend(ax, list(handles), list(labels), side, kw)
    if loc != "best":
        return _legend_for_loc(ax, list(handles), list(labels), loc, kw)

    fig, renderer = _renderer_for_axes(ax)
    twins = len(same_position_axes(ax)) > 1
    has_obstacles = twins or bool(ax.patches or ax.collections or ax.texts)
    ncols = _legend_candidate_ncols(list(labels), kw)
    if not has_obstacles and len(labels) < 5 and ncols == [1]:
        legend = _legend_for_loc(ax, list(handles), list(labels), "best", kw)
        if not _may_go_outside(kw) or not _covers_data(ax, legend, renderer):
            return legend
        legend.remove()
        return _outside_fallback(ax, list(handles), list(labels), kw)

    old_legend = ax.get_legend()
    if old_legend is not None:
        old_legend.remove()

    data_bboxes = _pair_occupancy_bboxes(ax, renderer)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        axes_bbox = Bbox.null()
    candidates: tuple[_LegendCandidate, ...] = (
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "upper center",
        "lower center",
    )
    trials: list[_LegendTrial] = []
    for ncol in ncols:
        legend_kw = dict(kw)
        legend_kw["ncol"] = ncol
        for candidate in candidates:
            legend = _legend_for_loc(
                ax, list(handles), list(labels), candidate, legend_kw
            )
            fig.canvas.draw()
            try:
                bbox = legend.get_window_extent(renderer)
            except BBOX_ERRORS:
                trials.append(_UnmeasuredLegend(candidate, ncol))
            else:
                trials.append(
                    _MeasuredLegend(
                        candidate,
                        ncol,
                        score=_score_legend_candidate(
                            bbox, data_bboxes, axes_bbox, ncol
                        ),
                        collision_free=(
                            _collision_area(bbox, data_bboxes) <= 0
                            and _outside_area(bbox, axes_bbox) <= 0
                        ),
                    )
                )
            legend.remove()

    best = _best_trial(trials)
    if _may_go_outside(kw) and not (
        isinstance(best, _MeasuredLegend) and best.collision_free
    ):
        return _outside_fallback(ax, list(handles), list(labels), kw)
    legend_kw = dict(kw)
    legend_kw["ncol"] = best.ncol
    legend = _legend_for_loc(
        ax, list(handles), list(labels), best.loc, legend_kw
    )
    _mark_placement(legend, best)
    return legend


_UNIT_SUFFIX_RE = re.compile(r"\s*([([][^)\]]{1,32}[)\]])\s*$")


def _split_label_two_lines(label: str) -> str | None:
    stripped = label.strip()
    if not stripped or "\n" in stripped:
        return None

    unit = ""
    body = stripped
    match = _UNIT_SUFFIX_RE.search(stripped)
    if match:
        unit = match.group(1)
        body = stripped[: match.start()].strip()

    words = body.split()
    if unit and len(words) == 1:
        return f"{body}\n{unit}"
    if len(words) < 2:
        return None

    target = len(body) / 2.0
    split_index = min(
        range(1, len(words)),
        key=lambda index: abs(len(" ".join(words[:index])) - target),
    )
    first = " ".join(words[:split_index])
    second = " ".join(words[split_index:])
    if unit:
        second = f"{second} {unit}" if second else unit
    if not first or not second:
        return None
    return f"{first}\n{second}"


def wrap_axis_label(ax: Axes, axis: str = "y", max_frac: float = 1.0) -> bool:
    """Wrap an overlong x/y-axis label to two lines at word boundaries.

    The rendered label length is compared with the corresponding axes spine
    length. Parenthesized or bracketed unit suffixes stay intact and are moved
    to the second line when wrapping is needed. Returns ``True`` only when the
    label text changed.
    """
    which = _parse_axis(axis, "axis must be 'x' or 'y'")
    if max_frac <= 0:
        raise ValueError("max_frac must be positive")

    label = ax.xaxis.label if which == "x" else ax.yaxis.label
    raw_text = label.get_text()
    wrapped = _split_label_two_lines(raw_text)
    if wrapped is None:
        return False

    _fig, renderer = _renderer_for_axes(ax)
    try:
        text_bbox = label.get_window_extent(renderer)
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    rendered_length = text_bbox.width if which == "x" else text_bbox.height
    axis_length = axes_bbox.width if which == "x" else axes_bbox.height
    if rendered_length <= axis_length * float(max_frac):
        return False

    label.set_text(wrapped)
    return True


def wrap_axis_labels(
    fig: Figure | SubFigure, axis: str = "both", max_frac: float = 1.0
) -> list[Text]:
    """Wrap overlong axis labels for every axes in a figure.

    ``axis`` may be ``"x"``, ``"y"``, or ``"both"``. The returned list
    contains the label Text objects that were changed.
    """
    axes_to_wrap: tuple[_Axis, ...] = (
        ("x", "y")
        if axis == "both"
        else (_parse_axis(axis, "axis must be 'x', 'y', or 'both'"),)
    )
    changed: list[Text] = []
    for ax in fig.axes:
        for axis_name in axes_to_wrap:
            if wrap_axis_label(ax, axis_name, max_frac=max_frac):
                label = ax.xaxis.label if axis_name == "x" else ax.yaxis.label
                changed.append(label)
    return changed


def arrow_axis(
    ax: Axes,
    direction: str,
    label: str,
    *,
    offset: float = -0.10,
    low: str = "Low",
    high: str = "High",
    fontsize: float | None = None,
    fontsize_label: float | None = None,
    pad: float = -0.005,
    weight: str = "normal",
    color: str = "black",
    arrow_kw: dict[str, Any] | None = None,
) -> None:
    """Draw a bidirectional Low-High arrow axis along the edge of a plot.

    Produces a visual like ``Low ◄── label ──► High`` near the spine exterior.

    Parameters
    ----------
    ax : Axes
        Target Axes object for the annotation.
    direction : {'x', 'y'}
        "x": insert a horizontal arrow axis below the x-axis spine.
        "y": insert a vertical arrow axis to the left of the y-axis spine.
    label : str
        Center label text placed at the midpoint of the axis.
    offset : float, optional
        Offset from the spine in Axes-fraction units. Default is -0.10
        (sufficiently outside to avoid overlap with tick labels).
    low : str, optional
        Text for the low end (bottom/left) of the axis. Default is "Low".
    high : str, optional
        Text for the high end (top/right) of the axis. Default is "High".
    fontsize : float | None, optional
        Font size for the Low/High endpoint labels. Default is fs(-1).
    fontsize_label : float | None, optional
        Font size for the center label. Default is fs(0).
    pad : float, optional
        Fractional gap between text and arrowheads. Default is -0.005.
    weight : str, optional
        Font weight applied to all text elements.
    color : str, optional
        Color for both text and arrows. Default is "black".
    arrow_kw : dict | None, optional
        Override the arrowprops passed to the internal ``ax.annotate`` calls.
    """
    if fontsize is None:
        fontsize = fs(-1)
    along = _parse_axis(
        direction,
        f"direction must be 'x' or 'y', got {direction!r}. "
        "(Any other value would silently draw a y-axis arrow.)",
    )
    if fontsize_label is None:
        fontsize_label = fs(0)
    if arrow_kw is None:
        arrow_kw = {
            "arrowstyle": "-|>,head_width=0.1",
            "color": color,
            "lw": 0.25,
        }

    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    renderer = get_renderer(fig)
    inv = ax.transAxes.inverted()
    rot_kw: dict[str, Any] = (
        {"rotation": 90, "rotation_mode": "anchor"} if along == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if along == "x":
        p_lo: tuple[float, float] = (0.0, float(offset))
        p_hi: tuple[float, float] = (1.0, float(offset))
        p_lb: tuple[float, float] = (0.5, float(offset))
    else:
        p_lo = (float(offset), 0.0)
        p_hi = (float(offset), 1.0)
        p_lb = (float(offset), 0.5)

    t_lo = ax.text(
        *p_lo,
        low,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="left",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_hi = ax.text(
        *p_hi,
        high,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="right",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_lb = ax.text(
        *p_lb,
        label,
        transform=ax.transAxes,
        fontsize=fontsize_label,
        fontweight=weight,
        color=color,
        ha="center",
        va="center",
        clip_on=False,
        **rot_kw,
    )

    # ── measure extents in axes fraction ─────────────────────
    fig.canvas.draw()

    def _edges(t: Text) -> np.ndarray[Any, Any]:
        bb = t.get_window_extent(renderer)
        return inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])

    i = 0 if along == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip: float, tail: float) -> None:
        if along == "x":
            ax.annotate(
                "",
                xy=(tip, offset),
                xytext=(tail, offset),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )
        else:
            ax.annotate(
                "",
                xy=(offset, tip),
                xytext=(offset, tail),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )

    _arrow(lo_end + pad, lb_lo - pad)
    _arrow(hi_start - pad, lb_hi + pad)


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """Create a translation offset transform for positioning figure elements.

    Parameters
    ----------
    x : float
        Horizontal offset in points.
    y : float
        Vertical offset in points.
    fig : matplotlib.figure.Figure
        The Figure whose DPI scale is used.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        A translation transform that can be added to other transforms.
    """
    dx, dy = x / 72, y / 72
    return ScaledTranslation(dx, dy, fig.dpi_scale_trans)
