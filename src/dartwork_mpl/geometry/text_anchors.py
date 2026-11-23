"""Recognise horizontal anchors tied to an individual mark."""

from __future__ import annotations

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Transform

from .model import coordinate_follows_data


def follows_mark(text: Text) -> bool:
    """Whether shifting x would move the text off a data or artist anchor."""
    axes = text.axes
    if not isinstance(axes, Axes):
        return False
    if isinstance(text, Annotation):
        coords = text.xycoords
        x = (
            coords
            if isinstance(coords, (str, Artist, Transform)) or callable(coords)
            else coords[0]
        )
        if isinstance(x, Transform):
            return x.contains_branch_seperately(axes.transData)[0]
        # An artist or a callable may place each row relative to its own mark.
        return not isinstance(x, str) or coordinate_follows_data(x)
    if not axes.axison and not (
        axes.lines or axes.patches or axes.collections or axes.images
    ):
        return False  # a text-only side Axes has no marks to leave behind
    transform = text.get_transform()
    if not transform.contains_branch_seperately(axes.transData)[0]:
        return False
    point = text.get_unitless_position()
    x, _ = transform.transform(point)
    if axes.bbox.x0 <= x <= axes.bbox.x1:
        return True
    # A manually placed column may use a constant data x beyond the plot.
    return not any(
        peer is not text
        and peer.get_visible()
        and not isinstance(peer, Annotation)
        and peer.get_transform() is transform
        and peer.get_unitless_position()[0] == point[0]
        and peer.get_unitless_position()[1] != point[1]
        for peer in axes.texts
    )
