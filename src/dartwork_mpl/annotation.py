"""Axes-based annotation helper module.

Provides ``label_axes`` for adding standard alphabetic sub-labels to figure
panels, ``annotate_value`` / ``label_hline`` for compact in-axes labels,
``place_legend`` for axes legends, and ``arrow_axis`` for drawing
bidirectional Low-High arrow axes.
"""

from __future__ import annotations

__all__ = [
    "annotate_value",
    "arrow_axis",
    "label_axes",
    "label_hline",
    "place_legend",
]

import string
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.legend import Legend
from matplotlib.text import Text
from matplotlib.transforms import Bbox, blended_transform_factory

from ._helpers import BBOX_ERRORS, get_renderer
from .scale import fs

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure


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

    ``side="auto"`` starts above the point, then flips below when the
    rendered label would overlap same-axes data/text or escape the axes top.
    When text needs to move, this helper uses a vertical single-axis offset
    first; it does not introduce diagonal arrow-style displacement.
    """
    if fontsize is None:
        fontsize = fs(-2)
    if side not in {"auto", "above", "below"}:
        raise ValueError("side must be 'auto', 'above', or 'below'")

    existing_texts = list(ax.texts)
    place_below = side == "below"
    va = "top" if place_below else "bottom"
    offset = (0.0, -float(offset_pt) if place_below else float(offset_pt))

    ann = ax.annotate(
        text,
        xy=(x, y),
        xycoords="data",
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", "center"),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )

    if side != "auto":
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        label_bbox = ann.get_window_extent(renderer)
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann

    collision_bboxes = [
        *_line_segment_bboxes(ax),
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]
    overlaps = any(
        _overlap_area(label_bbox, bbox) > 0 for bbox in collision_bboxes
    )
    escapes_top = label_bbox.y1 > axes_bbox.y1
    if overlaps or escapes_top:
        ann.set_verticalalignment("top")
        _set_annotation_offset(ann, (0.0, -float(offset_pt)))
        fig.canvas.draw()

    return ann


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

    ``x`` is interpreted in axes-fraction coordinates (``"left"``,
    ``"center"``, ``"right"``, or a float). Vertical movement uses a
    single-axis point offset so the label stays attached to the reference
    line rather than drifting diagonally.
    """
    if fontsize is None:
        fontsize = fs(-2)
    if side not in {"above", "below"}:
        raise ValueError("side must be 'above' or 'below'")

    if isinstance(x, str):
        x_map = {"left": 0.0, "center": 0.5, "right": 1.0}
        if x not in x_map:
            raise ValueError("x must be 'left', 'center', 'right', or a float")
        x_pos = x_map[x]
        ha = x
    else:
        x_pos = float(x)
        ha = "center"

    va = "bottom" if side == "above" else "top"
    offset = (0.0, float(gap_pt) if side == "above" else -float(gap_pt))
    transform = blended_transform_factory(ax.transAxes, ax.transData)
    return ax.annotate(
        text,
        xy=(x_pos, y),
        xycoords=transform,
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )


def _legend_for_loc(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    loc: str,
    legend_kw: dict[str, Any],
) -> Legend:
    return ax.legend(handles, labels, loc=loc, **legend_kw)


def _score_legend_candidate(
    legend_bbox: Bbox, data_bboxes: list[Bbox]
) -> float:
    area = max(float(legend_bbox.width * legend_bbox.height), 1.0)
    return sum(_overlap_area(legend_bbox, bbox) for bbox in data_bboxes) / area


def place_legend(ax: Axes, *, loc: str = "best", **kw: Any) -> Legend | None:
    """Place or reposition an axes legend.

    ``loc="best"`` delegates to matplotlib for line-only axes. For
    patch/collection-heavy axes, it scores four corners plus upper center
    against data-artist occupancy and selects the least occupied location.
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

    if loc != "best" or not (ax.patches or ax.collections):
        return _legend_for_loc(ax, list(handles), list(labels), loc, kw)

    fig, renderer = _renderer_for_axes(ax)
    data_bboxes = _data_occupancy_bboxes(ax)
    if not data_bboxes:
        return _legend_for_loc(ax, list(handles), list(labels), "best", kw)

    old_legend = ax.get_legend()
    if old_legend is not None:
        old_legend.remove()

    candidates = (
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "upper center",
    )
    scores: list[tuple[float, str]] = []
    for candidate in candidates:
        legend = _legend_for_loc(ax, list(handles), list(labels), candidate, kw)
        fig.canvas.draw()
        try:
            bbox = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            score = float("inf")
        else:
            score = _score_legend_candidate(bbox, data_bboxes)
        scores.append((score, candidate))
        legend.remove()

    _score, best_loc = min(scores, key=lambda item: item[0])
    return _legend_for_loc(ax, list(handles), list(labels), best_loc, kw)


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
