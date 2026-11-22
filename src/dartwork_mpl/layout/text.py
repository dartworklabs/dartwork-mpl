"""Read what text fitting needs from a drawn figure. Nothing here changes it.

Crowded bottom tick rows, axis names longer than their plot, and the grid
spacing between panels nobody spaced, with the artists their ids name.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, assert_never

import matplotlib as mpl
from matplotlib.axis import Axis
from matplotlib.gridspec import GridSpec
from matplotlib.text import Text

from ..geometry import drawn_tick_labels, same_position_axes
from ..vocab import X, Y
from .apply import WrappedTickFormatter
from .measure import (
    box_of,
    canvas,
    cartesian,
    content_boxes,
    grid_axes,
    grid_of,
)
from .model import (
    CLEARANCE_EM,
    ArtistId,
    AxisName,
    Count,
    Gap,
    HSpace,
    Line,
    Px,
    Reach,
    Share,
    Spacing,
    TextFacts,
    TickGroup,
    TickRow,
    Width,
    WSpace,
    authored,
    centred,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties


def _width_of(renderer: RendererBase, prop: FontProperties) -> Width:
    def width(line: Line) -> Px:
        w, _h, _d = renderer.get_text_width_height_descent(line, prop, False)
        return Px(float(w))

    return width


def _row(
    ax: Axes, renderer: RendererBase, unwrap: dict[str, str]
) -> TickRow | None:
    """The bottom tick labels of ``ax`` drawn now, as they read unwrapped."""
    axis = ax.xaxis
    bottom = {id(t.label1) for t in axis.get_major_ticks()}
    labels = [
        t
        for t in drawn_tick_labels(ax, X())
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
    authored_ = (
        any(authored(t) for t in texts)
        or {float(t.get_rotation()) for t in labels} != {0.0}
        or not all(centred(t.get_horizontalalignment()) for t in labels)
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
        width=width,
    )


@dataclass(frozen=True)
class TextArtists:
    """The artists the ids in text facts name: tick axes, axis labels."""

    axes: dict[int, Axis]
    labels: dict[int, Text]


def _groups(
    fig: Figure, renderer: RendererBase, objects: TextArtists
) -> list[TickGroup]:
    """The fitted Axes by shared x axis (one formatter, so one wrap)."""
    fitted = [ax for ax in fig.axes if cartesian(ax)]
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
            objects.axes[id(member.xaxis)] = member.xaxis
            if (row := _row(member, renderer, unwrap)) is not None:
                rows.append(row)
        wrapped = {Line(k): Line(v) for k, v in lines.items()}
        groups.append(TickGroup(ArtistId(id(axis)), tuple(rows), wrapped))
    return groups


def _names(
    fig: Figure, renderer: RendererBase, objects: TextArtists
) -> list[AxisName]:
    """Visible one-line names without mathtext."""
    names: list[AxisName] = []
    boxes = content_boxes(fig, renderer)
    for ax in fig.axes:
        gs = grid_of(ax)
        if gs is None or not cartesian(ax):
            continue
        frame = ax.get_window_extent(renderer)
        for which, axis, span in (
            (X(), ax.xaxis, frame.width),
            (Y(), ax.yaxis, frame.height),
        ):
            label, text = axis.label, axis.label.get_text()
            if (
                span <= 0
                or not axis.get_visible()
                or not label.get_visible()
                or not text.strip()
                or authored(text)
            ):
                continue
            objects.labels[id(label)] = label
            here = {id(a) for a in same_position_axes(ax)} | {id(ax)}
            name = AxisName(
                label=ArtistId(id(label)),
                text=Line(text),
                span=Px(float(span)),
                group=(ArtistId(id(gs)), which),
                width=_width_of(renderer, label.get_fontproperties()),
                box=box_of(label.get_window_extent(renderer)),
                others=tuple(b for k, b in boxes.items() if k not in here),
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


def _free(fig: Figure, gs: GridSpec, key: Gap) -> bool:
    """Nobody set the spacing (``gridspec_kw``, ``add_gridspec`` and
    ``fig.subplots_adjust`` do; so does an earlier layout)."""
    return spacing_of(gs, key) is None and _figure_default(fig, key)


def spacings(
    fig: Figure, gs: GridSpec, renderer: RendererBase, keys: Collection[Gap]
) -> list[Spacing]:
    """The spacings ``keys`` of ``gs`` as drawn now, set or not."""
    nrows, ncols = gs.get_geometry()
    free = [
        key
        for key, n in ((WSpace(), ncols), (HSpace(), nrows))
        if n > 1 and key in keys
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
    fig: Figure, gs: GridSpec, renderer: RendererBase, held: Collection[Gap]
) -> tuple[TextFacts, TextArtists]:
    """What text fitting reads, and the artists its ids name; the spacings
    nobody set, but for those ``held`` where they are."""
    objects = TextArtists({}, {})
    free = [
        key
        for key in (WSpace(), HSpace())
        if key not in held and _free(fig, gs, key)
    ]
    facts = TextFacts(
        tuple(_groups(fig, renderer, objects)),
        tuple(_names(fig, renderer, objects)),
        tuple(spacings(fig, gs, renderer, free)),
        canvas(fig),
    )
    return facts, objects
