"""Facts the label decisions read from a drawn figure.

Bars as runs of positions and lengths, the colour a label on a bar or at a
line's end takes, the boxes a point label must stay clear of, and what each
panel draws around its top-left corner.
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

from ..colorspace import (
    ContrastFacts,
    Ratio,
    Rgb,
    Rgba,
    composite_over,
    lifted,
    readable,
)
from ..geometry import BBOX_ERRORS, axes_titles, get_renderer, label_side
from ..vocab import (
    AlignBottom,
    AlignTop,
    Baseline,
    Far,
    Near,
    VCentre,
    VCentreBaseline,
    X,
    Y,
    bars_along,
    parse_valign,
)
from .model import Panel, Title, Try
from .stacks import BarRun

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.patches import Rectangle
    from matplotlib.typing import ColorType

FloatArray = np.ndarray


def drawn_renderer(ax: Axes) -> RendererBase:
    """The renderer of ``ax``'s figure after a draw (boxes are current)."""
    fig = ax.get_figure(root=True)
    if fig is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    fig.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
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


def label_anchor(
    container: BarContainer, index: int, vertical: bool
) -> tuple[float, float]:
    """Where bar ``index``'s label hangs: the middle of its end, or the far
    tip of its error bar when it has one (a value on the whisker is unread)."""
    bar = container.patches[index]
    x, y = bar_end(bar, vertical)
    errorbar = container.errorbar
    if errorbar is None:
        return x, y
    along = 1 if vertical else 0
    grows = (bar.get_height() if vertical else bar.get_width()) >= 0
    end = y if vertical else x
    for collection in errorbar.lines[2]:
        segments = collection.get_segments()
        if index >= len(segments):
            continue
        tips = np.asarray(segments[index], dtype=float)
        if tips.shape != (2, 2) or tips[0, 1 - along] != tips[1, 1 - along]:
            continue  # the error bar across the value axis
        reach = tips[:, along][np.isfinite(tips[:, along])]
        if reach.size:
            tip = float(reach.max() if grows else reach.min())
            end = max(end, tip) if grows else min(end, tip)
    return (x, end) if vertical else (end, y)


def stands_up(container: BarContainer) -> bool:
    """Whether the bars stand along x (``ax.bar``) rather than y (``barh``);
    a container made without an orientation is read as upright."""
    match bars_along(container.orientation):
        case X() | None:
            return True
        case Y():
            return False


def bar_run(container: BarContainer) -> BarRun:
    """Each bar's middle across, start and signed length along its value."""
    rows: list[tuple[float, float, float]] = []
    upright = stands_up(container)
    for p in container.patches:
        x, y, w, h = (
            float(v)
            for v in (p.get_x(), p.get_y(), p.get_width(), p.get_height())
        )
        rows.append((x + w / 2, y, h) if upright else (y + h / 2, x, w))
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


def bar_centres(bar_axes: Axes, vertical: bool) -> tuple[float, ...]:
    """The middle across the bars, on screen, of every bar of ``bar_axes``."""
    boxes = [
        patch.get_window_extent()
        for container in bar_axes.containers
        if isinstance(container, BarContainer)
        for patch in container.patches
        if patch.get_visible()
    ]
    return tuple(
        (b.x0 + b.x1) / 2 if vertical else (b.y0 + b.y1) / 2 for b in boxes
    )


#: Text against its background: WCAG's 4.5:1 for body text.
TEXT_CONTRAST = Ratio(4.5)


def _rgb(color: ColorType) -> Rgb:
    """``color`` as matplotlib reads it, alpha dropped."""
    return Rgb.of(mcolors.to_rgba(color))


def readable_on(color: ColorType, background: ColorType) -> str:
    """``color``, darkened or lightened to 4.5:1 contrast on ``background``
    when it falls short (as ``dm.ensure_contrast`` does)."""
    facts = ContrastFacts(_rgb(color), _rgb(background), TEXT_CONTRAST)
    lift = lifted(facts)
    if lift is not None:
        return lift.rgb().hex()
    return color if isinstance(color, str) else facts.color.hex()


def backdrop(ax: Axes) -> tuple[float, float, float, float]:
    """What shows behind ``ax``'s data: its patch, else the figure's."""
    face = mcolors.to_rgba(ax.patch.get_facecolor())
    if not ax.patch.get_visible() or face[3] == 0:
        face = mcolors.to_rgba(ax.figure.get_facecolor())
    return face


def readable_ink(patch: Rectangle, bar_axes: Axes) -> str:
    """White or the preset text colour, whichever reads better on the bar."""
    face = Rgba.of(mcolors.to_rgba(patch.get_facecolor()))
    shown = composite_over(face, Rgba.of(backdrop(bar_axes)).rgb)
    dark = mcolors.to_hex(mpl.rcParams["text.color"])
    return readable(shown, _rgb("white"), _rgb(dark)).pick("white", dark)


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
                patch.get_path()  # pyright: ignore[reportUnknownMemberType]
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


def _cell(ax: Axes) -> tuple[tuple[int, int], tuple[int, int]] | None:
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    grid = id(spec.get_gridspec())
    return (grid, spec.rowspan.start), (grid, spec.colspan.start)


def _ylabel_box(ax: Axes, renderer: RendererBase) -> Bbox | None:
    """The y-axis name of ``ax`` when it is drawn on the left."""
    label = ax.yaxis.label
    match label_side(ax.yaxis):
        case Near():
            pass
        case Far():
            return None
    if not _shown(label):
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
    match parse_valign(text.get_verticalalignment()):
        case Baseline():
            return float(text.get_transform().transform(text.get_position())[1])
        case AlignBottom() | AlignTop() | VCentre() | VCentreBaseline():
            pass
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


def _width(text: Text | None, renderer: RendererBase) -> float | None:
    if text is None or not _shown(text):
        return None
    return float(text.get_window_extent(renderer).width)


def panel(
    ax: Axes,
    letter: Text,
    renderer: RendererBase,
    joined: Text | None,
    apart: Text | None,
) -> Panel:
    """What ``ax`` draws around its top-left corner, for its ``letter``;
    ``joined`` is the title that follows a letter in a run, ``apart`` one
    that stays."""
    corner = tuple(map(float, ax.transAxes.transform((0.0, 1.0))))
    box = letter.get_window_extent(renderer)
    ticks = _ytick_box(ax, renderer)
    titles = tuple(
        Title(baseline_px(t, renderer))
        for t in axes_titles(ax).values()
        if _shown(t)
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
        height=float(box.height),
        descent=baseline_px(letter, renderer) - float(box.y0),
        size=float(letter.get_fontsize()) * px_per_pt(ax),
        cell=_cell(ax),
        titles=titles,
        top=top,
        decos=decos,
        plot_width=float(ax.get_window_extent(renderer).width),
        joined=_width(joined, renderer),
        apart=_width(apart, renderer),
    )
