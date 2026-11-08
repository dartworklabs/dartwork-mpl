"""The twin scale line: a ``twinx`` member's right spine, a ``twiny``'s top.

This docstring is the one statement of the rule; :func:`show_twin_spines`
and ``dm.simple_layout`` refer here. Design:
docs/development/twin-spine-at-layout.md (D7).

The presets hide the right and the top spine, so the second y scale of a
``twinx`` pair (the second x scale of a ``twiny`` pair) would have tick
marks and labels but no axis line. ``dm.simple_layout`` shows that line.
The rule is written for the right spine; the top spine follows it with x
and y swapped (see "The top"):

* **Which Axes.** One that draws its own y scale on the right of a shared
  plot area: it is drawn in the same box as another visible rectilinear
  Axes (inset Axes count here, so an inset's ``twinx`` does too; the twin
  colours still leave inset pairs alone), it shares x with such a member
  and not y, its y axis is visible, and its scale sits on the right:
  - an Axes whose x axis shows needs both its y ticks and its y label on
    the right;
  - an Axes whose x axis is hidden shows nothing but its y scale
    (``ax.twinx()`` hides the twin's), so its y ticks or its y label on the
    right is enough.
  The ticks are on the right when the y tick labels show there and not on
  the left (``tick_params(right=False)`` keeps a scale of labels without
  marks); an axis without tick labels is read by its tick marks. All of it
  is public state (positions, the shared axes groupers, axis visibility,
  tick and label positions), not how the Axes was made. So a twin keeps
  its line when only its ticks or only its label moved left (``b.twinx()``
  of a twin moves ``b``'s ticks), and so does an overlay drawn like a twin
  (x axis hidden, ticks or label on the right). A ``sharex`` overlay whose
  ticks and label were moved to the right counts; a twin whose ticks and
  label both moved left, or whose y axis is hidden, does not.
* **The twin's line first.** When an Axes with a hidden x axis draws its
  right spine in a box, no Axes whose x axis shows draws one there,
  wherever its spine sits: a parent whose scale was moved to the right of
  its twin keeps the preset's look, also with
  ``spines["right"].set_position(("outward", 30))``, while twins of one
  parent all keep theirs.
* **The top.** The same two rules with x and y swapped: an Axes drawing its
  own x scale on the top of a shared plot area (same box, it shares y with
  a member and not x, its x axis is visible, its x ticks and x label are
  on the top, or one of them when its y axis is hidden as
  ``ax.twiny()`` hides the twin's) gets its top spine, and when an Axes
  with a hidden y axis draws its top spine in a box, no Axes whose y axis
  shows draws one there. The two sides are read apart: a parent with a
  ``twinx`` and a ``twiny`` gives the right line to the one and the top
  line to the other.
* **What.** ``spines["right"].set_visible(True)``, or ``spines["top"]``.
  The line width, colour, position and bounds stay as they are; a spine is
  made with the preset's ``axes.linewidth`` already. Nothing else changes:
  partners' spines and single Axes stay with the preset.
* **Once.** The layout settles each side of an Axes apart, the first time
  it shows that side's line for it, shown or already showing, and never
  again. A spine hidden after that layout stays hidden. A spine hidden
  before the first layout cannot be told from the preset's hidden spine
  and shows; hide it after ``dm.simple_layout``, or give it
  ``linewidth=0``. :func:`settled_twin_spines` reads the record back.
* **Only at the layout.** ``ax.twinx()`` and ``ax.twiny()`` themselves are
  matplotlib's: a figure that is not laid out by ``dm.simple_layout`` (or
  whose call is refused, such as a figure without a GridSpec) keeps the
  preset's hidden spine.

Four questions about Axes in one figure are kept apart, and each has its
own answer:

* **Shared axes** (``_figure_geometry.shared_axes``): which Axes read one
  scale, from ``sharex`` / ``sharey`` or a twin.
* **Same position** (``_figure_geometry.same_position_axes``): which Axes are
  drawn in one box, whatever they share.
* **Native twin**: which Axes matplotlib made with ``twinx`` / ``twiny``.
  Only its private ``_twinned_axes`` grouper knows; no library code reads
  it, and tests read it only as an independent control.
* **Twin role** (:func:`drawn_like_twin`): which Axes is drawn as a twin is,
  read from public state. ``PRESET_OVERRIDE`` skips such an Axes.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, NamedTuple, TypeAlias

from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure

from .._figure_geometry import same_position_axes, shared_axes, with_insets
from ._twin_colors import _own_sides, _rectilinear

__all__ = ["drawn_like_twin", "settled_twin_spines", "show_twin_spines"]

TwinSide: TypeAlias = Literal["right", "top"]
"""A side whose spine the layout shows for a twin scale."""


class _SideRule(NamedTuple):
    """How the rule reads one side."""

    scale: Literal["x", "y"]  # the axis whose scale sits on this side
    other: Literal["x", "y"]  # the axis a twin hides
    near: Literal["left", "bottom"]  # the opposite side
    record: str  # set on an Axes once its spine here is settled ("Once")


_RULES: dict[TwinSide, _SideRule] = {
    "right": _SideRule("y", "x", "left", "_dm_twin_spine_right_settled"),
    "top": _SideRule("x", "y", "bottom", "_dm_twin_spine_top_settled"),
}


def _axis(ax: Axes, name: Literal["x", "y"]) -> Axis:
    return ax.xaxis if name == "x" else ax.yaxis


def _boxes(fig: Figure) -> list[list[Axes]]:
    """Visible rectilinear Axes drawn in one box, two or more.

    The walk covers inset Axes too (:func:`with_insets`, depth first): an
    inset is not in ``fig.axes`` but its ``twinx`` is, so the inset finds
    its twin among the figure's Axes.
    """
    groups: list[list[Axes]] = []
    seen: set[int] = set()
    for ax in with_insets(fig.axes):
        if id(ax) in seen or not _rectilinear(ax):
            continue
        group = [m for m in same_position_axes(ax) if _rectilinear(m)]
        if len(group) < 2:
            continue
        seen.update(id(m) for m in group)
        groups.append(group)
    return groups


def _ticks_on_far_side(axis: Axis) -> bool:
    """Whether the ticks show on the right / top and not the left / bottom.

    The tick labels decide (``tick_params(right=False)`` leaves a scale of
    labels without marks); an axis showing no tick labels is read by its
    tick marks. ``label1`` and ``tick1line`` are the left / bottom ones.
    """
    tick = (axis.get_major_ticks() or axis.get_major_ticks(1))[0]
    labels = (tick.label1.get_visible(), tick.label2.get_visible())
    marks = (tick.tick1line.get_visible(), tick.tick2line.get_visible())
    near, far = labels if any(labels) else marks
    return far and not near


def _draws_scale_on(ax: Axes, group: Sequence[Axes], side: TwinSide) -> bool:
    """Whether ``ax`` draws its own scale on ``side`` of the box.

    ``_own_sides`` gives a side of the scale's axis when that axis shows,
    the other axis is shared with a member and this one is not. Then the
    ticks and the label must both be on ``side``, or one of them when the
    other axis is hidden.
    """
    rule = _RULES[side]
    if not any(own in (side, rule.near) for own in _own_sides(ax, group)):
        return False
    scale = _axis(ax, rule.scale)
    ticks = _ticks_on_far_side(scale)
    # matplotlib types every axis's label position as top/bottom.
    label = str(scale.get_label_position()) == side
    if _axis(ax, rule.other).get_visible():
        return ticks and label
    return ticks or label


def _selected(group: Sequence[Axes], side: TwinSide) -> list[Axes]:
    """The members of one box whose ``side`` spine the layout shows.

    The twin's line first: when a member whose other axis is hidden draws
    its scale there, no member whose other axis shows does.
    """
    other = _RULES[side].other
    drawing = [ax for ax in group if _draws_scale_on(ax, group, side)]
    twins = [ax for ax in drawing if not _axis(ax, other).get_visible()]
    return twins or drawing


def show_twin_spines(fig: Figure) -> int:
    """Show the right / top spine of each Axes drawing a twin scale there.

    The rule (which Axes, the twin's line first, the top, what changes,
    once per side) is stated in the docstring of the module
    ``dartwork_mpl.formatting._twin_spines``. ``dm.simple_layout`` calls
    this with the twin colours.

    Returns the number of spines this call showed. Safe to call again: a
    side it settled is not touched.
    """
    shown = 0
    for group in _boxes(fig):
        for side, rule in _RULES.items():
            for ax in _selected(group, side):
                if getattr(ax, rule.record, False):
                    continue
                spine = ax.spines[side]
                if not spine.get_visible():
                    spine.set_visible(True)
                    shown += 1
                setattr(ax, rule.record, True)
    return shown


def settled_twin_spines(ax: Axes) -> frozenset[TwinSide]:
    """The sides of ``ax`` whose spine ``dm.simple_layout`` settled.

    A side is settled when a layout selected ``ax`` for it and showed the
    spine or found it showing ("Once" in the module docstring). The record
    says nothing about the spine now: it may have been hidden since, and a
    later layout leaves it hidden.
    """
    return frozenset(
        side for side, rule in _RULES.items() if getattr(ax, rule.record, False)
    )


def drawn_like_twin(ax: Axes) -> bool:
    """Whether ``ax`` is drawn as a twin is: the twin role, public state.

    An earlier Axes drawn in the same box (visible and rectilinear; figure
    order with each Axes followed by its insets, so an inset comes before
    its ``twinx``) shares exactly one axis with ``ax``, x and not y or y
    and not x, and ``ax`` does not show that shared axis: the earlier Axes
    draws it. ``ax.twinx()`` hides the twin's x axis, ``ax.twiny()`` its y
    axis. An Axes with no such Axes before it in its box, a parent say,
    does not play the role.

    It is not the native twin (see the module docstring) and differs from
    it in two ways: a ``sharex`` overlay with its x axis hidden plays the
    role though ``twinx`` did not make it (decision 14 of the D7 review),
    and a twin whose x axis was shown again does not play it though
    ``twinx`` made it.
    """
    fig = ax.get_figure(root=True)
    if fig is None or not _rectilinear(ax):
        return False
    order = with_insets(fig.axes)
    if ax not in order:
        return False
    earlier = [
        m
        for m in order[: order.index(ax)]
        if _rectilinear(m) and ax in same_position_axes(m)
    ]
    shared_x, shared_y = shared_axes(ax, "x"), shared_axes(ax, "y")
    return any(
        (m in shared_x and m not in shared_y and not ax.xaxis.get_visible())
        or (m in shared_y and m not in shared_x and not ax.yaxis.get_visible())
        for m in earlier
    )
