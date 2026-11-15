"""Read the layout's facts from a drawn figure. Nothing here changes it."""

from __future__ import annotations

import contextlib
import math
from itertools import pairwise
from typing import TYPE_CHECKING, Any, assert_never

import matplotlib as mpl
from matplotlib.axis import Axis
from matplotlib.gridspec import (
    GridSpec,
    GridSpecBase,
    GridSpecFromSubplotSpec,
    SubplotSpec,
)
from matplotlib.text import Text

from ..edgecase import settle
from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    drawn_tick_labels,
    iter_figure_level_extents,
    same_position_axes,
)
from ..labels import note_gap_pt
from ..legend import figure_reserve, outside_side
from . import decide
from .edges import FIT_EDGES
from .model import (
    CLEARANCE_EM,
    ArtistId,
    AxesContent,
    AxisName,
    Bottom,
    Box,
    Canvas,
    ContentFacts,
    Count,
    Edge,
    Edges,
    FigureArtist,
    Gap,
    HSpace,
    Left,
    Line,
    Piece,
    PlotSize,
    Px,
    Reach,
    Share,
    Sides,
    Spacing,
    TextFacts,
    TickGroup,
    TickRow,
    Top,
    Width,
    WSpace,
    XAxis,
    YAxis,
    authored,
    centred,
    edge_of,
    parse_projection,
)

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.transforms import Bbox

    from ..legend import Side
    from .apply import Record


def _edge(side: Side) -> Edge:
    """The plot or canvas edge a legend side names."""
    return edge_of(across=side.across, far=side.far)


def root_grid(
    fig: Figure, gs: GridSpecBase | SubplotSpec | None
) -> GridSpec | None:
    """The root GridSpec under ``gs`` (default: the first Axes')."""
    if gs is None and not fig.axes:
        return None
    found: GridSpecBase | SubplotSpec | None
    if gs is not None:
        found = gs.get_gridspec() if isinstance(gs, SubplotSpec) else gs
    else:
        found = fig.axes[0].get_gridspec()
    if isinstance(found, GridSpecFromSubplotSpec):
        found = found.get_topmost_subplotspec().get_gridspec()
    return found if isinstance(found, GridSpec) else None


def grid_of(ax: Axes) -> GridSpec | None:
    """The root GridSpec ``ax`` sits on, if any."""
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    gs = spec.get_topmost_subplotspec().get_gridspec()
    return gs if isinstance(gs, GridSpec) else None


def grid_axes(fig: Figure, gs: GridSpec) -> list[Axes]:
    """Every Axes of ``fig`` on the root GridSpec ``gs``."""
    return [ax for ax in fig.axes if grid_of(ax) is gs]


def _cartesian(ax: Axes) -> bool:
    """A visible rectilinear Axes with its axes on: the only kind fitted."""
    return ax.get_visible() and ax.axison and parse_projection(ax.name).flat


# -- one step -----------------------------------------------------------------


def _box(ext: Bbox) -> Box:
    return Box(float(ext.x0), float(ext.x1), float(ext.y0), float(ext.y1))


def _measurable(ext: Bbox) -> bool:
    """A finite, non-empty extent (text at infinity has a NaN width)."""
    finite = all(math.isfinite(v) for v in ext.extents)
    return finite and ext.width > 0 and ext.height > 0


def _across(owner: Axes, value: float, box: Bbox, along_x: bool) -> bool:
    """Whether a tick sits across ``box`` (0.5 px slack): a reciprocal
    secondary axis puts ticks in view but far off the canvas."""
    if along_x:
        place = owner.get_xaxis_transform().transform([(value, 0.0)])[0][0]
        return bool(box.x0 - 0.5 <= place <= box.x1 + 0.5)
    place = owner.get_yaxis_transform().transform([(0.0, value)])[0][1]
    return bool(box.y0 - 0.5 <= place <= box.y1 + 0.5)


def _texts(owner: Axes, renderer: RendererBase) -> list[Piece]:
    """Texts, the three titles and both axis names."""
    pieces: list[Piece] = []
    labels = (owner.xaxis.label, owner.yaxis.label)
    for text in (*owner.texts, *axes_titles(owner).values(), *labels):
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if _measurable(ext):
            pieces.append(Piece(_box(ext)))
    return pieces


def _ticks(owner: Axes, renderer: RendererBase) -> list[Piece]:
    """Labels of ticks in view and across the plot; offset texts."""
    pieces: list[Piece] = []
    for axis in (owner.xaxis, owner.yaxis):
        vmin, vmax = sorted(axis.get_view_interval())
        tol = abs(vmax - vmin) * 1e-5
        along_x = axis is owner.xaxis
        try:
            box = owner.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        for tick in axis.get_ticklabels():
            if not tick.get_visible() or not tick.get_text().strip():
                continue
            try:
                ext = tick.get_window_extent(renderer)
                pos = tick.get_position()
            except BBOX_ERRORS:
                continue
            value = pos[0] if along_x else pos[1]
            if value < vmin - tol or value > vmax + tol:
                continue
            if _measurable(ext) and _across(owner, value, box, along_x):
                pieces.append(Piece(_box(ext)))
        offset = axis.get_offset_text()
        if offset.get_visible() and offset.get_text().strip():
            with contextlib.suppress(*BBOX_ERRORS):
                ext = offset.get_window_extent(renderer)
                if _measurable(ext):
                    pieces.append(Piece(_box(ext)))
    return pieces


def _tight_3d(ax: Axes, renderer: RendererBase) -> tuple[Piece, ...]:
    """A 3-D Axes' axes, legend, titles and 2-D texts by their tight boxes
    (a ``Text3D`` has none, as matplotlib's own layouts find)."""
    pieces: list[Piece] = []
    # Its x, y and z axes: a 3-D Axes lists the z axis among its children.
    axes = {id(c): c for c in ax.get_children() if isinstance(c, Axis)}
    for artist in (*axes.values(), ax.get_legend()):
        if artist is None or not artist.get_visible():
            continue
        with contextlib.suppress(*BBOX_ERRORS):
            bb = artist.get_tightbbox(renderer)
            if bb is not None and bb.width > 0 and bb.height > 0:
                pieces.append(Piece(_box(bb)))
    for text in (*axes_titles(ax).values(), *ax.texts):
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_tightbbox(renderer)
        except BBOX_ERRORS:
            continue
        if ext is not None and ext.width > 0 and ext.height > 0:
            pieces.append(Piece(_box(ext)))
    return tuple(pieces)


def axes_content(ax: Axes, renderer: RendererBase) -> AxesContent | None:
    """What of ``ax`` must stay on the canvas; ``None`` for a hidden Axes."""
    if not ax.get_visible():
        return None
    p = ax.get_position()
    position = Sides(float(p.x0), float(p.x1), float(p.y0), float(p.y1))
    try:
        window = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        window = None
    plot = None
    if window is not None and window.width > 0 and window.height > 0:
        plot = _box(window)
    if parse_projection(ax.name).cube:
        if window is None:
            return None
        return AxesContent(plot, position, (), _tight_3d(ax, renderer))
    pieces = [*_texts(ax, renderer), *_ticks(ax, renderer)]
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        with contextlib.suppress(*BBOX_ERRORS):
            ext = legend.get_window_extent(renderer)
            if ext.width > 0 and ext.height > 0:
                side = outside_side(legend)
                outside = None if side is None else _edge(side)
                pieces.append(Piece(_box(ext), outside))
    return AxesContent(plot, position, tuple(pieces))


def _roles(fig: Figure) -> dict[int, Edge]:
    """The edge each of ``fig``'s suptitle, supxlabel and supylabel holds,
    by ``id`` of the text in ``fig.texts`` that writes it.

    matplotlib names these texts only by what they write
    (``get_suptitle`` and so on); the first text writing it is taken.
    """
    roles: dict[int, Edge] = {}
    for written, edge in (
        (fig.get_suptitle(), Top()),
        (fig.get_supxlabel(), Bottom()),
        (fig.get_supylabel(), Left()),
    ):
        found = next((t for t in fig.texts if t.get_text() == written), None)
        if written and found is not None:
            roles.setdefault(id(found), edge)
    return roles


def _figure_artist(
    fig: Figure, roles: dict[int, Edge], art: Artist, ext: Bbox
) -> FigureArtist:
    vertical = (
        45 <= art.get_rotation() % 180 <= 135 if isinstance(art, Text) else None
    )
    reserve = figure_reserve(art)
    if reserve is not None:
        side, gap_pt = _edge(reserve.side), reserve.gap_pt
    else:
        side, gap_pt = None, note_gap_pt(art) or 0.0
    return FigureArtist(
        _box(ext),
        roles.get(id(art)),
        vertical,
        side,
        Px(gap_pt * fig.dpi / 72.0),
    )


def canvas(fig: Figure) -> Canvas:
    """The canvas size in display pixels."""
    return Canvas(Px(float(fig.bbox.width)), Px(float(fig.bbox.height)))


def content_facts(
    fig: Figure, renderer: RendererBase, margins: Sides, last: Edges | None
) -> ContentFacts:
    """Every Axes' content and the figure-level artists, as drawn now."""
    contents = [axes_content(ax, renderer) for ax in fig.axes]
    roles = _roles(fig)
    artists = tuple(
        _figure_artist(fig, roles, art, ext)
        for art, ext in iter_figure_level_extents(
            fig, renderer, subfigures=False
        )
        if art.get_in_layout()
    )
    axes = tuple(c for c in contents if c is not None)
    return ContentFacts(axes, artists, canvas(fig), margins, last)


def content_boxes(fig: Figure, renderer: RendererBase) -> dict[int, Box]:
    """Each visible Axes' content as the margins see it (``id(ax)`` keys)."""
    boxes: dict[int, Box] = {}
    for ax in fig.axes:
        content = axes_content(ax, renderer)
        if content is None:
            continue
        nil = Sides(0.0, 0.0, 0.0, 0.0)
        facts = ContentFacts((content,), (), canvas(fig), nil, None)
        fit = settle(facts, decide.fit(facts), FIT_EDGES).plan
        box = decide.content_box(fit.axes[0])
        if box is not None:
            boxes[id(ax)] = box
    return boxes


def plot_sizes(fig: Figure, renderer: RendererBase) -> dict[ArtistId, PlotSize]:
    """Each visible Axes' plot box size."""
    sizes: dict[ArtistId, PlotSize] = {}
    for ax in fig.axes:
        if ax.get_visible():
            box = ax.get_window_extent(renderer)
            size = PlotSize(Px(float(box.width)), Px(float(box.height)))
            sizes[ArtistId(id(ax))] = size
    return sizes


# -- text ---------------------------------------------------------------------


def _width_of(renderer: RendererBase, prop: FontProperties) -> Width:
    def width(line: Line) -> Px:
        w, _h, _d = renderer.get_text_width_height_descent(line, prop, False)
        return Px(float(w))

    return width


def _row(
    ax: Axes, renderer: RendererBase, unwrap: dict[str, str], record: Record
) -> TickRow | None:
    """The bottom tick labels of ``ax`` drawn now, as they read unwrapped."""
    axis = ax.xaxis
    bottom = {id(t.label1) for t in axis.get_major_ticks()}
    labels = [
        t
        for t in drawn_tick_labels(ax, "x")
        if id(t) in bottom and t.get_text().strip()
    ]
    if len(labels) < 2:
        return None
    texts = [unwrap.get(t.get_text(), t.get_text()) for t in labels]
    centres = [
        float(t.get_transform().transform(t.get_position())[0]) for t in labels
    ]
    order = sorted(range(len(labels)), key=centres.__getitem__)
    gaps = [Px(centres[b] - centres[a]) for a, b in pairwise(order)]
    if min(gaps) <= 0:
        return None
    turn = record.axis_turns.get(axis)
    authored_ = any(authored(t) for t in texts) or (
        turn is None
        and (
            {float(t.get_rotation()) for t in labels} != {0.0}
            or not all(centred(t.get_horizontalalignment()) for t in labels)
        )
    )
    font = labels[0].get_fontproperties()
    width = _width_of(renderer, font)
    _w, height, _d = renderer.get_text_width_height_descent("Ag", font, False)
    em = float(labels[0].get_fontsize()) * ax.figure.dpi / 72.0
    ordered = tuple(Line(texts[i]) for i in order)
    return TickRow(
        axis=ArtistId(id(axis)),
        texts=ordered,
        widths=tuple(
            max(width(Line(part)) for part in t.split("\n")) for t in ordered
        ),
        gaps=tuple(gaps),
        clearance=Px(CLEARANCE_EM * em),
        line_height=Px(float(height)),
        authored=authored_,
        turned=None if turn is None else turn.angle,
        width=width,
    )


def _groups(
    fig: Figure, renderer: RendererBase, record: Record, objects: dict[int, Any]
) -> list[TickGroup]:
    """The fitted Axes by shared x axis (one formatter, so one wrap)."""
    from .apply import WrappedTickFormatter

    fitted = [ax for ax in fig.axes if _cartesian(ax)]
    seen: set[int] = set()
    groups: list[TickGroup] = []
    for ax in fitted:
        if id(ax) in seen:
            continue
        siblings = {id(a) for a in ax.get_shared_x_axes().get_siblings(ax)}  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportUnknownArgumentType]
        members = [a for a in fitted if id(a) in siblings]
        seen.update(id(a) for a in members)
        axis = members[0].xaxis
        fmt = axis.get_major_formatter()
        lines = fmt.lines if isinstance(fmt, WrappedTickFormatter) else {}
        unwrap = {v: k for k, v in lines.items()}
        rows: list[TickRow] = []
        for member in members:
            objects[id(member.xaxis)] = member.xaxis
            if (row := _row(member, renderer, unwrap, record)) is not None:
                rows.append(row)
        wrapped = {Line(k): Line(v) for k, v in lines.items()}
        groups.append(TickGroup(ArtistId(id(axis)), tuple(rows), wrapped))
    return groups


def _names(
    fig: Figure, renderer: RendererBase, record: Record, objects: dict[int, Any]
) -> list[AxisName]:
    """One-line names without mathtext that this layout has not wrapped."""
    boxes: dict[int, Box] | None = None
    names: list[AxisName] = []
    for ax in fig.axes:
        gs = grid_of(ax)
        if gs is None or not _cartesian(ax):
            continue
        frame = ax.get_window_extent(renderer)
        for which, axis, span in (
            (XAxis(), ax.xaxis, frame.width),
            (YAxis(), ax.yaxis, frame.height),
        ):
            label, text = axis.label, axis.label.get_text()
            if (
                span <= 0
                or not axis.get_visible()
                or not label.get_visible()
                or not text.strip()
                or authored(text)
                or label in record.names
            ):
                continue
            boxes = content_boxes(fig, renderer) if boxes is None else boxes
            here = {id(a) for a in same_position_axes(ax)} | {id(ax)}
            objects[id(label)] = label
            name = AxisName(
                label=ArtistId(id(label)),
                text=Line(text),
                span=Px(float(span)),
                box=_box(label.get_window_extent(renderer)),
                group=(ArtistId(id(gs)), which),
                others=tuple(b for k, b in boxes.items() if k not in here),
                width=_width_of(renderer, label.get_fontproperties()),
            )
            names.append(name)
    return names


def spacing_of(gs: GridSpec, key: Gap) -> float | None:
    """The ``wspace`` / ``hspace`` set on ``gs`` (``None``: the figure's)."""
    match key:
        case WSpace():
            return gs.wspace
        case HSpace():
            return gs.hspace
        case _:
            assert_never(key)


def _figure_default(fig: Figure, key: Gap) -> bool:
    """The figure's own spacing is still matplotlib's default."""
    match key:
        case WSpace():
            now, rc = (
                fig.subplotpars.wspace,
                mpl.rcParams["figure.subplot.wspace"],
            )
        case HSpace():
            now, rc = (
                fig.subplotpars.hspace,
                mpl.rcParams["figure.subplot.hspace"],
            )
        case _:
            assert_never(key)
    return bool(now == rc)


def _free(fig: Figure, gs: GridSpec, key: Gap, record: Record) -> bool:
    """Nobody but this layout set the spacing (``gridspec_kw``,
    ``add_gridspec`` and ``fig.subplots_adjust`` do)."""
    value = spacing_of(gs, key)
    if value is not None:
        return record.gaps_of(gs).get(key) == value
    return _figure_default(fig, key)


def _spacings(
    fig: Figure, gs: GridSpec, renderer: RendererBase, record: Record
) -> list[Spacing]:
    nrows, ncols = gs.get_geometry()
    free = [
        key
        for key, n in ((WSpace(), ncols), (HSpace(), nrows))
        if n > 1 and _free(fig, gs, key, record)
    ]
    if not free:
        return []
    bottoms, tops, lefts, rights = gs.get_grid_positions(fig)
    fw, fh = fig.bbox.width, fig.bbox.height
    boxes = content_boxes(fig, renderer)
    cols: list[Reach] = []
    rows: list[Reach] = []
    for ax in grid_axes(fig, gs):
        box, spec = boxes.get(id(ax)), ax.get_subplotspec()
        if box is None or spec is None:
            continue
        top = spec.get_topmost_subplotspec()
        r = (top.rowspan.start, top.rowspan.stop)
        c = (top.colspan.start, top.colspan.stop)
        back, ahead = lefts[c[0]] * fw - box.x0, box.x1 - rights[c[1] - 1] * fw
        cols.append(Reach(c, r, Px(back), Px(ahead)))
        back, ahead = box.y1 - tops[r[0]] * fh, bottoms[r[1] - 1] * fh - box.y0
        rows.append(Reach(r, c, Px(back), Px(ahead)))
    params = gs.get_subplot_params(fig)
    em = Px(float(mpl.rcParams["font.size"]) * fig.dpi / 72.0)
    out: list[Spacing] = []
    for key in free:
        match key:
            case WSpace():
                gaps = [
                    (lefts[i + 1] - rights[i]) * fw for i in range(ncols - 1)
                ]
                reaches, total, cells = (
                    cols,
                    (rights[-1] - lefts[0]) * fw,
                    ncols,
                )
                now = Share(float(params.wspace))
            case HSpace():
                gaps = [
                    (bottoms[i] - tops[i + 1]) * fh for i in range(nrows - 1)
                ]
                reaches, total, cells = (
                    rows,
                    (tops[0] - bottoms[-1]) * fh,
                    nrows,
                )
                now = Share(float(params.hspace))
            case _:
                assert_never(key)
        gaps_px = tuple(Px(float(g)) for g in gaps)
        out.append(
            Spacing(
                key, tuple(reaches), gaps_px, Px(total), Count(cells), now, em
            )
        )
    return out


def text_facts(
    fig: Figure, gs: GridSpec, renderer: RendererBase, record: Record
) -> tuple[TextFacts, dict[int, Any]]:
    """What text fitting reads, and the artists its ids name."""
    objects: dict[int, Any] = {}
    groups = _groups(fig, renderer, record, objects)
    names = _names(fig, renderer, record, objects)
    wrapped = {
        (n.group, Line(n.before)): Line(n.after)
        for label, n in record.names.items()
        if label.get_text() == n.after
    }
    spacings = _spacings(fig, gs, renderer, record)
    facts = TextFacts(
        tuple(groups), tuple(names), wrapped, tuple(spacings), canvas(fig)
    )
    return facts, objects
