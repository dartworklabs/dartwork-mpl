"""Facts the label decisions read from a drawn figure.

Bars as runs of positions and lengths, the boxes a point label must stay
clear of, the colours a bar label can take, and what each panel draws
around its top-left corner.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.container import BarContainer
from matplotlib.text import Text
from matplotlib.transforms import Bbox, IdentityTransform

from .._colors.contrast import (
    composite_layers,
    composite_over,
    ensure_contrast,
    readable_text_color,
)
from .._figure_geometry import (
    BBOX_ERRORS,
    axes_titles,
    backdrop_layers,
    get_renderer,
    same_position_axes,
)
from .model import Ink, Panel, Title, Try
from .stacks import BarRun

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.patches import Rectangle

    from .model import Kind

FloatArray = np.ndarray


def drawn_renderer(ax: Axes) -> RendererBase:
    """The renderer of ``ax``'s figure after a draw (boxes are current)."""
    fig = ax.get_figure(root=True)
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    fig.canvas.draw()
    return get_renderer(fig)


def px_per_pt(artist: Text | Axes) -> float:
    """Display pixels per point at the artist's figure dpi."""
    fig = artist.get_figure(root=True)
    return (fig.dpi if fig is not None else 72.0) / 72.0


# ------------------------------------------------------------ bars
def bar_values(container: BarContainer) -> FloatArray:
    """The container's values; masked (``np.ma``) values read as NaN."""
    return np.ma.filled(
        np.ma.asarray(container.datavalues, dtype=float), np.nan
    )


def bar_end(bar: Rectangle, vertical: bool) -> tuple[float, float]:
    """The middle of the bar's end, in its data coordinates."""
    x, y = float(bar.get_x()), float(bar.get_y())
    w, h = float(bar.get_width()), float(bar.get_height())
    return (x + w / 2, y + h) if vertical else (x + w, y + h / 2)


def bar_run(container: BarContainer) -> BarRun:
    """Each bar's middle across, start and signed length along its value."""
    rows = []
    for p in container.patches:
        x, y, w, h = (
            float(v)
            for v in (p.get_x(), p.get_y(), p.get_width(), p.get_height())
        )
        rows.append(
            (x + w / 2, y, h)
            if container.orientation == "vertical"
            else (y + h / 2, x, w)
        )
    table = np.asarray(rows, dtype=float).reshape(-1, 3)
    host = (
        id(container.patches[0].axes) if container.patches else None,
        container.orientation,
    )
    values = bar_values(container)[: len(container.patches)]
    return BarRun(
        tuple(table[:, 0]),
        tuple(table[:, 1]),
        tuple(table[:, 2]),
        tuple(float(v) for v in values),
        host,
    )


def error_extent(
    container: BarContainer, index: int, vertical: bool
) -> FloatArray | None:
    """The bar's error bar along its value axis, as data values, if any."""
    errorbar = container.errorbar
    if errorbar is None:
        return None
    along = 1 if vertical else 0
    for collection in errorbar.lines[2]:
        segments = collection.get_segments()
        if index >= len(segments):
            continue
        segment = np.asarray(segments[index], dtype=float)
        if (
            segment.shape != (2, 2)
            or segment[0, 1 - along] != segment[1, 1 - along]
        ):
            continue  # the error bar across the value axis
        extent = segment[:, along][np.isfinite(segment[:, along])]
        return extent if extent.size else None
    return None


def bar_centres(bar_axes: Axes, vertical: bool) -> tuple[float, ...]:
    """The middle across the bars, on screen, of every bar in the plot area."""
    out = []
    for member in same_position_axes(bar_axes):
        for container in member.containers:
            if not isinstance(container, BarContainer):
                continue
            for patch in container.patches:
                if patch.get_visible():
                    box = patch.get_window_extent()
                    out.append(
                        (box.x0 + box.x1) / 2
                        if vertical
                        else (box.y0 + box.y1) / 2
                    )
    return tuple(out)


def _background(bar_axes: Axes) -> tuple[float, float, float]:
    """What shows behind the bars: the figure, then each visible Axes patch."""
    return composite_layers(backdrop_layers(same_position_axes(bar_axes)))


def readable_ink(patch: Rectangle, bar_axes: Axes) -> Ink:
    """White or the preset text colour, whichever reads better on the bar."""
    shown = composite_over(
        mcolors.to_rgba(patch.get_facecolor()), _background(bar_axes)
    )
    return Ink(
        readable_text_color(
            mcolors.to_hex(shown),
            light="white",
            dark=mcolors.to_hex(mpl.rcParams["text.color"]),
        )
    )


def series_ink(patch: Rectangle, bar_axes: Axes, kind: Kind) -> Ink:
    """The bar's colour as drawn, darkened (or lightened) to 4.5:1 text."""
    if kind == "total":
        return Ink()
    background = _background(bar_axes)
    face = mcolors.to_rgba(patch.get_facecolor())
    if face[3] == 0 and patch.get_linewidth() > 0:
        face = mcolors.to_rgba(patch.get_edgecolor())
    shown = mcolors.to_hex(composite_over(face, background))
    return Ink(ensure_contrast(shown, mcolors.to_hex(background)))


# ------------------------------------------------------------ obstacles
def _padded(x0: float, y0: float, x1: float, y1: float, pad: float) -> Bbox:
    return Bbox.from_extents(x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def line_boxes(ax: Axes, pad_px: float = 2.0) -> list[Bbox]:
    """Each visible line segment's box, padded."""
    boxes: list[Bbox] = []
    for line in ax.lines:
        if not line.get_visible():
            continue
        xy = np.asarray(line.get_xydata(), dtype=float)
        if len(xy) < 2:
            continue
        points = line.get_transform().transform(xy)
        points = points[np.isfinite(points).all(axis=1)]
        for a, b in pairwise(points):
            boxes.append(
                _padded(
                    float(min(a[0], b[0])),
                    float(min(a[1], b[1])),
                    float(max(a[0], b[0])),
                    float(max(a[1], b[1])),
                    pad_px,
                )
            )
    return boxes


def patch_boxes(ax: Axes) -> list[Bbox]:
    """Each visible patch's display box."""
    boxes: list[Bbox] = []
    for patch in ax.patches:
        if not patch.get_visible():
            continue
        try:
            box = (
                patch.get_path()
                .transformed(patch.get_transform())
                .get_extents()
            )
        except (RuntimeError, ValueError, AttributeError):
            continue
        if box.width > 0 and box.height > 0:
            boxes.append(box)
    return boxes


def point_boxes(ax: Axes, pad_px: float = 6.0) -> list[Bbox]:
    """A padded box around each point of each visible collection."""
    boxes: list[Bbox] = []
    for collection in ax.collections:
        if not collection.get_visible():
            continue
        try:
            points = collection.get_offset_transform().transform(
                collection.get_offsets()
            )
        except (RuntimeError, ValueError, AttributeError):
            continue
        if len(points) == 0:
            continue
        points = points[np.isfinite(points).all(axis=1)]
        boxes += [
            _padded(float(x), float(y), float(x), float(y), pad_px)
            for x, y in points
        ]
    return boxes


def text_boxes(texts: list[Text], renderer: RendererBase) -> list[Bbox]:
    """Each shown, non-empty text's display box."""
    boxes: list[Bbox] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            box = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if box.width > 0 and box.height > 0:
            boxes.append(box)
    return boxes


def _overlap(a: Bbox, b: Bbox) -> float:
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return float(w * h) if w > 0 and h > 0 else 0.0


def measure_try(box: Bbox, frame: Bbox, obstacles: list[Bbox]) -> Try:
    """How much of ``box`` leaves ``frame`` and covers ``obstacles``."""
    area = max(float(box.width * box.height), 0.0)
    return Try(
        area - _overlap(box, frame), sum(_overlap(box, o) for o in obstacles)
    )


# ------------------------------------------------------------ panels
def _shown(text: Text) -> bool:
    return text.get_visible() and bool(text.get_text().strip())


def _cell(
    ax: Axes, outer: bool
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    if outer:
        spec = spec.get_topmost_subplotspec()
    grid = id(spec.get_gridspec())
    return (grid, spec.rowspan.start), (grid, spec.colspan.start)


def _ylabel_box(ax: Axes, renderer: RendererBase) -> Bbox | None:
    """The y-axis name of ``ax`` when it is drawn on the left."""
    label = ax.yaxis.label
    if not _shown(label) or str(ax.yaxis.get_label_position()) != "left":
        return None
    try:
        return label.get_window_extent(renderer)
    except BBOX_ERRORS:
        return None


def _ytick_box(ax: Axes, renderer: RendererBase) -> Bbox | None:
    """The left y tick labels of ``ax`` drawn inside the view."""
    lo, hi = sorted(ax.get_ylim())
    boxes: list[Bbox] = []
    for tick in ax.yaxis.get_major_ticks():
        if _shown(tick.label1) and lo - 1e-9 <= tick.get_loc() <= hi + 1e-9:
            try:
                boxes.append(tick.label1.get_window_extent(renderer))
            except BBOX_ERRORS:
                continue
    return Bbox.union(boxes) if boxes else None


def baseline_px(text: Text, renderer: RendererBase) -> float:
    """The baseline of ``text`` in display pixels."""
    if text.get_verticalalignment() == "baseline":
        return float(text.get_transform().transform(text.get_position())[1])
    probe = Text(
        0,
        0,
        text.get_text(),
        fontproperties=text.get_fontproperties(),
        va="baseline",
    )
    probe.set_figure(text.figure)
    probe.set_transform(IdentityTransform())
    descent = -probe.get_window_extent(renderer).y0
    return float(text.get_window_extent(renderer).y0 + descent)


def _guess_ylabel_x0(ax: Axes, renderer: RendererBase) -> float:
    """Where the outer edge of a y-axis name of ``ax`` would be."""
    x0 = float(ax.transAxes.transform((0.0, 1.0))[0])
    if ax.name != "rectilinear":
        return x0
    ticks = _ytick_box(ax, renderer)
    inner = min(x0, ticks.x0) if ticks is not None else x0
    _w, height, _d = renderer.get_text_width_height_descent(
        "Ag", ax.yaxis.label.get_fontproperties(), ismath=False
    )
    return inner - float(ax.yaxis.labelpad) * px_per_pt(ax) - float(height)


def _left_neighbours_x1(ax: Axes, renderer: RendererBase) -> float | None:
    """The right end of what the panels just left of ``ax`` draw (same
    top-level grid, cells ending where its cell starts, a shared row)."""
    spec, root = ax.get_subplotspec(), ax.get_figure(root=True)
    if spec is None or root is None:
        return None
    top = spec.get_topmost_subplotspec()
    rows = set(top.rowspan)
    end: float | None = None
    for other in root.axes:
        other_spec = other.get_subplotspec()
        if other is ax or other_spec is None or not other.get_visible():
            continue
        cell = other_spec.get_topmost_subplotspec()
        if (
            cell.get_gridspec() is not top.get_gridspec()
            or cell.colspan.stop != top.colspan.start
            or not rows & set(cell.rowspan)
        ):
            continue
        try:
            box = other.get_tightbbox(renderer)
        except BBOX_ERRORS:
            continue
        if box is not None:
            end = float(box.x1) if end is None else max(end, float(box.x1))
    return end


def panel(ax: Axes, letter: Text, renderer: RendererBase) -> Panel:
    """What ``ax`` draws around its top-left corner, for its ``letter``."""
    k = px_per_pt(ax)
    corner = tuple(map(float, ax.transAxes.transform((0.0, 1.0))))
    box = letter.get_window_extent(renderer)
    rectilinear = ax.name == "rectilinear"
    ylabel = _ylabel_box(ax, renderer) if rectilinear else None
    ticks = _ytick_box(ax, renderer)
    bare = rectilinear and ylabel is None and ticks is None
    titles = tuple(
        Title(loc, float(ext.x0), float(ext.x1), baseline_px(t, renderer))
        for loc, t in axes_titles(ax).items()
        if _shown(t) and (ext := t.get_window_extent(renderer)) is not None
    )
    top = corner[1]
    try:
        xbox = ax.xaxis.get_tightbbox(renderer)
    except BBOX_ERRORS:
        xbox = None
    if xbox is not None:
        top = max(top, float(xbox.y1))
    decos = tuple(
        (float(d.x0), float(d.x1), float(d.y1))
        for d in (_ylabel_box(ax, renderer), ticks)
        if d is not None
    )
    return Panel(
        corner=(corner[0], corner[1]),
        width=float(box.width),
        descent=baseline_px(letter, renderer) - float(box.y0),
        gap=0.5 * float(letter.get_fontsize()) * k,
        cell=_cell(ax, outer=False),
        outer_cell=_cell(ax, outer=True),
        ylabel_x0=None if ylabel is None else float(ylabel.x0),
        guess_x0=_guess_ylabel_x0(ax, renderer),
        bare=bare,
        neighbour_x1=_left_neighbours_x1(ax, renderer) if bare else None,
        titles=titles,
        top=top,
        decos=decos,
    )
