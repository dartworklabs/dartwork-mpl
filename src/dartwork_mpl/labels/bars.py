"""Value labels on bars: ``label_bars``.

A label prints its value like its axis's ticks and is rewritten at every
draw (a later ``set_ylim`` or formatter moves the unit); ``bar_layout``
settles the labels at the size ``dm.simple_layout`` fits.
"""

from __future__ import annotations

import logging
import weakref
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.text import Annotation, Text
from matplotlib.transforms import IdentityTransform

from ..edgecase import settle
from ..geometry import canvas_renderer
from ..vocab import AlignCentre, VCentre
from . import decide, edges
from .bar_geometry import Higher, Kind, Lower, Toward
from .given import PresetText, TickText
from .measure import bar_run, label_anchor, readable_ink, stands_up
from .model import Chosen, choose_bars
from .stacks import BarsFacts

if TYPE_CHECKING:
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.patches import Rectangle

    from ..vocab import TickScale

LOG = logging.getLogger("dartwork_mpl.labels")

# Between a bar end and its label, in points.
OFFSET_PT = 3.0


class BarLabel(Annotation):
    """One bar's value label, rewritten in its axis's tick unit at each draw.

    ``kind``: beyond the bar's end (a plain bar, a stack's net) or at the
    middle of a stack's segment, in white or the text colour, whichever
    reads on the bar.
    """

    def __init__(
        self,
        family: BarFamily,
        container: BarContainer,
        index: int,
        kind: Kind,
        value: float,
    ) -> None:
        """A label for bar ``index`` of ``container``, not yet added."""
        self.family = family
        self.container = container
        self.index = index
        self.bar = container.patches[index]
        bar_axes = self.bar.axes
        assert isinstance(bar_axes, Axes)  # label_bars labels drawn bars only
        self.bar_axes: Axes = bar_axes
        self.kind: Kind = kind
        self.value = value
        self.vertical = stands_up(container)
        self.hidden = False  # hidden by the layout for room
        self.turned = 0.0  # the rotation the layout last gave it
        self.tick_scale: TickScale | None = None
        self._measuring = False
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            "",
            (0.0, 0.0),
            xytext=(0.0, 0.0),
            xycoords=self.bar if kind.centred else "data",
            textcoords="offset points",
            annotation_clip=False,
            fontsize=family.preset.size(-1),
            fontweight=family.preset.weight(1),
        )
        if kind.centred:
            self.set_color(readable_ink(self.bar, bar_axes))

    @property
    def value_axis(self) -> Axis:
        """The axis the bar's value runs along."""
        return self.bar_axes.yaxis if self.vertical else self.bar_axes.xaxis

    @property
    def outward(self) -> Toward:
        """The way the bar grows on screen."""
        bar = self.bar
        length = bar.get_height() if self.vertical else bar.get_width()
        grows_up = (length >= 0) != bool(self.value_axis.get_inverted())
        return Higher() if grows_up else Lower()

    def arrange(self, angle: float, shown: bool) -> None:
        """Turn and show or hide the label for room, as the layout's own."""
        self.set_rotation(angle)
        self.turned = angle
        self.set_visible(shown)
        self.hidden = not shown

    @property
    def authored(self) -> bool:
        """The caller turned or hid it since the layout last arranged it:
        it stays as they left it."""
        turned = float(self.get_rotation()) != self.turned
        return turned or not (super().get_visible() or self.hidden)

    def get_visible(self) -> bool:
        """Visible and, a segment's label, held by its bar."""
        if not super().get_visible():
            return False
        if self._measuring or not self.kind.centred:
            return True
        self._measuring = True
        try:
            self.family.follow(self)
            return self._fits()
        finally:
            self._measuring = False

    def update_positions(self, renderer: RendererBase) -> None:
        """Follow the tick unit and the bar, then position as usual."""
        self.family.follow(self)
        super().update_positions(renderer)

    def _fits(self) -> bool:
        """Whether the bar is as long as the text along it."""
        fig = self.get_figure(root=True)
        renderer = canvas_renderer(fig) if fig is not None else None
        text = Text.get_window_extent(self, renderer)
        bar = self.bar.get_window_extent()
        along, length = (
            (text.height, bar.height)
            if self.vertical
            else (text.width, bar.width)
        )
        return bool(np.isfinite(length) and length >= along)

    def place(self) -> None:
        """Anchor and align the label on its bar."""
        if self.kind.centred:
            self.xy, self.xyann = (0.5, 0.5), (0.0, 0.0)
            self.set_horizontalalignment(AlignCentre.mpl)
            self.set_verticalalignment(VCentre.mpl)
            return
        toward = self.outward
        self.xy = label_anchor(self.container, self.index, self.vertical)
        if self.vertical:
            self.xyann = (0.0, toward.sign * OFFSET_PT)
            self.set_horizontalalignment(AlignCentre.mpl)
            self.set_verticalalignment(toward.va.mpl)
        else:
            self.xyann = (toward.sign * OFFSET_PT, 0.0)
            self.set_horizontalalignment(toward.ha.mpl)
            self.set_verticalalignment(VCentre.mpl)
        self.stale = True


@dataclass(eq=False)
class BarFamily:
    """One ``label_bars`` call: its labels and how they print."""

    preset: PresetText
    ticks: TickText
    texts: list[BarLabel] = field(default_factory=list)

    def refresh(self) -> None:
        """Every label's text in its axis's tick unit now, one decimal count
        for the call."""
        scales = [
            self.ticks.scale_of(t.value_axis, t.value) for t in self.texts
        ]
        scaled = [
            t.value / s.factor for t, s in zip(self.texts, scales, strict=True)
        ]
        count = self.ticks.decimals(scaled)
        for label, scale, value in zip(self.texts, scales, scaled, strict=True):
            label.tick_scale = scale
            label.set_text(
                self.ticks.number(
                    value,
                    count,
                    prefix=scale.prefix,
                    suffix=scale.suffix,
                    zero=scale.zero,
                )
            )

    def follow(self, label: BarLabel) -> None:
        """Follow the tick unit and the bar."""
        if (
            self.ticks.scale_of(label.value_axis, label.value)
            != label.tick_scale
        ):
            self.refresh()
        label.place()


def _chosen(ax: Axes, bars: object) -> tuple[Chosen[BarContainer], ...]:
    """The bars to label: ``bars=`` among the figure's, or all of ``ax``'s."""
    if bars is None:
        here = [c for c in ax.containers if isinstance(c, BarContainer)]
        if not here:
            raise ValueError(
                "ax has no bars to label: dm.label_bars labels what ax.bar / "
                "ax.barh / ax.hist drew on this Axes"
            )
        return choose_bars(here, here)
    fig = ax.get_figure(root=True)
    drawn = [
        c
        for a in (fig.axes if fig is not None else [ax])
        for c in a.containers
        if isinstance(c, BarContainer)
    ]
    return choose_bars(bars, drawn)


# The ``label_bars`` calls on each Axes, oldest first.
FAMILIES: weakref.WeakKeyDictionary[Axes, list[BarFamily]] = (
    weakref.WeakKeyDictionary()
)


def families_of(ax: Axes) -> list[BarFamily]:
    """The ``label_bars`` calls recorded on ``ax``, oldest first."""
    return FAMILIES.get(ax, [])


def format_ticks_now(axis: Axis) -> None:
    """Let ``axis``'s formatter decide now, as the next draw would."""
    axis.get_major_formatter().format_ticks(list(axis.get_majorticklocs()))


def label_bars(
    ax: Axes,
    bars: BarContainer
    | Iterable[BarContainer]
    | Iterable[Rectangle]
    | None = None,
    *,
    preset: PresetText,
    ticks: TickText,
) -> list[Text]:
    """``dm.label_bars``: text sized by ``preset``, values printed as ``ticks`` print them."""
    chosen = _chosen(ax, bars)
    containers = [c.bars for c in chosen]
    facts = BarsFacts(tuple(bar_run(c) for c in containers))
    plan = settle(
        facts, decide.plain_labels(facts), edges.BARS_EDGES, log=LOG
    ).plan
    family = BarFamily(preset, ticks)
    for p in plan.labels:
        if p.index not in chosen[p.run].indices:
            continue
        container = containers[p.run]
        if not isinstance(container.patches[p.index].axes, Axes):
            continue
        label = BarLabel(family, container, p.index, p.kind, p.value)
        label.set_transform(IdentityTransform())
        label.bar_axes.add_artist(label)
        label.set_clip_box(None)
        label.set_clip_path(None)
        family.texts.append(label)
    for axis in dict.fromkeys(t.value_axis for t in family.texts):
        format_ticks_now(axis)
    family.refresh()
    for label in family.texts:
        family.follow(label)
    FAMILIES.setdefault(ax, []).append(family)
    return list(family.texts)
