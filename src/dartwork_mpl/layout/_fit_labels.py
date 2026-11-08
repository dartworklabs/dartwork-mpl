"""Text that grew: the ladder ``simple_layout`` climbs when labels collide.

After the margins converge, ``simple_layout`` looks for text that collides
and takes the steps below, each only where text collides and only on what
nobody set by hand; whatever a round changed, the margins are fitted again
and the next round looks again (at most ``_FIT_ROUNDS`` rounds):

``axis_labels``
    An axis name longer than its side of the plot wraps at its spaces into
    as few lines as fit (at most ``_MAX_NAME_LINES``) when it would run
    into a neighbour (a panel beside an x name, above or below a y name)
    or past the figure (longer than the figure is wide / tall, where it
    pushes the margins until the plot collapses). A name that only hangs
    past its own plot, inside the figure, stays: wrapping a y name costs
    a line of width. So does a name whose lines would take more than
    ``_MAX_TEXT_SHARE`` of the figure across them (an x name's height, a y
    name's width): they would crush the plot. A bracketed unit stays whole,
    the lines are as even as the words allow, and nothing but an existing
    space becomes a break.
``space``
    The root GridSpec's ``wspace`` / ``hspace`` grow where the content of
    neighbouring panels (tick labels, axis names, titles, colorbars,
    outside legends) reaches into the other panel's: to the deepest reach
    plus ``_TARGET_EM`` (of the rc font size), never smaller than they are.
    A collision that would need more than ``_MAX_GAP_FRACTION`` of a cell is
    left as it is (narrower panels would not clear it) and reported as
    ``CROSS_AXES_OVERLAP``. Only spacing nobody passed:
    ``gridspec_kw={"hspace": ...}`` and ``fig.add_gridspec(hspace=...)``
    stay.
``wrap``
    Bottom tick labels that collide with a neighbour wrap at their spaces,
    each into the fewest lines (at most ``_MAX_TICK_LINES``) that keep it
    ``_TARGET_EM`` clear of both neighbours; a label beside short ones may
    use the room they leave (:func:`wrap_limit`). Only the labels that
    need it wrap.
``rotate``
    When a label cannot wrap narrow enough (no space to break at, a number,
    too long for three lines), the labels turn 30, 45 or 90 degrees in
    their original one-line form: the smallest angle at which neighbours
    clear (:func:`smallest_angle`), with matplotlib's ``"xtick"`` rotation
    mode, which puts each label's end at its tick. When no angle clears,
    90 degrees, but only if the labels then overlap less than flat (long
    names, not two short numbers on a squeezed axis). Not when the turned
    labels would take more than ``_MAX_TEXT_SHARE`` of the figure height:
    names that long belong on a horizontal bar chart, which is the
    author's choice, so they stay as they are and ``dm.validate_figure``
    reports ``TICK_OVERLAP``.

Nothing is shortened, hidden or made smaller. Text collides when it
overlaps by more than ``_TOUCH_PX`` (half a display pixel); text that only
comes close stays, so a figure without a collision draws exactly as it
would without this module. Within one call the ladder only climbs: a
rotation never turns back into a wrap and an angle never shrinks.

What you set wins and is left alone: tick labels you rotated, wrote with
line breaks or aligned other than centred, mathtext labels, axis names
with line breaks or mathtext, ``wspace`` / ``hspace`` you passed. What
this module set is recorded, and each ``simple_layout`` call first undoes
it where it is still as set (:func:`restore_fitted`), so a re-layout at
another size fits from the figure as you left it and ``fit_labels=False``
gives that figure back; a formatter, rotation, name or spacing changed
since is yours and stays. Polar, 3D and other non-rectilinear Axes are
not fitted, and nor are the labels of a vertical axis (crowded rows of a
horizontal bar chart need a taller canvas, which is the author's call).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

import matplotlib as mpl
from matplotlib.gridspec import GridSpec
from matplotlib.text import Text
from matplotlib.ticker import Formatter

from .._figure_geometry import drawn_tick_labels
from ._content_extent import _axes_content_extent_px

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties

#: Every step name ``fit_labels`` accepts; the default is all of them.
STEPS: tuple[str, ...] = ("axis_labels", "space", "wrap", "rotate")

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
# Most of the figure, across the text, that turned tick labels or a wrapped
# axis name may take.
_MAX_TEXT_SHARE = 0.35


def resolve_steps(fit_labels: bool | Iterable[str] | None) -> frozenset[str]:
    """The steps one ``simple_layout`` call may take.

    ``None`` reads :data:`dartwork_mpl.config.fit_labels`; ``True`` is every
    step, ``False`` none, a string or an iterable of strings names the
    steps. Unknown names raise ``ValueError``, any other value
    ``TypeError``.
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
    if not isinstance(fit_labels, Iterable):
        raise TypeError(
            "fit_labels must be True, False or step names; got "
            f"{type(fit_labels).__name__}"
        )
    chosen = frozenset(fit_labels)
    unknown = sorted(map(str, chosen - set(STEPS)))
    if unknown:
        raise ValueError(
            f"fit_labels: unknown step(s) {unknown}; known: {list(STEPS)}"
        )
    return chosen


# ─────────────────────────────────────────────────────────────────────
# What this module set, so the next call starts from the user's figure
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Turn:
    """A rotation this module set on an axis' tick labels."""

    angle: float
    mode_before: str


# axis -> the rotation this module set on its tick labels
_TURNED: WeakKeyDictionary[Axis, _Turn] = WeakKeyDictionary()
# axis label Text -> (text before wrapping, wrapped text)
_NAMES: WeakKeyDictionary[Text, tuple[str, str]] = WeakKeyDictionary()
# GridSpec -> {"wspace" / "hspace": the value this module set}
_GAPS: WeakKeyDictionary[GridSpec, dict[str, float]] = WeakKeyDictionary()


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


def restore_fitted(fig: Figure) -> None:
    """Undo what earlier layouts of ``fig`` fitted, where it is still as set.

    A formatter, rotation, axis name or spacing changed since (by you) is
    yours and stays; its record is dropped.
    """
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            fmt = axis.get_major_formatter()
            if isinstance(fmt, WrappedTickFormatter):
                _unwrap(axis, fmt)
            turn = _TURNED.pop(axis, None)
            if turn is not None and {
                (float(t.label1.get_rotation()), t.label1.get_rotation_mode())
                for t in axis.get_major_ticks()
            } == {(turn.angle, "xtick")}:
                axis.set_tick_params(
                    labelrotation=0, labelrotation_mode=turn.mode_before
                )
        for label in (ax.xaxis.label, ax.yaxis.label):
            record = _NAMES.pop(label, None)
            if record is not None and label.get_text() == record[1]:
                label.set_text(record[0])
    for gs in {g for ax in fig.axes if (g := _root_gridspec(ax)) is not None}:
        for key, value in _GAPS.pop(gs, {}).items():
            if getattr(gs, key) == value:
                gs.update(**{key: None})


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


# ─────────────────────────────────────────────────────────────────────
# One fitting round (measures on the last draw; the caller re-fits the
# margins after any change)
# ─────────────────────────────────────────────────────────────────────


@dataclass
class FitState:
    """What one ``simple_layout`` call has fitted so far (the ladder climbs)."""

    turned: dict[int, float] = field(default_factory=dict)  # id(axis) -> angle
    wrapped: set[int] = field(default_factory=set)  # id(axis)


def fit_round(
    fig: Figure,
    renderer: RendererBase,
    steps: frozenset[str],
    gs: GridSpec,
    state: FitState,
) -> bool:
    """Take every step that has a collision to fix now; return whether any did."""
    changed = False
    if "axis_labels" in steps:
        changed |= _fit_axis_names(fig, renderer)
    if "space" in steps:
        changed |= _fit_panel_gaps(fig, renderer, gs)
    if steps & {"wrap", "rotate"}:
        for ax in fig.axes:
            if _cartesian(ax):
                changed |= _fit_x_ticks(ax, renderer, steps, state)
    return changed


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


def _fit_axis_names(fig: Figure, renderer: RendererBase) -> bool:
    changed = False
    for ax in fig.axes:
        if not _cartesian(ax):
            continue
        frame = ax.get_window_extent(renderer)
        # along: the figure side the name runs along; across: the other
        for axis, span, beside, along, across in (
            (ax.xaxis, frame.width, "row", fig.bbox.width, fig.bbox.height),
            (ax.yaxis, frame.height, "col", fig.bbox.height, fig.bbox.width),
        ):
            label = axis.label
            text = label.get_text()
            if (
                span <= 0
                or not axis.get_visible()
                or not label.get_visible()
                or not text.strip()
                or "\n" in text
                or "$" in text
                or label in _NAMES
            ):
                continue
            width = _width_of(renderer, label.get_fontproperties())
            length = width(text)
            if length <= span:
                continue
            if length <= along and not _has_neighbour(ax, fig, beside):
                continue  # hangs past its plot, but nothing is in its way
            wrapped = wrap_to(text, span, width, _MAX_NAME_LINES)
            if wrapped is None:
                words = tokens(text)
                if len(words) < 2:
                    continue
                wrapped = "\n".join(
                    balanced_lines(words, _MAX_NAME_LINES, width)[0]
                )
            if _depth(label, wrapped, renderer, fig) > _MAX_TEXT_SHARE * across:
                continue  # the lines would crush the plot: left (reported)
            _NAMES[label] = (text, wrapped)
            label.set_text(wrapped)
            changed = True
    return changed


def _depth(
    label: Text, text: str, renderer: RendererBase, fig: Figure
) -> float:
    """How far ``text`` set like ``label`` reaches across its lines (px)."""
    probe = Text(0, 0, text)
    probe.update_from(label)
    probe.set_rotation(0)
    probe.set_figure(fig)
    return float(probe.get_window_extent(renderer).height)


def _has_neighbour(ax: Axes, fig: Figure, along: str) -> bool:
    """Whether another panel of ``ax``'s grid shares its row (``"row"``:
    one sits left or right of it) or its column (``"col"``: above or below)."""
    gs = _root_gridspec(ax)
    if gs is None:
        return False
    mine = ax.get_subplotspec().get_topmost_subplotspec()  # type: ignore[union-attr]
    for other in fig.axes:
        if (
            other is ax
            or not other.get_visible()
            or _root_gridspec(other) is not gs
        ):
            continue
        spec = other.get_subplotspec().get_topmost_subplotspec()  # type: ignore[union-attr]
        rows = set(spec.rowspan) & set(mine.rowspan)
        cols = set(spec.colspan) & set(mine.colspan)
        if (rows and not cols) if along == "row" else (cols and not rows):
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


def _fit_panel_gaps(fig: Figure, renderer: RendererBase, gs: GridSpec) -> bool:
    """Grow the ``wspace`` / ``hspace`` of ``gs`` where panel content meets."""
    nrows, ncols = gs.get_geometry()
    ours = _GAPS.get(gs, {})
    free = {
        key: n > 1
        and (getattr(gs, key) is None or ours.get(key) == getattr(gs, key))
        for key, n in (("wspace", ncols), ("hspace", nrows))
    }
    if not any(free.values()):
        return False
    bottoms, tops, lefts, rights = gs.get_grid_positions(fig)
    fw, fh = fig.bbox.width, fig.bbox.height
    across_cols: list[_Reach] = []
    across_rows: list[_Reach] = []
    for ax in fig.axes:
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
                back=lefts[cols.start] * fw - x0,
                ahead=x1 - rights[cols.stop - 1] * fw,
            )
        )
        across_rows.append(
            _Reach(
                rows,
                cols,
                back=y1 - tops[rows.start] * fh,
                ahead=bottoms[rows.stop - 1] * fh - y0,
            )
        )
    em = float(mpl.rcParams["font.size"]) * fig.dpi / 72.0
    params = gs.get_subplot_params(fig)
    changed = False
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
            continue  # parting them would take more: left as is, and reported
        if gap > getattr(params, key) + 1e-6:
            gs.update(**{key: gap})
            _GAPS.setdefault(gs, {})[key] = gap
            changed = True
    return changed


# ── wrap / rotate ────────────────────────────────────────────────────


def _fit_x_ticks(
    ax: Axes, renderer: RendererBase, steps: frozenset[str], state: FitState
) -> bool:
    """Wrap or turn the bottom tick labels of ``ax`` that collide."""
    axis = ax.xaxis
    key = id(axis)
    bottom = {id(t.label1) for t in axis.get_major_ticks()}
    labels = [
        t
        for t in drawn_tick_labels(ax, "x")
        if id(t) in bottom and t.get_text().strip()
    ]
    if len(labels) < 2:
        return False
    fmt = axis.get_major_formatter()
    wrapper = fmt if isinstance(fmt, WrappedTickFormatter) else None
    unwrap = {v: k for k, v in wrapper.lines.items()} if wrapper else {}
    texts = [unwrap.get(t.get_text(), t.get_text()) for t in labels]
    angle_now = state.turned.get(key)
    if angle_now is None and (
        {float(t.get_rotation()) for t in labels} != {0.0}
        or {t.get_horizontalalignment() for t in labels} != {"center"}
    ):
        return False  # your rotation or alignment
    if any("\n" in t or "$" in t for t in texts):
        return False  # your line breaks, or mathtext
    centres = [
        float(t.get_transform().transform(t.get_position())[0]) for t in labels
    ]
    order = sorted(range(len(labels)), key=centres.__getitem__)
    texts = [texts[i] for i in order]
    gaps = [centres[b] - centres[a] for a, b in pairwise(order)]
    if min(gaps) <= 0:
        return False
    fig = ax.get_figure(root=True)
    if fig is None:
        return False
    font = labels[0].get_fontproperties()
    width = _width_of(renderer, font)
    widths = [width(t) for t in texts]
    clearance = _TARGET_EM * float(labels[0].get_fontsize()) * fig.dpi / 72.0
    if angle_now is None:
        collide = any(
            (widths[i] + widths[i + 1]) / 2 - gap > _TOUCH_PX
            for i, gap in enumerate(gaps)
        )
        if wrapper is None and not collide:
            return False
        if "wrap" in steps:
            lines = _wrap_lines(texts, widths, gaps, width, clearance)
            if lines is not None:
                return _set_wrap(axis, fmt, wrapper, lines, state)
        if "rotate" not in steps:
            return False
    _w, line_h, _d = renderer.get_text_width_height_descent(
        "Ag", font, ismath=False
    )
    angle = smallest_angle(
        min(gaps), float(line_h), clearance, start=angle_now or 0.0
    )
    if angle is None:
        # No angle clears. Upright gives the most room, and is worth it only
        # when it leaves neighbours overlapping less than they do flat (long
        # names, not a pair of short numbers on a squeezed axis).
        flat = max(
            (widths[i] + widths[i + 1]) / 2 - gap for i, gap in enumerate(gaps)
        )
        if float(line_h) - min(gaps) >= flat:
            return False
        angle = 90.0
    if angle_now is not None and angle <= angle_now:
        return False
    turn = math.radians(angle)
    height = max(widths) * math.sin(turn) + float(line_h) * math.cos(turn)
    if height > _MAX_TEXT_SHARE * fig.bbox.height:
        return False  # too long to turn: left for the author (TICK_OVERLAP)
    if wrapper is not None:
        _unwrap(axis, wrapper)
        state.wrapped.discard(key)
    if axis not in _TURNED:
        mode = labels[0].get_rotation_mode()
        _TURNED[axis] = _Turn(angle, mode)
    else:
        _TURNED[axis] = _Turn(angle, _TURNED[axis].mode_before)
    ax.tick_params(axis="x", labelrotation=angle, labelrotation_mode="xtick")
    state.turned[key] = angle
    return True


def _wrap_lines(
    texts: Sequence[str],
    widths: Sequence[float],
    gaps: Sequence[float],
    width: Callable[[str], float],
    clearance: float,
) -> dict[str, str] | None:
    """The wrapped text of each label that needs it; ``None`` when one cannot wrap."""
    lines: dict[str, str] = {}
    for i, text in enumerate(texts):
        limit = wrap_limit(i, widths, gaps, clearance)
        if widths[i] <= limit:
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
) -> bool:
    """Put ``lines`` on the axis (none: its own formatter); whether that changed it."""
    if lines == (wrapper.lines if wrapper is not None else {}):
        return False
    if wrapper is not None:
        _unwrap(axis, wrapper)
        fmt = wrapper.base
    if lines:
        axis.set_major_formatter(
            WrappedTickFormatter(fmt, lines, axis.isDefault_majfmt)
        )
        state.wrapped.add(id(axis))
    else:
        state.wrapped.discard(id(axis))
    return True
