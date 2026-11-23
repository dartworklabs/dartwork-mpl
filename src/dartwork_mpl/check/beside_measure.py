"""How far each text set beside a plot is from what is drawn next to it."""

from __future__ import annotations

from collections.abc import Callable
from copy import copy
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..geometry import DataInk, marks_ink
from .model import Beside, Gap, Heading, Placed, Step

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase

    from .model import Text

#: A neighbour's distance is found to this many px.
RESOLUTION_PX = 0.5


def ink_gap(
    ink: DataInk[object], strip: Callable[[float], Bbox], limit: float
) -> float | None:
    """How wide ``strip`` grows before it meets ink (``None``: never)."""
    if limit <= 0 or not ink.meets(strip(limit)):
        return None
    low, high = 0.0, limit
    while high - low > RESOLUTION_PX:
        mid = (low + high) / 2
        if ink.meets(strip(mid)):
            high = mid
        else:
            low = mid
    return high


def leftward(x: float, y0: float, y1: float) -> Callable[[float], Bbox]:
    """A strip growing to the left of ``x``."""
    return lambda reach: Bbox.from_extents(x - reach, y0, x, y1)


def rightward(x: float, y0: float, y1: float) -> Callable[[float], Bbox]:
    """A strip growing to the right of ``x``."""
    return lambda reach: Bbox.from_extents(x, y0, x + reach, y1)


def placed(artist: MplText, renderer: RendererBase) -> Placed | None:
    """The x the author gave the text and what one unit of it moves."""
    if artist.get_children():
        return None  # drawn as pieces: its x is not the author's
    moved = copy(artist)
    x, y = artist.get_unitless_position()
    moved.set_position((x + 1.0, y))
    step = float(
        moved.get_window_extent(renderer).x0
        - artist.get_window_extent(renderer).x0
    )
    return Placed(float(x), step) if np.isfinite(step) and step else None


def centre(text: Text) -> float:
    """The middle of a text, left to right."""
    return (text.box.x0 + text.box.x1) / 2


def among_marks(text: Text, ink: DataInk[object], canvas: Bbox) -> bool:
    """The text is on a mark or has marks on both sides of it at its
    height: the number of a cell, a segment or a dot."""
    quarter = text.box.height / 4
    y0, y1 = text.box.y0 + quarter, text.box.y1 - quarter
    if ink.meets(Bbox.from_extents(text.box.x0, y0, text.box.x1, y1)):
        return True
    return bool(
        ink.meets(Bbox.from_extents(canvas.x0, y0, text.box.x0, y1))
        and ink.meets(Bbox.from_extents(text.box.x1, y0, canvas.x1, y1))
    )


def step(
    text: Text,
    level: list[Text],
    ink: DataInk[object],
    canvas: Bbox,
    sign: float,
) -> Step | None:
    """How the text continues the numbers among the marks of its row: the
    two nearest of them give the spacing."""
    numbers = sorted(
        (centre(t) for t in level if among_marks(t, ink, canvas)),
        key=lambda x: abs(x - centre(text)),
    )
    if len(numbers) < 2:
        return None
    last, before = numbers[:2]
    pitch = abs(last - before)
    if pitch <= 0 or (last - centre(text)) * sign < 0:
        return None
    return Step(last - sign * pitch - centre(text), pitch)


def beside(
    texts: tuple[Text, ...],
    others: tuple[Text, ...],
    axes: list[Axes],
    renderer: RendererBase,
    px_per_pt: float,
    canvas: Bbox,
) -> tuple[tuple[Beside, ...], tuple[Heading, ...]]:
    """Each text the user set beside a plot (marks on one side of it at its
    height), with the nearest thing on that side: a mark, a plot's edge or
    another text. And each with marks on neither side: a heading."""
    chosen = [
        (text, artist)
        for text in texts
        if text.role.free
        and isinstance(artist := text.handle, MplText)
        and artist.get_rotation() == 0
        and not (
            isinstance(artist, Annotation) and artist.arrow_patch is not None
        )
        and isinstance(artist.axes, Axes)
    ]
    if not chosen:
        return (), ()
    ink = marks_ink(axes, renderer, px_per_pt)
    frames = [ax.bbox for ax in axes if ax.axison]
    result: list[Beside] = []
    headings: list[Heading] = []
    for text, artist in chosen:
        box = text.box
        quarter = (box.y1 - box.y0) / 4
        y0, y1 = box.y0 + quarter, box.y1 - quarter
        if ink.meets(Bbox.from_extents(box.x0, y0, box.x1, y1)):
            continue  # a text on a mark belongs to that mark
        to_left = ink_gap(ink, leftward(box.x0, y0, y1), box.x0 - canvas.x0)
        to_right = ink_gap(ink, rightward(box.x1, y0, y1), canvas.x1 - box.x1)
        if to_left is not None and to_right is not None:
            continue  # marks on both sides: a cell of a grid
        level = [
            t
            for t in (*texts, *others)
            if t.handle is not artist and t.box.y1 > y0 and t.box.y0 < y1
        ]
        if to_left is None and to_right is None:
            lefts = [
                Gap(max(box.x0 - t.box.x1, 0.0), t)
                for t in level
                if t.box.x0 < box.x0
            ]
            rights = [
                Gap(max(t.box.x0 - box.x1, 0.0), t)
                for t in level
                if t.box.x1 > box.x1
            ]
            headings.append(
                Heading(
                    text,
                    min(lefts, key=lambda g: g.px, default=None),
                    min(rights, key=lambda g: g.px, default=None),
                )
            )
            continue
        if to_left is not None:
            found: list[tuple[float, Text | None]] = [(to_left, None)]
            found += [
                (max(box.x0 - t.box.x1, 0.0), t)
                for t in level
                if t.box.x0 < box.x0
            ]
            found += [
                (float(box.x0 - f.x1), None)
                for f in frames
                if f.y1 > y0 and f.y0 < y1 and f.x1 <= box.x0
            ]
            sign = -1.0
        else:
            found = [(to_right or 0.0, None)]
            found += [
                (max(t.box.x0 - box.x1, 0.0), t)
                for t in level
                if t.box.x1 > box.x1
            ]
            found += [
                (float(f.x0 - box.x1), None)
                for f in frames
                if f.y1 > y0 and f.y0 < y1 and f.x0 >= box.x1
            ]
            sign = 1.0
        gap, neighbour = min(found, key=lambda pair: pair[0])
        result.append(
            Beside(
                text,
                sign * gap,
                neighbour,
                placed(artist, renderer),
                step(text, level, ink, canvas, sign),
            )
        )
    return tuple(result), tuple(headings)
