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

from ..colorspace import (
    ContrastFacts,
    Ratio,
    Rgb,
    Rgba,
    composite_layers,
    composite_over,
    lifted,
    readable,
)
from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    get_renderer,
    label_side,
    projection,
    same_position_axes,
)
from ..vocab import (
    AlignBottom,
    AlignTop,
    Baseline,
    Curved,
    Far,
    Near,
    Rectilinear,
    ThreeD,
    VCentre,
    VCentreBaseline,
    X,
    Y,
    bars_along,
    parse_valign,
)
from .bar_options import Edge, Ink, Segment, StackTotal
from .panels import Panel, Title
from .places import Try
from .stacks import BarRun

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.patches import Rectangle
    from matplotlib.typing import ColorType

    from .bar_options import Kind

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
    out: list[float] = []
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


#: Text against its background: WCAG's 4.5:1 for body text.
TEXT_CONTRAST = Ratio(4.5)
WHITE = Rgb(1.0, 1.0, 1.0)


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


def _background(bar_axes: Axes) -> Rgb:
    """What shows behind the bars: the figure, then each visible Axes patch."""
    layers = backdrop_layers(same_position_axes(bar_axes))
    return composite_layers(tuple(Rgba.of(layer) for layer in layers), WHITE)


def readable_ink(patch: Rectangle, bar_axes: Axes) -> Ink:
    """White or the preset text colour, whichever reads better on the bar."""
    face = Rgba.of(mcolors.to_rgba(patch.get_facecolor()))
    shown = mcolors.to_hex(composite_over(face, _background(bar_axes)).channels)
    dark = mcolors.to_hex(mpl.rcParams["text.color"])
    ink = readable(_rgb(shown), _rgb("white"), _rgb(dark))
    return Ink(ink.pick("white", dark))


def series_ink(patch: Rectangle, bar_axes: Axes, kind: Kind) -> Ink:
    """The bar's colour as drawn, darkened (or lightened) to 4.5:1 text."""
    match kind:
        case StackTotal():
            return Ink()
        case Edge() | Segment():
            pass
    background = _background(bar_axes)
    face = mcolors.to_rgba(patch.get_facecolor())
    if face[3] == 0 and patch.get_linewidth() > 0:
        face = mcolors.to_rgba(patch.get_edgecolor())
    shown = composite_over(Rgba.of(face), background)
    return Ink(
        readable_on(
            mcolors.to_hex(shown.channels), mcolors.to_hex(background.channels)
        )
    )


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


def _guess_ylabel_x0(ax: Axes, renderer: RendererBase) -> float:
    """Where the outer edge of a y-axis name of ``ax`` would be."""
    x0 = float(ax.transAxes.transform((0.0, 1.0))[0])
    if not _plain(ax):
        return x0
    ticks = _ytick_box(ax, renderer)
    inner = min(x0, ticks.x0) if ticks is not None else x0
    _w, height, _d = renderer.get_text_width_height_descent(
        "Ag", ax.yaxis.label.get_fontproperties(), ismath=False
    )
    return inner - float(ax.yaxis.labelpad) * px_per_pt(ax) - float(height)


def panel(ax: Axes, letter: Text, renderer: RendererBase) -> Panel:
    """What ``ax`` draws around its top-left corner, for its ``letter``."""
    corner = tuple(map(float, ax.transAxes.transform((0.0, 1.0))))
    box = letter.get_window_extent(renderer)
    ylabel = _ylabel_box(ax, renderer) if _plain(ax) else None
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
        descent=baseline_px(letter, renderer) - float(box.y0),
        cell=_cell(ax),
        ylabel_x0=None if ylabel is None else float(ylabel.x0),
        guess_x0=_guess_ylabel_x0(ax, renderer),
        titles=titles,
        top=top,
        decos=decos,
    )


def host_axes(ax: Axes) -> Axes:
    """The Axes drawn last in ``ax``'s box: the top-most twin.

    Matplotlib draws Axes by zorder, then in figure order, so the
    ``ax.set_zorder(ax2.get_zorder() + 1)`` idiom puts ``ax`` on top.
    """
    owners = same_position_axes(ax)
    parent = ax.get_figure(root=False)
    order = parent.axes if parent is not None else owners
    return max(
        owners,
        key=lambda member: (
            member.get_zorder(),
            order.index(member) if member in order else -1,
        ),
    )


def backdrop_layers(
    axes: Sequence[Axes],
) -> list[tuple[float, float, float, float]]:
    """The patch colours that show behind ``axes``' data, lowest first.

    The figure's patch, then its subfigure's (when the Axes sit in one),
    then each Axes' own patch in zorder (stable on the order given); a patch
    that is not drawn adds nothing. Fold them over white with
    ``colorspace.composite_layers``. The ``axes`` share one figure.
    """
    first = axes[0]
    root = first.get_figure(root=True)
    parent = first.get_figure(root=False)
    containers = (root, parent if parent is not root else None)
    layers = [
        mcolors.to_rgba(container.get_facecolor())
        for container in containers
        if container is not None and container.patch.get_visible()
    ]
    layers.extend(
        mcolors.to_rgba(member.get_facecolor())
        for member in sorted(axes, key=lambda m: m.get_zorder())
        if _frame_on(member) and member.patch.get_visible()
    )
    return layers


def _plain(ax: Axes) -> bool:
    """Whether ``ax`` is matplotlib's plain 2D Axes."""
    match projection(ax):
        case Rectilinear():
            return True
        case ThreeD() | Curved():
            return False


def _frame_on(ax: Axes) -> bool:
    """Whether ``ax`` draws its patch; a 3D Axes has no frame switch.

    ``Axes3D`` sets ``get_frame_on`` to ``None`` and always draws its patch.
    """
    match projection(ax):
        case ThreeD():
            return True
        case Rectilinear() | Curved():
            return ax.get_frame_on()
