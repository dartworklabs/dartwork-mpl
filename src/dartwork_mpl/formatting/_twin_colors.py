"""Series colours on ``twinx`` / ``twiny`` pairs.

A twin pair puts two scales around one plot area, and a reader matches each
scale to its series by colour. :func:`apply_twin_colors` (run by
``dm.simple_layout``) gives each side of a pair the colour of the one series
it scales: the spine and tick marks take the colour as it shows (alpha
composited over the background) raised to 3:1, and the tick labels, offset
text and axis label take the same hue darkened (lightened on a dark
background) to 4.5:1 with ``ensure_contrast``.

A *side* is a twin's own axis: the y axis of each ``twinx`` member (they share
x) and the x axis of each ``twiny`` member, found with matplotlib's public
shared-axes groupers among the Axes drawn in the same box. Its data are the
lines, patches and collections drawn in data coordinates; reference artists
in axes coordinates (``axhline``, ``axvspan``, ``axline``) are not a series.
A side qualifies when every data artist draws the same colour; a
colour-mapped collection or an image disqualifies it, and two sides drawing
the same colour both stay neutral because colour cannot tell them apart.

Single Axes are never touched. On a twin, a part (spine, tick marks, tick
labels, axis label) is painted only while its colour is the rcParams default
or the colour painted here last time, so a colour the user set wins whether
it came before or after a layout. Each painted part remembers the default it
replaced: a side that stops qualifying, or ``dm.config.twin_colors =
"neutral"``, gets that default back on the next call.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypeAlias

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.axes import Axes
from matplotlib.axis import Axis, Tick
from matplotlib.figure import Figure

from .._colors.contrast import ensure_contrast
from .._figure_geometry import same_position_axes
from ..config import config

__all__ = ["apply_twin_colors"]

Side: TypeAlias = Literal["left", "right", "bottom", "top"]
Part: TypeAlias = Literal["spine", "ticks", "ticklabels", "label"]
RGB: TypeAlias = tuple[float, float, float]
RGBA: TypeAlias = tuple[float, float, float, float]

# WCAG 2.x: 3:1 for graphical objects (spines, tick marks), 4.5:1 for text.
_LINE_RATIO = 3.0
_TEXT_RATIO = 4.5
# Up to one 8-bit channel step apart counts as the same colour.
_RGBA_TOL = 1.5 / 255
# Painted parts per Axes: (side, part) -> (default replaced, colour painted).
_RECORD = "_dm_twin_colors"
_NOTHING = frozenset({"None", "none", "", " "})

_Record: TypeAlias = dict[tuple[Side, Part], tuple[RGBA, RGBA]]


def _series_mode() -> bool:
    """Whether ``config.twin_colors`` asks for series colours.

    Raises
    ------
    ValueError
        Naming ``config.twin_colors`` unless it is ``"series"`` or
        ``"neutral"``.
    """
    mode = config.twin_colors
    if mode not in ("series", "neutral"):
        raise ValueError(
            f"config.twin_colors must be 'series' or 'neutral', got {mode!r}"
        )
    return mode == "series"


def _rgba(color: object) -> RGBA:
    r, g, b, a = mcolors.to_rgba(color)  # type: ignore[arg-type]
    return (float(r), float(g), float(b), float(a))


def _same(left: RGBA, right: RGBA) -> bool:
    return all(
        abs(a - b) <= _RGBA_TOL for a, b in zip(left, right, strict=True)
    )


def _over(top: RGBA, below: RGB) -> RGB:
    """``top`` composited over the opaque ``below``."""
    alpha = top[3]
    r, g, b = (
        alpha * t + (1.0 - alpha) * u
        for t, u in zip(top[:3], below, strict=True)
    )
    return (r, g, b)


def _key(color: RGBA) -> str:
    """The colour without its alpha: what makes two artists one series."""
    return mcolors.to_hex(color, keep_alpha=False)


# --------------------------------------------------------------- the pairs
def _rectilinear(ax: Axes) -> bool:
    return ax.get_visible() and ax.name == "rectilinear"


def _twin_groups(fig: Figure) -> list[list[Axes]]:
    """The Axes drawn in one box, two or more, in figure order."""
    groups: list[list[Axes]] = []
    seen: set[int] = set()
    for ax in fig.axes:
        if id(ax) in seen or not _rectilinear(ax):
            continue
        group = [m for m in same_position_axes(ax) if _rectilinear(m)]
        if len(group) < 2:
            continue
        seen.update(id(m) for m in group)
        groups.append(sorted(group, key=fig.axes.index))
    return groups


def _own_sides(ax: Axes, group: Sequence[Axes]) -> list[Side]:
    """Sides where ``ax`` draws a scale its partners do not share.

    A ``twinx`` member shares x with its partner and owns its y axis (left
    or right, wherever its label sits); a ``twiny`` member owns its x axis.
    """
    shared_x, shared_y = ax.get_shared_x_axes(), ax.get_shared_y_axes()
    others = [m for m in group if m is not ax]
    sides: list[Side] = []
    if ax.yaxis.get_visible() and any(
        shared_x.joined(ax, m) and not shared_y.joined(ax, m) for m in others
    ):
        # matplotlib types every axis's label position as top/bottom.
        right = str(ax.yaxis.get_label_position()) == "right"
        sides.append("right" if right else "left")
    if ax.xaxis.get_visible() and any(
        shared_y.joined(ax, m) and not shared_x.joined(ax, m) for m in others
    ):
        top = ax.xaxis.get_label_position() == "top"
        sides.append("top" if top else "bottom")
    return sides


# ------------------------------------------------------------ the series
def _drawn(face: RGBA, edge: RGBA, linewidth: float) -> RGBA | None:
    """The colour a patch shows: its face, else a drawn edge."""
    if face[3] > 0:
        return face
    if edge[3] > 0 and linewidth > 0:
        return edge
    return None


def _data_colors(ax: Axes) -> list[RGBA] | None:
    """Colours the data artists of ``ax`` draw; ``None`` when colour-mapped."""
    if any(image.get_visible() for image in ax.images):
        return None
    data = ax.transData
    colors: list[RGBA] = []
    for line in ax.lines:
        if not line.get_visible() or line.get_transform() is not data:
            continue
        if (
            str(line.get_linestyle()) in _NOTHING
            and str(line.get_marker()) in _NOTHING
        ):
            continue
        colors.append(
            _rgba(mcolors.to_rgba(line.get_color(), line.get_alpha()))
        )
    for patch in ax.patches:
        if not patch.get_visible() or patch.get_data_transform() is not data:
            continue
        drawn = _drawn(
            _rgba(patch.get_facecolor()),
            _rgba(patch.get_edgecolor()),
            float(patch.get_linewidth()),
        )
        if drawn is not None:
            colors.append(drawn)
    for collection in ax.collections:
        if not collection.get_visible() or (
            collection.get_transform() is not data
            and collection.get_offset_transform() is not data
        ):
            continue
        if collection.get_array() is not None:
            return None
        faces = mcolors.to_rgba_array(collection.get_facecolor())
        shown = faces[faces[:, 3] > 0]
        if not len(shown) and np.any(
            np.asarray(collection.get_linewidth(), dtype=float) > 0
        ):
            edges = mcolors.to_rgba_array(collection.get_edgecolor())
            shown = edges[edges[:, 3] > 0]
        colors.extend(_rgba(tuple(row)) for row in shown)
    return [color for color in colors if color[3] > 0]


def _series_color(ax: Axes) -> RGBA | None:
    """The one colour every data artist of ``ax`` draws, most opaque first."""
    colors = _data_colors(ax)
    if not colors or len({_key(color) for color in colors}) != 1:
        return None
    return max(colors, key=lambda color: color[3])


def _background(group: Sequence[Axes]) -> RGB:
    """What shows behind the pair's data: the figure, then visible patches."""
    below: RGB = (1.0, 1.0, 1.0)
    root = group[0].get_figure(root=True)
    parent = group[0].get_figure(root=False)
    for container in (root, parent if parent is not root else None):
        if container is not None and container.patch.get_visible():
            below = _over(_rgba(container.get_facecolor()), below)
    # Axes draw in zorder (stable on figure order), each patch over the last.
    for member in sorted(group, key=lambda m: m.get_zorder()):
        if member.get_frame_on() and member.patch.get_visible():
            below = _over(_rgba(member.get_facecolor()), below)
    return below


def _inks(color: RGBA, background: RGB) -> tuple[str, str]:
    """(spine and tick marks, text) for a series ``color`` on ``background``."""
    shown = mcolors.to_hex(_over(color, background))
    ground = mcolors.to_hex(background)
    return (
        ensure_contrast(shown, ground, min_ratio=_LINE_RATIO),
        ensure_contrast(shown, ground, min_ratio=_TEXT_RATIO),
    )


# ------------------------------------------------------------- the parts
def _axis(ax: Axes, side: Side) -> Axis:
    return ax.yaxis if side in ("left", "right") else ax.xaxis


def _ticks(axis: Axis) -> list[Tick]:
    """Every major and minor tick, at least one of each.

    ``get_major_ticks(1)`` builds a tick from the axis's stored tick
    parameters when none exists yet, so what ``tick_params`` set shows even
    on an axis without ticks in view.
    """
    major = axis.get_major_ticks() or axis.get_major_ticks(1)
    minor = axis.get_minor_ticks() or axis.get_minor_ticks(1)
    return [*major, *minor]


def _read(ax: Axes, side: Side, part: Part) -> list[RGBA]:
    """Every colour the part has now (one per tick for tick parts)."""
    if part == "spine":
        return [_rgba(ax.spines[side].get_edgecolor())]
    axis = _axis(ax, side)
    if part == "label":
        return [_rgba(axis.label.get_color())]
    first = side in ("left", "bottom")
    if part == "ticks":
        return [
            _rgba((t.tick1line if first else t.tick2line).get_markeredgecolor())
            for t in _ticks(axis)
        ]
    labels = [(t.label1 if first else t.label2) for t in _ticks(axis)]
    return [
        _rgba(text.get_color()) for text in (*labels, axis.get_offset_text())
    ]


def _rc_default(side: Side, part: Part) -> RGBA:
    """The colour matplotlib gives the part from the rcParams."""
    rc = mpl.rcParams
    if part == "spine":
        return _rgba(rc["axes.edgecolor"])
    if part == "label":
        return _rgba(rc["axes.labelcolor"])
    vertical = side in ("left", "right")
    tick = rc["ytick.color"] if vertical else rc["xtick.color"]
    if part == "ticks":
        return _rgba(tick)
    label = rc["ytick.labelcolor"] if vertical else rc["xtick.labelcolor"]
    return _rgba(tick if label == "inherit" else label)


def _write(ax: Axes, side: Side, part: Part, color: RGBA) -> None:
    if part == "spine":
        ax.spines[side].set_edgecolor(color)
        return
    axis = _axis(ax, side)
    if part == "label":
        axis.label.set_color(color)
    elif part == "ticks":
        axis.set_tick_params(which="both", color=color)
    else:  # tick labels; matplotlib gives the offset text the same colour
        axis.set_tick_params(which="both", labelcolor=color)


def _settle(ax: Axes, side: Side, part: Part, target: str | None) -> bool:
    """Paint one part ``target`` (``None``: its default back).

    Returns whether the part now shows ``target``. A part whose colour is
    neither its default nor the colour painted here last was set by someone
    else and is left as it is.
    """
    record: _Record = getattr(ax, _RECORD, {})
    key = (side, part)
    current = _read(ax, side, part)
    if key in record:
        default, painted = record[key]
        if not all(_same(c, painted) or _same(c, default) for c in current):
            del record[key]  # set by someone since: theirs now
            return False
    elif target is None:
        return False
    else:
        default = _rc_default(side, part)
        if not all(_same(c, default) for c in current):
            return False
    if target is None:
        _write(ax, side, part, default)
        del record[key]
        return False
    color = _rgba(target)
    _write(ax, side, part, color)
    record[key] = (default, color)
    setattr(ax, _RECORD, record)
    return True


def _settle_side(
    group: Sequence[Axes],
    owners: set[tuple[int, Side]],
    owner: Axes,
    side: Side,
    inks: tuple[str, str] | None,
    settled: set[tuple[int, Side, Part]],
) -> bool:
    """Settle one side's parts; True when any shows the series colour."""
    line, text = inks if inks is not None else (None, None)
    painted = _settle(owner, side, "spine", line)
    settled.add((id(owner), side, "spine"))
    # A partner's spine on this side draws in the same place (a twinx copy
    # of the left spine sits over its partner's), so it follows the owner's.
    for other in group:
        if (id(other), side) in owners or not other.spines[side].get_visible():
            continue
        _settle(other, side, "spine", line if painted else None)
        settled.add((id(other), side, "spine"))
    parts: tuple[tuple[Part, str | None], ...] = (
        ("ticks", line),
        ("ticklabels", text),
        ("label", text),
    )
    for part, target in parts:
        painted = _settle(owner, side, part, target) or painted
        settled.add((id(owner), side, part))
    return painted


def apply_twin_colors(fig: Figure) -> int:
    """Colour each side of a ``twinx`` / ``twiny`` pair like its series.

    A side whose data draw one colour gets it on its spine and tick marks as
    it shows (alpha composited, at least 3:1 against the background) and on
    its tick labels, offset text and axis label darkened to 4.5:1. A side
    drawing several colours, two sides drawing the same colour, single Axes
    and every part whose colour someone set stay as they are.
    ``dm.config.twin_colors = "neutral"`` gives painted parts their defaults
    back. ``dm.simple_layout`` calls this after the default tick formats.

    Returns the number of sides showing a series colour. Safe to call
    again: a repeat paints the same colours.

    Raises
    ------
    ValueError
        If ``dm.config.twin_colors`` is not ``"series"`` or ``"neutral"``.
    """
    series = _series_mode()
    coloured = 0
    settled: set[tuple[int, Side, Part]] = set()
    for group in _twin_groups(fig):
        sides = [(ax, side) for ax in group for side in _own_sides(ax, group)]
        owners = {(id(ax), side) for ax, side in sides}
        colors = {id(ax): _series_color(ax) if series else None for ax in group}
        # One colour on two owners: neither side can be told apart by it.
        holders: dict[str, set[int]] = {}
        for ax, _side in sides:
            color = colors[id(ax)]
            if color is not None:
                holders.setdefault(_key(color), set()).add(id(ax))
        background = _background(group)
        for ax, side in sides:
            color = colors[id(ax)]
            inks = None
            if color is not None and len(holders[_key(color)]) == 1:
                inks = _inks(color, background)
            coloured += _settle_side(group, owners, ax, side, inks, settled)
    # Parts painted on an earlier call whose pair is gone get their default.
    for ax in fig.axes:
        record: _Record = getattr(ax, _RECORD, {})
        for side, part in list(record):
            if (id(ax), side, part) not in settled:
                _settle(ax, side, part, None)
    return coloured
