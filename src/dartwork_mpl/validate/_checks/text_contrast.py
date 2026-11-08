"""TEXT_CONTRAST: WCAG text/background contrast advisory check.

The background of a text is what is painted at its centre (the pixel there):
the figure and Axes patches, then, in drawing order (zorder, then the order
they were added), every filled patch, filled collection (``fill_between``,
``contourf``, ``pcolormesh``, a 3D surface) and image whose drawn area holds
that point, and the text's own box or legend frame on top. A patch counts
by its drawn path (a donut's hole and the corners of a wedge's box are not
the wedge), clipped to where it is drawn. The Axes drawn before the text's
own in the same place (a ``twinx`` host) count beneath it. Markers placed by
offsets (``scatter``) are not a background. One point stands for the whole
text: a label across two fills is read on the one under its centre, and a
``Text3D`` is placed where matplotlib reports it (before projection).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, TypedDict

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.collections import Collection, QuadMesh
from matplotlib.legend import Legend
from matplotlib.patches import Patch
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform, TransformedPath

from ..._colors.contrast import contrast_ratio as _contrast_ratio
from ..._figure_geometry import backdrop_layers, same_position_axes
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from matplotlib.artist import Artist
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.image import AxesImage

__all__ = ["check_text_contrast"]

_LARGE_AA_THRESHOLD = 3.0
_NORMAL_AA_THRESHOLD = 4.5
_LARGE_TEXT_PT = 18.0
_LARGE_BOLD_TEXT_PT = 14.0
_MAX_GROUPS = 6
_MAX_SAMPLES_PER_GROUP = 3
_SAMPLE_CHARS = 40
_BOLD_WEIGHTS = frozenset(
    {"bold", "heavy", "black", "extra bold", "semibold", "demibold"}
)

_RGBA = tuple[float, float, float, float]


class TextContrastDetail(TypedDict):
    """Texts sharing one colour pair fall below the WCAG AA ``threshold``."""

    ratio: float
    threshold: float
    minimum_threshold: float
    sample: str
    samples: list[str]
    count: int
    text_color: str
    background_color: str
    large_text: bool
    omitted_groups: int


@dataclass(frozen=True)
class _ContrastGroup:
    """Texts sharing (severity, text colour, background, threshold).

    The contrast facts are those of the first text seen; ``samples`` holds
    at most ``_MAX_SAMPLES_PER_GROUP`` of the ``count`` texts.
    """

    severity: Severity
    ratio: float
    threshold: float
    text_hex: str
    background_hex: str
    large_text: bool
    samples: tuple[str, ...] = ()
    count: int = 0

    def with_sample(self, sample: str) -> _ContrastGroup:
        """Count one more text, keeping its sample while there is room."""
        samples = (
            (*self.samples, sample)
            if len(self.samples) < _MAX_SAMPLES_PER_GROUP
            else self.samples
        )
        return replace(self, samples=samples, count=self.count + 1)


def _rgba(color: Any) -> _RGBA | None:
    try:
        raw = mcolors.to_rgba(color)
    except (TypeError, ValueError):
        return None
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _hex(rgba: _RGBA) -> str:
    return mcolors.to_hex(rgba, keep_alpha=False)


def _composite(foreground: _RGBA, background: _RGBA) -> _RGBA:
    alpha = foreground[3]
    background_alpha = background[3]
    out_alpha = alpha + background_alpha * (1.0 - alpha)
    if out_alpha <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        (
            foreground[0] * alpha
            + background[0] * background_alpha * (1.0 - alpha)
        )
        / out_alpha,
        (
            foreground[1] * alpha
            + background[1] * background_alpha * (1.0 - alpha)
        )
        / out_alpha,
        (
            foreground[2] * alpha
            + background[2] * background_alpha * (1.0 - alpha)
        )
        / out_alpha,
        out_alpha,
    )


def _sample(value: str) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= _SAMPLE_CHARS:
        return collapsed
    return f"{collapsed[: _SAMPLE_CHARS - 3]}..."


def _visible_texts(fig: Figure) -> Iterator[Text]:
    for artist in fig.findobj(Text):
        if not isinstance(artist, Text):
            continue
        if not artist.get_visible():
            continue
        if not artist.get_text().strip():
            continue
        yield artist


def _axes_beneath(axes: Axes) -> list[Axes]:
    """``axes`` and the Axes in its place drawn before it, in drawing order.

    The figure draws its Axes by zorder, ties in the order they were added;
    a ``twinx`` host drawn first shows through its transparent partner.
    """
    group = same_position_axes(axes)
    parent = axes.get_figure(root=False)
    order = (
        {id(member): index for index, member in enumerate(parent.axes)}
        if parent is not None
        else {}
    )
    drawn = sorted(
        group,
        key=lambda member: (member.get_zorder(), order.get(id(member), 0)),
    )
    return drawn[: drawn.index(axes) + 1]


def _base_layers(text: Text, beneath: list[Axes]) -> list[_RGBA]:
    """The figure, subfigure and Axes patches behind ``text``, lowest first."""
    if beneath:
        return [_as_rgba(layer) for layer in backdrop_layers(beneath)]
    root = text.get_figure(root=True)
    parent = text.get_figure(root=False)
    containers = (root, parent if parent is not root else None)
    return [
        _as_rgba(mcolors.to_rgba(container.get_facecolor()))
        for container in containers
        if container is not None and container.patch.get_visible()
    ]


def _as_rgba(color: tuple[float, ...]) -> _RGBA:
    return (float(color[0]), float(color[1]), float(color[2]), float(color[3]))


def _text_center(
    text: Text, renderer: RendererBase
) -> tuple[float, float] | None:
    """The centre of the text's own box.

    ``Text.get_window_extent`` rather than the artist's: an annotation's
    extent also holds its arrow, whose far end can sit on another fill.
    """
    try:
        extent = Text.get_window_extent(text, renderer)
    except BBOX_ERRORS:
        return None
    if extent.width <= 0 or extent.height <= 0:
        return None
    return ((extent.x0 + extent.x1) / 2.0, (extent.y0 + extent.y1) / 2.0)


def _patch_facecolor(patch: Any) -> _RGBA | None:
    if not patch.get_visible():
        return None
    facecolor = _rgba(patch.get_facecolor())
    if facecolor is None or facecolor[3] <= 0:
        return None
    return facecolor


def _clipped_away(artist: Artist, point: tuple[float, float]) -> bool:
    """Whether ``artist``'s clip box or clip path keeps it off ``point``.

    A bar past the axes limit is drawn up to the axes edge only, so text
    beyond the limit does not lie on it.
    """
    if not artist.get_clip_on():
        return False
    clip_box = artist.get_clip_box()
    if clip_box is not None and not clip_box.contains(*point):
        return True
    clip_path = artist.get_clip_path()  # stored as a TransformedPath, or None
    if not isinstance(clip_path, TransformedPath):
        return False
    return not clip_path.get_fully_transformed_path().contains_point(point)


def _patch_contains_point(
    patch: Patch, renderer: RendererBase, point: tuple[float, float]
) -> bool:
    """Whether ``patch``'s fill is drawn at display ``point``.

    Inside its drawn path, not merely its extent: the box around a wedge
    holds the donut's hole and the space beside the ring.
    """
    try:
        extent = patch.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    if extent.width <= 0 or extent.height <= 0:
        return False
    if not extent.contains(*point):
        return False
    if not patch.contains_point(point, radius=0):
        return False
    return not _clipped_away(patch, point)


def _drawn_in_place(collection: Collection) -> bool:
    """Whether ``collection`` draws its paths where they are, not as markers.

    ``fill_between``, ``contourf`` and 3D surfaces are; ``scatter`` repeats
    one marker path at each offset, and is not a background.
    """
    if len(collection.get_transforms()):
        return False
    if not isinstance(collection.get_offset_transform(), IdentityTransform):
        return False
    return not np.any(collection.get_offsets())


def _collection_rgba_at(
    collection: Collection,
    point: tuple[float, float],
    event: Callable[[], MouseEvent],
) -> _RGBA | None:
    """The face of ``collection`` drawn at ``point`` (the last path holding it)."""
    if not collection.get_visible() or _clipped_away(collection, point):
        return None
    faces = np.asarray(collection.get_facecolor(), dtype=float).reshape(-1, 4)
    if not len(faces) or not np.any(faces[:, 3] > 0):
        return None
    if isinstance(collection, QuadMesh):
        hit, info = collection.contains(event())
        indices = [int(i) for i in info.get("ind", ())] if hit else []
    elif _drawn_in_place(collection):
        transform = collection.get_transform()
        indices = [
            index
            for index, path in enumerate(collection.get_paths())
            if path.contains_point(point, transform)
        ]
    else:
        return None
    if not indices:
        return None
    face = faces[indices[-1] % len(faces)]
    return _as_rgba(tuple(face)) if face[3] > 0 else None


def _image_rgba_at(
    image: AxesImage,
    point: tuple[float, float],
    event: Callable[[], MouseEvent],
) -> _RGBA | None:
    """The colour of ``image``'s cell drawn at ``point``."""
    if not image.get_visible() or _clipped_away(image, point):
        return None
    data = image.get_array()
    if data is None:
        return None
    value = image.get_cursor_data(event())
    if value is None:
        return None
    if np.ndim(data) == 3:
        cell = np.asarray(value).reshape(1, 1, -1)
        rgba = np.asarray(image.to_rgba(cell), dtype=float)[0, 0]
    else:
        shown = (
            np.ma.masked_array([0.0], mask=[True])
            if np.ma.is_masked(value)
            else np.ma.asarray([value], dtype=float)
        )
        rgba = np.asarray(image.to_rgba(shown), dtype=float)[0]
    alpha = image.get_alpha()
    if isinstance(alpha, (int, float)):
        rgba[3] *= float(alpha)
    return _as_rgba(tuple(rgba)) if rgba[3] > 0 else None


def _layer_at(
    artist: Artist,
    renderer: RendererBase,
    point: tuple[float, float],
    event: Callable[[], MouseEvent],
) -> _RGBA | None:
    if isinstance(artist, Patch):
        face = _patch_facecolor(artist)
        if face is None or not _patch_contains_point(artist, renderer, point):
            return None
        return face
    if isinstance(artist, Collection):
        return _collection_rgba_at(artist, point, event)
    return _image_rgba_at(artist, point, event)  # type: ignore[arg-type]


def _filled_layers(
    axes: Axes,
    renderer: RendererBase,
    point: tuple[float, float],
    event: Callable[[], MouseEvent],
) -> list[_RGBA]:
    """What ``axes`` paints at ``point``, in drawing order, lowest first."""
    members = {
        id(artist)
        for artist in (*axes.patches, *axes.collections, *axes.images)
    }
    drawn = sorted(
        (child for child in axes.get_children() if id(child) in members),
        key=lambda child: child.get_zorder(),
    )
    layers: list[_RGBA] = []
    for artist in drawn:
        layer = _layer_at(artist, renderer, point, event)
        if layer is not None:
            layers.append(layer)
    return layers


def _owning_legend(text: Text) -> Legend | None:
    parent = text.get_figure(root=False)
    if parent is None:
        return None
    holders = [ax.get_legend() for ax in parent.axes]
    holders.extend(parent.legends)
    for legend in holders:
        if not isinstance(legend, Legend):
            continue
        if text is legend.get_title() or any(
            text is entry for entry in legend.get_texts()
        ):
            return legend
    return None


def _background_under_text(
    text: Text, fig: Figure, renderer: RendererBase
) -> _RGBA:
    del fig  # the text's own figure, subfigure and Axes are read from it
    axes = text.axes
    beneath = _axes_beneath(axes) if isinstance(axes, Axes) else []
    layers = _base_layers(text, beneath)
    center = _text_center(text, renderer) if beneath else None
    root = text.get_figure(root=True)
    if center is not None and root is not None:
        # The centre of the pixel holding the text's centre, where the
        # renderer samples: a centre exactly on an edge (the seam of a
        # polar Axes' round clip path) is read as the pixel is painted.
        point = (math.floor(center[0]) + 0.5, math.floor(center[1]) + 0.5)
        canvas = root.canvas
        cached: list[MouseEvent] = []

        def event() -> MouseEvent:
            # Images and meshes answer where a mouse event lies.
            # matplotlib types x and y as int; display points are floats.
            if not cached:
                cached.append(
                    MouseEvent("motion_notify_event", canvas, *point)  # type: ignore[arg-type]
                )
            return cached[0]

        for member in beneath:
            layers.extend(_filled_layers(member, renderer, point, event))

    background: _RGBA = (1.0, 1.0, 1.0, 1.0)
    for layer in layers:
        if layer[3] > 0:
            background = _composite(layer, background)
    return background


def _background_rgba(text: Text, fig: Figure, renderer: RendererBase) -> _RGBA:
    background = _background_under_text(text, fig, renderer)

    legend = _owning_legend(text)
    if legend is not None and legend.get_frame_on():
        frame = _patch_facecolor(legend.get_frame())
        if frame is not None:
            background = _composite(frame, background)

    bbox_patch = text.get_bbox_patch()
    if bbox_patch is None:
        return background
    facecolor = _patch_facecolor(bbox_patch)
    if facecolor is None:
        return background
    return _composite(facecolor, background)


def _is_bold(weight: object) -> bool:
    if isinstance(weight, str):
        normalized = weight.replace("-", " ").replace("_", " ").lower()
        normalized = " ".join(normalized.split())
        if normalized in _BOLD_WEIGHTS:
            return True
        try:
            return float(normalized) >= 600
        except ValueError:
            return False

    if isinstance(weight, (int, float)):
        return float(weight) >= 600
    return False


def _is_large_text(text: Text) -> bool:
    size = float(text.get_fontsize())
    return size >= _LARGE_TEXT_PT or (
        size >= _LARGE_BOLD_TEXT_PT and _is_bold(text.get_fontweight())
    )


@register_check("TEXT_CONTRAST", order=80)
def check_text_contrast(
    fig: Figure, _renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text whose color contrast is below WCAG AA guidance."""
    groups: dict[tuple[Severity, str, str, float], _ContrastGroup] = {}

    for text in _visible_texts(fig):
        text_color = _rgba(text.get_color())
        if text_color is None or text_color[3] <= 0:
            continue

        background = _background_rgba(text, fig, _renderer)
        ratio = _contrast_ratio(text_color[:3], background[:3])
        large_text = _is_large_text(text)
        threshold = _LARGE_AA_THRESHOLD if large_text else _NORMAL_AA_THRESHOLD

        if ratio >= threshold:
            continue

        severity = (
            Severity.WARNING if ratio < _LARGE_AA_THRESHOLD else Severity.INFO
        )
        text_hex = _hex(text_color)
        bg_hex = _hex(background)
        key = (severity, text_hex, bg_hex, threshold)
        group = groups.get(key)
        if group is None:
            group = _ContrastGroup(
                severity=severity,
                ratio=ratio,
                threshold=threshold,
                text_hex=text_hex,
                background_hex=bg_hex,
                large_text=large_text,
            )
        groups[key] = group.with_sample(_sample(text.get_text()))

    warnings: list[VisualWarning] = []
    total_groups = len(groups)
    for group in list(groups.values())[:_MAX_GROUPS]:
        sample = group.samples[0] if group.samples else ""
        scope = "large text" if group.large_text else "normal text"
        extra = f" across {group.count} text items" if group.count > 1 else ""
        warnings.append(
            VisualWarning(
                severity=group.severity,
                check_id="TEXT_CONTRAST",
                message=(
                    f"Text contrast {group.ratio:.2f}:1 is below the "
                    f"{group.threshold:.1f}:1 AA threshold for {scope}"
                    f"{extra} (sample: {sample!r})"
                ),
                detail=wire(
                    TextContrastDetail(
                        ratio=round(group.ratio, 2),
                        threshold=group.threshold,
                        minimum_threshold=_LARGE_AA_THRESHOLD,
                        sample=sample,
                        samples=list(group.samples),
                        count=group.count,
                        text_color=group.text_hex,
                        background_color=group.background_hex,
                        large_text=group.large_text,
                        omitted_groups=max(0, total_groups - _MAX_GROUPS),
                    )
                ),
            )
        )

    return warnings
