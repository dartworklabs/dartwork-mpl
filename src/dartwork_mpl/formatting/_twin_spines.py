"""The right spine of a ``twinx`` member: the rule.

This docstring is the one statement of the rule; :func:`show_twin_spines`
and ``dm.simple_layout`` refer here. Design:
docs/development/twin-spine-at-layout.md (D7).

The presets hide the right spine, so the second y scale of a ``twinx`` pair
would have tick marks and labels but no axis line. ``dm.simple_layout``
shows that line:

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
* **The twin's line first.** Where an Axes with a hidden x axis draws its
  right spine, an Axes whose x axis shows draws none in the same place
  (``spine.get_position()``): a parent moved to the right under its twin
  keeps the preset's look, while twins of one parent all keep theirs.
* **What.** ``spines["right"].set_visible(True)``. The line width, colour,
  position and bounds stay as they are; a spine is made with the preset's
  ``axes.linewidth`` already. Nothing else changes: ``twiny`` top spines,
  partners' spines and single Axes stay with the preset.
* **Once.** The layout settles an Axes' right spine the first time it shows
  the line for it, shown or already showing, and never again. A spine
  hidden after that layout stays hidden. A spine hidden before the first
  layout cannot be told from the preset's hidden spine and shows; hide it
  after ``dm.simple_layout``, or give it ``linewidth=0``.
* **Only at the layout.** ``ax.twinx()`` itself is matplotlib's: a figure
  that is not laid out by ``dm.simple_layout`` (or whose call is refused,
  such as a figure without a GridSpec) keeps the preset's hidden spine.
"""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure

from .._figure_geometry import same_position_axes, with_insets
from ._twin_colors import _own_sides, _rectilinear

__all__ = ["show_twin_spines"]

# Set on an Axes once the layout settled its right spine (see "Once").
_SETTLED = "_dm_twin_spine_settled"


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


def _ticks_on_right(axis: Axis) -> bool:
    """Whether the y ticks show on the right and not on the left.

    The tick labels decide (``tick_params(right=False)`` leaves a scale of
    labels without marks); an axis showing no tick labels is read by its
    tick marks.
    """
    tick = (axis.get_major_ticks() or axis.get_major_ticks(1))[0]
    labels = (tick.label1.get_visible(), tick.label2.get_visible())
    marks = (tick.tick1line.get_visible(), tick.tick2line.get_visible())
    left, right = labels if any(labels) else marks
    return right and not left


def _draws_scale_on_right(ax: Axes, group: Sequence[Axes]) -> bool:
    """Whether ``ax`` draws its own y scale on the right of the box.

    ``_own_sides`` gives a y side when the y axis shows, x is shared with a
    member and y is not. Then the ticks and the label must both be on the
    right, or one of them when the x axis is hidden.
    """
    if not any(side in ("left", "right") for side in _own_sides(ax, group)):
        return False
    ticks = _ticks_on_right(ax.yaxis)
    label = str(ax.yaxis.get_label_position()) == "right"
    if ax.xaxis.get_visible():
        return ticks and label
    return ticks or label


def show_twin_spines(fig: Figure) -> int:
    """Show the right spine of each Axes drawing a twin y scale on the right.

    The rule (which Axes, the twin's line first, what changes, once per Axes)
    is stated in the docstring of the module
    ``dartwork_mpl.formatting._twin_spines``. ``dm.simple_layout`` calls
    this with the twin colours.

    Returns the number of spines this call showed. Safe to call again: an
    Axes it settled is not touched.
    """
    shown = 0
    for group in _boxes(fig):
        drawing = [ax for ax in group if _draws_scale_on_right(ax, group)]
        twin_places = {
            ax.spines["right"].get_position()
            for ax in drawing
            if not ax.xaxis.get_visible()
        }
        for ax in drawing:
            if getattr(ax, _SETTLED, False) or (
                ax.xaxis.get_visible()
                and ax.spines["right"].get_position() in twin_places
            ):
                continue
            spine = ax.spines["right"]
            if not spine.get_visible():
                spine.set_visible(True)
                shown += 1
            setattr(ax, _SETTLED, True)
    return shown
