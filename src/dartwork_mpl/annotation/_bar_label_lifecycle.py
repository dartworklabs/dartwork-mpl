"""The :func:`~._bar_labels.label_bars` calls an Axes records, and their life.

* **Record.** Each call is a :class:`~._bar_labels.BarLabelFamily` in the
  list ``ax._dm_bar_label_families`` (:func:`record`, :func:`families_of`).
* **Attach.** A label is added to its host Axes as ``ax.annotate`` adds an
  annotation, unclipped, anchored in its bars' data (:func:`attach`).
* **Prune.** A label gone from its Axes (``Artist.remove``, ``ax.cla()``) or
  whose bar is gone is dropped; a label left on a twin by its cleared bars
  is removed from it (:func:`prune`).
* **Release.** A later call on bars already labelled takes them over: their
  labels go, with the totals of every stack holding one of them
  (:func:`release`).
* **Re-host.** A label whose host is no longer the Axes drawn last in its
  bars' box (a twin made after the call, a zorder change) moves there as it
  is, explicit edits and all (:func:`rehost`).

What remains of a call keeps one decimal count (``BarLabelFamily.refresh``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from matplotlib.transforms import IdentityTransform

from ._bar_label_geometry import host_axes

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer

    from ._bar_labels import BarLabel, BarLabelFamily
    from ._bar_stacks import BarStack

__all__ = [
    "FAMILIES_ATTR",
    "attach",
    "families_of",
    "prune",
    "record",
    "rehost",
    "release",
]

# Where each Axes records its label_bars calls (a list of BarLabelFamily).
FAMILIES_ATTR = "_dm_bar_label_families"


def families_of(ax: Axes) -> list[BarLabelFamily]:
    """The :func:`label_bars` calls recorded on ``ax``, oldest first.

    The recorded list itself (edit it in place), or a new empty list when
    ``ax`` has none.
    """
    return getattr(ax, FAMILIES_ATTR, [])


def record(ax: Axes, family: BarLabelFamily) -> None:
    """Record ``family`` on ``ax``, after the calls already there."""
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


def _drop(family: BarLabelFamily, gone: Callable[[BarLabel], bool]) -> None:
    """Remove the labels ``gone`` picks from their Axes and ``family``."""
    kept = []
    for label in family.texts:
        if not gone(label):
            kept.append(label)
        elif label.axes is not None:
            label.remove()
    if len(kept) != len(family.texts):
        family.texts = kept
        if kept:
            family.refresh()  # one decimal count for what the call keeps


def prune(family: BarLabelFamily) -> bool:
    """Drop the labels of ``family`` no longer drawn; whether any remain.

    A label is gone when it left its Axes (``Artist.remove``, or
    ``ax.cla()`` on the Axes holding it) or its bar did (``ax.cla()`` on
    the bars' Axes, ``BarContainer.remove``); a label left behind on a twin
    by its cleared bars is removed from it.
    """
    _drop(family, lambda label: label.axes is None or label.bar.axes is None)
    return bool(family.texts)


def release(family: BarLabelFamily, containers: Iterable[BarContainer]) -> None:
    """Give the labels ``family`` holds on ``containers`` up to a later call.

    Their labels go, and so do the totals of every stack holding one of
    them (the later call labels that stack, or those bars, its own way).
    """
    taken = {id(c) for c in containers}
    if not taken.intersection(id(c) for c in family.containers):
        return

    def stacked_with_taken(stack: BarStack | None) -> bool:
        return stack is not None and any(
            id(c) in taken for c in stack.containers
        )

    _drop(
        family,
        lambda label: (
            id(label.container) in taken
            or (label.kind == "total" and stacked_with_taken(label.stack))
        ),
    )
    family.containers = [c for c in family.containers if id(c) not in taken]
    family.stacks = [s for s in family.stacks if not stacked_with_taken(s)]


def rehost(family: BarLabelFamily) -> None:
    """Move each label onto the Axes drawn last in its bars' box now.

    A twin made after the call (or a zorder change) changes that Axes; the
    label moves as it is, explicit edits and all (:func:`attach`).
    """
    for label in family.texts:
        host = host_axes(label.bar_axes)
        if label.axes is not host:
            attach(label, host)
