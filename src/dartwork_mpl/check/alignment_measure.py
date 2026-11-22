"""Read actual anchors and numeric offsets from the current renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText

from ..geometry import follows_mark
from ..vocab import NumericText, has_math, parse_halign
from .model import AlignmentSample

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase

    from .model import Text


def alignment_samples(
    texts: tuple[Text, ...], renderer: RendererBase
) -> tuple[tuple[AlignmentSample, ...], ...]:
    """Groups eligible for the column rule, by Axes and outer side."""
    groups: dict[tuple[Axes, bool], list[AlignmentSample]] = {}
    for text in texts:
        artist = text.handle
        if (
            not text.role.free
            or not isinstance(artist, MplText)
            or bool(artist.get_children())
            or artist.get_rotation() != 0
            or artist.get_usetex()
            or has_math(text.text)
            or len(text.text.splitlines()) != 1
            or (
                isinstance(artist, Annotation)
                and artist.arrow_patch is not None
            )
            or not isinstance(axes := artist.axes, Axes)
            or follows_mark(artist)
        ):
            continue
        x, y = artist.get_transform().transform(artist.get_unitless_position())
        if (
            axes.axison and axes.bbox.x0 <= x <= axes.bbox.x1
        ) or not axes.bbox.y0 <= y <= axes.bbox.y1:
            continue

        numeric = NumericText.parse(text.text)
        align = parse_halign(artist.get_horizontalalignment())
        box = artist.get_window_extent(renderer)
        font = artist.get_fontproperties()
        # Measuring the prefix in the selected renderer keeps the active font,
        # weight and hinting, including widths of any spaces actually typed.
        marks = (
            tuple(
                float(box.x0)
                + float(
                    renderer.get_text_width_height_descent(
                        run.prefix + run.dot, font, False
                    )[0]
                )
                - float(
                    renderer.get_text_width_height_descent(
                        run.dot, font, False
                    )[0]
                )
                for run in numeric.numbers
            )
            if artist.get_bbox_patch() is None
            else ()
        )
        key = (axes, bool(x > axes.bbox.x1))
        groups.setdefault(key, []).append(
            AlignmentSample(text, align, float(x), float(y), marks, hash(font))
        )
    return tuple(tuple(group) for group in groups.values())
