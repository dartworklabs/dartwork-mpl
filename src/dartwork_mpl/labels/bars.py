"""Value labels on bars: ``label_bars``.

A label prints its value like its axis's ticks and is rewritten at every
draw (a later ``set_ylim`` or formatter moves the unit); ``bar_layout``
settles the labels at the size ``dm.simple_layout`` fits.
"""

from __future__ import annotations

import string
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.text import Annotation, Text
from matplotlib.transforms import IdentityTransform

from .._figure_geometry import canvas_renderer, host_axes, same_position_axes
from ..edgecase import settle
from ..style import fs, fw
from . import decide, edges
from .measure import (
    bar_end,
    bar_run,
    error_extent,
    px_per_pt,
    readable_ink,
    series_ink,
)
from .model import (
    BarOptions,
    Ink,
    InkFacts,
    Kind,
    Placement,
    ValueFacts,
    parse_bar_options,
    placement,
    template_fields,
)
from .stacks import BarsFacts

if TYPE_CHECKING:
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase

    from ..ticks import TickScale

# Between a bar end and its label, in points.
OFFSET_PT = 3.0
# How far (px) an anchor may sit past the view and still show.
EDGE_TOL_PX = 1.0
# How far (px) a label on its bar may reach past the bar's sides.
FIT_TOL_PX = 0.5
FAMILIES_ATTR = "_dm_bar_labels"


class BarLabel(Annotation):
    """One bar's value label, rewritten in its axis's tick unit at each draw.

    ``kind``: ``"edge"`` a plain bar, ``"segment"`` one bar of a stack,
    ``"total"`` the stack's net (on the bar ending the stack); ``stack``:
    the ids of its stack's containers. ``off_bar``: an ``"inside"`` label
    its bar does not hold, drawn beyond the end instead.
    """

    def __init__(
        self,
        family: BarFamily,
        container: BarContainer,
        index: int,
        kind: Kind,
        value: float,
        stack: frozenset[int],
    ) -> None:
        """A label for bar ``index`` of ``container``, not yet added."""
        self.family, self.container, self.index = family, container, index
        self.bar = container.patches[index]
        self.bar_axes: Axes = self.bar.axes  # type: ignore[assignment]
        self.kind: Kind = kind
        self.value, self.stack = value, stack
        self.where: Placement = placement(kind, family.options.where)
        self.vertical = container.orientation != "horizontal"
        self.off_bar = False
        self.hidden = False  # hidden by the layout for room
        self.tick_scale: TickScale | None = None
        self.inked_for: bool | None = None
        self.text_ink = mcolors.to_rgba(mpl.rcParams["text.color"])
        self._measuring = False
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            "",
            (0.0, 0.0),
            xytext=(0.0, 0.0),
            xycoords=self.bar if self.where == "center" else "data",
            textcoords="offset points",
            annotation_clip=False,
            fontsize=fs(-1),
            fontweight=fw(1),
        )

    @property
    def value_axis(self) -> Axis:
        """The axis the bar's value runs along."""
        return self.bar_axes.yaxis if self.vertical else self.bar_axes.xaxis

    @property
    def on_bar(self) -> bool:
        """Whether the label is drawn on its bar."""
        if self.where == "center":
            return True
        return self.where == "inside" and not self.off_bar

    @property
    def beyond_end(self) -> bool:
        """Beyond its own bar's end, in the room the value axis gives."""
        return self.where == "outside" or self.off_bar

    @property
    def outward(self) -> Literal[1, -1]:
        """+1 when the bar grows towards higher display coordinates."""
        bar = self.bar
        length = bar.get_height() if self.vertical else bar.get_width()
        sign = -1 if length < 0 else 1
        return -sign if self.value_axis.get_inverted() else sign  # type: ignore[return-value]

    def get_visible(self) -> bool:
        """Visible, its anchor in the view, and (a segment) room on its bar."""
        if not (super().get_visible() and self._in_view()):
            return False
        if self.kind != "segment" or self.where == "outside" or self._measuring:
            return True
        self._measuring = True
        try:
            self.family.follow(self)
            return self.fits(self.extent()[0], along=True)
        finally:
            self._measuring = False

    def update_positions(self, renderer: RendererBase) -> None:
        """Follow the tick unit and the bar, then position as usual."""
        self.family.follow(self)
        super().update_positions(renderer)

    def _in_view(self) -> bool:
        if self.where == "center":
            box = self.bar.get_window_extent()
            shown = np.array([(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2])
        else:
            shown = self.bar_axes.transData.transform(
                bar_end(self.bar, self.vertical)
            )
        box = self.bar_axes.get_window_extent()
        return bool(
            np.all(np.isfinite(shown))
            and box.x0 - EDGE_TOL_PX <= shown[0] <= box.x1 + EDGE_TOL_PX
            and box.y0 - EDGE_TOL_PX <= shown[1] <= box.y1 + EDGE_TOL_PX
        )

    def extent(self) -> tuple[float, float]:
        """The text's extent (along, across) its bar, display pixels."""
        fig = self.get_figure(root=True)
        renderer = canvas_renderer(fig) if fig is not None else None
        box = Text.get_window_extent(self, renderer)
        w, h = float(box.width), float(box.height)
        return (h, w) if self.vertical else (w, h)

    def fits(self, px: float, *, along: bool) -> bool:
        """Whether ``px`` of text fits along (plus the inset) or across."""
        box = self.bar.get_window_extent()
        if not along:
            thick = box.width if self.vertical else box.height
            return bool(np.isfinite(thick) and px <= thick + FIT_TOL_PX)
        inset = OFFSET_PT * px_per_pt(self) if self.where == "inside" else 0.0
        length = box.height if self.vertical else box.width
        return bool(np.isfinite(length) and length >= px + inset)

    def place(self) -> None:
        """Anchor and align the label on its bar."""
        if self.where == "center":
            self.xy, self.xyann = (0.5, 0.5), (0.0, 0.0)
            self.set_horizontalalignment("center")
            self.set_verticalalignment("center")
            return
        x, y = bar_end(self.bar, self.vertical)
        inside = self.where == "inside" and not self.off_bar
        extent = error_extent(self.container, self.index, self.vertical)
        if not inside and extent is not None:  # past the cap, in the view
            low, high = sorted(map(float, self.value_axis.get_view_interval()))
            end = y if self.vertical else x
            if self.value >= 0:
                end = max(end, min(float(extent.max()), high))
            else:
                end = min(end, max(float(extent.min()), low))
            x, y = (x, end) if self.vertical else (end, y)
        toward = self.outward * (-1 if inside else 1)
        self.xy = (x, y)
        if self.vertical:
            self.xyann = (0.0, toward * OFFSET_PT)
            self.set_horizontalalignment("center")
            self.set_verticalalignment("bottom" if toward > 0 else "top")
        else:
            self.xyann = (toward * OFFSET_PT, 0.0)
            self.set_horizontalalignment("left" if toward > 0 else "right")
            self.set_verticalalignment("center")
        self.stale = True


@dataclass(eq=False)
class BarFamily:
    """One ``label_bars`` call: its labels, its bars, its options."""

    containers: list[BarContainer]
    options: BarOptions
    texts: list[BarLabel] = field(default_factory=list)

    def refresh(self) -> None:
        """Every label's text in its axis's tick unit now, one decimal count
        for the call unless ``decimals=`` fixed it."""
        # The ticks' number rule, imported here: the formatting package
        # still closes an import cycle through the root package.
        from ..ticks import tick_scale_of, value_label_decimals

        scales = [tick_scale_of(t.value_axis, t.value) for t in self.texts]
        scaled = [
            t.value / s.factor for t, s in zip(self.texts, scales, strict=True)
        ]
        count = self.options.decimals
        if count is None:
            count = value_label_decimals(scaled)
        for label, scale, value in zip(self.texts, scales, scaled, strict=True):
            label.tick_scale = scale
            label.set_text(compose(value, scale, count, self.options))

    def follow(self, label: BarLabel) -> None:
        """Follow the tick unit, the bar's room and the ink for where it sits."""
        from ..ticks import tick_scale_of

        if tick_scale_of(label.value_axis, label.value) != label.tick_scale:
            self.refresh()
        label.off_bar = False
        if label.kind == "edge" and label.where == "inside":
            along, across = label.extent()
            label.off_bar = not (
                label.fits(along, along=True)
                and label.fits(across, along=False)
            )
        label.place()
        if label.on_bar == label.inked_for:
            return
        label.inked_for = label.on_bar
        bar, axes = label.bar, label.bar_axes
        series = self.options.series and not label.on_bar
        facts = InkFacts(
            self.options,
            label.kind,
            label.on_bar,
            readable_ink(bar, axes) if label.on_bar else Ink(),
            series_ink(bar, axes, label.kind) if series else Ink(),
        )
        color = settle(facts, decide.ink(facts), edges.INK).plan.color
        label.set_color(label.text_ink if color is None else color)  # type: ignore[arg-type]


def _template(fmt: str, number: str, value: float) -> str:
    """``fmt`` with each ``{}`` replaced by ``number``; a field with a
    format spec formats ``value`` itself, with matplotlib's minus."""
    f = string.Formatter()
    out: list[str] = []
    for literal, spec, conversion in template_fields(fmt):
        out.append(literal)
        if spec or conversion:
            text = f.format_field(
                f.convert_field(value, conversion or None), spec
            )
            if mpl.rcParams["axes.unicode_minus"]:
                text = text.replace("-", "\N{MINUS SIGN}")
            out.append(text)
        else:
            out.append(number)
    tail = list(f.parse(fmt))[-1]
    return "".join(out) + (tail[0] if tail[1] is None else "")


def compose(
    scaled: float, scale: TickScale, decimals: int, options: BarOptions
) -> str:
    """One label's text for a value already divided by ``scale.factor``."""
    from ..ticks import number_text

    if callable(options.fmt):
        return str(options.fmt(scaled))
    fixed = options.decimals is not None
    facts = ValueFacts(scaled, decimals, fixed, options.precise, options.sign)
    text = settle(facts, decide.bar_text(facts), edges.TEXT).plan
    bound = text.lead in ("<", ">")
    if isinstance(options.fmt, str):
        if bound:
            number = number_text(text.value, text.decimals)
            return text.lead + _template(options.fmt, number, text.value)
        number = text.lead + number_text(
            text.value, text.decimals, fixed=text.fixed
        )
        return _template(options.fmt, number, scaled)
    return text.lead + number_text(
        text.value,
        text.decimals,
        fixed=text.fixed,
        prefix=scale.prefix,
        suffix=scale.suffix,
        zero="bare" if bound else scale.zero,
    )


def _containers(ax: Axes, bars: object) -> list[BarContainer]:
    if bars is None:
        found = [c for c in ax.containers if isinstance(c, BarContainer)]
        if not found:
            raise ValueError(
                "ax has no bars to label: dm.label_bars labels what ax.bar / "
                "ax.barh / ax.hist drew on this Axes (bars on a twin? pass "
                "that Axes)"
            )
        return found
    if isinstance(bars, BarContainer):
        items: list[object] = [bars]
    elif isinstance(bars, Iterable):
        items = list(cast("Iterable[object]", bars))
    else:
        items = [bars]
    containers: list[BarContainer] = [
        c for c in items if isinstance(c, BarContainer)
    ]
    if len(containers) != len(items):
        raise TypeError(
            "bars must be a BarContainer (what ax.bar / ax.barh return) or a "
            f"list of them (got {type(cast(object, bars)).__name__})"
        )
    box = same_position_axes(ax)
    for container in containers:
        drawn = {p.axes for p in container.patches} - {None}
        if container.datavalues is None or not drawn <= set(box):
            raise ValueError(
                f"bars must come from ax.bar / ax.barh / ax.hist on {ax!r} or "
                "a twin of it: pass the Axes that drew them"
            )
    return containers


def families_of(ax: Axes) -> list[BarFamily]:
    """The ``label_bars`` calls recorded on ``ax``, oldest first."""
    return getattr(ax, FAMILIES_ATTR, [])


def format_ticks_now(axis: Axis) -> None:
    """Let ``axis``'s formatter decide now, as the next draw would."""
    axis.get_major_formatter().format_ticks(list(axis.get_majorticklocs()))


def _release(ax: Axes, containers: list[BarContainer]) -> None:
    """Earlier calls give up their labels on ``containers`` (and the totals
    of the stacks holding them)."""
    taken = {id(c) for c in containers}
    for member in same_position_axes(ax):
        families = families_of(member)
        for family in families:
            for label in list(family.texts):
                if id(label.container) in taken or (
                    label.kind == "total" and label.stack & taken
                ):
                    family.texts.remove(label)
                    if label.axes is not None:
                        label.remove()
        families[:] = [f for f in families if f.texts]


def _add(family: BarFamily, label: BarLabel) -> None:
    """Add ``label`` unclipped to the Axes drawn last in its bars' box."""
    host = host_axes(label.bar_axes)
    if label.where != "center":
        label.xycoords = (
            "data" if host is label.bar_axes else label.bar_axes.transData
        )
    label.set_transform(IdentityTransform())
    host.add_artist(label)
    label.set_clip_box(None)
    label.set_clip_path(None)
    family.texts.append(label)


def label_bars(
    ax: Axes,
    bars: BarContainer | Iterable[BarContainer] | None = None,
    *,
    where: str = "auto",
    total: str | Literal[False] = "auto",
    crowded: str = "rotate",
    decimals: int | None = None,
    fmt: str | Callable[[float], object] | None = None,
    color: Any = None,
    sign: str = "-",
) -> list[Text]:
    """Label each bar with its value, printed like the axis's ticks.

    One call for "put the values on the bars" / "막대에 값 표시"::

        ax.bar(months, energy_wh)
        dm.label_bars(ax)
        dm.simple_layout(fig)

    ``dm.fs(-1)``, ``dm.fw(1)``, the text colour, 3 pt beyond the bar end
    (negative bars below, ``barh`` left; past an error bar's cap); the value
    in the axis's tick unit (``33G``, ``31%``, ``$800``; plain under
    ``dm.axis_unit``), three significant digits on the largest value and
    the fewest decimals that print every value exactly (a non-zero value
    that rounds to zero prints its bound, ``<0.1M``). Stacked bars get each
    segment's value at its middle and the stack's net beyond its end; a
    label on its bar takes white or the text colour, whichever reads.
    ``dm.simple_layout`` turns crowded labels vertical (vertical bars),
    hides those that still meet from the last bar (and warns), and grows an
    autoscaled value axis to hold them. Calling this again on the same bars
    replaces their labels; restyle a label after ``dm.simple_layout``.

    ``where``: ``"auto"``, ``"outside"``, ``"inside"`` (while the bar holds
    the label), ``"center"``. ``total``: ``"auto"``, ``"only"``, ``False``.
    ``crowded``: ``"rotate"`` or ``"skip"`` (hide every other label).
    ``decimals``: a fixed count. ``fmt``: a ``{}`` template (``"${}B"``,
    ``"{:+.1f}%"``) or a callable of the value in the tick unit. ``color``:
    any colour, or ``"series"`` (labels off their bar in the bar's colour,
    made readable). ``sign="+"`` signs rises too (``+30``).
    """
    options = parse_bar_options(
        where=where,
        total=total,
        crowded=crowded,
        decimals=decimals,
        fmt=fmt,
        color=color,
        sign=sign,
        is_color=mcolors.is_color_like,
    )
    containers = _containers(ax, bars)
    if not containers:
        return []
    _release(ax, containers)
    facts = BarsFacts(tuple(bar_run(c) for c in containers), options.total)
    plan = settle(facts, decide.plain_labels(facts), edges.BARS).plan
    stacks: dict[int | None, frozenset[int]] = {}
    for p in plan.labels:
        stacks[p.stack] = stacks.get(p.stack, frozenset()) | {
            id(containers[p.run])
        }
    stacks[None] = frozenset()
    family = BarFamily(containers, options)
    for p in plan.labels:
        container = containers[p.run]
        if isinstance(container.patches[p.index].axes, Axes):
            label = BarLabel(
                family, container, p.index, p.kind, p.value, stacks[p.stack]
            )
            _add(family, label)
    for axis in dict.fromkeys(t.value_axis for t in family.texts):
        format_ticks_now(axis)
    family.refresh()
    for label in family.texts:
        family.follow(label)
    if not hasattr(ax, FAMILIES_ATTR):
        setattr(ax, FAMILIES_ATTR, [])
    families_of(ax).append(family)
    return list(family.texts)
