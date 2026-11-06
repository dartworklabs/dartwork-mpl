"""Value labels on bars: :func:`label_bars`.

Downstream code hand-wrote these labels: ten font sizes, ``"bold"`` against
the ``dm.fw(1)`` rule, mixed greys, formats that repeat the axis unit
(``38 GWh`` above ``(GWh)``). One call settles each of these:

* **Look.** ``dm.fs(-1)``, ``dm.fw(1)``, the preset text colour, 3 pt from
  the bar end (as ``dm.annotate_value``).
* **Unit.** A label prints like its axis's ticks (:func:`tick_scale_of`):
  under ``dm.axis_unit`` the label names the unit, so labels are plain
  scaled numbers (``33.0`` under ``Energy (GWh)``); a formatter whose
  ticks carry a suffix gives the labels the same unit and suffix (``33G``
  under the library's default numbers or ``format_axis_si``, ``31%`` under
  a ``PercentFormatter``). The decision is re-read at every draw, so a
  later ``set_ylim``, ``dm.axis_unit`` or ``dm.simple_layout`` that moves
  the tick unit moves the labels with it.
* **Decimals.** Three significant digits on the largest ``|value|``, cut to
  the fewest decimals that print every value exactly, one count for the
  whole call (:func:`value_label_decimals`): ``21.4, 18.0, 21.5``;
  ``120, 135``; never a meaningless ``.0``. Zero prints ``0``; U+2212 minus
  like the ticks.
* **Side.** Outside the bar end; a negative bar's label below it (``barh``:
  left of it); an inverted value axis flips the side with the bar; error
  bars push the label past their caps, but not past the view.
* **Stacks.** Containers at the same positions, each starting where the
  ones before it ended, with two non-zero bars standing together somewhere
  (:mod:`._bar_stacks`), are a stack: each segment's label at its middle,
  shown while the segment is at least as long as the label, and the
  stack's net sum beyond the end the net points to. Floating bars (a
  waterfall), bars that never stand together (a two-colour waterfall, a
  highlight split in two) and grouped bars are no stack; a zero bar beside
  a non-zero one at its position pads it and gets no label.
* **Ink.** A label on its bar (a segment's, ``"inside"``, ``"center"``)
  takes white or the preset text colour, whichever reads better on the bar
  as drawn; a label off the bar keeps the text colour, or with
  ``color="series"`` its bar's colour, totals excepted
  (:mod:`._bar_label_ink`).
* **View.** A label shows while its bar's end (its middle for
  ``where="center"``) lies in the view, within one pixel: a bar ending on a
  limit keeps its label just outside the axes, a bar outside the view or
  running past a limit the caller set has none (nor any room in a
  ``bbox_inches="tight"`` save).
* **Twins.** On a ``twinx`` / ``twiny`` pair the labels go on the Axes drawn
  last (by zorder, then figure order), placed with the bars' own data
  transform, so no partner's line is drawn over them.
* **Explicit wins.** A label's text, placement, rotation, visibility and
  colour are rewritten only while they still hold what this module last
  wrote; a later ``Text.set_*`` on a returned label is kept through every
  draw and layout.
* **Calls.** A later call on bars already labelled replaces their earlier
  labels (and the totals of their stacks); the earlier call keeps the rest.

Each call is recorded on its Axes as a :class:`BarLabelFamily` in
``ax._dm_bar_label_families`` (the labels, the containers, the options, the
stacks) for the layout's later passes: crowding, headroom, dropping cleared
labels and moving labels onto a twin made later
(:mod:`._bar_label_settle`, run by ``dm.simple_layout``). The geometry
(anchor, side, view, room, host Axes) lives in :mod:`._bar_label_geometry`;
the keywords and the text they compose in :mod:`._bar_label_options`.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import matplotlib.colors as mcolors
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.text import Annotation, Text
from matplotlib.transforms import IdentityTransform

from .._figure_geometry import canvas_renderer, same_position_axes
from ..formatting import TickScale, tick_scale_of, value_label_decimals
from ..scale import fs, fw
from ._bar_label_geometry import (
    fits_on_bar,
    host_axes,
    in_view,
    place,
    text_length,
)
from ._bar_label_ink import label_ink
from ._bar_label_options import (
    BarLabelOptions,
    Crowded,
    Kind,
    Orientation,
    Placement,
    Total,
    Where,
    compose_text,
    parse_options,
)
from ._bar_stacks import BarStack, bar_values, pile_bars

if TYPE_CHECKING:
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.patches import Rectangle
    from matplotlib.typing import CoordsType

__all__ = [
    "FAMILIES_ATTR",
    "BarLabel",
    "BarLabelFamily",
    "BarLabelOptions",
    "attach",
    "families_of",
    "format_ticks_now",
    "label_bars",
]

# Where each Axes records its label_bars calls (a list of BarLabelFamily).
FAMILIES_ATTR = "_dm_bar_label_families"

_UNSET: Any = object()


# ------------------------------------------------------------ the labels
class BarLabel(Annotation):
    """One bar's value label: an ``Annotation`` that keeps reading like its axis.

    It belongs to its call's :class:`BarLabelFamily`. Each time matplotlib
    positions it (every draw, every extent measurement) the family re-reads
    the bar axis's tick unit and rewrites what it still owns.

    ``kind`` says what it labels: ``"edge"`` a plain bar, ``"segment"`` one
    bar of a :class:`BarStack` (``stack``), ``"total"`` that stack's net sum
    at position ``index``, anchored on the bar that ends the stack on the
    net's side (``bar``). ``asked`` is where the call put it on ``bar``;
    ``where`` is where it sits now (the layout's ``crowded="inside"`` may
    move an outside label into its bar). ``clear_of`` holds the other bars
    an outside label must clear (a crowded label wider than its own bar).
    """

    def __init__(
        self,
        bar_family: BarLabelFamily,
        container: BarContainer,
        index: int,
        value: float,
        *,
        bar_axes: Axes,
        xycoords: CoordsType,
        kind: Kind = "edge",
        where: Placement = "outside",
        stack: BarStack | None = None,
        **text_kw: Any,
    ) -> None:
        # Set first: get_visible (overridden below) reads them.
        self.bar_family = bar_family
        self.container = container
        self.index = index
        self.bar: Rectangle = container.patches[index]
        self.bar_axes = bar_axes
        self.value = value
        self.orientation: Orientation = (
            "horizontal"
            if container.orientation == "horizontal"
            else "vertical"
        )
        self.kind: Kind = kind
        self.asked: Placement = where
        self.where: Placement = where
        self.stack = stack
        self.clear_of: tuple[Rectangle, ...] = ()
        # The tick scale the text was last written in (None: not yet).
        self.tick_scale: TickScale | None = None
        # What this module last wrote to each property it owns.
        self._written: dict[str, object] = {}
        # True while get_visible measures the text (which asks it again).
        self._measuring = False
        # The last text measurement: (what decides it, pixels).
        self._text_px: tuple[tuple[object, ...], float] | None = None
        super().__init__(
            "",
            (0.0, 0.0),
            xytext=(0.0, 0.0),
            xycoords=xycoords,
            textcoords="offset points",
            annotation_clip=False,
            **text_kw,
        )
        # What the call wrote: a later change by anyone else is theirs.
        self.ink = mcolors.to_rgba(self.get_color())
        self._written.update(
            rotation=self.get_rotation(), visible=True, color=self.ink
        )

    @property
    def value_axis(self) -> Axis:
        """The axis that scales the bar's value (y for ``bar``, x for ``barh``)."""
        if self.orientation == "vertical":
            return self.bar_axes.yaxis
        return self.bar_axes.xaxis

    def own(
        self,
        name: str,
        current: object,
        wanted: object,
        write: Callable[[Any], object],
    ) -> None:
        """Write ``wanted`` unless ``name`` changed since this module wrote it.

        A property someone else set (``Text.set_*`` on a returned label) is
        theirs from then on.
        """
        last = self._written.get(name, _UNSET)
        if last is not _UNSET and current != last:
            return
        if current != wanted:
            write(wanted)
        self._written[name] = wanted

    def own_rotation(self, degrees: float) -> None:
        """:meth:`own` for the text's rotation."""
        self.own("rotation", self.get_rotation(), degrees, self.set_rotation)

    def own_visible(self, shown: bool) -> None:
        """:meth:`own` for the drawn flag (``Artist.set_visible``)."""
        self.own("visible", super().get_visible(), shown, self.set_visible)

    def own_color(self, color: object) -> None:
        """:meth:`own` for the colour, compared as RGBA."""
        rgba = mcolors.to_rgba(color)  # type: ignore[arg-type]
        current = mcolors.to_rgba(self.get_color())
        self.own("color", current, rgba, self.set_color)

    @property
    def must_fit(self) -> bool:
        """Whether the label sits on a stack segment and so must fit on it."""
        return self.kind == "segment" and self.where != "outside"

    def get_visible(self) -> bool:
        """Visible, the bar's anchor in the bar axes' view, and room for it.

        A bar outside the view (or past a limit the caller set) shows no
        label, nor does a stack segment shorter than its label along the
        value axis (:func:`fits_on_bar`). Both are measured at each call, so
        a wider view or a taller figure brings the label back. Matplotlib
        neither draws an invisible text nor counts it in a tight bbox
        (``Text.get_tightbbox`` is null), and the layout and the validation
        checks skip it.
        """
        if not (super().get_visible() and in_view(self, self.where)):
            return False
        if not self.must_fit or self._measuring:
            return True
        self._measuring = True
        try:
            # Measure the text this draw will write (the unit may move).
            self.bar_family.follow(self)
            return fits_on_bar(self, self.measured_length())
        finally:
            self._measuring = False

    def measured_length(self) -> float:
        """:func:`text_length`, measured again only when what decides it moved.

        A draw asks a label's visibility twice (``Annotation.draw``, then
        ``Text.draw``); the text, font, rotation and dpi rarely change
        between the two. The renderer is the canvas's at the current dpi, or
        (a vector canvas while saving) the one matplotlib's draw set.
        """
        figure = self.get_figure(root=True)
        renderer = canvas_renderer(figure) if figure is not None else None
        key = (
            self.get_text(),
            hash(self.get_fontproperties()),
            self.get_rotation(),
            self.get_linespacing(),
            self.get_usetex(),
            self.get_parse_math(),
            None if figure is None else figure.dpi,
            None if renderer is None else renderer.points_to_pixels(72.0),
        )
        if self._text_px is None or self._text_px[0] != key:
            self._text_px = (key, text_length(self, renderer))
        return self._text_px[1]

    def update_positions(self, renderer: RendererBase) -> None:
        """Follow the tick unit and the bar end, then position as usual."""
        self.bar_family.follow(self)
        super().update_positions(renderer)


@dataclass(eq=False)
class BarLabelFamily:
    """One :func:`label_bars` call: its labels, the bars and the options.

    ``stacks`` holds the stacks found among ``containers``; each segment
    and total label points to its own (``BarLabel.stack``).
    """

    ax: Axes
    containers: list[BarContainer]
    options: BarLabelOptions
    texts: list[BarLabel] = field(default_factory=list)
    stacks: list[BarStack] = field(default_factory=list)

    def refresh(self) -> None:
        """Write every label's text in its axis's current tick scale.

        One decimal count for the whole call, unless ``decimals=`` fixed it.
        A text someone else set is kept.
        """
        scales = [tick_scale_of(t.value_axis, t.value) for t in self.texts]
        scaled = [
            t.value / s.factor for t, s in zip(self.texts, scales, strict=True)
        ]
        decimals = self.options.decimals
        if decimals is None:
            decimals = value_label_decimals(scaled)
        for label, scale, value in zip(self.texts, scales, scaled, strict=True):
            label.tick_scale = scale
            text = compose_text(value, scale, decimals, self.options)
            label.own("text", label.get_text(), text, label.set_text)

    def follow(self, label: BarLabel) -> None:
        """Re-read the tick scale for ``label``; rewrite the call when it moved."""
        if tick_scale_of(label.value_axis, label.value) != label.tick_scale:
            self.refresh()
        place(label, label.where)

    def _drop(self, gone: Callable[[BarLabel], bool]) -> None:
        """Remove the labels ``gone`` picks from their Axes and the family."""
        kept = []
        for label in self.texts:
            if not gone(label):
                kept.append(label)
            elif label.axes is not None:
                label.remove()
        if len(kept) != len(self.texts):
            self.texts = kept
            if kept:
                self.refresh()  # one decimal count for what the call keeps

    def prune(self) -> bool:
        """Drop the labels no longer drawn; whether any remain.

        A label is gone when it left its Axes (``Artist.remove``, or
        ``ax.cla()`` on the Axes holding it) or its bar did (``ax.cla()`` on
        the bars' Axes, ``BarContainer.remove``); a label left behind on a
        twin by its cleared bars is removed from it.
        """
        self._drop(lambda label: label.axes is None or label.bar.axes is None)
        return bool(self.texts)

    def release(self, containers: Iterable[BarContainer]) -> None:
        """Give the labels of ``containers`` up to a later call.

        Their labels go, and so do the totals of every stack holding one of
        them (the later call labels that stack, or those bars, its own way).
        """
        taken = {id(c) for c in containers}
        if not taken.intersection(id(c) for c in self.containers):
            return

        def stacked_with_taken(stack: BarStack | None) -> bool:
            return stack is not None and any(
                id(c) in taken for c in stack.containers
            )

        self._drop(
            lambda label: (
                id(label.container) in taken
                or (label.kind == "total" and stacked_with_taken(label.stack))
            )
        )
        self.containers = [c for c in self.containers if id(c) not in taken]
        self.stacks = [s for s in self.stacks if not stacked_with_taken(s)]

    def rehost(self) -> None:
        """Move each label onto the Axes drawn last in its bars' box now.

        A twin made after the call (or a zorder change) changes that Axes;
        the label moves as it is, explicit edits and all (:func:`attach`).
        """
        for label in self.texts:
            host = host_axes(label.bar_axes)
            if label.axes is not host:
                attach(label, host)


def families_of(ax: Axes) -> list[BarLabelFamily]:
    """The :func:`label_bars` calls recorded on ``ax``, oldest first.

    The recorded list itself (edit it in place), or a new empty list when
    ``ax`` has none.
    """
    return getattr(ax, FAMILIES_ATTR, [])


def _record(ax: Axes, family: BarLabelFamily) -> None:
    families = getattr(ax, FAMILIES_ATTR, None)
    if families is None:
        families = []
        setattr(ax, FAMILIES_ATTR, families)
    families.append(family)


def attach(label: BarLabel, host: Axes) -> None:
    """Add ``label`` to ``host``, off any Axes it was on, unclipped.

    As ``ax.annotate`` does: the text is placed in display space, and
    nothing clips it (a label beyond the bar end may leave the axes).
    ``add_artist`` clips to the Axes patch, a rectangle that matplotlib
    stores as the clip box: both are cleared. An end label is anchored in
    the bars' data (``"data"`` on the bars' own Axes); a centred one on the
    bar itself.
    """
    if label.axes is not None:
        label.remove()
    if label.asked != "center":
        bar_axes = label.bar_axes
        label.xycoords = "data" if host is bar_axes else bar_axes.transData
    label.set_transform(IdentityTransform())
    host.add_artist(label)
    label.set_clip_box(None)
    label.set_clip_path(None)


# ------------------------------------------------------------ the call
def _containers(ax: Axes, bars: object) -> list[BarContainer]:
    if bars is None:
        found = [c for c in ax.containers if isinstance(c, BarContainer)]
        if not found:
            raise ValueError(
                "ax has no bars to label: dm.label_bars labels what "
                "ax.bar / ax.barh / ax.hist drew on this Axes (bars on a "
                "twin? pass that Axes)"
            )
        return found
    if isinstance(bars, BarContainer):
        return [bars]
    message = (
        "bars must be a BarContainer (what ax.bar / ax.barh return) or a "
        f"list of them (got {type(bars).__name__})"
    )
    if not isinstance(bars, Iterable):
        raise TypeError(message)
    items = list(bars)
    if not all(isinstance(item, BarContainer) for item in items):
        raise TypeError(message)
    return items


def _check_plot_area(ax: Axes, containers: list[BarContainer]) -> None:
    """Every container is drawn on ``ax`` or a twin of it (the same box)."""
    plot_area = same_position_axes(ax)
    for container in containers:
        for patch in container.patches:
            drawn_on = patch.axes
            if drawn_on is not None and drawn_on not in plot_area:
                raise ValueError(
                    f"bars must be drawn on {ax!r} or a twin of it (an Axes "
                    f"in the same box); these are on {drawn_on!r}: pass that "
                    "Axes as ax"
                )


def format_ticks_now(axis: Axis) -> None:
    """Let ``axis``'s formatter decide now, as the next draw would."""
    axis.get_major_formatter().format_ticks(list(axis.get_majorticklocs()))


def _placement(kind: Kind, where: Where) -> Placement:
    """Where a label of ``kind`` sits for the call's ``where``.

    ``"auto"`` puts a plain bar's label outside its end and a stack
    segment's at its middle; a total always sits beyond the stack's end.
    """
    if kind == "total":
        return "outside"
    match where:
        case "auto":
            return "center" if kind == "segment" else "outside"
        case "outside" | "inside" | "center":
            return where


def _add_label(
    family: BarLabelFamily,
    container: BarContainer,
    index: int,
    value: float,
    *,
    kind: Kind,
    stack: BarStack | None,
    fontsize: float | str,
) -> None:
    """Create the label of bar ``index`` of ``container`` and add it."""
    patch = container.patches[index]
    bar_axes = patch.axes
    if not isinstance(bar_axes, Axes):
        return
    where = _placement(kind, family.options.where)
    text_kw: dict[str, Any] = {"fontsize": fontsize, "fontweight": fw(1)}
    color = label_ink(family.options.color, kind, where, patch, bar_axes)
    if color is not None:
        text_kw["color"] = color
    label = BarLabel(
        family,
        container,
        index,
        value,
        bar_axes=bar_axes,
        # A centred label's frame is its bar; attach sets an end label's.
        xycoords=patch if where == "center" else "data",
        kind=kind,
        where=where,
        stack=stack,
        **text_kw,
    )
    attach(label, host_axes(bar_axes))
    family.texts.append(label)


def label_bars(
    ax: Axes,
    bars: BarContainer | Iterable[BarContainer] | None = None,
    *,
    where: Where = "auto",
    total: Total = "auto",
    crowded: Crowded = "rotate",
    decimals: int | None = None,
    fmt: str | Callable[[float], object] | None = None,
    size: float | str | None = None,
    color: Any = None,
) -> list[Text]:
    """Label each bar with its value, printed like the axis's ticks.

    One call for "put the values on the bars" / "막대에 값 표시", so every
    caller draws the same labels::

        ax.bar(months, energy_wh)
        dm.axis_unit(ax, "y", label="Energy ({unit}Wh)")
        dm.label_bars(ax)        # 21.4 … 33.0 above the bars
        dm.simple_layout(fig)

    Defaults (every one a keyword away):

    - ``dm.fs(-1)`` text, ``dm.fw(1)`` weight, the preset text colour, 3 pt
      beyond the bar end; negative bars below (``barh``: left);
    - the value in the axis's tick unit with no unit repeated under
      ``dm.axis_unit`` (``33.0`` under ``Energy (GWh)``), or the ticks'
      suffix when they carry one (``33G``, ``31%``); other formatters print
      the plain value (pass ``fmt=``). The unit is re-read at every draw,
      so later limit or formatter changes keep the labels in step;
    - three significant digits on the largest ``|value|``, then the fewest
      decimals that print every value exactly, one count for the call,
      totals included (``21.4, 18.0, 21.5``; ``120, 135``); zero prints
      ``0``; U+2212 minus;
    - stacked bars (containers at the same positions, each starting where
      the ones before it ended, as ``bottom=`` / ``left=`` build them;
      positives on the positive end, negatives on the negative end): each
      segment's label at its middle, hidden while the segment is shorter
      than the label (a taller figure brings it back), and the stack's net
      sum 3 pt beyond the end the net points to. A stack needs two
      non-zero bars standing together at some position: floating bars (a
      waterfall), bars that never stand together (a two-colour waterfall,
      a highlight split into grey and an accent) and grouped bars get
      plain labels, no totals, each value once (a zero bar beside a
      non-zero one is padding and gets no label);
    - a label on its bar (a segment's, ``"inside"``, ``"center"``) in white
      or the preset text colour, whichever reads better on the bar as drawn
      (``dm.readable_text_color``); labels off the bars, totals included,
      in the text colour;
    - on a ``twinx`` / ``twiny`` pair the labels are added to the Axes drawn
      last (by zorder, then figure order; placed with the bars' data), so
      the partner's line never covers them;
    - a label shows while its bar's end (its middle for ``"center"``) lies
      in the view, within one pixel: a bar ending on a limit you set keeps
      its label just outside the axes, a bar outside the view or running
      past such a limit has none. Error bars push a label at most to the
      edge of the view;
    - ``dm.simple_layout`` settles the labels at the size it fits: labels
      wider than the distance to the next bar less 1.5 pt follow
      ``crowded`` (below), and a value axis whose limits matplotlib
      autoscales grows just enough to keep the outside labels and 3 pt
      inside the axes. Limits you set stay: a label that does not fit sits
      outside the axes, and the layout keeps it inside the figure.

    Calling ``label_bars`` again on bars already labelled replaces the
    earlier labels of those bars (and the totals of their stacks). Labels
    made before a twin existed move onto it at the next
    ``dm.simple_layout``, as they are. A later ``Text.set_*`` on a returned
    label (text, colour, size, weight, alignment, rotation, visibility)
    wins over every redraw and ``dm.simple_layout``.

    Parameters
    ----------
    ax : Axes
        The Axes that drew the bars.
    bars : BarContainer or list of BarContainer, optional
        The bars to label (what ``ax.bar`` / ``ax.barh`` / ``ax.hist``
        return). ``None`` (default) labels every bar container on ``ax``.
    where : {"auto", "outside", "inside", "center"}
        Where each bar's label sits; a stack segment is a bar.
        ``"auto"`` (default): beyond a plain bar's end, at a segment's
        middle; ``"outside"``: beyond the end; ``"inside"``: just inside the
        end; ``"center"``: the bar's middle. Totals always sit beyond the
        stack's end.
    total : {"auto", "only", False}
        Stacked bars: segment labels plus a total (``"auto"``), the totals
        only, or the segments only. Bars in no stack are labelled alike.
    crowded : {"rotate", "skip", "inside"}
        What a call does when one of its labels is wider than the distance
        to the next bar less 1.5 pt (decided at each ``dm.simple_layout``):
        ``"rotate"`` (default) turns the labels of vertical bars vertical;
        ``"skip"`` hides every other label, keeping the last bar's (the
        top row's for ``barh``); ``"inside"`` puts plain bars' labels
        inside their ends (vertical text on vertical bars, readable ink),
        leaving a bar too short for its label with the label outside.
        ``barh`` never turns: rows thinner than the text hide every other
        label. Under any rule, labels that would still overlap are hidden
        the same way, and a kept label wider than its bar is lifted past
        the taller bars it spans.
    decimals : int, optional
        A fixed decimal count instead of the rule above.
    fmt : str or callable, optional
        A ``{}`` template around the number (``fmt="${}B"`` -> ``$38.5B``;
        the template supplies any unit, the tick suffix is not added;
        ``{:.2f}`` formats the scaled value itself), or a callable that gets
        the value in the axis's tick unit and returns the whole text. A
        template wraps the signed number, so ``"${}B"`` on -3.5 prints
        ``$-3.5B`` (the minus is U+2212); for ``-$3.5B`` use a callable.
    size : float or str, optional
        Font size; default ``dm.fs(-1)``.
    color : color, optional
        ``None`` (default) the inks above; ``"series"``: a label off its bar
        in the bar's colour as drawn, darkened to 4.5:1 against the
        background (``dm.ensure_contrast``), while a label on its bar keeps
        the readable ink and a total (of no single series) the text colour;
        any matplotlib colour, for every label.

    Returns
    -------
    list of Text
        The labels, container by container and bar by bar, then each
        stack's totals position by position; a bar whose value is NaN or
        infinite gets none. Each label's ``kind`` is ``"edge"``,
        ``"segment"`` or ``"total"``.

    Raises
    ------
    ValueError
        For an unknown ``where`` / ``total`` / ``crowded``, a negative
        ``decimals``, a ``fmt`` template without ``{}``, an invalid
        ``color``, ``bars=None`` on an Axes without bars, or bars drawn on
        an Axes other than ``ax`` and its twins.
    TypeError
        If ``bars`` is not a ``BarContainer`` or a list of them.
    """
    options = parse_options(
        where=where,
        total=total,
        crowded=crowded,
        decimals=decimals,
        fmt=fmt,
        size=size,
        color=color,
    )
    containers = _containers(ax, bars)
    _check_plot_area(ax, containers)
    for container in containers:
        if container.orientation not in ("vertical", "horizontal") or (
            container.datavalues is None
        ):
            raise ValueError(
                "bars must come from ax.bar / ax.barh / ax.hist: a "
                "BarContainer with an orientation and datavalues"
            )
    if not containers:
        return []
    # A later call on bars already labelled replaces the earlier labels.
    for member in same_position_axes(ax):
        families = families_of(member)
        for earlier in families:
            earlier.release(containers)
        families[:] = [f for f in families if f.texts]

    piles = pile_bars(containers)
    family = BarLabelFamily(ax, containers, options, stacks=piles.stacks)
    stack_of = {
        id(c): stack for stack in family.stacks for c in stack.containers
    }
    fontsize = fs(-1) if size is None else size
    for container in containers:
        stack = stack_of.get(id(container))
        if stack is not None and options.total == "only":
            continue
        # Masked values (np.ma) are missing values, like NaN: no label.
        values = bar_values(container)[: len(container.patches)]
        for index, value in enumerate(values):
            padding = (id(container), index) in piles.padding
            if math.isfinite(value) and not padding:
                _add_label(
                    family,
                    container,
                    index,
                    float(value),
                    kind="edge" if stack is None else "segment",
                    stack=stack,
                    fontsize=fontsize,
                )
    if options.total is not False:
        for stack in family.stacks:
            for index in range(len(stack.containers[0].patches)):
                found = stack.total(index)
                if found is None:  # no bar stands at this position
                    continue
                net, outer = found
                _add_label(
                    family,
                    outer,
                    index,
                    net,
                    kind="total",
                    stack=stack,
                    fontsize=fontsize,
                )

    for axis in dict.fromkeys(label.value_axis for label in family.texts):
        format_ticks_now(axis)
    family.refresh()
    for label in family.texts:
        place(label, label.where)

    _record(ax, family)
    return list(family.texts)
