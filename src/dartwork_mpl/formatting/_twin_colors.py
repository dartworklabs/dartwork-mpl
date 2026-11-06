"""Series colours on ``twinx`` / ``twiny`` pairs: the rules.

This docstring is the one statement of the rules; ``apply_twin_colors``,
``dm.config.twin_colors`` and ``dm.simple_layout`` refer here.

A twin pair puts two scales around one plot area, and a reader matches each
scale to its series by colour. :func:`apply_twin_colors` (run by
``dm.simple_layout`` after the default tick formats) colours each side of a
pair like the one series read on it:

* **Sides.** A side is a twin's own axis: the y axis of each ``twinx``
  member (left or right, wherever its label sits) and the x axis of each
  ``twiny`` member (bottom or top), among the Axes drawn in the same box,
  found with matplotlib's public shared-axes groupers. A side's scale is
  read by every member that shares that axis with its owner (a ``twiny`` of
  the parent reads the parent's y), so its *series* are the data of those
  members, and its *partners* are the data of the other members.
* **Data.** Lines, patches and collections drawn in data coordinates.
  Reference artists in axes coordinates (``axhline``, ``axvspan``,
  ``axline``) are not data. A line counts by what it draws: its line colour
  where a line shows and its markers' face and edge where markers show
  (``"none"`` and alpha 0 draw nothing, and a marker part that vanishes into
  the background, such as a white halo edge, is not series ink); colours of
  one hue (within 0.10 in OKLab) make one series colour, several hues
  several.
* **Qualifying.** A side is coloured when its series all draw one colour
  (a colour-mapped collection or an image is not one colour), its partners
  hold data (otherwise it is a second scale for the same series), and no
  partner colour lies within 0.10 of it in OKLab (Euclidean, alpha
  ignored), so the colour tells the side's series from every series read
  on the other scale. Each side decides on its own; a side that fails stays
  neutral.
* **Colours.** The spine and tick marks take the series colour as it shows
  (alpha composited over the figure and Axes backgrounds) raised to 3:1
  against that background; the tick labels, offset text and axis label
  take the same hue darkened (lightened on a dark background) to 4.5:1,
  both with ``ensure_contrast``. Another member's spine on the same side
  (a ``twinx`` draws its own copy of the left spine over its parent's)
  follows the owner's spine.
* **Explicit colours win.** Single Axes are never touched. A part (spine,
  tick marks, tick labels, axis label) is painted only while it shows the
  colour matplotlib gives it from the rcParams in force at the layout, and
  is repainted later only while it still shows the colour painted here. A
  colour set after a layout is kept, whatever it is. A colour set before the
  first layout, or after ``ax.cla()``, that equals the default (``"black"``
  under the light presets) cannot be told from the default and is painted;
  use
  ``dm.config.twin_colors = "neutral"`` to keep such a figure neutral. A
  figure built under one preset and laid out under another sees its parts
  as set by hand and stays neutral (the safe side).
* **Undoing.** A painted part remembers the default it replaced: a side
  that stops qualifying, a pair that is gone, or ``dm.config.twin_colors =
  "neutral"`` gets that default back at the next call. A part that
  ``Axes.clear()`` reset to its default, wholly or partly, starts over as
  unpainted.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import combinations
from typing import Literal, TypeAlias

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.axes import Axes
from matplotlib.axis import Axis, Tick
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.typing import ColorType

from .._colors.contrast import composite_layers, composite_over, ensure_contrast
from .._colors.model import srgb_to_oklab
from .._figure_geometry import backdrop_layers, same_position_axes, shared_axes
from ..config import config

__all__ = ["apply_twin_colors"]

Side: TypeAlias = Literal["left", "right", "bottom", "top"]
Part: TypeAlias = Literal["spine", "ticks", "ticklabels", "label"]
RGB: TypeAlias = tuple[float, float, float]
RGBA: TypeAlias = tuple[float, float, float, float]

# WCAG 2.x: 3:1 for graphical objects (spines, tick marks), 4.5:1 for text.
_LINE_RATIO = 3.0
_TEXT_RATIO = 4.5
# Series colours closer than this in OKLab cannot tell two scales apart.
_SAME_HUE_OKLAB = 0.10
# Up to one 8-bit channel step apart counts as the same colour.
_RGBA_TOL = 1.5 / 255
# Parts per Axes: (side, part) -> (default replaced, colour painted), or
# None for a part someone recoloured after it was painted (theirs for good).
_RECORD = "_dm_twin_colors"
# The Axes background patch when the record was last written: Axes.clear()
# makes a new one, so a different patch means the Axes was cleared since.
_RECORD_PATCH = "_dm_twin_colors_patch"
_NOTHING = frozenset({"None", "none", "", " "})

_Record: TypeAlias = dict[tuple[Side, Part], tuple[RGBA, RGBA] | None]


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


def _reads_on(owner: Axes, side: Side, member: Axes) -> bool:
    """Whether ``member``'s data are read on ``owner``'s ``side`` scale."""
    if side in ("left", "right"):
        return member in shared_axes(owner, "y")
    return member in shared_axes(owner, "x")


def _own_sides(ax: Axes, group: Sequence[Axes]) -> list[Side]:
    """Sides where ``ax`` draws a scale its partners do not share.

    A ``twinx`` member shares x with its partner and owns its y axis (left
    or right, wherever its label sits); a ``twiny`` member owns its x axis.
    """
    shared_x, shared_y = shared_axes(ax, "x"), shared_axes(ax, "y")
    others = [m for m in group if m is not ax]
    sides: list[Side] = []
    if ax.yaxis.get_visible() and any(
        m in shared_x and m not in shared_y for m in others
    ):
        # matplotlib types every axis's label position as top/bottom.
        right = str(ax.yaxis.get_label_position()) == "right"
        sides.append("right" if right else "left")
    if ax.xaxis.get_visible() and any(
        m in shared_y and m not in shared_x for m in others
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


def _line_shows(line: Line2D) -> tuple[list[RGBA], list[RGBA]]:
    """The colours ``line`` draws: its line, and its marker face(s) and edge.

    The line colour counts where a line is drawn (a line style and a width
    above 0), the marker colours where markers are (a marker and a size
    above 0): the face of a filled marker (both halves of a half-filled
    one) and the edge when its width is above 0. ``"none"`` and alpha 0
    draw nothing. The line's alpha applies to every part, as it draws.
    Returns the line's colours and the markers' apart.
    """
    stroke: list[ColorType] = []
    shown: list[ColorType] = []
    if (
        str(line.get_linestyle()) not in _NOTHING
        and float(line.get_linewidth()) > 0
    ):
        stroke.append(line.get_color())
    if (
        str(line.get_marker()) not in _NOTHING
        and float(line.get_markersize()) > 0
    ):
        marker = MarkerStyle(line.get_marker(), line.get_fillstyle())
        if marker.is_filled():
            shown.append(line.get_markerfacecolor())
            if marker.get_alt_path() is not None:
                shown.append(line.get_markerfacecoloralt())
        if float(line.get_markeredgewidth()) > 0:
            shown.append(line.get_markeredgecolor())
    alpha = line.get_alpha()

    def drawn(parts: list[ColorType]) -> list[RGBA]:
        colors = [_rgba(mcolors.to_rgba(c, alpha)) for c in parts]
        return [color for color in colors if color[3] > 0]

    return drawn(stroke), drawn(shown)


def _line_colors(line: Line2D, background: RGB) -> list[RGBA]:
    """``line``'s series colour, or all it shows when that is several hues.

    A marker part that vanishes into the background where it is drawn (a
    white halo edge, a white face on a white Axes: within 0.10 of it in
    OKLab once composited) is not series ink and does not count. Colours
    within 0.10 of each other in OKLab, pair by pair, are one hue (the
    partner test's tolerance): the line counts as its most opaque one, the
    line colour first. Otherwise every colour counts, so the line's side has
    no one colour and the line's hues stand against the other scale.
    """
    stroke, marks = _line_shows(line)
    ground: RGBA = (*background, 1.0)
    colors = stroke + [
        mark
        for mark in marks
        if not _near((*composite_over(mark, background), 1.0), ground)
    ]
    if all(_near(a, b) for a, b in combinations(colors, 2)):
        return [max(colors, key=lambda color: color[3])] if colors else []
    return colors


def _data_colors(ax: Axes, background: RGB) -> list[RGBA] | None:
    """Colours the data artists of ``ax`` draw; ``None`` when colour-mapped."""
    if any(image.get_visible() for image in ax.images):
        return None
    data = ax.transData
    colors: list[RGBA] = []
    for line in ax.lines:
        if not line.get_visible() or line.get_transform() is not data:
            continue
        colors.extend(_line_colors(line, background))
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


def _merged(found: Sequence[list[RGBA] | None]) -> list[RGBA] | None:
    """The colours several Axes draw; ``None`` when any is colour-mapped."""
    colors: list[RGBA] = []
    for one in found:
        if one is None:
            return None
        colors.extend(one)
    return colors


def _series_color(colors: list[RGBA] | None) -> RGBA | None:
    """The one colour every data artist draws (``colors``), most opaque."""
    if not colors or len({_key(color) for color in colors}) != 1:
        return None
    return max(colors, key=lambda color: color[3])


def _near(left: RGBA, right: RGBA) -> bool:
    """Whether two series colours (alpha ignored) read as one hue."""
    distance = math.dist(srgb_to_oklab(left[:3]), srgb_to_oklab(right[:3]))
    return distance < _SAME_HUE_OKLAB


def _background(group: Sequence[Axes]) -> RGB:
    """What shows behind the pair's data: the figure, then visible patches."""
    return composite_layers(backdrop_layers(group))


def _inks(color: RGBA, background: RGB) -> tuple[str, str]:
    """(spine and tick marks, text) for a series ``color`` on ``background``."""
    shown = mcolors.to_hex(composite_over(color, background))
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

    Returns whether the part now shows ``target``. An unpainted part that
    does not show its rcParams default, or a painted part that no longer
    shows the colour painted here, was set by someone else and is left as
    it is, the latter for good.
    """
    record: _Record = getattr(ax, _RECORD, {})
    key = (side, part)
    current = _read(ax, side, part)
    if key in record:
        entry = record[key]
        if entry is None:
            return False
        default, painted = entry
        if not all(_same(c, painted) for c in current):
            record[key] = None  # set by someone since, even to the default
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


def _forget_cleared(fig: Figure) -> None:
    """Start over on parts that ``Axes.clear()`` reset, wholly or partly.

    Clearing an Axes puts some parts back to the rcParams colour (the axis
    label, the offset text among the tick labels) and keeps others. That is
    matplotlib's doing, not a user's choice: a part showing only its default
    and the colour painted here goes back to its default, unpainted.
    """
    for ax in fig.axes:
        record: _Record = getattr(ax, _RECORD, {})
        if not record or getattr(ax, _RECORD_PATCH, None) is ax.patch:
            continue
        for (side, part), entry in list(record.items()):
            default = _rc_default(side, part)
            current = _read(ax, side, part)
            reset = [_same(c, default) for c in current]
            if all(reset):
                del record[(side, part)]
            elif (
                entry is not None
                and any(reset)
                and all(
                    was or _same(c, entry[1])
                    for was, c in zip(reset, current, strict=True)
                )
            ):
                _write(ax, side, part, default)
                del record[(side, part)]


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


def _side_inks(
    owner: Axes,
    side: Side,
    group: Sequence[Axes],
    drawn: dict[int, list[RGBA] | None],
    background: RGB,
) -> tuple[str, str] | None:
    """(line, text) colours for one side, or ``None`` when it stays neutral.

    The side's series are the data of the members reading its scale, its
    partners the data of the others (module docstring, "Qualifying").
    """
    reading = [_reads_on(owner, side, m) for m in group]
    color = _series_color(
        _merged(
            [drawn[id(m)] for m, on in zip(group, reading, strict=True) if on]
        )
    )
    if color is None:
        return None
    partners = [
        drawn[id(m)] for m, on in zip(group, reading, strict=True) if not on
    ]
    # Colour-mapped data (None) is data too; only an empty list is not.
    if not any(found is None or found for found in partners):
        return None  # a second scale for the same series
    others = {_key(c): c for found in partners if found for c in found}
    if any(_near(color, other) for other in others.values()):
        return None
    return _inks(color, background)


def apply_twin_colors(fig: Figure) -> int:
    """Colour each side of a ``twinx`` / ``twiny`` pair like its series.

    The rules (which sides, which data, which colours, what is left alone)
    are stated once, in the docstring of the module
    ``dartwork_mpl.formatting._twin_colors``. In short: a side whose series
    draw one colour that no series on the other scale shares gets it on its
    spine and tick marks (3:1) and, darkened to 4.5:1, on its tick labels
    and axis label; colours set by hand stay. ``dm.simple_layout`` calls
    this after the default tick formats.

    Returns the number of sides showing a series colour. Safe to call
    again: a repeat paints the same colours.

    Raises
    ------
    ValueError
        If ``dm.config.twin_colors`` is not ``"series"`` or ``"neutral"``.
    """
    series = _series_mode()
    _forget_cleared(fig)
    coloured = 0
    settled: set[tuple[int, Side, Part]] = set()
    for group in _twin_groups(fig):
        sides = [(ax, side) for ax in group for side in _own_sides(ax, group)]
        owners = {(id(ax), side) for ax, side in sides}
        background = _background(group)
        drawn = {id(m): _data_colors(m, background) for m in group}
        for ax, side in sides:
            inks = (
                _side_inks(ax, side, group, drawn, background)
                if series
                else None
            )
            coloured += _settle_side(group, owners, ax, side, inks, settled)
    # Parts painted on an earlier call whose pair is gone get their default.
    for ax in fig.axes:
        record: _Record = getattr(ax, _RECORD, {})
        for (side, part), entry in list(record.items()):
            if entry is not None and (id(ax), side, part) not in settled:
                _settle(ax, side, part, None)
        if record:
            setattr(ax, _RECORD_PATCH, ax.patch)
    return coloured
