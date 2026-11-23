"""Where a plot's data ink is drawn, to find what a legend covers.

Gathered by ``geometry.DataInk``, as the legend slice gathers it: lines at
their width, markers and scatter points as discs, bars by their drawn
boxes, filled areas by their outlines, each only where its clip lets it
draw. What counts here: data in data coordinates (not an ``axhline``),
named by kind and label for the finding.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np
from matplotlib.collections import (
    Collection,
    LineCollection,
    PathCollection,
    PolyCollection,
)
from matplotlib.colors import to_rgba
from matplotlib.container import BarContainer
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..geometry import (
    BBOX_ERRORS,
    UNCLIPPED,
    DataInk,
    artist_shown,
    clip_path_px,
    clip_region,
    cut_to_clip,
    drawn_patch_box,
    in_data_coords,
    line_draws_markers,
    line_draws_stroke,
    patch_inks,
    text_inks,
    within_clip_path,
)
from .model import Hit

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.legend import Legend as MplLegend
    from matplotlib.typing import ColorType


class Named(Protocol):
    """An artist or container: it has a legend label."""

    def get_label(self) -> object:
        """The legend label."""
        ...


def name_of(artist: Named, unnamed: str = "") -> str:
    """The artist's legend label, ``unnamed`` for a ``_``-label."""
    label = str(artist.get_label() or "")
    return unnamed if not label or label.startswith("_") else label


def cut(box: Bbox, frame: Bbox) -> Bbox | None:
    """``box`` cut to ``frame``; ``None`` when nothing is left."""
    x0, y0 = max(box.x0, frame.x0), max(box.y0, frame.y0)
    x1, y1 = min(box.x1, frame.x1), min(box.y1, frame.y1)
    return Bbox.from_extents(x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


@dataclass(frozen=True)
class Ink:
    """The data ink of one plot box (an Axes and its twins), by artist."""

    frame: Bbox
    drawn: DataInk[Hit]

    def meets(self, box: Bbox, touch: float) -> list[Hit]:
        """What ``box`` covers by more than ``touch`` inside the plot box."""
        inner = cut(box.padded(-touch), self.frame)
        return [] if inner is None else self.drawn.meets(inner, touch)

    def holds(self, box: Bbox, off: float) -> bool:
        """Whether ``box`` sits centred (within ``off`` px) in one
        marker or scatter point with its ink inside it."""
        return self.drawn.holds(box, off)


def _hit(coll: Collection) -> Hit | None:
    """How a collection is named when covered (``None``: not counted)."""
    if isinstance(coll, PathCollection):
        return Hit("marker", name_of(coll)) if len(coll.get_sizes()) else None
    if isinstance(coll, PolyCollection):
        return Hit("area", name_of(coll, "filled area"))
    if isinstance(coll, LineCollection):
        return Hit("line", name_of(coll))
    return None


def data_ink(
    owners: list[Axes], frame: Bbox, renderer: RendererBase, px_per_pt: float
) -> Ink:
    """Bars, data lines, markers, scatter points, filled areas and data line
    collections of one plot box."""
    drawn: DataInk[Hit] = DataInk()

    def to_px(points: float) -> float:
        return points * px_per_pt

    for ax in owners:
        for line in ax.get_lines():
            if line.get_visible() and in_data_coords(line, ax):
                name = name_of(line)
                drawn.add_line(
                    line, to_px, Hit("line", name), Hit("marker", name)
                )
        for coll in ax.collections:
            if (coll.get_visible() and in_data_coords(coll, ax)) or (
                isinstance(coll, PathCollection) and coll.get_visible()
            ):
                hit = _hit(coll)
                if hit is not None:
                    drawn.add_collection(
                        coll, renderer, to_px, hit, filled=False
                    )
        for container in ax.containers:
            if not isinstance(container, BarContainer):
                continue
            for patch in container.patches:
                with suppress(*BBOX_ERRORS):
                    drawn.add_box(
                        Hit("bar", name_of(container)),
                        drawn_patch_box(patch, renderer),
                    )
    return Ink(frame, drawn)


def words_box(text: MplText, renderer: RendererBase) -> Bbox | None:
    """Where a text's words draw (not an annotation's arrow), cut to its clip."""
    box = MplText.get_window_extent(text, renderer)
    if not np.isfinite(box.extents).all() or box.width <= 0 or box.height <= 0:
        return None
    region = clip_region(text)
    seen = box if region is UNCLIPPED else cut(box, region)
    return within_clip_path(seen, clip_path_px(text))


def legend_inks(leg: MplLegend) -> bool:
    """A legend that draws a frame, a title or an entry text."""
    if leg.get_frame_on() and patch_inks(leg.get_frame()):
        return True
    return any(text_inks(t) for t in (leg.get_title(), *leg.get_texts()))


def data_artists(
    ax: Axes,
) -> tuple[Line2D | Patch | Collection | AxesImage, ...]:
    """The plot's marks, including ones that may be invisible."""
    return (*ax.lines, *ax.patches, *ax.collections, *ax.images)


def _line_ink(
    line: Line2D,
    ax: Axes,
    drawn: DataInk[Line2D | Collection],
    px_per_pt: float,
) -> None:
    """Measure a line's marks unless all its paint matches solid Axes paper."""
    paper = to_rgba(ax.patch.get_facecolor())
    if (
        ax.axison
        and ax.get_frame_on()
        and ax.patch.get_visible()
        and not ax.patch.get_hatch()
        and paper[3] == 1.0
        and line.get_clip_on()
    ):
        paints: list[ColorType] = []
        if line_draws_stroke(line):
            paints.append(line.get_color())
            if gap := line.get_gapcolor():
                paints.append(gap)
        if line_draws_markers(line):
            paints.extend(
                (line.get_markerfacecolor(), line.get_markerfacecoloralt())
            )
            if line.get_markeredgewidth() > 0:
                paints.append(line.get_markeredgecolor())
        colours = (to_rgba(colour, line.get_alpha()) for colour in paints)
        if all(rgba[3] == 0 or rgba[:3] == paper[:3] for rgba in colours):
            return
    drawn.add_line(line, lambda pt: pt * px_per_pt, line, line)


def data_shows(
    ax: Axes, canvas: Bbox, renderer: RendererBase, px_per_pt: float
) -> bool:
    """Whether the plot's artists can leave any visible mark on the canvas.

    Unknown artists and custom paint effects count as possible ink. Use
    the actual artist clip, so a mark drawn outside its plot can still show.
    """
    if any(artist_shown(a) for a in (*ax.tables, *ax.artists)):
        return True
    drawn: DataInk[Line2D | Collection] = DataInk()
    for artist in data_artists(ax):
        if not artist_shown(artist):
            continue
        filtered = artist.get_agg_filter() is not None  # pyright: ignore[reportUnknownMemberType]
        if artist.get_path_effects() or filtered:
            return True
        if isinstance(artist, Line2D):
            _line_ink(artist, ax, drawn, px_per_pt)
        elif isinstance(
            artist, (PathCollection, PolyCollection, LineCollection)
        ):
            drawn.add_collection(
                artist,
                renderer,
                lambda pt: pt * px_per_pt,
                artist,
                filled=isinstance(artist, PolyCollection),
            )
        elif isinstance(artist, Patch):
            box = drawn_patch_box(artist, renderer)
            if box is not None and cut(box, canvas) is not None:
                return True
        elif isinstance(artist, AxesImage):
            box = cut_to_clip(artist.get_window_extent(renderer), artist)
            if box is not None and cut(box, canvas) is not None:
                return True
        else:
            return True  # e.g. a QuadMesh, whose paint is not measured here
    return bool(drawn.meets(canvas))
