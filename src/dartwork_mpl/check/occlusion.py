"""Sample tick-label boxes against filled paths painted above the axis."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgba

from ..geometry import (
    artist_shown,
    clip_path_px,
    clip_region,
    drawn_collection_paths,
)
from .model import Text, TickOcclusion

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.path import Path
    from matplotlib.projections.polar import PolarAxes


def fills(ax: PolarAxes) -> Iterator[tuple[Artist, Path, float]]:
    """Filled patches and bands painted after the radial axis."""
    z = ax.yaxis.get_zorder()
    for patch in ax.patches:
        if artist_shown(patch) and patch.get_zorder() > z and patch.get_fill():
            alpha = to_rgba(patch.get_facecolor())[3]
            if alpha > 0:
                yield (
                    patch,
                    patch.get_transform().transform_path(patch.get_path()),
                    alpha,
                )
    for artist in ax.collections:
        if (
            not isinstance(artist, PolyCollection)
            or not artist_shown(artist)
            or artist.get_zorder() <= z
        ):
            continue
        colors = np.asarray(artist.get_facecolor(), dtype=float).reshape(-1, 4)
        if len(colors):
            for i, path in drawn_collection_paths(artist):
                alpha = float(colors[i % len(colors), 3])
                if alpha > 0:
                    yield artist, path, alpha


def measure_occlusion(
    ax: PolarAxes, labels: tuple[Text, ...]
) -> tuple[TickOcclusion, ...]:
    """Measure the mean alpha covering each label, respecting the fills' clips."""
    layers = [
        (path, alpha, clip_region(artist), clip_path_px(artist))
        for artist, path, alpha in fills(ax)
    ]
    if not layers:
        return ()
    found: list[TickOcclusion] = []
    centres = (np.arange(8) + 0.5) / 8
    for label in labels:
        box = label.box
        x, y = np.meshgrid(
            box.x0 + centres * box.width, box.y0 + centres * box.height
        )
        points = np.column_stack((x.ravel(), y.ravel()))
        shade = np.zeros(len(points))
        for path, alpha, region, clip in layers:
            inside = (
                (points[:, 0] >= region.x0)
                & (points[:, 0] <= region.x1)
                & (points[:, 1] >= region.y0)
                & (points[:, 1] <= region.y1)
            )
            if inside.any():
                inside &= path.contains_points(points)
                if clip is not None:
                    inside &= clip.contains_points(points)
                shade[inside] = np.maximum(shade[inside], alpha)
        found.append(TickOcclusion(label, float(shade.mean())))
    return tuple(found)
