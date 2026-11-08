"""VALUE_LABEL_ON_DATA: a value label drawn over a bar, a line or a marker.

A value label is a short numeric text inside an Axes (``ax.text``,
``ax.annotate``, ``dm.annotate_value``, ``dm.label_bars``), parsed as
VALUE_LABEL_DECIMAL parses it, so prose ("Peak season") never votes. Data is
what the reader reads values from, in the same plot box (the Axes and its
``twinx`` / ``twiny`` partners), clipped to the box and drawn with visible
ink:

* bars of ``ax.bar`` / ``ax.barh`` (the patches of a ``BarContainer``);
* ``Line2D`` drawn in data coordinates on both axes: the line at its width
  and its markers (``axhline`` / ``axvline`` / ``axline`` references are
  not data);
* ``scatter`` markers at their size.

A label covers data when its ink (the glyphs, not the text box with the
font's ascent and descent) meets one of them by more than half a point; a
label resting on a bar end or beside a line only touches it. A
label sitting on its own bar (inside it, centred across it) or with its
centre inside a marker (a bubble label) is there on purpose: that artist
does not count, any other still does. A label with a visible background box
(a ``bbox=`` patch) is drawn over data on purpose and is skipped, as are
``ax.clabel`` contour labels; a slanted label (rotation off 0/90/180/270)
is skipped because its box is not its ink. An annotation's arrow points at
the data on purpose: only its text counts. Labels over other labels are
OVERLAP's. Areas, images, meshes, contours, wedges and collections other
than ``scatter`` are not data here.
"""

from __future__ import annotations

from numbers import Integral, Real
from typing import TYPE_CHECKING, Literal, NamedTuple, TypeAlias, TypedDict

import numpy as np
from matplotlib import cbook
from matplotlib.collections import PathCollection
from matplotlib.colors import to_rgba
from matplotlib.container import BarContainer
from matplotlib.contour import ContourSet
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox, IdentityTransform

from ..._figure_geometry import same_position_axes
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix
from .value_label_decimal import _value_label

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.typing import ColorType

__all__ = ["check_value_label_on_data"]

Covered: TypeAlias = Literal["bar", "line", "marker"]

# Ink that meets data by no more than this (on any side) rests on it: a
# label on a bar end or beside a line touches the data, it does not cover it.
_TOUCH_PT = 0.5
_NO_LINE = ("None", "none", "", " ")
_NO_MARKER = (None, "None", "none", "", " ")
_SCATTER = -1  # the marker key of a scatter: never an ``id`` of a line


class ValueLabelOnDataDetail(TypedDict):
    """``count`` of the ``labels`` value labels of Axes ``axes_index`` cover data.

    ``covered`` lists the kinds met (``"bar"``, ``"line"``, ``"marker"``),
    ``artists`` the legend labels of the first three artists met (``""``
    when unnamed) and ``example`` the first covering label's text.
    """

    axes_index: int
    count: int
    labels: int
    covered: list[str]
    artists: list[str]
    example: str


class _Bars(NamedTuple):
    """Visible bars in display px, clipped to the plot box."""

    box: np.ndarray  # (n, 4): x0, y0, x1, y1
    horizontal: np.ndarray  # (n,) bool, ``ax.barh``
    names: list[str]


class _Polyline(NamedTuple):
    """A drawn line's finite segments in display px and their boxes.

    Sorted by their left end, so a label looks only at the segments that
    start within ``reach`` (the widest segment) of its left edge.
    """

    a: np.ndarray
    b: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    reach: float
    half: float  # half the line width, px
    name: str
    key: int  # ``id`` of the Line2D, so its markers are not counted twice


class _Markers(NamedTuple):
    """Visible marker centres in display px and their radii, sorted by x."""

    xy: np.ndarray
    r: np.ndarray
    reach: float  # the largest radius
    name: str
    key: int  # ``id`` of the owning Line2D, ``_SCATTER`` for a scatter


class _Data(NamedTuple):
    """The data of one plot box, measured once per Axes."""

    bars: _Bars
    lines: list[_Polyline]
    markers: list[_Markers]


class _Hit(NamedTuple):
    kind: Covered
    name: str


def _px(points: float, fig: Figure) -> float:
    return float(points) * fig.dpi / 72.0


def _name(artist: object) -> str:
    label = getattr(artist, "get_label", lambda: "")()
    return "" if not label or str(label).startswith("_") else str(label)


def _alpha(color: ColorType, alpha: float | None = None) -> float:
    return float(to_rgba(color, alpha)[3])


def _clip(box: Bbox, frame: Bbox) -> Bbox | None:
    x0, y0 = max(box.x0, frame.x0), max(box.y0, frame.y0)
    x1, y1 = min(box.x1, frame.x1), min(box.y1, frame.y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return Bbox.from_extents(x0, y0, x1, y1)


def _glyph_shares(text: Text, renderer: RendererBase) -> tuple[float, float]:
    """The shares of the text box under the baseline and over the glyphs.

    The box spans the font's descent and ascent about the baseline; a value
    label's ink sits on the baseline and rises to its glyphs' top. A comma's
    or a parenthesis' tail below the baseline does not hide data, so a label
    resting on a bar end is a touch however it is punctuated. The baseline's
    place in the box comes from laying the same string out unrotated on a
    baseline at the origin: matplotlib's own layout, without touching the
    label.
    """
    figure = text.get_figure(root=True)
    if figure is None:
        return 0.0, 0.0
    string = text.get_text()
    prop = text.get_fontproperties()
    probe = Text(
        0,
        0,
        string,
        fontproperties=prop,
        linespacing=text.get_linespacing(),
        usetex=text.get_usetex(),
        parse_math=text.get_parse_math(),
        transform=IdentityTransform(),
    )
    probe.set_figure(figure)
    line = probe.get_window_extent(renderer)  # [-descent, ascent], baseline 0
    ismath: bool | Literal["TeX"] = (
        "TeX"
        if text.get_usetex()
        else bool(text.get_parse_math()) and cbook.is_math_text(string)
    )
    _w, height, descent = renderer.get_text_width_height_descent(
        string, prop, ismath=ismath
    )
    if line.height <= 0:
        return 0.0, 0.0
    under = max(0.0, -line.y0) / line.height
    over = max(0.0, line.y1 - (height - descent)) / line.height
    return under, over


def _inset(x0: float, y0: float, x1: float, y1: float, by: float) -> Bbox:
    """The box inset by ``by`` on every side; one too small keeps its centre."""
    x0, y0, x1, y1 = x0 + by, y0 + by, x1 - by, y1 - by
    if x1 < x0:
        x0 = x1 = (x0 + x1) / 2
    if y1 < y0:
        y0 = y1 = (y0 + y1) / 2
    return Bbox.from_extents(x0, y0, x1, y1)


def _ink_box(
    text: Text, box: Bbox, renderer: RendererBase, touch: float
) -> Bbox:
    """The label's glyphs within its text ``box``, less the ``touch`` margin."""
    under, over = _glyph_shares(text, renderer)
    x0, y0, x1, y1 = box.x0, box.y0, box.x1, box.y1
    w, h = box.width, box.height
    match round(float(text.get_rotation())) % 360:
        case 90:  # the glyphs' tops face left
            x0, x1 = x0 + over * w, x1 - under * w
        case 180:
            y0, y1 = y0 + over * h, y1 - under * h
        case 270:
            x0, x1 = x0 + under * w, x1 - over * w
        case _:
            y0, y1 = y0 + under * h, y1 - over * h
    return _inset(x0, y0, x1, y1, touch)


# ------------------------------------------------------------------ data
def _bars(owners: list[Axes], frame: Bbox, renderer: RendererBase) -> _Bars:
    boxes: list[tuple[float, float, float, float]] = []
    horizontal: list[bool] = []
    names: list[str] = []
    for owner in owners:
        for container in owner.containers:
            if not isinstance(container, BarContainer):
                continue
            name = _name(container)
            for patch in container.patches:
                if not patch.get_visible():
                    continue
                face = _alpha(patch.get_facecolor())
                edge = _alpha(patch.get_edgecolor())
                if face <= 0 and (edge <= 0 or patch.get_linewidth() <= 0):
                    continue  # an invisible spacer bar holds no value
                try:
                    raw = patch.get_window_extent(renderer)
                except BBOX_ERRORS:
                    continue
                bar = _clip(raw, frame)
                if bar is None:
                    continue
                boxes.append((bar.x0, bar.y0, bar.x1, bar.y1))
                horizontal.append(container.orientation == "horizontal")
                names.append(name)
    return _Bars(
        np.asarray(boxes, dtype=np.float64).reshape(-1, 4),
        np.asarray(horizontal, dtype=bool),
        names,
    )


def _is_data_line(line: Line2D, owner: Axes) -> bool:
    """Drawn in data coordinates on both axes (``axhline``, ``axline`` are not)."""
    try:
        in_x, in_y = line.get_transform().contains_branch_seperately(
            owner.transData
        )
    except BBOX_ERRORS:
        return False
    return bool(in_x and in_y)


def _polyline(
    line: Line2D, frame: Bbox, fig: Figure, key: int
) -> _Polyline | None:
    if line.get_linestyle() in _NO_LINE or line.get_linewidth() <= 0:
        return None
    if _alpha(line.get_color(), line.get_alpha()) <= 0:
        return None
    points = line.get_transform().transform(
        np.asarray(line.get_path().vertices, dtype=np.float64)
    )
    a, b = points[:-1], points[1:]
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    half = _px(line.get_linewidth(), fig) / 2
    # Finite segments that reach the plot box; NaN breaks the line.
    keep = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
    keep &= (lo[:, 0] <= frame.x1 + half) & (hi[:, 0] >= frame.x0 - half)
    keep &= (lo[:, 1] <= frame.y1 + half) & (hi[:, 1] >= frame.y0 - half)
    if not keep.any():
        return None
    order = np.argsort(lo[keep][:, 0], kind="stable")
    a, b, lo, hi = (v[keep][order] for v in (a, b, lo, hi))
    reach = float(np.max(hi[:, 0] - lo[:, 0]))
    return _Polyline(a, b, lo, hi, reach, half, _name(line), key)


def _sorted_markers(
    xy: np.ndarray, r: np.ndarray, name: str, key: int
) -> _Markers:
    order = np.argsort(xy[:, 0], kind="stable")
    return _Markers(xy[order], r[order], float(np.max(r)), name, key)


def _window(xs: np.ndarray, reach: float, x0: float, x1: float) -> slice:
    """The run of ascending ``xs`` within ``[x0 - reach, x1 + reach]``."""
    start = int(np.searchsorted(xs, x0 - reach, side="left"))
    return slice(start, int(np.searchsorted(xs, x1 + reach, side="right")))


def _in_frame(xy: np.ndarray, frame: Bbox) -> np.ndarray:
    x, y = xy[:, 0], xy[:, 1]
    ok = np.isfinite(x) & np.isfinite(y)
    ok &= (frame.x0 <= x) & (x <= frame.x1)
    ok &= (frame.y0 <= y) & (y <= frame.y1)
    return np.asarray(ok, dtype=np.bool_)


def _marked(xy: np.ndarray, every: object) -> np.ndarray | None:
    """The points ``markevery`` puts a marker on, picked as matplotlib does.

    ``None`` for a spacing in Axes fractions (a float), which follows the
    drawn path's length: those markers are left out, the line still counts.
    """
    if every is None:
        return xy
    if isinstance(every, Integral):
        every = (0, every)
    if isinstance(every, tuple):
        start, step = every if len(every) == 2 else (None, None)
        if isinstance(start, Integral) and isinstance(step, Integral):
            return xy[int(start) :: int(step)]
        return None
    if isinstance(every, Real):
        return None
    if isinstance(every, slice):
        return xy[every]
    try:  # fancy indexing: indices or a boolean mask
        picked: np.ndarray = xy[np.asarray(every)]
    except (ValueError, IndexError):
        return None
    return picked


def _line_markers(
    line: Line2D, frame: Bbox, fig: Figure, key: int
) -> _Markers | None:
    if line.get_marker() in _NO_MARKER or line.get_markersize() <= 0:
        return None
    face = _alpha(line.get_markerfacecolor(), line.get_alpha())
    edge = _alpha(line.get_markeredgecolor(), line.get_alpha())
    if face <= 0 and (edge <= 0 or line.get_markeredgewidth() <= 0):
        return None
    xy = _marked(
        line.get_transform().transform(
            np.asarray(line.get_xydata(), dtype=np.float64)
        ),
        line.get_markevery(),
    )
    if xy is None:
        return None
    xy = xy[_in_frame(xy, frame)]
    if not len(xy):
        return None
    r = _px(line.get_markersize() / 2 + line.get_markeredgewidth() / 2, fig)
    return _sorted_markers(xy, np.full(len(xy), r), _name(line), key)


def _scatter(
    coll: PathCollection, frame: Bbox, fig: Figure, key: int
) -> _Markers | None:
    offsets = np.asarray(coll.get_offsets(), dtype=np.float64).reshape(-1, 2)
    sizes = np.asarray(coll.get_sizes(), dtype=np.float64)
    if not len(offsets) or not sizes.size:
        return None
    n = len(offsets)
    xy = coll.get_offset_transform().transform(offsets)
    faces = np.asarray(coll.get_facecolor(), dtype=np.float64).reshape(-1, 4)
    edges = np.asarray(coll.get_edgecolor(), dtype=np.float64).reshape(-1, 4)
    widths = np.asarray(coll.get_linewidth(), dtype=np.float64).ravel()
    face = np.resize(faces[:, 3], n) if len(faces) else np.zeros(n)
    edge = np.resize(edges[:, 3], n) if len(edges) else np.zeros(n)
    width = np.resize(widths, n) if widths.size else np.zeros(n)
    radius = _px(1.0, fig) * (np.sqrt(np.resize(sizes, n)) + width) / 2
    keep = _in_frame(xy, frame) & ((face > 0) | ((edge > 0) & (width > 0)))
    keep &= radius > 0
    if not keep.any():
        return None
    return _sorted_markers(xy[keep], radius[keep], _name(coll), key)


def _measure(
    owners: list[Axes], frame: Bbox, renderer: RendererBase, fig: Figure
) -> _Data:
    lines: list[_Polyline] = []
    markers: list[_Markers] = []
    for owner in owners:
        for line in owner.get_lines():
            if not line.get_visible() or not _is_data_line(line, owner):
                continue
            try:
                drawn = _polyline(line, frame, fig, id(line))
                marks = _line_markers(line, frame, fig, id(line))
            except BBOX_ERRORS:
                continue
            lines.extend([drawn] if drawn is not None else [])
            markers.extend([marks] if marks is not None else [])
        for coll in owner.collections:
            if not isinstance(coll, PathCollection) or not coll.get_visible():
                continue
            try:
                dots = _scatter(coll, frame, fig, _SCATTER)
            except BBOX_ERRORS:
                continue
            markers.extend([dots] if dots is not None else [])
    return _Data(_bars(owners, frame, renderer), lines, markers)


# ------------------------------------------------------------------ hits
def _segments_hit(line: _Polyline, box: Bbox) -> bool:
    """Whether ``line`` meets ``box`` (Liang-Barsky on the segments near it)."""
    run = _window(line.lo[:, 0], line.reach, box.x0, box.x1)
    lo, hi = line.lo[run], line.hi[run]
    near = (lo[:, 0] <= box.x1) & (hi[:, 0] >= box.x0)
    near &= (lo[:, 1] <= box.y1) & (hi[:, 1] >= box.y0)
    if not near.any():
        return False
    a, b = line.a[run][near], line.b[run][near]
    d = b - a
    t0 = np.zeros(len(a))
    t1 = np.ones(len(a))
    alive = np.ones(len(a), dtype=bool)
    for p, q in (
        (-d[:, 0], a[:, 0] - box.x0),
        (d[:, 0], box.x1 - a[:, 0]),
        (-d[:, 1], a[:, 1] - box.y0),
        (d[:, 1], box.y1 - a[:, 1]),
    ):
        parallel = p == 0
        alive &= ~(parallel & (q < 0))
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.where(parallel, 0.0, q / np.where(parallel, 1.0, p))
        t0 = np.where((p < 0) & ~parallel, np.maximum(t0, r), t0)
        t1 = np.where((p > 0) & ~parallel, np.minimum(t1, r), t1)
    return bool(np.any(alive & (t0 <= t1)))


def _bar_hits(
    bars: _Bars, ink: Bbox, centre: tuple[float, float], touch: float
) -> list[str]:
    """Names of the bars ``ink`` meets, leaving out the bar it sits on.

    A label on its own bar (``dm.label_bars(where="inside")``, a stack
    segment's) has its centre across the bar and its ink held within the
    bar's length; a label centred on the bar's end sticks out of it and
    covers the end, which is the value.
    """
    if not len(bars.box):
        return []
    x0, y0, x1, y1 = bars.box.T
    cx, cy = centre
    on_vertical = (x0 <= cx) & (cx <= x1)
    on_vertical &= (ink.y0 >= y0 - touch) & (ink.y1 <= y1 + touch)
    on_horizontal = (y0 <= cy) & (cy <= y1)
    on_horizontal &= (ink.x0 >= x0 - touch) & (ink.x1 <= x1 + touch)
    own = np.where(bars.horizontal, on_horizontal, on_vertical)
    meets = np.minimum(ink.x1, x1) > np.maximum(ink.x0, x0)
    meets &= np.minimum(ink.y1, y1) > np.maximum(ink.y0, y0)
    return [bars.names[i] for i in np.flatnonzero(meets & ~own)]


def _hits(
    data: _Data,
    frame: Bbox,
    ink: Bbox,
    centre: tuple[float, float],
    touch: float,
) -> list[_Hit]:
    found = [
        _Hit("bar", name) for name in _bar_hits(data.bars, ink, centre, touch)
    ]
    clipped = _clip(ink, frame)
    if clipped is None:
        return found
    lined: set[int] = set()
    for line in data.lines:
        grown = Bbox.from_extents(
            clipped.x0 - line.half,
            clipped.y0 - line.half,
            clipped.x1 + line.half,
            clipped.y1 + line.half,
        )
        if _segments_hit(line, grown):
            found.append(_Hit("line", line.name))
            lined.add(line.key)
    for marks in data.markers:
        if marks.key in lined:
            continue  # a line met is one hit: its own markers are not again
        run = _window(marks.xy[:, 0], marks.reach, clipped.x0, clipped.x1)
        x, y = marks.xy[run, 0], marks.xy[run, 1]
        r2 = marks.r[run] ** 2
        # The marker the label sits inside (a bubble label: centred on it
        # and no wider than it) does not count; a small marker under a
        # label centred on it is covered.
        inside = (centre[0] - x) ** 2 + (centre[1] - y) ** 2 <= r2
        inside &= marks.r[run] >= max(ink.width, ink.height) / 2
        nx = np.clip(x, clipped.x0, clipped.x1)
        ny = np.clip(y, clipped.y0, clipped.y1)
        if np.any(~inside & ((x - nx) ** 2 + (y - ny) ** 2 <= r2)):
            found.append(_Hit("marker", marks.name))
    return found


# ---------------------------------------------------------------- labels
def _contour_labels(ax: Axes) -> set[int]:
    """``ax.clabel`` texts: inline labels drawn on their contour on purpose."""
    found: set[int] = set()
    for coll in ax.collections:
        if isinstance(coll, ContourSet):
            found.update(id(t) for t in getattr(coll, "labelTexts", []))
    return found


def _text_box(text: Text, renderer: RendererBase) -> Bbox | None:
    """The label's own text box in display px; ``None`` when not drawn.

    ``Annotation.get_window_extent`` adds the arrow, which points at the
    data on purpose; its ``get_tightbbox`` is null when matplotlib skips the
    annotation (``annotation_clip``).
    """
    if isinstance(text, Annotation):
        drawn = text.get_tightbbox(renderer)
        if drawn is None or not np.isfinite(drawn.extents).all():
            return None
        box = Text.get_window_extent(text, renderer)
    else:
        box = text.get_window_extent(renderer)
    if box.width <= 0 or box.height <= 0:
        return None
    return box


def _is_value_label(text: Text, contour: set[int]) -> bool:
    if not text.get_visible() or _value_label(text.get_text()) is None:
        return False
    if id(text) in contour:
        return False
    if _alpha(text.get_color(), text.get_alpha()) <= 0:
        return False  # drawn without ink
    # A slanted label's box is not its ink: leave it out.
    if float(text.get_rotation()) % 90 != 0:
        return False
    patch = text.get_bbox_patch()
    if patch is None or not patch.get_visible():
        return True
    # A visible background box: drawn over the data on purpose.
    return _alpha(patch.get_facecolor()) <= 0


def _value_labels(ax: Axes, renderer: RendererBase) -> list[tuple[Text, Bbox]]:
    contour = _contour_labels(ax)
    found: list[tuple[Text, Bbox]] = []
    for text in ax.texts:
        if not _is_value_label(text, contour):
            continue
        try:
            box = _text_box(text, renderer)
        except BBOX_ERRORS:
            continue
        if box is not None:
            found.append((text, box))
    return found


def _label_hits(
    text: Text,
    box: Bbox,
    data: _Data,
    frame: Bbox,
    renderer: RendererBase,
    touch: float,
) -> list[_Hit]:
    """What the label's ink covers.

    The ink lies inside the text box, so a box that meets nothing has ink
    that meets nothing: the glyphs are measured only for a box that does.
    """
    centre = ((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
    whole = _inset(box.x0, box.y0, box.x1, box.y1, touch)
    if not _hits(data, frame, whole, centre, touch):
        return []
    try:
        ink = _ink_box(text, box, renderer, touch)
    except BBOX_ERRORS:
        return []
    return _hits(data, frame, ink, centre, touch)


@register_check("VALUE_LABEL_ON_DATA", order=57)
def check_value_label_on_data(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Flag Axes whose value labels are drawn over bars, lines or markers."""
    warnings: list[VisualWarning] = []
    touch = _px(_TOUCH_PT, fig)
    for axes_index, ax in enumerate(fig.axes):
        if not ax.get_visible() or ax.name != "rectilinear":
            continue
        labels = _value_labels(ax, renderer)
        if not labels:
            continue
        frame = ax.get_window_extent(renderer)
        data = _measure(same_position_axes(ax), frame, renderer, fig)
        covering: list[tuple[Text, list[_Hit]]] = []
        for text, box in labels:
            hits = _label_hits(text, box, data, frame, renderer, touch)
            if hits:
                covering.append((text, hits))
        if not covering:
            continue
        kinds: list[str] = sorted(
            {hit.kind for _text, hits in covering for hit in hits}
        )
        names = list(
            dict.fromkeys(hit.name for _text, hits in covering for hit in hits)
        )
        example = covering[0][0].get_text().strip()
        warnings.append(
            VisualWarning(
                severity=Severity.WARNING,
                check_id="VALUE_LABEL_ON_DATA",
                message=(
                    f"Axes[{axes_index}]: {len(covering)} of {len(labels)} "
                    "value labels are drawn over "
                    f"{', '.join(kind + 's' for kind in kinds)} "
                    f"(first {example!r}); move them off the data"
                ),
                detail=wire(
                    ValueLabelOnDataDetail(
                        axes_index=axes_index,
                        count=len(covering),
                        labels=len(labels),
                        covered=kinds,
                        artists=names[:3],
                        example=example[:30],
                    )
                ),
            )
        )
    return warnings


@register_fix("VALUE_LABEL_ON_DATA")
def _fix_value_label_on_data(_warning: VisualWarning) -> list[str]:
    """Placements that keep a value label off the data it names."""
    return [
        "# Bar values beyond the bar ends (or inside their own bars)\n"
        "dm.label_bars(ax)",
        "# A value on a line or a point, on a free side 3 pt away\n"
        "dm.annotate_value(ax, x, y, text)",
        "# By hand: offset in points, not in data units\n"
        "ax.annotate(text, (x, y), xytext=(0, 3), textcoords='offset points',\n"
        "            ha='center', va='bottom')",
    ]
