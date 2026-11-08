"""VALUE_LABEL_ON_DATA: a value label drawn over a bar, a line or a marker.

A value label is a short numeric text inside an Axes (``ax.text``,
``ax.annotate``, ``dm.annotate_value``, ``dm.label_bars``), parsed as
VALUE_LABEL_DECIMAL parses it, so prose ("Peak season") never votes. Data is
what the reader reads values from, in the same plot box (the Axes and its
``twinx`` / ``twiny`` partners), clipped to the box and drawn with visible
ink:

* bars of ``ax.bar`` / ``ax.barh`` (the patches of a ``BarContainer``);
* ``Line2D`` drawn in data coordinates on both axes: the line at its width
  where its dash pattern inks it (a dashed line's gaps are not data, unless
  a ``gapcolor`` fills them) and the markers ``markevery`` keeps, both read
  back from ``Line2D.draw`` (``axhline`` / ``axvline`` / ``axline``
  references are not data; a line with path effects or a sketch counts
  solid, the former with every point marked);
* ``scatter`` markers at their size.

A label covers data when its ink (the glyphs down to their descenders, not
the text box with the font's ascent and descent; the tails of commas,
parentheses and currency signs aside) meets one of them by more than half a
point; a label resting on a bar end or beside a line only touches it. A
clipped label (``clip_on`` with a clip box or path) counts by the part its
clip draws, and not at all when it draws none. A label sitting on its own
bar (inside it, centred across it) or with its
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

import re
import unicodedata
from typing import TYPE_CHECKING, Literal, NamedTuple, TypeAlias, TypedDict

import numpy as np
from matplotlib import cbook
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import PathCollection
from matplotlib.colors import to_rgba
from matplotlib.container import BarContainer
from matplotlib.contour import ContourSet
from matplotlib.path import Path
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox, IdentityTransform, TransformedPath

from ..._figure_geometry import same_position_axes
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix
from .value_label_decimal import _value_label

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import GraphicsContextBase
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.transforms import Transform
    from matplotlib.typing import ColorType
    from numpy.typing import ArrayLike

__all__ = ["check_value_label_on_data"]

Covered: TypeAlias = Literal["bar", "line", "marker"]

# Ink that meets data by no more than this (on any side) rests on it: a
# label on a bar end or beside a line touches the data, it does not cover it.
_TOUCH_PT = 0.5
_NO_LINE = ("None", "none", "", " ")
_NO_MARKER = (None, "None", "none", "", " ")
_SCATTER = -1  # the marker key of a scatter: never an ``id`` of a line
_DOLLAR = re.compile(r"(?<!\\)\$")  # an unescaped mathtext delimiter
_UNCLIPPED = Bbox.from_extents(-np.inf, -np.inf, np.inf, np.inf)
# A dash is widened by this at both ends: where a rasteriser snaps and
# smooths the dash ends (measured within 0.6 px of Agg's).
_DASH_SLACK_PX = 1.0
_MAX_DASH_CUTS = 1_000_000  # more pattern edges than this: count it solid
_NOWHERE = Bbox.from_extents(0.0, 0.0, 0.0, 0.0)  # meets nothing


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


def _laid_out(text: Text) -> tuple[str, bool | Literal["TeX"]]:
    """The string matplotlib measures for ``text`` and how it parses it.

    ``Text`` hands the renderer its string unchanged under ``usetex`` or
    when it is mathtext, and with ``\\$`` unescaped otherwise.
    """
    string = text.get_text()
    if text.get_usetex():
        return string, "TeX"
    if not text.get_parse_math():
        return string, False
    if cbook.is_math_text(string):
        return string, True
    return string.replace(r"\$", "$"), False


def _without_marks(string: str, ismath: bool | Literal["TeX"]) -> str:
    """``string`` less its punctuation and symbols outside mathtext.

    Commas, parentheses, currency and percent signs and the like dip below
    the baseline as tails of the marks around a number; letters and digits
    keep theirs (``g``, ``y``, ``p``). Mathtext is kept whole and TeX
    untouched: their glyphs count as drawn.
    """

    def kept(part: str) -> str:
        return "".join(
            ch for ch in part if unicodedata.category(ch)[0] not in "PS"
        )

    if ismath == "TeX":
        return string
    if not ismath:
        return kept(string)
    parts = _DOLLAR.split(string)  # text, math, text, ...
    return "$".join(
        part if i % 2 else kept(part) for i, part in enumerate(parts)
    )


class _Glyphs(NamedTuple):
    """Where a label's glyphs lie in its unrotated text box (px).

    The box spans the font's descent and ascent about the baseline; the ink
    rises to the glyphs' top and drops to their descent: a ``g``'s or a
    ``p``'s tail is drawn, the room under digits is not. The tail of a
    mark around the number (a comma, a parenthesis, a ``$``) does not hide
    data, so a label resting on a bar end is a touch however it is
    punctuated: ``depth`` measures the string without those marks.
    """

    below: float  # the box's depth under the baseline
    above: float  # the box's height over the baseline
    top: float  # the glyphs' top over the baseline
    tails: float  # the deepest glyph under the baseline, marks included
    core: str | None  # the string less its marks; None when it has none
    ismath: bool | Literal["TeX"]

    def depth(self, text: Text, renderer: RendererBase) -> float:
        """How far the glyphs other than the marks drop under the baseline."""
        if self.core is None:
            return self.tails
        if not self.core.strip(" $"):
            return 0.0
        try:
            _w, _h, descent = renderer.get_text_width_height_descent(
                self.core, text.get_fontproperties(), self.ismath
            )
        except ValueError:  # mathtext that no longer parses: keep it all
            return self.tails
        return max(0.0, min(float(descent), self.tails))


def _glyphs(text: Text, renderer: RendererBase) -> _Glyphs | None:
    """Measure the label's glyphs; ``None`` when it has no figure or box.

    The baseline's place in the box comes from laying the same string out
    unrotated on a baseline at the origin: matplotlib's own layout, without
    touching the label.
    """
    figure = text.get_figure(root=True)
    if figure is None:
        return None
    prop = text.get_fontproperties()
    probe = Text(
        0,
        0,
        text.get_text(),
        fontproperties=prop,
        linespacing=text.get_linespacing(),
        usetex=text.get_usetex(),
        parse_math=text.get_parse_math(),
        transform=IdentityTransform(),
    )
    probe.set_figure(figure)
    line = probe.get_window_extent(renderer)  # [-descent, ascent], baseline 0
    if line.height <= 0:
        return None
    string, ismath = _laid_out(text)
    _w, height, descent = renderer.get_text_width_height_descent(
        string, prop, ismath=ismath
    )
    core = _without_marks(string, ismath)
    return _Glyphs(
        below=max(0.0, -line.y0),
        above=max(0.0, line.y1),
        top=float(height - descent),
        tails=max(0.0, float(descent)),
        core=None if core == string else core,
        ismath=ismath,
    )


def _inset(x0: float, y0: float, x1: float, y1: float, by: float) -> Bbox:
    """The box inset by ``by`` on every side; one too small keeps its centre."""
    x0, y0, x1, y1 = x0 + by, y0 + by, x1 - by, y1 - by
    if x1 < x0:
        x0 = x1 = (x0 + x1) / 2
    if y1 < y0:
        y0 = y1 = (y0 + y1) / 2
    return Bbox.from_extents(x0, y0, x1, y1)


def _ink_box(
    text: Text,
    box: Bbox,
    glyphs: _Glyphs | None,
    depth: float,
    touch: float,
    region: Bbox,
) -> Bbox | None:
    """The label's glyphs down to ``depth`` under the baseline within its
    text ``box``, where its clip ``region`` lets them through, less the
    ``touch`` margin; ``None`` when nothing is let through."""
    under = over = 0.0
    if glyphs is not None:
        height = glyphs.below + glyphs.above
        under = max(0.0, glyphs.below - depth) / height
        over = max(0.0, glyphs.above - glyphs.top) / height
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
    seen = _clip(Bbox.from_extents(x0, y0, x1, y1), region)
    if seen is None:
        return None
    return _inset(seen.x0, seen.y0, seen.x1, seen.y1, touch)


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


class _Stroke(NamedTuple):
    """One stroke of a line as the canvas gets it."""

    path: Path  # display px; NaN gaps and the canvas cut out, MOVETO per run
    half: float  # half its width, px
    # The dash offset and on/off lengths (px) it is stroked with; None: solid.
    dashes: tuple[float, np.ndarray] | None = None


class _Recorder(RendererBase):
    """A renderer that takes down what a ``Line2D`` draws, drawing nothing.

    ``Line2D.draw`` makes its drawing decisions itself: which markers
    ``markevery`` keeps (by index, or along the drawn path's length for a
    float), the strokes and their dash patterns. Drawing a line into this
    renderer reads those decisions back through the public renderer
    interface, so they are matplotlib's own, not a copy of its rules.
    """

    def __init__(self, renderer: RendererBase) -> None:
        super().__init__()
        self._renderer = renderer
        self.strokes: list[_Stroke] = []
        self.marks: list[np.ndarray] = []

    def points_to_pixels(self, points: ArrayLike) -> ArrayLike:
        return self._renderer.points_to_pixels(points)

    def get_canvas_width_height(self) -> tuple[float, float]:
        return self._renderer.get_canvas_width_height()

    def draw_path(
        self,
        gc: GraphicsContextBase,
        path: Path,
        transform: Transform,
        rgbFace: ColorType | None = None,
    ) -> None:
        width = float(np.asarray(self.points_to_pixels(gc.get_linewidth())))
        if width <= 0 or gc.get_rgb()[3] <= 0:
            return
        # The vertices the canvas strokes: NaN removed, cut to the canvas,
        # simplified and snapped as the backends prepare a path.
        w, h = self.get_canvas_width_height()
        drawn = path.cleaned(
            transform=transform,
            remove_nans=True,
            clip=(0.0, 0.0, w, h),
            simplify=path.should_simplify,
            snap=gc.get_snap(),
            stroke_width=width,
        )
        self.strokes.append(_Stroke(drawn, width / 2, self._dashes(gc)))

    def _dashes(
        self, gc: GraphicsContextBase
    ) -> tuple[float, np.ndarray] | None:
        """The stroke's dash offset and on/off lengths in px; None: solid.

        ``Line2D.draw`` hands the renderer its pattern already scaled to
        the width, in points. An odd list repeats (as SVG and PDF dash).
        A sketched stroke wanders off its path, so its dashes cannot be
        placed: it counts as solid, which can only add hits.
        """
        offset, lengths = gc.get_dashes()
        if lengths is None or gc.get_sketch_params() is not None:
            return None
        try:
            on_off = np.asarray(
                self.points_to_pixels(np.asarray(lengths, dtype=np.float64)),
                dtype=np.float64,
            ).ravel()
            shift = float(np.asarray(self.points_to_pixels(float(offset))))
        except (TypeError, ValueError):
            return None
        if (
            not on_off.size
            or not np.isfinite(on_off).all()
            or (on_off < 0).any()
            or on_off.sum() <= 0
            or not np.isfinite(shift)
        ):
            return None
        if on_off.size % 2:
            on_off = np.concatenate([on_off, on_off])
        return shift, on_off

    def draw_markers(
        self,
        gc: GraphicsContextBase,
        marker_path: Path,
        marker_trans: Transform,
        path: Path,
        trans: Transform,
        rgbFace: ColorType | None = None,
    ) -> None:
        face = 0.0 if rgbFace is None else _alpha(rgbFace)
        edge = gc.get_rgb()[3] if gc.get_linewidth() > 0 else 0.0
        if face <= 0 and edge <= 0:
            return
        xy = trans.transform(np.asarray(path.vertices, dtype=np.float64))
        self.marks.append(xy[np.isfinite(xy).all(axis=1)])

    def take(self, line: Line2D) -> tuple[list[_Stroke], np.ndarray]:
        """The strokes and the marker centres (display px) ``line`` draws."""
        self.strokes, self.marks = [], []
        line.draw(self)
        marks = np.concatenate(self.marks) if self.marks else np.empty((0, 2))
        return self.strokes, marks


def _as_set(line: Line2D, fig: Figure) -> tuple[list[_Stroke], np.ndarray]:
    """A line drawn through path effects, read from its properties.

    A path effect redraws the stroke its own way (a halo, a shadow) and its
    markers as paths, so the drawing cannot be read back: the whole line
    counts as one solid stroke and every point as marked, which can only
    add hits.
    """
    strokes: list[_Stroke] = []
    transform = line.get_transform()
    if (
        line.get_linestyle() not in _NO_LINE
        and line.get_linewidth() > 0
        and _alpha(line.get_color(), line.get_alpha()) > 0
    ):
        path = transform.transform_path(line.get_path())
        strokes.append(
            _Stroke(
                path.cleaned(remove_nans=True),
                _px(line.get_linewidth(), fig) / 2,
            )
        )
    face = _alpha(line.get_markerfacecolor(), line.get_alpha())
    edge = _alpha(line.get_markeredgecolor(), line.get_alpha())
    if (
        line.get_marker() in _NO_MARKER
        or line.get_markersize() <= 0
        or (face <= 0 and (edge <= 0 or line.get_markeredgewidth() <= 0))
    ):
        return strokes, np.empty((0, 2))
    xy = transform.transform(np.asarray(line.get_xydata(), dtype=np.float64))
    return strokes, xy[np.isfinite(xy).all(axis=1)]


def _joined(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """A path's vertices and which of them a LINETO joins to the next."""
    vertices = np.asarray(path.vertices, dtype=np.float64)
    if path.codes is None:
        return vertices, np.ones(max(len(vertices) - 1, 0), dtype=bool)
    codes = np.asarray(path.codes)
    return vertices, np.asarray(codes[1:] == Path.LINETO, dtype=bool)


def _near(a: np.ndarray, b: np.ndarray, frame: Bbox, by: float) -> np.ndarray:
    """Segments whose box, grown by ``by``, reaches the plot box."""
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    near = (lo[:, 0] <= frame.x1 + by) & (hi[:, 0] >= frame.x0 - by)
    near &= (lo[:, 1] <= frame.y1 + by) & (hi[:, 1] >= frame.y0 - by)
    return np.asarray(near, dtype=np.bool_)


def _dashed(
    vertices: np.ndarray,
    joined: np.ndarray,
    dashes: tuple[float, np.ndarray],
    frame: Bbox,
    by: float,
) -> tuple[np.ndarray, np.ndarray]:
    """The pieces of the joined segments a dash pattern inks, display px.

    The pattern runs along each run of the path from ``offset`` into it and
    starts over after a MOVETO (a NaN gap, a re-entry into the canvas), as
    the canvas strokes it. Every dash is widened by ``_DASH_SLACK_PX`` at
    both ends for a rasteriser's snapping; a pattern whose widened dashes
    close its gaps, or one too fine to cut up, counts as solid.
    """
    offset, lengths = dashes
    a, b = vertices[:-1][joined], vertices[1:][joined]
    period = float(lengths.sum())
    starts = np.concatenate([[0.0], np.cumsum(lengths)[:-1]])
    on_start = starts[0::2] - _DASH_SLACK_PX
    on_length = lengths[0::2] + 2 * _DASH_SLACK_PX
    if not len(a) or np.any(on_length >= period):
        return a, b
    # The distance along its run at which each segment starts.
    seg = np.hypot(*(b - a).T)
    index = np.flatnonzero(joined)
    new_run = np.concatenate([[True], index[1:] != index[:-1] + 1])
    before = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
    u0 = before - before[new_run][np.cumsum(new_run) - 1]
    keep = (seg > 0) & _near(a, b, frame, by)
    a, b, seg, u0 = a[keep], b[keep], seg[keep], u0[keep]
    # Where the pattern turns ink on or off: phase (u + offset) mod period.
    # Edge k falls in a segment at u = edge_k - offset + m * period for the
    # whole m from ``first`` to ``last``.
    edges = np.mod(np.concatenate([on_start, on_start + on_length]), period)
    first = np.ceil((u0[:, None] + offset - edges) / period)
    last = np.floor(((u0 + seg)[:, None] + offset - edges) / period)
    count = np.clip(last - first + 1, 0, None).astype(np.int64).ravel()
    if count.sum() > _MAX_DASH_CUTS:
        return a, b
    of_seg = np.repeat(np.repeat(np.arange(len(a)), len(edges)), count)
    of_edge = np.repeat(np.tile(np.arange(len(edges)), len(a)), count)
    step = np.arange(count.sum()) - np.repeat(np.cumsum(count) - count, count)
    m = np.repeat(first.ravel(), count) + step
    cut = edges[of_edge] - offset + m * period
    # Cut each segment at its pattern edges and keep the pieces in ink.
    at = np.concatenate(
        [np.zeros(len(a)), np.ones(len(a)), (cut - u0[of_seg]) / seg[of_seg]]
    )
    owner = np.concatenate([np.arange(len(a)), np.arange(len(a)), of_seg])
    order = np.lexsort((at, owner))
    at, owner = np.clip(at[order], 0.0, 1.0), owner[order]
    piece = (owner[1:] == owner[:-1]) & (at[1:] > at[:-1])
    t0, t1, i = at[:-1][piece], at[1:][piece], owner[:-1][piece]
    phase = np.mod(u0[i] + (t0 + t1) / 2 * seg[i] + offset, period)
    ink = np.zeros(len(i), dtype=bool)
    for start, length in zip(on_start, on_length, strict=True):
        ink |= np.mod(phase - start, period) <= length
    i, t0, t1 = i[ink], t0[ink, None], t1[ink, None]
    d = b[i] - a[i]
    return a[i] + t0 * d, a[i] + t1 * d


def _polyline(
    stroke: _Stroke, frame: Bbox, name: str, key: int
) -> _Polyline | None:
    vertices, joined = _joined(stroke.path)
    half = stroke.half
    if stroke.dashes is None:
        a, b = vertices[:-1][joined], vertices[1:][joined]
    else:
        a, b = _dashed(vertices, joined, stroke.dashes, frame, half)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    # Finite segments that reach the plot box; a MOVETO breaks the line.
    keep = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
    keep &= (lo[:, 0] <= frame.x1 + half) & (hi[:, 0] >= frame.x0 - half)
    keep &= (lo[:, 1] <= frame.y1 + half) & (hi[:, 1] >= frame.y0 - half)
    if not keep.any():
        return None
    order = np.argsort(lo[keep][:, 0], kind="stable")
    a, b, lo, hi = (v[keep][order] for v in (a, b, lo, hi))
    reach = float(np.max(hi[:, 0] - lo[:, 0]))
    return _Polyline(a, b, lo, hi, reach, half, name, key)


def _sorted_markers(
    xy: np.ndarray, r: np.ndarray, name: str, key: int
) -> _Markers:
    order = np.argsort(xy[:, 0], kind="stable")
    return _Markers(xy[order], r[order], float(np.max(r)), name, key)


def _window(xs: np.ndarray, reach: float, x0: float, x1: float) -> slice:
    """The run of ascending ``xs`` within ``[x0 - reach, x1 + reach]``."""
    start = int(np.searchsorted(xs, x0 - reach, side="left"))
    return slice(start, int(np.searchsorted(xs, x1 + reach, side="right")))


def _meets_frame(xy: np.ndarray, r: np.ndarray, frame: Bbox) -> np.ndarray:
    """Markers drawn into the plot box: a centre just outside reaches in."""
    x, y = xy[:, 0], xy[:, 1]
    ok = np.isfinite(x) & np.isfinite(y)
    ok &= (frame.x0 <= x + r) & (x - r <= frame.x1)
    ok &= (frame.y0 <= y + r) & (y - r <= frame.y1)
    return np.asarray(ok, dtype=np.bool_)


def _line(
    line: Line2D, frame: Bbox, fig: Figure, recorder: _Recorder
) -> tuple[list[_Polyline], _Markers | None]:
    """A data line's drawn strokes and markers in the plot box."""
    strokes, xy = (
        _as_set(line, fig) if line.get_path_effects() else recorder.take(line)
    )
    name, key = _name(line), id(line)
    drawn = [_polyline(stroke, frame, name, key) for stroke in strokes]
    lines = [polyline for polyline in drawn if polyline is not None]
    r = np.full(
        len(xy),
        _px(line.get_markersize() / 2 + line.get_markeredgewidth() / 2, fig),
    )
    seen = _meets_frame(xy, r, frame)
    if not seen.any():
        return lines, None
    return lines, _sorted_markers(xy[seen], r[seen], name, key)


def _scatter(
    coll: PathCollection, frame: Bbox, fig: Figure, key: int
) -> _Markers | None:
    # A masked x or y (``scatter`` masks both where x, y, s or c is masked)
    # is not drawn: NaN keeps it out of the plot box below.
    offsets = np.ma.filled(
        np.ma.asarray(coll.get_offsets(), dtype=np.float64), np.nan
    ).reshape(-1, 2)
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
    keep = _meets_frame(xy, radius, frame)
    keep &= (face > 0) | ((edge > 0) & (width > 0))
    keep &= radius > 0
    if not keep.any():
        return None
    return _sorted_markers(xy[keep], radius[keep], _name(coll), key)


def _measure(
    owners: list[Axes], frame: Bbox, renderer: RendererBase, fig: Figure
) -> _Data:
    lines: list[_Polyline] = []
    markers: list[_Markers] = []
    recorder = _Recorder(renderer)
    for owner in owners:
        for line in owner.get_lines():
            if not line.get_visible() or not _is_data_line(line, owner):
                continue
            try:
                drawn, marks = _line(line, frame, fig, recorder)
            except BBOX_ERRORS:
                continue
            lines.extend(drawn)
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


def _clip_region(text: Text) -> Bbox:
    """Where the label's clip lets its glyphs be drawn, in display px.

    ``Text.draw`` clips to its clip box and clip path when ``clip_on`` (an
    ``ax.text`` is unclipped unless asked). A clip path counts by its
    bounding box, which keeps the ink a curved clip cuts away: that can only
    add hits.
    """
    region = _UNCLIPPED
    if not text.get_clip_on():
        return region
    clip_box = text.get_clip_box()
    if clip_box is not None:
        region = _clip(region, clip_box) or _NOWHERE
    clip_path = text.get_clip_path()  # set_clip_path stores it transformed
    if isinstance(clip_path, TransformedPath):
        extent = clip_path.get_fully_transformed_path().get_extents()
        region = _clip(region, extent) or _NOWHERE
    return region


class _Label(NamedTuple):
    text: Text
    box: Bbox  # its text box, display px
    region: Bbox  # what its clip lets through


def _value_labels(ax: Axes, renderer: RendererBase) -> list[_Label]:
    """The value labels drawn in ``ax``; one clipped away is not drawn."""
    contour = _contour_labels(ax)
    found: list[_Label] = []
    for text in ax.texts:
        if not _is_value_label(text, contour):
            continue
        try:
            box = _text_box(text, renderer)
            region = _clip_region(text)
        except BBOX_ERRORS:
            continue
        if box is not None and _clip(box, region) is not None:
            found.append(_Label(text, box, region))
    return found


def _label_hits(
    label: _Label,
    data: _Data,
    frame: Bbox,
    renderer: RendererBase,
    touch: float,
) -> list[_Hit]:
    """What the label's ink covers, where its clip lets it be drawn.

    A bigger ink box covers no less (it meets more, and is less often a
    label on its own bar or inside its bubble), so the measuring stops as
    soon as the answer is settled: a text box that meets nothing has ink
    that meets nothing, and when the glyphs down to every tail meet what
    they meet standing on the baseline, the depth without the marks
    between the two is not measured.
    """
    box, text, region = label.box, label.text, label.region
    centre = ((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
    seen = _clip(box, region)
    if seen is None:
        return []
    whole = _inset(seen.x0, seen.y0, seen.x1, seen.y1, touch)
    if not _hits(data, frame, whole, centre, touch):
        return []

    def covered(depth: float) -> list[_Hit]:
        ink = _ink_box(text, box, glyphs, depth, touch, region)
        return [] if ink is None else _hits(data, frame, ink, centre, touch)

    try:
        glyphs = _glyphs(text, renderer)
        if glyphs is None:
            return covered(0.0)
        deepest = covered(glyphs.tails)
        if not deepest or glyphs.core is None or glyphs.tails <= 0:
            return deepest
        if covered(0.0) == deepest:
            return deepest
        return covered(glyphs.depth(text, renderer))
    except BBOX_ERRORS:
        return []


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
        for label in labels:
            hits = _label_hits(label, data, frame, renderer, touch)
            if hits:
                covering.append((label.text, hits))
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
