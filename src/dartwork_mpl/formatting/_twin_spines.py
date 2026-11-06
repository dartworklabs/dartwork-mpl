"""The right spine of a ``twinx`` member: the rule.

This docstring is the one statement of the rule; :func:`show_twin_spines`
and ``dm.simple_layout`` refer here. Design:
docs/development/twin-spine-at-layout.md (D7).

The presets hide the right spine, so the second y scale of a ``twinx`` pair
would have tick marks and labels but no axis line. ``dm.simple_layout``
(before the twin colours, which then colour the spine) shows that line:

* **Which Axes.** One that draws its own y scale on the right of a shared
  plot area: among the Axes drawn in the same box it shares x with a member
  and not y, its y axis is visible, and its y label sits on the right.
  ``ax.twinx()`` leaves its new Axes that way. These are the twin colours'
  "sides" (``_twin_colors``), read from public state: positions, the shared
  axes groupers and the label position, not from how the Axes was made. So a
  ``sharex`` overlay moved to the right counts, and a twin whose scale was
  moved to the left, or whose y axis is hidden, does not.
* **What.** ``spines["right"].set_visible(True)``. The line width, colour,
  position and bounds stay as they are; a spine is made with the preset's
  ``axes.linewidth`` already. Nothing else changes: ``twiny`` top spines,
  partners' spines and single Axes stay with the preset.
* **Once.** The layout settles an Axes' right spine the first time it finds
  the Axes drawing its scale there, shown or already showing, and never
  again. A spine hidden after that layout stays hidden. A spine hidden before
  the first layout cannot be told from the preset's hidden spine and shows;
  hide it after ``dm.simple_layout``, or give it ``linewidth=0``.
* **Only at the layout.** ``ax.twinx()`` itself is matplotlib's: a figure
  that is not laid out by ``dm.simple_layout`` (or whose call is refused,
  such as a figure without a GridSpec) keeps the preset's hidden spine.
"""

from __future__ import annotations

from matplotlib.figure import Figure

from ._twin_colors import _own_sides, _twin_groups

__all__ = ["show_twin_spines"]

# Set on an Axes once the layout settled its right spine (see "Once").
_SETTLED = "_dm_twin_spine_settled"


def show_twin_spines(fig: Figure) -> int:
    """Show the right spine of each Axes drawing a twin y scale on the right.

    The rule (which Axes, what changes, once per Axes) is stated in the
    docstring of the module ``dartwork_mpl.formatting._twin_spines``.
    ``dm.simple_layout`` calls this before the twin colours.

    Returns the number of spines this call showed. Safe to call again: an
    Axes it settled is not touched.
    """
    shown = 0
    for group in _twin_groups(fig):
        for ax in group:
            if getattr(ax, _SETTLED, False) or "right" not in _own_sides(
                ax, group
            ):
                continue
            spine = ax.spines["right"]
            if not spine.get_visible():
                spine.set_visible(True)
                shown += 1
            setattr(ax, _SETTLED, True)
    return shown
