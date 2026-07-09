"""Axes-based annotation helper module.

Provides ``label_axes`` for adding standard alphabetic sub-labels to figure
panels, ``annotate_value`` / ``annotate_corner`` / ``label_hline`` for compact
in-axes labels, ``place_legend`` for axes legends, and ``arrow_axis`` for
drawing bidirectional Low-High arrow axes.
"""

from __future__ import annotations

__all__ = [
    "annotate_corner",
    "annotate_value",
    "arrow_axis",
    "label_axes",
    "label_hline",
    "place_legend",
    "wrap_axis_label",
    "wrap_axis_labels",
]

import re
import string
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from matplotlib.axes import Axes
from matplotlib.legend import Legend
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from ._helpers import BBOX_ERRORS, get_renderer
from .scale import fs

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure

HorizontalAlign = Literal["left", "center", "right"]
VerticalAlign = Literal[
    "bottom", "baseline", "center", "center_baseline", "top"
]


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


def label_axes(
    axes: list[Axes] | np.ndarray[Any, Any],
    labels: list[str] | None = None,
    fontsize: float | None = None,
    fontweight: str = "normal",
    x: float | str = "auto",
    y: float = 1.05,
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
        a y-axis label is present (-0.18 or -0.02).
    y : float, optional
        Vertical position in Axes-relative coordinates. Default is 1.05.
    **kwargs
        Additional text properties passed to ``ax.text()``.

    Returns
    -------
    list
        List of created Text objects.
    """
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
            y,
            label,
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va="bottom",
            ha="left",
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
    return (
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
    side: str, offset_pt: float
) -> tuple[tuple[float, float], HorizontalAlign, VerticalAlign]:
    offset = float(offset_pt)
    specs: dict[
        str, tuple[tuple[float, float], HorizontalAlign, VerticalAlign]
    ] = {
        "above": ((0.0, offset), "center", "bottom"),
        "below": ((0.0, -offset), "center", "top"),
        "right": ((offset, 0.0), "left", "center"),
        "left": ((-offset, 0.0), "right", "center"),
    }
    return specs[side]


def _apply_annotation_side(text: Text, side: str, offset_pt: float) -> None:
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
    """
    if fontsize is None:
        fontsize = fs(-2)
    if side not in {"auto", "above", "below", "left", "right"}:
        raise ValueError(
            "side must be 'auto', 'above', 'below', 'left', or 'right'"
        )

    existing_texts = list(ax.texts)
    initial_side = "above" if side == "auto" else side
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

    if side != "auto":
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
    scores: list[tuple[float, str]] = []

    vertical_sides = ("above", "below")
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

    for candidate in ("right", "left"):
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
    str,
    tuple[
        tuple[float, float], tuple[float, float], HorizontalAlign, VerticalAlign
    ],
] = {
    "upper left": ((0.0, 1.0), (1.0, -1.0), "left", "top"),
    "upper right": ((1.0, 1.0), (-1.0, -1.0), "right", "top"),
    "lower left": ((0.0, 0.0), (1.0, 1.0), "left", "bottom"),
    "lower right": ((1.0, 0.0), (-1.0, 1.0), "right", "bottom"),
}


def _corner_order(loc: str) -> list[str]:
    order = ["upper left", "upper right", "lower left", "lower right"]
    if loc == "upper left":
        return order
    return [loc, *[candidate for candidate in order if candidate != loc]]


def _apply_corner(text: Text, loc: str, inset_pt: float) -> None:
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
    if loc not in _CORNER_SPECS:
        raise ValueError(
            "loc must be 'upper left', 'upper right', 'lower left', "
            "or 'lower right'"
        )

    existing_texts = list(ax.texts)
    anchor, offset_direction, ha, va = _CORNER_SPECS[loc]
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

    scores: list[tuple[float, str]] = []
    for candidate in _corner_order(loc):
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
    ax: Axes, y: float, x: str | float
) -> tuple[float, HorizontalAlign]:
    left, right = _visible_hline_span(ax, y)
    if isinstance(x, str):
        if x == "left":
            return left, "left"
        if x == "right":
            return right, "right"
        if x == "center":
            return (left + right) / 2.0, "center"
        raise ValueError(
            "x must be 'auto', 'left', 'center', 'right', or a float"
        )
    return _axes_fraction_to_data_x(ax, float(x), y), "center"


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
    if side not in {"above", "below"}:
        raise ValueError("side must be 'above' or 'below'")

    va = "bottom" if side == "above" else "top"
    offset = (0.0, float(gap_pt) if side == "above" else -float(gap_pt))
    existing_texts = list(ax.texts)
    x_pos, ha = _hline_x_spec(ax, y, "right" if x == "auto" else x)
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
    if x != "auto":
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
    scores: list[tuple[float, str]] = []
    for candidate in ("right", "left"):
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
    return ax.legend(handles, labels, loc=loc, **legend_kw)


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


def place_legend(ax: Axes, *, loc: str = "best", **kw: Any) -> Legend | None:
    """Place or reposition an axes legend.

    ``loc="best"`` delegates to matplotlib for simple line-only axes. When the
    axes contains bars/collections/text obstacles or a tall legend, it scores
    four corners plus upper/lower center across one to three columns and
    selects the least obstructed in-axes location. The returned Legend receives
    ``_dm_collision_free`` and ``_dm_collision_score`` attributes for callers
    that need to detect an unavoidable collision fallback.
    """
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        legend = ax.get_legend()
        if legend is None:
            return None
        handles = [
            handle for handle in legend.legend_handles if handle is not None
        ]
        labels = [text.get_text() for text in legend.get_texts()]
    if not handles:
        return None

    if loc != "best":
        return _legend_for_loc(ax, list(handles), list(labels), loc, kw)

    fig, renderer = _renderer_for_axes(ax)
    has_obstacles = bool(ax.patches or ax.collections or ax.texts)
    ncols = _legend_candidate_ncols(list(labels), kw)
    if not has_obstacles and len(labels) < 5 and ncols == [1]:
        return _legend_for_loc(ax, list(handles), list(labels), "best", kw)

    old_legend = ax.get_legend()
    if old_legend is not None:
        old_legend.remove()

    data_bboxes = _data_occupancy_bboxes(ax, renderer)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        axes_bbox = Bbox.null()
    candidates = (
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "upper center",
        "lower center",
    )
    scores: list[tuple[float, str, int, bool]] = []
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
                score = float("inf")
                collision_free = False
            else:
                score = _score_legend_candidate(
                    bbox, data_bboxes, axes_bbox, ncol
                )
                collision_free = (
                    _collision_area(bbox, data_bboxes) <= 0
                    and _outside_area(bbox, axes_bbox) <= 0
                )
            scores.append((score, candidate, ncol, collision_free))
            legend.remove()

    best_score, best_loc, best_ncol, collision_free = min(
        scores, key=lambda item: item[0]
    )
    legend_kw = dict(kw)
    legend_kw["ncol"] = best_ncol
    legend = _legend_for_loc(
        ax, list(handles), list(labels), best_loc, legend_kw
    )
    legend._dm_collision_free = collision_free  # type: ignore[attr-defined]
    legend._dm_collision_score = best_score  # type: ignore[attr-defined]
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
    if axis not in {"x", "y"}:
        raise ValueError("axis must be 'x' or 'y'")
    if max_frac <= 0:
        raise ValueError("max_frac must be positive")

    label = ax.xaxis.label if axis == "x" else ax.yaxis.label
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
    rendered_length = text_bbox.width if axis == "x" else text_bbox.height
    axis_length = axes_bbox.width if axis == "x" else axes_bbox.height
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
    if axis not in {"x", "y", "both"}:
        raise ValueError("axis must be 'x', 'y', or 'both'")

    axes_to_wrap = ("x", "y") if axis == "both" else (axis,)
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
    if direction not in ("x", "y"):
        raise ValueError(
            f"direction must be 'x' or 'y', got {direction!r}. "
            "(Any other value would silently draw a y-axis arrow.)"
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
        {"rotation": 90, "rotation_mode": "anchor"} if direction == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if direction == "x":
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

    i = 0 if direction == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip: float, tail: float) -> None:
        if direction == "x":
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
