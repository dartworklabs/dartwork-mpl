"""Outside legends for ``place_legend``: one plan per side, the side that costs the plot least, and wrapped names.

A plan is measured before anything is drawn: trial legends
(:func:`~._legend_fit.probe`) give the size each column count would take,
so choosing a side, a column count or a wrapping costs no canvas draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    anchor_outside,
    outside_side,
    outside_span_px,
)
from ._legend_fit import (
    ceil_div,
    free_sides,
    handle_overhead,
    legend_em,
    legend_pad,
    legend_size,
    points_px,
    probe,
    text_width,
    wrap_label,
)
from ._legend_look import remember_look

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.legend import Legend
    from matplotlib.transforms import Bbox
    from matplotlib.typing import LegendLocType

# The legend's own anchor point (matplotlib ``loc``) for each outside side:
# the legend edge that faces the Axes touches the anchor.
OUTSIDE_LEGEND_LOCS: dict[OutsideSide, LegendLocType] = {
    "above": "lower center",
    "below": "upper center",
    "right": "center left",
    "left": "center right",
}

#: A plan that fits and takes at most this share of the plot is a good fit.
GOOD_FIT_LOSS = 0.6

#: A later plan of the same fit replaces an earlier one only when it takes
#: this much less of the plot, relatively and in absolute share: a small gain
#: does not move the legend off its usual side or break its names.
RELATIVE_GAIN = 0.9
ABSOLUTE_GAIN = 0.05

#: Between plans of the same fit, the one whose names take more lines wins
#: only when it also leaves the plot at least this share of the canvas more:
#: a name broken into more lines is harder to read than a slightly shorter
#: plot (2026-11-08 review of capture 10).
LINES_GAIN = 0.05

#: A legend on a side the caller named right or left wraps its names when it
#: is wider than this share of the Axes.
WIDE_SHARE = 0.4

#: Right and left, wrapped names are tried at these shares of the canvas
#: width (from the canvas, not the Axes: the Axes narrows by the legend's own
#: width when the layout makes room, which would move the limit).
SIDE_WRAP_SHARES = (0.35, 0.25)

#: A wrap limit narrower than this many font sizes is not tried.
MIN_WRAP_EM = 4.0


def split_ncols(kw: dict[str, Any]) -> tuple[dict[str, Any], int | None]:
    """``kw`` without ``ncol`` / ``ncols``, and the column count they asked for."""
    legend_kw = dict(kw)
    explicit = legend_kw.pop("ncols", None)
    explicit = legend_kw.pop("ncol", explicit)
    return legend_kw, int(explicit) if explicit is not None else None


@dataclass(frozen=True)
class OutsidePlan:
    """One way to draw a legend outside a side, measured before drawing.

    ``loss`` is the share of the Axes the legend takes on that side (its
    height above or below, its width right or left, each with the gap);
    ``fits`` says it fits across the side (:func:`plan_side`): on the
    canvas and off the neighbouring panels; ``canvas_share`` is the plot area it takes (that height times the Axes
    width, or that width times the Axes height) as a share of the canvas.
    """

    side: OutsideSide
    ncols: int
    labels: tuple[str, ...]
    width: float
    height: float
    loss: float
    fits: bool
    canvas_share: float = 0.0

    @property
    def level(self) -> int:
        """2: fits and leaves 40 % of the plot; 1: fits; 0: does not fit."""
        if not self.fits or self.loss >= 1.0:
            return 0
        return 2 if self.loss <= GOOD_FIT_LOSS else 1

    @property
    def lines(self) -> int:
        """The most lines one entry name takes."""
        return max((label.count("\n") + 1 for label in self.labels), default=1)


#: Trial-legend measurements of one legend's entries and keywords, kept
#: across plans: a legend's size does not depend on the Axes, so the layout
#: plans again at a new size without building the same trials again.
#: Keys hold the renderer's px per pt, so another dpi measures afresh.
Sizes: TypeAlias = dict[tuple[Any, ...], Any]


@dataclass(frozen=True)
class OutsideSource:
    """What an outside legend was planned from, for ``settle_legends``.

    ``size`` is the Axes' width and height in px when it was planned and
    ``span`` the length the legend could take along its side then
    (:func:`span_length`); ``sizes`` the trial measurements made so far
    (:data:`Sizes`).
    """

    handles: list[Any]
    labels: list[str]
    kw: dict[str, Any]
    plan: OutsidePlan
    size: tuple[float, float]
    sizes: Sizes = field(default_factory=dict)
    span: float | None = None


def span_length(
    ax: Axes, side: OutsideSide, legend: Legend, renderer: RendererBase
) -> float:
    """How long ``legend`` may be along ``side`` of ``ax`` now, px.

    :func:`~dartwork_mpl._figure_geometry.outside_span_px` with the
    legend's pad as the margin: it changes when the canvas or a
    neighbouring panel does, not only when ``ax`` is resized.
    """
    low, high = outside_span_px(
        ax, side, renderer, legend_pad(legend, renderer)
    )
    return float(high - low)


def _scale(renderer: RendererBase) -> float:
    return points_px(renderer, 1.0)


def _trial_size(
    ax: Axes,
    handles: list[Any],
    labels: tuple[str, ...],
    ncols: int,
    legend_kw: dict[str, Any],
    renderer: RendererBase,
    sizes: Sizes,
) -> tuple[float, float]:
    """Width and height of the legend with ``ncols`` columns, measured once.

    An ``mode="expand"`` legend takes the width of its anchor box, which
    the layout moves, so it is measured every time.
    """
    key = ("size", ncols, labels, _scale(renderer))
    if key not in sizes or legend_kw.get("mode") == "expand":
        trial = probe(ax, handles, labels, ncols=ncols, **legend_kw)
        try:
            sizes[key] = legend_size(trial, renderer)
        except BBOX_ERRORS:
            sizes[key] = (float("inf"), float("inf"))
    found: tuple[float, float] = sizes[key]
    return found


def _plain_trial(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    legend_kw: dict[str, Any],
    renderer: RendererBase,
    sizes: Sizes,
) -> Legend:
    """The legend as asked, built once: its font, pad and handle metrics."""
    key = ("trial", _scale(renderer))
    if key not in sizes:
        sizes[key] = probe(ax, handles, labels, **legend_kw)
    trial: Legend = sizes[key]
    return trial


def trial_pad(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    legend_kw: dict[str, Any],
    renderer: RendererBase,
    sizes: Sizes,
) -> float:
    """The legend's ``borderaxespad`` in px (the gap a plan counts)."""
    return legend_pad(
        _plain_trial(ax, handles, labels, legend_kw, renderer, sizes), renderer
    )


def _column_steps(
    count: int, along_width: bool, explicit: int | None
) -> list[int]:
    """Column counts to try, fewest rows first above and below, fewest columns right and left."""
    if explicit is not None:
        return [explicit]
    if along_width:
        return list(
            dict.fromkeys(ceil_div(count, r) for r in range(1, count + 1))
        )
    return list(range(1, count + 1))


def plan_side(
    ax: Axes,
    handles: list[Any],
    labels: list[str] | tuple[str, ...],
    side: OutsideSide,
    legend_kw: dict[str, Any],
    explicit: int | None,
    renderer: RendererBase,
    axes_box: Bbox,
    pad: float,
    sizes: Sizes | None = None,
    room: float | None = None,
) -> OutsidePlan:
    """Columns for ``labels`` on ``side`` and what that costs the plot.

    Above and below: the fewest rows whose legend fits across the side (one
    column when none does). Right and left: the fewest columns whose legend
    fits along it. A legend fits when it is no longer than
    :func:`~dartwork_mpl._figure_geometry.outside_span_px` with its pad as
    the margin: centred on the Axes and moved in where it would cross the
    canvas, it stays on the canvas and off the neighbouring panels' columns
    (rows, right and left), however much longer than the Axes it is.
    ``explicit`` columns win. ``legend_kw`` holds no ``ncol`` / ``ncols``;
    ``sizes`` keeps the trial sizes for the next plan of the same legend.

    ``room`` (above and below, once laid out) is the height the Axes and
    the legend now share: the layout gives the Axes what a shorter legend
    frees and takes what a taller one needs, so the loss is measured
    against the Axes height this plan would leave, ``room`` less the
    legend. Measured against the height now instead, a legend that wraps
    to fit a short plot would unwrap once the plot grew, and back.
    """
    if sizes is None:
        sizes = {}
    along_width = side in ("above", "below")
    steps = _column_steps(max(len(labels), 1), along_width, explicit)
    width = height = float("inf")
    ncols = steps[-1]
    fits = False
    low, high = outside_span_px(ax, side, renderer, pad)
    limit = high - low
    for ncols in steps:
        width, height = _trial_size(
            ax, handles, tuple(labels), ncols, legend_kw, renderer, sizes
        )
        fits = (width if along_width else height) <= limit + 0.5
        if fits:
            break
    if along_width:
        plot = axes_box.height if room is None else room - height
        loss = (height + pad) / max(plot, 1.0)
        taken = (height + pad) * axes_box.width
    else:
        loss = (width + pad) / max(axes_box.width, 1.0)
        taken = (width + pad) * axes_box.height
    canvas_w, canvas_h = renderer.get_canvas_width_height()
    canvas_share = taken / max(float(canvas_w) * float(canvas_h), 1.0)
    return OutsidePlan(
        side, ncols, tuple(labels), width, height, loss, fits, canvas_share
    )


def _wrapped_variants(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    legend_kw: dict[str, Any],
    explicit: int | None,
    renderer: RendererBase,
    sizes: Sizes,
) -> list[tuple[str, ...]]:
    """Label sets with long names broken at spaces, for ``side`` (distinct only).

    Above and below, each name is limited to the width of one of one to
    three columns across the span the legend may take
    (:func:`~dartwork_mpl._figure_geometry.outside_span_px`; the asked
    column count only, when one was asked); right and left, to
    :data:`SIDE_WRAP_SHARES` of the canvas.
    """
    if not labels:
        return []
    trial = _plain_trial(ax, handles, labels, legend_kw, renderer, sizes)
    overhead = handle_overhead(trial, renderer)
    em = legend_em(trial, renderer)
    spacing = float(trial.columnspacing) * em
    if side in ("above", "below"):
        low, high = outside_span_px(
            ax, side, renderer, legend_pad(trial, renderer)
        )
        width = high - low
        columns = [explicit] if explicit is not None else [1, 2, 3]
        caps = [(width - (k - 1) * spacing) / k - overhead for k in columns]
    else:
        canvas = float(renderer.get_canvas_width_height()[0])
        caps = [share * canvas - overhead for share in SIDE_WRAP_SHARES]
    scale = _scale(renderer)

    def measure(text: str) -> float:
        key = ("text", text, scale)
        if key not in sizes:
            sizes[key] = text_width(text, trial.prop, renderer)
        found: float = sizes[key]
        return found

    out: list[tuple[str, ...]] = []
    for cap in caps:
        if cap < MIN_WRAP_EM * em:
            continue
        wrapped = tuple(wrap_label(label, cap, measure) for label in labels)
        if wrapped != tuple(labels) and wrapped not in out:
            out.append(wrapped)
    return out


def _clearly_cheaper(plan: OutsidePlan, than: OutsidePlan) -> bool:
    """Under :data:`RELATIVE_GAIN` of ``than``'s loss and :data:`ABSOLUTE_GAIN` less."""
    return (
        plan.loss < than.loss * RELATIVE_GAIN
        and than.loss - plan.loss >= ABSOLUTE_GAIN
    )


def _wins_with_more_lines(plan: OutsidePlan, than: OutsidePlan) -> bool:
    """``plan`` breaks names into more lines than ``than``: clearly cheaper and
    :data:`LINES_GAIN` of the canvas less plot taken, or it loses."""
    return (
        _clearly_cheaper(plan, than)
        and than.canvas_share - plan.canvas_share >= LINES_GAIN
    )


def choose(plans: list[OutsidePlan]) -> OutsidePlan:
    """The best-fitting plan; among equals the first, unless one clearly costs less.

    Clearly: under :data:`RELATIVE_GAIN` of the earlier plan's loss and at
    least :data:`ABSOLUTE_GAIN` of the plot less. Between plans of the same
    fit whose names take a different number of lines, the one with more
    lines wins only when it is also clearly cheaper and leaves the plot at
    least :data:`LINES_GAIN` of the canvas more; otherwise the one with
    fewer lines does, wherever it is in the list. ``plans`` is not empty.
    """
    best = plans[0]
    for plan in plans[1:]:
        if plan.level != best.level:
            if plan.level > best.level:
                best = plan
        elif plan.lines > best.lines:
            if _wins_with_more_lines(plan, best):
                best = plan
        elif plan.lines < best.lines:
            if not _wins_with_more_lines(best, plan):
                best = plan
        elif _clearly_cheaper(plan, best):
            best = plan
    return best


def side_plans(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    kw: dict[str, Any],
    renderer: RendererBase,
    *,
    named: bool,
    sizes: Sizes | None = None,
    room: float | None = None,
) -> list[OutsidePlan]:
    """The plans for ``side``: names as given, then wrapped when allowed.

    Names wrap (``dm.config.legend_wrap``) only to make the legend fit:
    when it does not fit across the side (:func:`plan_side`) or takes more than
    :data:`GOOD_FIT_LOSS` of the plot, or, on a side the caller named
    right or left, is wider than :data:`WIDE_SHARE` of the Axes. A legend
    that fits keeps its names on one line. ``sizes`` keeps the trial
    measurements for the next plan of the same legend; ``room`` is
    :func:`plan_side`'s.
    """
    from ..config import config

    if sizes is None:
        sizes = {}
    legend_kw, explicit = split_ncols(kw)
    axes_box = ax.get_window_extent(renderer)
    pad = trial_pad(ax, handles, labels, legend_kw, renderer, sizes)
    plain = plan_side(
        ax,
        handles,
        labels,
        side,
        legend_kw,
        explicit,
        renderer,
        axes_box,
        pad,
        sizes,
        room,
    )
    plans = [plain]
    if not config.legend_wrap:
        return plans
    wide = (
        named
        and side in ("right", "left")
        and plain.width > WIDE_SHARE * axes_box.width
    )
    if plain.level == 2 and not wide:
        return plans
    plans.extend(
        plan_side(
            ax,
            handles,
            wrapped,
            side,
            legend_kw,
            explicit,
            renderer,
            axes_box,
            pad,
            sizes,
            room,
        )
        for wrapped in _wrapped_variants(
            ax, handles, labels, side, legend_kw, explicit, renderer, sizes
        )
    )
    return plans


def draw_outside(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    plan: OutsidePlan,
    kw: dict[str, Any],
    renderer: RendererBase,
    sizes: Sizes | None = None,
) -> Legend:
    """Draw the legend of ``ax`` as ``plan`` says, past the labels of its side.

    Records ``_dm_wrapped`` (a name was broken), ``_dm_outside_source``
    (what ``settle_legends`` plans again from, with the trial ``sizes``)
    and the legend's look (:func:`~._legend_look.remember_look`).
    """
    legend_kw, _explicit = split_ncols(kw)
    legend = ax.legend(
        handles,
        list(plan.labels),
        loc=OUTSIDE_LEGEND_LOCS[plan.side],
        ncols=plan.ncols,
        **legend_kw,
    )
    anchor_outside(legend, ax, plan.side, renderer)
    legend._dm_wrapped = plan.labels != tuple(labels)  # type: ignore[attr-defined]
    box = ax.get_window_extent(renderer)
    legend._dm_outside_source = OutsideSource(  # type: ignore[attr-defined]
        list(handles),
        list(labels),
        dict(kw),
        plan,
        (box.width, box.height),
        {} if sizes is None else sizes,
        span_length(ax, plan.side, legend, renderer),
    )
    remember_look(legend, renderer, str(OUTSIDE_LEGEND_LOCS[plan.side]), kw)
    return legend


def fallback_sides(ax: Axes) -> list[OutsideSide]:
    """Sides a legend with no side named may take (``dm.config.legend_fallback``)."""
    from ..config import config

    mode = config.legend_fallback
    match mode:
        case "auto":
            return list(free_sides(ax))
        case "above" | "right" | "below":
            return [mode]
        case "inside":
            return []
        case _:
            raise ValueError(
                "dm.config.legend_fallback must be 'auto', 'above', 'right', "
                f"'below' or 'inside', not {mode!r}"
            )


def _sibling_sides(ax: Axes) -> set[OutsideSide]:
    """Sides the fallback legends of the figure's other panels took (those
    in its SubFigures too)."""
    fig = ax.get_figure(root=True)
    if fig is None:
        return set()
    sides: set[OutsideSide] = set()
    for other in fig.axes:
        legend = other.get_legend()
        if other is ax or legend is None:
            continue
        side = outside_side(legend)
        if side is not None and getattr(legend, "_dm_outside_fallback", False):
            sides.add(side)
    return sides


def outside_fallback(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    kw: dict[str, Any],
    renderer: RendererBase,
) -> Legend | None:
    """Put the legend outside because every inside spot covers data.

    The side is the one of :func:`fallback_sides` whose plan costs the plot
    least (above first: a later side must clearly cost less, see
    :func:`choose`). A side another panel's fallback legend already took
    wins when it fits as well, so the panels of one figure agree. ``None``
    when no side may be used.
    """
    plans: list[OutsidePlan] = []
    sizes: Sizes = {}
    for side in fallback_sides(ax):
        plans += side_plans(
            ax, handles, labels, side, kw, renderer, named=False, sizes=sizes
        )
    if not plans:
        return None
    best = choose(plans)
    taken = _sibling_sides(ax)
    agreeing = [p for p in plans if p.side in taken and p.level == best.level]
    if agreeing and best.side not in taken:
        best = choose(agreeing)
    legend = draw_outside(ax, handles, labels, best, kw, renderer, sizes)
    legend._dm_collision_free = True  # type: ignore[attr-defined]
    legend._dm_collision_score = 0.0  # type: ignore[attr-defined]
    legend._dm_outside_fallback = True  # type: ignore[attr-defined]
    return legend


__all__ = [
    "ABSOLUTE_GAIN",
    "GOOD_FIT_LOSS",
    "OUTSIDE_LEGEND_LOCS",
    "RELATIVE_GAIN",
    "OutsidePlan",
    "OutsideSource",
    "Sizes",
    "choose",
    "draw_outside",
    "fallback_sides",
    "outside_fallback",
    "plan_side",
    "side_plans",
    "span_length",
    "split_ncols",
    "trial_pad",
]
