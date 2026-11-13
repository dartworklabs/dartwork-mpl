"""Text that grew: the ladder ``simple_layout`` climbs when labels collide.

After the margins converge, ``simple_layout`` looks for text that collides
and takes the steps below, each only where text collides and only on what
nobody set by hand. A round's changes are kept only if, once the margins
are fitted again, no plot lost more than ``1 - _MIN_PLOT_SHARE`` of its
width or height and no axis has more pairs of overlapping neighbouring tick
labels on a side than before (:func:`climb`; the count of
``tick_label_overlaps``, so labels beyond a neighbour that come to overlap
on an axis whose neighbours all overlap already are not counted);
otherwise the round is taken back, its changes are tried one at a time,
and those that do harm are dropped for the rest of the call. At most
``_FIT_ROUNDS`` rounds:

``axis_labels``
    An axis name longer than its side of the plot that overlaps (by more
    than ``_TOUCH_PX``) a neighbouring panel's text or plot, or runs past
    the figure edge (a name longer than the figure, which pushes the
    margins until the plot collapses), wraps at its spaces into as few
    lines as fit (at most ``_MAX_NAME_LINES``). A name in nobody's way
    stays, and lines that would crush the plot are taken back by the check
    after the round. A bracketed unit stays whole, the lines are as even as
    the words allow, and nothing but an existing space becomes a break.
``space``
    The root GridSpec's ``wspace`` / ``hspace`` grow where the content of
    neighbouring panels (tick labels, axis names, titles, colorbars,
    outside legends) reaches into the other panel's: to the deepest reach
    plus ``_TARGET_EM`` (of the rc font size), never smaller than they are.
    A collision that would need more than ``_MAX_GAP_FRACTION`` of a cell is
    left as it is (narrower panels would not clear it). Only spacing nobody
    set: ``gridspec_kw={"hspace": ...}``, ``fig.add_gridspec(hspace=...)``
    and ``fig.subplots_adjust(hspace=...)`` (any figure spacing other than
    the rc default) stay.
``wrap``
    Bottom tick labels that collide with a neighbour, or sit closer to it
    than ``_TARGET_EM`` (closer, two names read as one: "Iceland Sweden"
    0.38 em apart in ``advanced/bar`` on a slide), wrap at their spaces,
    each into the fewest lines (at most ``_MAX_TICK_LINES``) that keep it
    ``_TARGET_EM`` clear of both neighbours; a label beside short ones may
    use the room they leave (:func:`wrap_limit`). Only the labels that
    need it wrap.
``rotate``
    When a label cannot wrap narrow enough (no space to break at, a number,
    too long for three lines), the bottom labels turn 30, 45 or 90 degrees
    in their original one-line form: the smallest angle at which
    neighbours clear (:func:`smallest_angle`), with matplotlib's
    ``"xtick"`` rotation mode, which puts each label's end at its tick.
    When no angle clears, 90 degrees, but only if the labels then overlap
    less than flat (long names, not two short numbers on a squeezed axis).
    However long the turned labels, the check after the round decides: a
    turn that would leave a plot too little of the figure is taken back,
    and the names that long stay for the author (a horizontal bar chart).
``pad``
    An x tick label that overlaps a y tick label of the same plot box (the
    ``-3`` and ``-3`` at the corner of a -3..3 square, or a first category
    name wide enough to reach under the y labels; any corner, a twin's
    right labels included, :func:`~dartwork_mpl._figure_geometry.corner_tick_overlaps`)
    moves out: the tick pad of one axis grows by the overlap plus
    ``CORNER_GAP_EM`` of its label size, the axis whose labels move less,
    so the row or column keeps its alignment and every label stays at its
    tick. Taken once the other steps have nothing left to change, and kept
    only if the pairs are clear after the margins are fitted again. A pad
    you set (``ax.tick_params(pad=...)``, or one tick's ``set_pad``),
    before a layout or after one, stays, and so does that axis on the
    next layout; if both axes have one, the pair is the author's. Labels
    drawn at alpha 0 leave no ink and are no pair.

An axis whose ticks matplotlib picks by its length (``AutoLocator``, no
locator set by hand) and that a round made shorter keeps the intervals it
had before the climb (:func:`_keep_tick_budgets`): ``0 2 4 ... 10`` does
not become ``0.0 2.5 ... 10.0`` because a gap grew. That too is a change
the check after the round judges, and it stays only while its labels keep
``_TARGET_EM`` apart; an axis a round made longer takes the ticks of its
new length.

Nothing is shortened, hidden or made smaller. Text collides when it
overlaps by more than ``_TOUCH_PX`` (half a display pixel); text that only
comes close stays, but for neighbouring bottom tick labels, which climb
``wrap`` and ``rotate`` from under ``_TARGET_EM`` apart (a row that cannot
wrap and that no angle clears stays flat). So a figure without a collision
and with its bottom tick labels half an em apart draws exactly as it would
without this module. Within one call the ladder only climbs: a rotation
never turns back into a wrap and an angle never shrinks.

What is left is the author's. Tick labels that still overlap are reported
by ``TICK_OVERLAP``, an x label on a y label at a corner by
``TICK_CORNER_OVERLAP`` and text over another panel's text by
``CROSS_AXES_OVERLAP``; text reaching into another panel's plot area is
not reported yet.

What you set wins and is left alone: tick labels you rotated, wrote with
line breaks or aligned other than centred (bottom and top labels alike,
since only the bottom ones are turned), mathtext labels, axis names with
line breaks or mathtext, spacing and tick pads you set. What this module set is recorded
per artist, and each ``simple_layout`` call first undoes it where it is
still as set (:func:`restore_fitted`), so a re-layout at another size fits
from the figure as you left it and ``fit_labels=False`` gives that figure
back; a formatter, locator, label rotation, name or spacing changed since
is yours and stays. The margins go back to where the last call started
them while they are as it left them (:func:`remember_layout`), so a second
call draws exactly as the first (but for a date axis whose ticks the first
call thinned: its thinned locator stays, so it can move on the second call,
and draws the same from then on). Only the Axes the call lays out are
fitted and restored
(``use_all_axes=False`` keeps to the GridSpec passed), and what they share
with an Axes the call leaves out (the tick formatter of a shared x, the
spacing of their grid) is neither changed nor restored: such Axes only turn
their own labels. Polar, 3D and other
non-rectilinear Axes are not fitted, and nor are the labels of a vertical
axis (crowded rows of a horizontal bar chart need a taller canvas, which
is the author's call).
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal, TypeAlias
from weakref import WeakKeyDictionary

import matplotlib as mpl
import numpy as np
from matplotlib.axis import Axis
from matplotlib.gridspec import GridSpec
from matplotlib.text import Text
from matplotlib.ticker import AutoLocator, Formatter, Locator

from .._figure_geometry import (
    CORNER_GAP_EM,
    CornerOverlap,
    corner_tick_overlaps,
    drawn_in_tree,
    drawn_tick_labels,
    get_renderer,
    same_position_axes,
    tick_label_overlaps,
    tick_pad,
)
from ._content_extent import _axes_content_extent_px

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.axis import Tick
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties

#: Every step name ``fit_labels`` accepts; the default is all of them.
STEPS: tuple[str, ...] = ("axis_labels", "space", "wrap", "rotate", "pad")

# Overlap (display px) above which two texts collide; less only touches.
_TOUCH_PX = 0.5
# A step that makes room leaves this many ems between neighbours.
_TARGET_EM = 0.5
# Angles ``rotate`` tries, smallest first.
_ANGLES = (30.0, 45.0, 90.0)
_MAX_TICK_LINES = 3
_MAX_NAME_LINES = 4
# Largest wspace / hspace ``space`` sets (a fraction of the mean cell); a
# collision that needs more is left as it is.
_MAX_GAP_FRACTION = 1.5
#: The same cap for ``simple_layout(gutter=...)``.
MAX_GAP_FRACTION = _MAX_GAP_FRACTION
# Least of its width and of its height a plot keeps through one round.
# Measured (I-O1 follow-up): the 169 rounds the stress corpus and the shipped
# templates (native size, and squeezed to 9 cm) keep held at least 0.39 of
# each plot side; the one that crushed a plot (advanced/boxplot turned 45
# degrees at 9 cm in presentation) kept 0.01-0.22, by the margin asked.
_MIN_PLOT_SHARE = 0.3
# Most fitting rounds per call, each followed by a fresh margin fit.
_FIT_ROUNDS = 5


def resolve_steps(fit_labels: bool | Iterable[str] | None) -> frozenset[str]:
    """The steps one ``simple_layout`` call may take.

    ``None`` reads :data:`dartwork_mpl.config.fit_labels`; ``True`` is every
    step, ``False`` none, a string or an iterable of strings names the
    steps. A value that is neither, or a step that is not a string
    (``bytes`` included), raises ``TypeError``; an unknown step name
    ``ValueError``.
    """
    if fit_labels is None:
        from ..config import config

        fit_labels = config.fit_labels
    if fit_labels is True:
        return frozenset(STEPS)
    if fit_labels is False:
        return frozenset()
    if isinstance(fit_labels, str):
        fit_labels = (fit_labels,)
    if isinstance(fit_labels, (bytes, bytearray)) or not isinstance(
        fit_labels, Iterable
    ):
        raise TypeError(
            "fit_labels must be True, False or step names; got "
            f"{type(fit_labels).__name__}"
        )
    chosen = tuple(fit_labels)
    for step in chosen:
        if not isinstance(step, str):
            raise TypeError(
                "fit_labels step names must be str; got "
                f"{type(step).__name__} {step!r}"
            )
    unknown = sorted(set(chosen) - set(STEPS))
    if unknown:
        raise ValueError(
            f"fit_labels: unknown step(s) {unknown}; known: {list(STEPS)}"
        )
    return frozenset(chosen)


# ─────────────────────────────────────────────────────────────────────
# What this module set, so the next call starts from the user's figure
# ─────────────────────────────────────────────────────────────────────


_RotationMode: TypeAlias = Literal["default", "anchor", "xtick", "ytick"]


@dataclass(frozen=True)
class _Turned:
    """A tick label this module turned: the angle it set, its state before."""

    angle: float
    rotation: float
    mode: _RotationMode


# tick label Text -> the turn this module set on it
_TURNED: WeakKeyDictionary[Text, _Turned] = WeakKeyDictionary()
# axis -> the turn of its first label (for ticks matplotlib adds later,
# which copy the first tick's angle)
_TURNED_AXES: WeakKeyDictionary[Axis, _Turned] = WeakKeyDictionary()
# axis label Text -> (text before wrapping, wrapped text)
_NAMES: WeakKeyDictionary[Text, tuple[str, str]] = WeakKeyDictionary()
# GridSpec -> {"wspace" / "hspace": the value this module set}
_GAPS: WeakKeyDictionary[GridSpec, dict[str, float]] = WeakKeyDictionary()


@dataclass(frozen=True)
class _Padded:
    """An axis whose label pad this module grew: the pads before, as set."""

    major: float
    minor: float
    major_set: float
    minor_set: float


# axis -> the pads this module set on its ticks (``pad``)
_PADS: WeakKeyDictionary[Axis, _Padded] = WeakKeyDictionary()

#: A root GridSpec's ``left``, ``right``, ``bottom`` and ``top``.
Edges: TypeAlias = tuple[float | None, float | None, float | None, float | None]


#: A locator's parameters (all but the axis it measures), comparable.
Params: TypeAlias = tuple[tuple[str, object], ...]


@dataclass(frozen=True)
class _Kept:
    """What a kept tick budget replaced, and how this module set it.

    ``auto`` is matplotlib's own locator, waiting off any axis (so neither
    it nor this record holds an axis, nor through one a figure); ``params``
    are the kept locator's parameters as set, so an edit since
    (``ax.locator_params(...)``, ``set_params``) makes it yours.
    """

    auto: Locator
    params: Params


# kept locator -> what it replaced. Keyed by the locator its axis holds, a
# record lives as long as that axis keeps it: a locator you set instead, or
# a figure closed and let go, takes the record with it.
_KEPT: WeakKeyDictionary[Locator, _Kept] = WeakKeyDictionary()
# root GridSpec -> (its edges before the last layout, the edges it left)
_LAID: WeakKeyDictionary[GridSpec, tuple[Edges, Edges]] = WeakKeyDictionary()


def grid_edges(gs: GridSpec) -> Edges:
    """The edges of ``gs`` (``None``: the figure's subplot parameters)."""
    return (gs.left, gs.right, gs.bottom, gs.top)


def remember_layout(gs: GridSpec, start: Edges) -> None:
    """Record that a layout fitted the margins of ``gs`` from ``start``.

    While the edges stay as that layout left them, the next layout starts
    from ``start`` again (:func:`restore_fitted`): the margin fit stops
    within half a pixel of its fixed point, so where it starts decides the
    last hundredths of a pixel, and a second call on the same figure draws
    exactly as the first (a date axis whose ticks the first call thinned
    excepted, see the module docstring). The record holds only numbers and
    is keyed weakly by the grid: it lets the figure go.
    """
    _LAID[gs] = (start, grid_edges(gs))


class WrappedTickFormatter(Formatter):
    """The axis' own formatter, with line breaks in some of its labels.

    ``lines`` maps a label as ``base`` writes it to the wrapped text; other
    labels pass through. Offsets, data formatting and tick locations stay
    the base formatter's. :func:`restore_fitted` puts ``base`` back (and
    ``base_default``, the axis' ``isDefault_majfmt`` before wrapping).
    """

    def __init__(
        self, base: Formatter, lines: Mapping[str, str], base_default: bool
    ) -> None:
        self.base = base
        self.lines = dict(lines)
        self.base_default = base_default

    def __call__(self, x: float, pos: int | None = None) -> str:
        text = self.base(x, pos)
        return self.lines.get(text, text)

    def format_ticks(self, values: list[float]) -> list[str]:
        return [self.lines.get(t, t) for t in self.base.format_ticks(values)]

    def set_locs(self, locs: list[float]) -> None:
        self.base.set_locs(locs)

    def get_offset(self) -> str:
        return self.base.get_offset()

    def format_data(self, value: float) -> str:
        return self.base.format_data(value)

    def format_data_short(self, value: float) -> str:
        return self.base.format_data_short(value)

    def set_axis(self, axis: Any) -> None:
        super().set_axis(axis)
        self.base.set_axis(axis)


def _unwrap(axis: Axis, wrapper: WrappedTickFormatter) -> None:
    axis.set_major_formatter(wrapper.base)
    axis.isDefault_majfmt = wrapper.base_default


def _set_turn(label: Text, rotation: float, mode: _RotationMode) -> None:
    label.set_rotation(rotation)
    label.set_rotation_mode(mode)


def _turn_now(label: Text) -> tuple[float, _RotationMode]:
    return float(label.get_rotation()), label.get_rotation_mode()


def restore_fitted(fig: Figure, axes: Iterable[Axes] | None = None) -> None:
    """Undo what earlier layouts fitted on ``axes`` (default: all of
    ``fig``'s), where it is still as set.

    A formatter, tick locator, tick label rotation, axis name or spacing
    changed since (by you) is yours and stays; its record is dropped. What
    other Axes share, a formatter or locator (shared x or y) or a grid's
    spacing, comes back only when every Axes sharing it is among ``axes``:
    a layout of one grid does not undo what a layout of the whole figure
    set for the others. The margins of a grid the last layout left as they
    are go back to where that layout started (:func:`remember_layout`).
    """
    chosen = list(fig.axes if axes is None else axes)
    ids = {id(ax) for ax in chosen}
    for ax in chosen:
        for axis, shared in (
            (ax.xaxis, ax.get_shared_x_axes()),
            (ax.yaxis, ax.get_shared_y_axes()),
        ):
            whole = _all_in(shared.get_siblings(ax), ids)
            fmt = axis.get_major_formatter()
            if isinstance(fmt, WrappedTickFormatter) and whole:
                _unwrap(axis, fmt)
            locator = axis.get_major_locator()
            kept = _KEPT.get(locator)
            if kept is not None and whole:
                del _KEPT[locator]
                if _locator_params(locator) == kept.params:
                    owner = locator.axis
                    _put_back_auto(
                        owner if isinstance(owner, Axis) else axis, kept.auto
                    )
            first = _TURNED_AXES.pop(axis, None)
            for tick in axis.get_major_ticks():
                label = tick.label1
                turn = _TURNED.pop(label, None) or first
                if turn is not None and _turn_now(label) == (
                    turn.angle,
                    "xtick",
                ):
                    _set_turn(label, turn.rotation, turn.mode)
            padded = _PADS.pop(axis, None)
            if padded is not None:
                _restore_pads(axis, padded)
        for label in (ax.xaxis.label, ax.yaxis.label):
            record = _NAMES.pop(label, None)
            if record is not None and label.get_text() == record[1]:
                label.set_text(record[0])
    for gs in {g for ax in chosen if (g := _root_gridspec(ax)) is not None}:
        moved = False
        laid = _LAID.pop(gs, None)
        if laid is not None and grid_edges(gs) == laid[1]:
            gs.update(**dict(zip(_EDGES, laid[0], strict=True)))
            moved = True
        if _all_in(_on_grid(fig, gs), ids):  # else: their spacing too
            for key, value in _GAPS.pop(gs, {}).items():
                if getattr(gs, key) == value:
                    gs.update(**{key: None})
                    moved = True
        if moved:
            _place(fig, gs)


def put_back_edges(fig: Figure, gs: GridSpec, edges: Edges) -> None:
    """Give ``gs`` the ``edges`` (from :func:`grid_edges`) and move its Axes
    there, whichever figure holds them."""
    gs.update(**dict(zip(_EDGES, edges, strict=True)))
    _place(fig, gs)


def _place(fig: Figure, gs: GridSpec) -> None:
    """Put the Axes of ``gs`` where its edges and spacing say now.

    ``GridSpec.update`` moves the Axes of pyplot's open figures only; the
    Axes of any other figure follow their SubplotSpec here, as the margin
    fit moves them.
    """
    for ax in _on_grid(fig, gs):
        spec = ax.get_subplotspec()
        if spec is None:
            continue
        # Matplotlib accepts the local SubFigure here, though its
        # SubplotSpec stub only declares Figure.
        position = spec.get_position(ax.get_figure(root=False))  # type: ignore[arg-type]
        if ax.get_position(original=True).bounds != position.bounds:
            ax.set_subplotspec(spec)


def _put_back_auto(axis: Axis, auto: Locator) -> None:
    """Matplotlib's auto locator a kept budget replaced, on ``axis`` again
    (the axis it measured, the one the budget was set on)."""
    axis.set_major_locator(auto)
    axis.isDefault_majloc = True


def _locator_params(locator: Locator) -> Params:
    """The parameters of ``locator``, all but the axis it measures."""
    return tuple(
        (key, value.tolist() if isinstance(value, np.ndarray) else value)
        for key, value in sorted(vars(locator).items())
        if key != "axis"
    )


def _all_in(members: Iterable[Axes], ids: set[int]) -> bool:
    """Whether every one of ``members`` is among the Axes ``ids``."""
    return all(id(member) in ids for member in members)


def _on_grid(fig: Figure, gs: GridSpec) -> list[Axes]:
    """Every Axes of ``fig`` placed on the root GridSpec ``gs``."""
    return [ax for ax in fig.axes if _root_gridspec(ax) is gs]


# ─────────────────────────────────────────────────────────────────────
# Pure decisions
# ─────────────────────────────────────────────────────────────────────


def tokens(text: str) -> list[str]:
    """Words of ``text`` split at its spaces outside brackets.

    A bracketed unit (``(MWh per year)``) stays one token, and text attached
    to a word (``(kW),``) stays attached: joining the tokens with single
    spaces gives ``text`` back, with its runs of spaces made single.
    """
    out: list[str] = []
    depth = 0
    word = ""
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]" and depth:
            depth -= 1
        if ch.isspace() and depth == 0:
            if word:
                out.append(word)
            word = ""
        else:
            word += ch
    if word:
        out.append(word)
    return out


def balanced_lines(
    words: Sequence[str], n_lines: int, width: Callable[[str], float]
) -> tuple[list[str], float]:
    """Split ``words`` into ``n_lines`` lines minimising the widest line.

    Returns the lines and that width. Fewer words than lines gives one word
    per line. Ties keep the earlier break (the first line longer).
    """
    n = len(words)
    memo: dict[tuple[int, int], tuple[float, list[str]]] = {}

    def best(i: int, left: int) -> tuple[float, list[str]]:
        key = (i, left)
        if key in memo:
            return memo[key]
        if left == 1:
            line = " ".join(words[i:])
            result = (width(line), [line])
        else:
            result = (math.inf, [])
            for j in range(i + 1, n - left + 2):
                head = " ".join(words[i:j])
                w_head = width(head)
                if w_head >= result[0]:
                    break  # a longer first line only gets wider
                w_rest, rest = best(j, left - 1)
                w = max(w_head, w_rest)
                if w < result[0]:
                    result = (w, [head, *rest])
        memo[key] = result
        return result

    w, lines = best(0, min(n_lines, n))
    return lines, w


def wrap_to(
    text: str, limit: float, width: Callable[[str], float], max_lines: int
) -> str | None:
    """``text`` in the fewest lines whose widest is at most ``limit``.

    ``None`` when no wrap into at most ``max_lines`` lines fits, or when the
    text cannot break.
    """
    words = tokens(text)
    for n in range(2, min(max_lines, len(words)) + 1):
        lines, w = balanced_lines(words, n, width)
        if w <= limit:
            return "\n".join(lines)
    return None


def wrap_limit(
    i: int, widths: Sequence[float], gaps: Sequence[float], clearance: float
) -> float:
    """Widest label ``i`` may be and still clear both neighbours.

    Label ``i`` and its neighbour ``j`` (``gap`` apart, centred on their
    ticks) clear when their half-widths add up to at most
    ``gap - clearance``. Each label may count on a neighbour taking no more
    than its own fair share (``gap - clearance``) or its width, whichever is
    smaller, so a long label beside short ones wraps less, and two long
    neighbours each keep to their share.
    """
    limit = math.inf
    for j, gap in (
        (i - 1, gaps[i - 1] if i > 0 else None),
        (i + 1, gaps[i] if i < len(gaps) else None),
    ):
        if gap is None:
            continue
        share = gap - clearance
        limit = min(limit, 2 * share - min(widths[j], share))
    return limit


def smallest_angle(
    spacing: float, line_height: float, clearance: float, start: float = 0.0
) -> float | None:
    """The smallest of ``_ANGLES`` (not below ``start``) at which labels clear.

    Two parallel labels ``spacing`` apart along the axis sit
    ``spacing * sin(angle)`` apart across their text direction; they clear
    when that is at least ``line_height + clearance``. ``None`` when even 90
    degrees does not clear.
    """
    for angle in _ANGLES:
        if angle < start:
            continue
        if spacing * math.sin(math.radians(angle)) >= line_height + clearance:
            return angle
    return None


def gap_fraction(need_px: float, total_px: float, n: int) -> float | None:
    """GridSpec ``wspace`` / ``hspace`` whose gaps are ``need_px`` wide.

    ``total_px`` is the grid's extent between its outer edges and ``n`` the
    number of cells along it. Matplotlib sizes a cell as
    ``total / (n + gap * (n - 1))`` and a gap as ``gap`` cells, whatever the
    ratios. ``None`` when ``need_px`` gaps leave no room for the cells.
    """
    room = total_px - need_px * (n - 1)
    if room <= 0:
        return None
    return need_px * n / room


def record_spacing(gs: GridSpec, key: str, value: float) -> None:
    """Set ``gs``'s ``wspace`` / ``hspace`` as a layout setting it.

    The next layout undoes it while it is still as set
    (:func:`restore_fitted`), like the spacing ``space`` grows.
    """
    gs.update(**{key: value})
    _GAPS.setdefault(gs, {})[key] = value


def box_overlap_px(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    """How deep two ``(x0, x1, y0, y1)`` boxes cross (<= 0: apart)."""
    return min(
        min(a[1], b[1]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[2], b[2])
    )


# ─────────────────────────────────────────────────────────────────────
# The climb: rounds of changes, each kept only if it harmed nothing
# ─────────────────────────────────────────────────────────────────────

#: What a change touched: ``(rung, id of the artist or grid it changed)``.
Key: TypeAlias = tuple[str, int]


@dataclass(frozen=True)
class _Change:
    """One change a rung made, and how to take it back.

    ``kept``: whether the change may stay once the margins are fitted
    again, besides harming nothing (:func:`_harmed`); ``None``: it may.
    """

    key: Key
    undo: Callable[[], None]
    kept: Callable[[RendererBase], bool] | None = None


@dataclass(frozen=True)
class _Budget:
    """An axis whose ticks matplotlib picks by its length (``AutoLocator``)
    and the most intervals it had room for before the climb."""

    axis: Axis
    auto: AutoLocator
    nbins: int


@dataclass
class FitState:
    """What one ``simple_layout`` call has fitted so far (the ladder climbs)."""

    turned: dict[int, float] = field(default_factory=dict)  # id(axis) -> angle
    wrapped: set[int] = field(default_factory=set)  # id(axis)
    rejected: set[Key] = field(default_factory=set)  # changes that did harm
    only: frozenset[Key] | None = None  # while trying changes one at a time
    budgets: list[_Budget] = field(default_factory=list)  # before the climb

    def allows(self, key: Key) -> bool:
        return key not in self.rejected and (
            self.only is None or key in self.only
        )


@dataclass(frozen=True)
class _Health:
    """What a round may not make worse: plot sizes, overlapping tick labels."""

    plots: dict[int, tuple[float, float]]  # id(ax) -> (width, height) px
    overlaps: dict[tuple[int, str], int]  # (id(ax), "x" / "y") -> pairs


def _health(axes: Sequence[Axes], renderer: RendererBase) -> _Health:
    plots: dict[int, tuple[float, float]] = {}
    overlaps: dict[tuple[int, str], int] = {}
    for ax in axes:
        if not ax.get_visible():
            continue
        box = ax.get_window_extent(renderer)
        plots[id(ax)] = (float(box.width), float(box.height))
        if _cartesian(ax):
            for which in ("x", "y"):
                overlaps[(id(ax), which)] = tick_label_overlaps(
                    ax, which, renderer
                ).pairs
    return _Health(plots, overlaps)


def _harmed(before: _Health, after: _Health) -> bool:
    """Whether a plot was crushed or an axis gained pairs of overlapping
    neighbouring tick labels (on either side)."""
    for key, (w, h) in before.plots.items():
        w_now, h_now = after.plots.get(key, (w, h))
        if w_now < _MIN_PLOT_SHARE * w or h_now < _MIN_PLOT_SHARE * h:
            return True
    return any(
        pairs > before.overlaps.get(key, 0)
        for key, pairs in after.overlaps.items()
    )


def _undo(changes: Sequence[_Change]) -> None:
    for change in reversed(changes):
        change.undo()


def climb(
    fig: Figure,
    steps: frozenset[str],
    grid: GridSpec,
    axes: Sequence[Axes],
    refit: Callable[[], bool],
) -> bool:
    """Climb the ladder on ``axes`` of ``fig`` until nothing collides that it
    can clear; return whether it tried changes and took every one back.

    ``grid`` is the root GridSpec the margins are fitted on, whose
    ``wspace`` / ``hspace`` ``space`` may grow between the panels of
    ``axes`` when every Axes on it is among them. ``refit`` fits the margins
    again and returns ``False`` when nothing can be measured. Each round
    measures on the draw of the last layout step, which the converged edges
    moved by less than the solver's tolerance, so a figure without a
    collision costs no extra draw. A round that harmed a plot or an axis
    (:func:`_harmed`) is taken back, with the grid's edges as they were
    before it, and its changes are tried one at a time (a round of one
    change is not tried again alone); a change that does harm on its own
    is taken back the same way and not tried again in this call.

    Each take-back fits the margins again from the round's edges, and the
    fit stops within its tolerance of a fixed point, a hair from where it
    stood; when every change was taken back, the caller fits the margins
    afresh from where it started, so the figure draws as without fitting.
    """
    state = FitState(budgets=_tick_budgets(axes))
    tried = kept = False

    def changes_now(only: Key | None) -> list[_Change]:
        state.only = None if only is None else frozenset({only})
        try:
            return fit_round(fig, get_renderer(fig), steps, grid, axes, state)
        finally:
            state.only = None

    def attempt(only: Key | None) -> bool | None:
        """One round (or one change of it); ``None``: nothing was measurable."""
        nonlocal tried, kept
        changes = changes_now(only)
        if not changes:
            return False
        # Something to change: measure the figure as it was (a figure with
        # no collision never pays for this), then make the changes again.
        _undo(changes)
        before = _health(axes, get_renderer(fig))
        changes = changes_now(only)
        edges = {side: getattr(grid, side) for side in _EDGES}
        tried = True
        if not refit():
            return None
        renderer = get_renderer(fig)
        if not _harmed(before, _health(axes, renderer)) and all(
            change.kept is None or change.kept(renderer) for change in changes
        ):
            kept = True
            return True
        _undo(changes)
        grid.update(**edges)
        if not refit():
            return None
        if only is not None or len(changes) == 1:
            # one change, alone already: the harm was its own
            state.rejected.add(changes[0].key if only is None else only)
            return True
        for change in changes:
            if attempt(change.key) is None:
                return None
        return True

    for _round in range(_FIT_ROUNDS):
        done = attempt(None)
        if done is None:
            return False  # nothing to measure: no fresh fit either
        if not done:
            break
    return tried and not kept


# The GridSpec edges the margin fit sets, restored with a round taken back.
_EDGES = ("left", "right", "bottom", "top")


def fit_round(
    fig: Figure,
    renderer: RendererBase,
    steps: frozenset[str],
    gs: GridSpec,
    axes: Sequence[Axes],
    state: FitState,
) -> list[_Change]:
    """Take every step that has a collision to fix now; return the changes."""
    changes: list[_Change] = []
    if "axis_labels" in steps:
        changes += _fit_axis_names(fig, renderer, axes, state)
    if "space" in steps:
        changes += _fit_panel_gaps(fig, renderer, gs, axes, state)
    if steps & {"wrap", "rotate"}:
        for group, whole in _shared_x_groups(axes):
            changes += _fit_x_ticks(group, whole, renderer, steps, state)
    if "pad" in steps and not changes:
        # once the labels have settled: a wrap or a turn moves the corners
        changes += _fit_corners(fig, renderer, axes, state)
    changes += _keep_tick_budgets(axes, state)
    return changes


def _width_of(
    renderer: RendererBase, prop: FontProperties
) -> Callable[[str], float]:
    def width(line: str) -> float:
        w, _h, _d = renderer.get_text_width_height_descent(
            line, prop, ismath=False
        )
        return float(w)

    return width


def _cartesian(ax: Axes) -> bool:
    """A visible rectilinear Axes with its axes on (polar, 3D, maps: no)."""
    return (
        ax.get_visible()
        and getattr(ax, "axison", True)
        and getattr(ax, "name", None) == "rectilinear"
    )


def _root_gridspec(ax: Axes) -> GridSpec | None:
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    gs = spec.get_topmost_subplotspec().get_gridspec()
    return gs if isinstance(gs, GridSpec) else None


# ── axis_labels ──────────────────────────────────────────────────────


def _fit_axis_names(
    fig: Figure, renderer: RendererBase, axes: Sequence[Axes], state: FitState
) -> list[_Change]:
    changes: list[_Change] = []
    for ax in axes:
        if not _cartesian(ax):
            continue
        frame = ax.get_window_extent(renderer)
        for axis, span in ((ax.xaxis, frame.width), (ax.yaxis, frame.height)):
            label = axis.label
            text = label.get_text()
            key: Key = ("axis_labels", id(label))
            if (
                span <= 0
                or not state.allows(key)
                or not axis.get_visible()
                or not label.get_visible()
                or not text.strip()
                or "\n" in text
                or "$" in text
                or label in _NAMES
            ):
                continue
            width = _width_of(renderer, label.get_fontproperties())
            if width(text) <= span or not _in_the_way(label, ax, fig, renderer):
                continue
            wrapped = wrap_to(text, span, width, _MAX_NAME_LINES)
            if wrapped is None:
                words = tokens(text)
                if len(words) < 2:
                    continue
                wrapped = "\n".join(
                    balanced_lines(words, _MAX_NAME_LINES, width)[0]
                )
            _NAMES[label] = (text, wrapped)
            label.set_text(wrapped)

            def undo(label: Text = label, text: str = text) -> None:
                label.set_text(text)
                _NAMES.pop(label, None)

            changes.append(_Change(key, undo))
    return changes


def _in_the_way(
    label: Text, ax: Axes, fig: Figure, renderer: RendererBase
) -> bool:
    """Whether an axis name runs past the figure or into another panel.

    Another panel is the content of any other visible Axes (its text and
    plot, :func:`_axes_content_extent_px`), not one drawn in the same place
    (a twin); both by more than ``_TOUCH_PX``.
    """
    box = label.get_window_extent(renderer)
    name = (box.x0, box.x1, box.y0, box.y1)
    if (
        -name[0] > _TOUCH_PX
        or name[1] - fig.bbox.width > _TOUCH_PX
        or -name[2] > _TOUCH_PX
        or name[3] - fig.bbox.height > _TOUCH_PX
    ):
        return True
    here = {id(a) for a in same_position_axes(ax)} | {id(ax)}
    for other in fig.axes:
        if id(other) in here or not drawn_in_tree(other):
            continue  # a hidden SubFigure's panel is no neighbour
        extent = _axes_content_extent_px(other, renderer, fig)
        if extent is not None and box_overlap_px(name, extent) > _TOUCH_PX:
            return True
    return False


# ── space ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Reach:
    """How far a panel's content reaches past its grid cell, along one direction.

    ``along`` are the cell's columns (for ``wspace``) or rows (``hspace``),
    ``across`` the other; ``back`` is the reach (px) past the cell's left /
    top edge, ``ahead`` past its right / bottom edge.
    """

    along: range
    across: range
    back: float
    ahead: float


def _deepest_reach(reaches: Sequence[_Reach], seps: Sequence[float]) -> float:
    """The widest gap any two facing panels need, or 0 when none collide.

    ``seps[k]`` is the gap (px) between cell ``k`` and ``k + 1``; two
    panels face each other across it when one ends at ``k``, the other
    starts at ``k + 1`` and they share a row (column).
    """
    need = 0.0
    for k, sep in enumerate(seps):
        for a in reaches:
            if a.along.stop - 1 != k:
                continue
            for b in reaches:
                if b.along.start != k + 1 or not set(a.across) & set(b.across):
                    continue
                reach = max(a.ahead, 0.0) + max(b.back, 0.0)
                if reach - sep > _TOUCH_PX:
                    need = max(need, reach)
    return need


def _spacing_is_free(fig: Figure, gs: GridSpec, key: str) -> bool:
    """Whether nobody set ``gs``'s ``wspace`` / ``hspace`` but this module.

    The grid's own value (``gridspec_kw``, ``add_gridspec``) is set unless
    this module set it; when it is unset the figure's applies, which is
    set when it differs from the rc default (``fig.subplots_adjust``).
    """
    value = getattr(gs, key)
    if value is not None:
        return bool(_GAPS.get(gs, {}).get(key) == value)
    default = (
        mpl.rcParams["figure.subplot.wspace"]
        if key == "wspace"
        else mpl.rcParams["figure.subplot.hspace"]
    )
    return bool(getattr(fig.subplotpars, key) == default)


def _fit_panel_gaps(
    fig: Figure,
    renderer: RendererBase,
    gs: GridSpec,
    axes: Sequence[Axes],
    state: FitState,
) -> list[_Change]:
    """Grow the ``wspace`` / ``hspace`` of ``gs`` where panel content meets.

    Only when every Axes on ``gs`` is laid out by this call: the spacing
    moves them all.
    """
    if not _all_in(_on_grid(fig, gs), {id(ax) for ax in axes}):
        return []
    nrows, ncols = gs.get_geometry()
    free = {
        key: n > 1
        and state.allows(("space_" + key, id(gs)))
        and _spacing_is_free(fig, gs, key)
        for key, n in (("wspace", ncols), ("hspace", nrows))
    }
    if not any(free.values()):
        return []
    # The grid's positions are fractions of the (Sub)Figure it is on; the
    # canvas starts at 0, a SubFigure's box where it sits on the canvas.
    frame = getattr(gs, "figure", None) or fig
    bottoms, tops, lefts, rights = gs.get_grid_positions(frame)
    fw, fh = frame.bbox.width, frame.bbox.height
    ox, oy = frame.bbox.x0, frame.bbox.y0
    across_cols: list[_Reach] = []
    across_rows: list[_Reach] = []
    for ax in axes:
        if _root_gridspec(ax) is not gs:
            continue
        extent = _axes_content_extent_px(ax, renderer, fig)
        if extent is None:
            continue
        spec = ax.get_subplotspec().get_topmost_subplotspec()  # type: ignore[union-attr]
        rows, cols = spec.rowspan, spec.colspan
        x0, x1, y0, y1 = extent
        across_cols.append(
            _Reach(
                cols,
                rows,
                back=ox + lefts[cols.start] * fw - x0,
                ahead=x1 - (ox + rights[cols.stop - 1] * fw),
            )
        )
        across_rows.append(
            _Reach(
                rows,
                cols,
                back=y1 - (oy + tops[rows.start] * fh),
                ahead=oy + bottoms[rows.stop - 1] * fh - y0,
            )
        )
    em = float(mpl.rcParams["font.size"]) * fig.dpi / 72.0
    params = gs.get_subplot_params(frame)
    changes: list[_Change] = []
    for key, n, reaches, seps, total in (
        (
            "wspace",
            ncols,
            across_cols,
            [(lefts[c + 1] - rights[c]) * fw for c in range(ncols - 1)],
            (rights[-1] - lefts[0]) * fw,
        ),
        (
            "hspace",
            nrows,
            across_rows,
            [(bottoms[r] - tops[r + 1]) * fh for r in range(nrows - 1)],
            (tops[0] - bottoms[-1]) * fh,
        ),
    ):
        if not free[key]:
            continue
        need = _deepest_reach(reaches, seps)
        if need <= 0:
            continue
        gap = gap_fraction(need + _TARGET_EM * em, total, n)
        if gap is None or gap > _MAX_GAP_FRACTION:
            continue  # parting them would take more: left as it is
        if gap <= getattr(params, key) + 1e-6:
            continue
        before = getattr(gs, key)
        gs.update(**{key: gap})
        _GAPS.setdefault(gs, {})[key] = gap

        def undo(key: str = key, before: float | None = before) -> None:
            gs.update(**{key: before})
            if before is None:
                _GAPS.get(gs, {}).pop(key, None)
            else:
                _GAPS.setdefault(gs, {})[key] = before

        changes.append(_Change(("space_" + key, id(gs)), undo))
    return changes


# ── wrap / rotate ────────────────────────────────────────────────────


def _shared_x_groups(axes: Sequence[Axes]) -> list[tuple[list[Axes], bool]]:
    """The fitted Axes grouped by shared x axis, in figure order.

    Axes that share x (``sharex=True``, a twin) share the tick formatter,
    so their labels wrap together; each still turns its own labels. With
    each group, whether every Axes sharing that x is among ``axes``: only
    then may the shared formatter change.
    """
    groups: list[tuple[list[Axes], bool]] = []
    seen: set[int] = set()
    ids = {id(ax) for ax in axes}
    fitted = [ax for ax in axes if _cartesian(ax)]
    for ax in fitted:
        if id(ax) in seen:
            continue
        siblings = ax.get_shared_x_axes().get_siblings(ax)
        sibling_ids = {id(a) for a in siblings}
        group = [a for a in fitted if id(a) in sibling_ids]
        seen.update(id(a) for a in group)
        groups.append((group, _all_in(siblings, ids)))
    return groups


@dataclass(frozen=True)
class _Row:
    """The bottom tick labels of one Axes as the ladder reads them.

    ``texts`` (as the axis' own formatter writes them), ``widths`` (one
    line, px) and ``gaps`` between neighbouring centres run left to right.
    ``yours``: a rotation (not this call's), an alignment other than
    centred, line breaks or mathtext set by hand.
    """

    ax: Axes
    texts: list[str]
    widths: list[float]
    gaps: list[float]
    clearance: float
    line_height: float
    yours: bool
    width: Callable[[str], float]

    @property
    def collides(self) -> bool:
        return any(
            (self.widths[i] + self.widths[i + 1]) / 2 - gap > _TOUCH_PX
            for i, gap in enumerate(self.gaps)
        )

    @property
    def crowded(self) -> bool:
        """Neighbours closer than ``clearance`` (half an em), overlapping or
        not: what starts ``wrap`` and ``rotate``, whose targets are the same
        clearance. Half a pixel of slack keeps a row that is exactly half an
        em apart as it is."""
        return any(
            gap - (self.widths[i] + self.widths[i + 1]) / 2
            < self.clearance - _TOUCH_PX
            for i, gap in enumerate(self.gaps)
        )


def _read_row(
    ax: Axes,
    renderer: RendererBase,
    wrapper: WrappedTickFormatter | None,
    state: FitState,
) -> _Row | None:
    axis = ax.xaxis
    bottom = {id(t.label1) for t in axis.get_major_ticks()}
    labels = [
        t
        for t in drawn_tick_labels(ax, "x")
        if id(t) in bottom and t.get_text().strip()
    ]
    fig = ax.get_figure(root=True)
    if len(labels) < 2 or fig is None:
        return None
    unwrap = {v: k for k, v in wrapper.lines.items()} if wrapper else {}
    texts = [unwrap.get(t.get_text(), t.get_text()) for t in labels]
    centres = [
        float(t.get_transform().transform(t.get_position())[0]) for t in labels
    ]
    order = sorted(range(len(labels)), key=centres.__getitem__)
    gaps = [centres[b] - centres[a] for a, b in pairwise(order)]
    if min(gaps) <= 0:
        return None
    yours = any("\n" in t or "$" in t for t in texts) or (
        id(axis) not in state.turned
        and (
            {float(t.get_rotation()) for t in labels} != {0.0}
            or {t.get_horizontalalignment() for t in labels} != {"center"}
        )
    )
    texts = [texts[i] for i in order]
    font = labels[0].get_fontproperties()
    width = _width_of(renderer, font)
    _w, line_height, _d = renderer.get_text_width_height_descent(
        "Ag", font, ismath=False
    )
    return _Row(
        ax=ax,
        texts=texts,
        widths=[max(map(width, t.split("\n"))) for t in texts],
        gaps=gaps,
        clearance=_TARGET_EM * float(labels[0].get_fontsize()) * fig.dpi / 72.0,
        line_height=float(line_height),
        yours=yours,
        width=width,
    )


def _fit_x_ticks(
    group: Sequence[Axes],
    whole: bool,
    renderer: RendererBase,
    steps: frozenset[str],
    state: FitState,
) -> list[_Change]:
    """Wrap (together) or turn (each) the bottom tick labels of Axes that
    share x and collide or crowd (:attr:`_Row.crowded`).

    ``whole``: every Axes sharing this x is laid out by this call. When one
    is not, the shared formatter is not this call's: no wrap goes on or
    comes off (labels wrapped by a layout of every Axes stay as they are),
    and each Axes of the call may only turn its own labels.
    """
    axis = group[0].xaxis  # the group's formatter is set through this axis
    fmt = axis.get_major_formatter()
    wrapper = fmt if isinstance(fmt, WrappedTickFormatter) else None
    if wrapper is not None and not whole:
        return []
    rows = [
        row
        for ax in group
        if (row := _read_row(ax, renderer, wrapper, state)) is not None
    ]
    if not rows:
        return []
    turned = any(id(row.ax.xaxis) in state.turned for row in rows)
    if (
        whole
        and not turned
        and (wrapper is not None or any(r.crowded for r in rows))
        and "wrap" in steps
        and state.allows(("wrap", id(axis)))
        and not any(row.yours for row in rows)
    ):
        lines = _wrap_lines(rows)
        if lines is not None:
            return _set_wrap(axis, fmt, wrapper, lines, state)
    if "rotate" not in steps:
        return []
    changes: list[_Change] = []
    for row in rows:
        angle = _turn_angle(row, state)
        if angle is None:
            continue
        unwrapped: list[_Change] = []
        if wrapper is not None:
            # Turned labels are one line: the group's wraps come off with
            # the first turn, and come back if that turn is taken back.
            unwrapped = _set_wrap(axis, fmt, wrapper, {}, state)
            wrapper = None
        changes += _set_turn_on(row.ax, angle, state, unwrapped)
    return changes


def _turn_angle(row: _Row, state: FitState) -> float | None:
    """The angle ``row``'s labels turn to now, or ``None`` (they stay)."""
    key = id(row.ax.xaxis)
    angle_now = state.turned.get(key)
    if not state.allows(("rotate", key)):
        return None
    if angle_now is None and (row.yours or not row.crowded):
        return None
    angle = smallest_angle(
        min(row.gaps), row.line_height, row.clearance, start=angle_now or 0.0
    )
    if angle is None:
        # No angle clears. Upright gives the most room, and is worth it only
        # when it leaves neighbours overlapping less than they do flat (long
        # names, not a pair of short numbers on a squeezed axis).
        flat = max(
            (row.widths[i] + row.widths[i + 1]) / 2 - gap
            for i, gap in enumerate(row.gaps)
        )
        if row.line_height - min(row.gaps) >= flat:
            return None
        angle = 90.0
    if angle_now is not None and angle <= angle_now:
        return None
    # However long the turned labels, the check after the round decides:
    # a turn that leaves a plot under _MIN_PLOT_SHARE is taken back.
    return angle


def _set_turn_on(
    ax: Axes, angle: float, state: FitState, unwrapped: list[_Change]
) -> list[_Change]:
    """Turn the bottom labels of ``ax`` (only those: the top labels stay as
    they are), recording each label's state before; ``unwrapped`` (the
    group's wraps taken off for it) comes back with the turn."""
    axis = ax.xaxis
    key = id(axis)
    labels = [tick.label1 for tick in axis.get_major_ticks()]
    before = [(label, _turn_now(label), _TURNED.get(label)) for label in labels]
    axis_before = _TURNED_AXES.get(axis)
    angle_before = state.turned.get(key)
    for label, (rotation, mode), record in before:
        first = record or _Turned(angle, rotation, mode)
        _TURNED[label] = _Turned(angle, first.rotation, first.mode)
        _set_turn(label, angle, "xtick")
    _TURNED_AXES[axis] = _TURNED[labels[0]]
    state.turned[key] = angle

    def undo() -> None:
        for label, (rotation, mode), record in before:
            _set_turn(label, rotation, mode)
            if record is None:
                _TURNED.pop(label, None)
            else:
                _TURNED[label] = record
        if axis_before is None:
            _TURNED_AXES.pop(axis, None)
        else:
            _TURNED_AXES[axis] = axis_before
        if angle_before is None:
            state.turned.pop(key, None)
        else:
            state.turned[key] = angle_before
        _undo(unwrapped)

    return [_Change(("rotate", key), undo)]


def _wrap_lines(rows: Sequence[_Row]) -> dict[str, str] | None:
    """The wrapped text of each label that needs it, for every Axes of a
    shared axis at once; ``None`` when one cannot wrap.

    A label wraps to the tightest limit any Axes sets it (each one's
    neighbours and fair shares, :func:`wrap_limit`).
    """
    limits: dict[str, float] = {}
    for row in rows:
        for i, text in enumerate(row.texts):
            limit = wrap_limit(i, row.widths, row.gaps, row.clearance)
            limits[text] = min(limits.get(text, math.inf), limit)
    width = rows[0].width
    lines: dict[str, str] = {}
    for text, limit in limits.items():
        if width(text) <= limit:
            continue
        if not any(ch.isalpha() for ch in text):
            return None  # a number turns rather than breaks
        wrapped = wrap_to(text, limit, width, _MAX_TICK_LINES)
        if wrapped is None:
            return None
        lines[text] = wrapped
    return lines


def _set_wrap(
    axis: Axis,
    fmt: Formatter,
    wrapper: WrappedTickFormatter | None,
    lines: dict[str, str],
    state: FitState,
) -> list[_Change]:
    """Put ``lines`` on the (shared) formatter of ``axis`` (none: its own)."""
    if lines == (wrapper.lines if wrapper is not None else {}):
        return []
    key = id(axis)
    before = (fmt, axis.isDefault_majfmt, key in state.wrapped)
    if wrapper is not None:
        _unwrap(axis, wrapper)
        fmt = wrapper.base
    if lines:
        axis.set_major_formatter(
            WrappedTickFormatter(fmt, lines, axis.isDefault_majfmt)
        )
        state.wrapped.add(key)
    else:
        state.wrapped.discard(key)

    def undo() -> None:
        formatter, default, wrapped = before
        axis.set_major_formatter(formatter)
        axis.isDefault_majfmt = default
        if wrapped:
            state.wrapped.add(key)
        else:
            state.wrapped.discard(key)

    return [_Change(("wrap", key), undo)]


# ── ticks: an axis the climb shortened keeps the ticks it had ────────


def _ticks(locator: Locator, axis: Axis) -> np.ndarray:
    vmin, vmax = axis.get_view_interval()
    return np.asarray(locator.tick_values(vmin, vmax), dtype=float)


def _with_budget(auto: AutoLocator, nbins: int) -> AutoLocator:
    """``auto`` with room for ``nbins`` intervals, whatever the length."""
    kept = copy.copy(auto)
    kept.set_params(nbins=nbins)
    return kept


def _room(axis: Axis) -> int:
    """The intervals ``AutoLocator`` gives ``axis`` at its length now."""
    return int(np.clip(axis.get_tick_space(), 1, 9))


def _tick_budgets(axes: Sequence[Axes]) -> list[_Budget]:
    """The axes of ``axes`` whose ticks matplotlib picks by their length,
    with the intervals they have room for now, before the climb."""
    budgets: list[_Budget] = []
    seen: set[int] = set()
    for ax in axes:
        if not _cartesian(ax):
            continue
        for axis in (ax.xaxis, ax.yaxis):
            auto = axis.get_major_locator()
            if (
                id(auto) in seen
                or not isinstance(auto, AutoLocator)
                or not axis.isDefault_majloc
                or not isinstance(owner := auto.axis, Axis)
            ):
                continue
            seen.add(id(auto))
            nbins = _room(owner)
            if not np.array_equal(
                _ticks(_with_budget(auto, nbins), owner), _ticks(auto, owner)
            ):
                continue  # not picked by length (classic mode): nothing to keep
            budgets.append(_Budget(owner, auto, nbins))
    return budgets


def _keep_tick_budgets(axes: Sequence[Axes], state: FitState) -> list[_Change]:
    """Give an axis the climb shortened the intervals it had before.

    Matplotlib gives an axis as many intervals as fit its length, so a plot
    a rung made smaller can lose ticks it had room for: ``0 2 4 ... 10``
    becomes ``0.0 2.5 ... 10.0``, a value axis keeps two ticks. Such an
    axis keeps the ticks it had, unless another Axes it shares them with
    is not laid out. Like every change, it stays only if the check after
    the round finds no harm, and only if its labels stay ``_TARGET_EM``
    apart then (:func:`_labels_clear`). An axis the climb made longer (a
    plot an axis name had crushed) takes the ticks of its new length.
    """
    ids = {id(ax) for ax in axes}
    changes: list[_Change] = []
    for budget in state.budgets:
        axis = budget.axis
        key = ("ticks", id(axis))
        ax = axis.axes
        if (
            axis.get_major_locator() is not budget.auto
            or not state.allows(key)
            or _room(axis) >= budget.nbins
        ):
            continue
        is_x = axis is ax.xaxis
        shared = ax.get_shared_x_axes() if is_x else ax.get_shared_y_axes()
        siblings = shared.get_siblings(ax)
        if not _all_in(siblings, ids):
            continue
        kept = _with_budget(budget.auto, budget.nbins)
        if np.array_equal(_ticks(kept, axis), _ticks(budget.auto, axis)):
            continue  # the same ticks at this length
        changes.append(
            _set_budget(budget, kept, siblings, "x" if is_x else "y")
        )
    return changes


def _set_budget(
    budget: _Budget,
    kept: Locator,
    siblings: Sequence[Axes],
    which: Literal["x", "y"],
) -> _Change:
    axis = budget.axis
    axis.set_major_locator(kept)
    # Off its axis while it waits: the record then holds no figure.
    budget.auto.set_axis(None)
    _KEPT[kept] = _Kept(budget.auto, _locator_params(kept))

    def undo() -> None:
        _KEPT.pop(kept, None)
        _put_back_auto(axis, budget.auto)

    def clear(renderer: RendererBase) -> bool:
        return all(_labels_clear(ax, which, renderer) for ax in siblings)

    return _Change(("ticks", id(axis)), undo, clear)


def _labels_clear(
    ax: Axes, which: Literal["x", "y"], renderer: RendererBase
) -> bool:
    """Whether neighbouring drawn major tick labels of one axis of ``ax``
    stay ``_TARGET_EM`` apart on each side."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    first = {id(tick.label1) for tick in axis.get_major_ticks()}
    labels = [t for t in drawn_tick_labels(ax, which) if t.get_text().strip()]
    fig = ax.get_figure(root=True)
    if fig is None:
        return True
    for side in (True, False):
        group = [t for t in labels if (id(t) in first) is side]
        if len(group) < 2:
            continue
        boxes = sorted(
            (t.get_window_extent(renderer) for t in group),
            key=lambda box: box.x0 if which == "x" else box.y0,
        )
        need = _TARGET_EM * float(group[0].get_fontsize()) * fig.dpi / 72.0
        for a, b in pairwise(boxes):
            gap = b.x0 - a.x1 if which == "x" else b.y0 - a.y1
            if gap < need:
                return False
    return True


# ── pad ──────────────────────────────────────────────────────────────


def _pads_now(axis: Axis) -> tuple[float, float]:
    """The label pads (pt) of ``axis``' first major and first minor tick,
    which the ticks matplotlib adds later copy."""
    return (tick_pad(axis.majorTicks[0]), tick_pad(axis.minorTicks[0]))


def _set_pads(axis: Axis, major: float, minor: float) -> None:
    """Give every major and every minor tick of ``axis`` these pads (pt)."""
    for tick in axis.majorTicks:
        tick.set_pad(major)
    for tick in axis.minorTicks:
        tick.set_pad(minor)


def _pad_is_free(axis: Axis) -> bool:
    """Whether ``pad`` may grow ``axis``' label pad.

    Not when you set it: for the axis (``ax.tick_params(pad=...)``, which
    matplotlib keeps in ``get_tick_params`` for the ticks it adds), or for
    a tick of its own (``Tick.set_pad``: the ticks of a kind no longer
    share one pad), before a layout or after one. Within a layout, the pad
    this module grew stays its own while it is as set.
    """
    if any(
        "pad" in axis.get_tick_params(which=which)
        for which in ("major", "minor")
    ):
        return False
    pads = (
        {tick_pad(tick) for tick in axis.majorTicks},
        {tick_pad(tick) for tick in axis.minorTicks},
    )
    if any(len(kind) > 1 for kind in pads):
        return False
    padded = _PADS.get(axis)
    if padded is not None:
        return pads == ({padded.major_set}, {padded.minor_set})
    return True


def _restore_pads(axis: Axis, padded: _Padded) -> None:
    """Give back the pads ``pad`` grew on ``axis``, where they are as it set
    them: a pad set for the axis since (``tick_params(pad=...)``, even at
    the fitted value) stays for that kind of tick, and so does a tick whose
    pad was set by itself (``Tick.set_pad``); the others, the ticks
    matplotlib added since included (they copy the first tick), go back."""
    kinds: tuple[
        tuple[Literal["major", "minor"], list[Tick], float, float], ...
    ]
    kinds = (
        ("major", axis.majorTicks, padded.major, padded.major_set),
        ("minor", axis.minorTicks, padded.minor, padded.minor_set),
    )
    for which, ticks, before, mine in kinds:
        if "pad" in axis.get_tick_params(which=which):
            continue  # set for the axis since: yours
        for tick in ticks:
            if tick_pad(tick) == mine:
                tick.set_pad(before)


def _corner_moves(
    pairs: Sequence[CornerOverlap], dpi: float
) -> tuple[dict[Axis, float], dict[Axis, float]]:
    """How far (pt) the labels of each x axis, or of each y axis, move out
    to clear every pair: the overlap plus ``CORNER_GAP_EM`` of their size.
    """
    to_pt = 72.0 / dpi
    xs: dict[Axis, float] = {}
    ys: dict[Axis, float] = {}
    for pair in pairs:
        for moves, axis, depth, label in (
            (xs, pair.x_axes.xaxis, pair.down, pair.x_label),
            (ys, pair.y_axes.yaxis, pair.across, pair.y_label),
        ):
            need = depth * to_pt + CORNER_GAP_EM * float(label.get_fontsize())
            moves[axis] = max(moves.get(axis, 0.0), need)
    return xs, ys


def _fit_corners(
    fig: Figure, renderer: RendererBase, axes: Sequence[Axes], state: FitState
) -> list[_Change]:
    """Move the labels of one axis out where x and y labels of a plot box
    overlap: the x labels or the y labels, whichever move less."""
    changes: list[_Change] = []
    for group in _plot_boxes(axes):
        key: Key = ("pad", id(group[0]))
        if not state.allows(key):
            continue
        pairs = corner_tick_overlaps(group, renderer)
        if not pairs:
            continue
        options = [
            moves
            for moves in _corner_moves(pairs, fig.dpi)
            if all(_pad_is_free(axis) for axis in moves)
        ]
        if not options:
            continue  # both pads yours: the author's (TICK_CORNER_OVERLAP)
        moves = min(options, key=lambda option: max(option.values()))
        changes.append(_grow_pads(moves, group, key))
    return changes


def _plot_boxes(axes: Sequence[Axes]) -> list[list[Axes]]:
    """The fitted ``axes`` grouped by the box they are drawn in (an Axes and
    its twins), from where they were placed: the active position applies
    the aspect of a fixed-aspect Axes (``imshow``, ``set_aspect``) and would
    move it mid-layout, so a figure without a corner pair would not draw
    as before."""
    groups: dict[tuple[int, tuple[float, ...]], list[Axes]] = {}
    for ax in axes:
        if not _cartesian(ax):
            continue
        box = tuple(round(v, 9) for v in ax.get_position(original=True).bounds)
        parent = ax.get_figure(root=False)
        groups.setdefault((id(parent), box), []).append(ax)
    return list(groups.values())


def _grow_pads(
    moves: Mapping[Axis, float], group: Sequence[Axes], key: Key
) -> _Change:
    before = {axis: (_pads_now(axis), _PADS.get(axis)) for axis in moves}
    for axis, by in moves.items():
        (major, minor), padded = before[axis]
        _set_pads(axis, major + by, minor + by)
        _PADS[axis] = _Padded(
            padded.major if padded is not None else major,
            padded.minor if padded is not None else minor,
            major + by,
            minor + by,
        )

    def undo() -> None:
        for axis, ((major, minor), padded) in before.items():
            _set_pads(axis, major, minor)
            if padded is None:
                _PADS.pop(axis, None)
            else:
                _PADS[axis] = padded

    def clear(renderer: RendererBase) -> bool:
        return not corner_tick_overlaps(group, renderer)

    return _Change(key, undo, clear)
