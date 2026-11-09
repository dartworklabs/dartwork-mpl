"""TEXT_CONTRAST: WCAG text/background contrast advisory check.

The background of a text is read from the figure as matplotlib paints it:
the root figure is drawn once more, to a renderer of its own at the
figure's DPI, with the ink of every text made fully transparent, and the
background is the per-channel median of the pixels inside the text's own
box (an annotation's words, not its arrow; a 3D Axes' text where it is
projected). Interpolated and alpha-blended images, collections, overlapping
faces, Axes drawing order, clip paths and markers all count as they are
drawn; a text's own box (``bbox=``), a legend's frame and a stroke drawn
around a text by a path effect stay in the picture, other texts do not.
The draw does not touch the caller's canvas, and the colours are put back
even when drawing fails. A text with no finite box on the canvas is not
read.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, TypedDict

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.text import Annotation, Text

from ..._colors.contrast import contrast_ratio as _contrast_ratio
from ..._figure_geometry import holders_shown, text_window_extent
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.transforms import Bbox

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
_RGB = tuple[float, float, float]
_PixelBox = tuple[int, int, int, int]  # rows top..bottom, columns left..right


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


def _hex(rgb: _RGB | _RGBA) -> str:
    return mcolors.to_hex(rgb[:3], keep_alpha=False)


def _sample(value: str) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= _SAMPLE_CHARS:
        return collapsed
    return f"{collapsed[: _SAMPLE_CHARS - 3]}..."


def _visible_texts(fig: Figure) -> Iterator[Text]:
    for artist in fig.findobj(Text):
        if not isinstance(artist, Text) or not holders_shown(artist):
            continue  # a hidden SubFigure hides its text
        if not artist.get_visible():
            continue
        if not artist.get_text().strip():
            continue
        yield artist


def _text_box(text: Text, renderer: RendererBase) -> Bbox | None:
    """The text's own box where it draws, or ``None`` when it has none.

    An annotation's extent also holds its arrow, whose far end can sit on
    another fill, so its words are measured alone. A 3D Axes' text is
    measured at its projected place (:func:`text_window_extent`). A text at
    a missing coordinate (``nan``) has no finite box and is not read.
    """
    try:
        extent = (
            Text.get_window_extent(text, renderer)
            if isinstance(text, Annotation)
            else text_window_extent(text, renderer)
        )
    except BBOX_ERRORS:
        return None
    bounds = (extent.x0, extent.y0, extent.x1, extent.y1)
    if not all(math.isfinite(value) for value in bounds):
        return None
    if extent.width <= 0 or extent.height <= 0:
        return None
    return extent


def _pixel_box(box: Bbox, height: int, width: int) -> _PixelBox | None:
    """Rows and columns of the buffer the box covers, clipped to the canvas."""
    left = max(0, math.floor(box.x0))
    right = min(width, math.ceil(box.x1))
    top = max(0, math.floor(height - box.y1))
    bottom = min(height, math.ceil(height - box.y0))
    if right <= left or bottom <= top:
        return None
    return (top, bottom, left, right)


def _hide_ink(text: Text) -> Callable[[], None]:
    """Make the text's glyphs fully transparent; return the undo.

    Only the colour (and an alpha the text sets, which overrides it) moves:
    the text keeps its visibility, size and place, so a layout engine that
    runs in the draw measures it as before, and its box, arrow and
    path-effect strokes are still drawn.
    """
    color = text.get_color()
    alpha = text.get_alpha()
    rgba = mcolors.to_rgba(color)
    text.set_color((rgba[0], rgba[1], rgba[2], 0.0))
    if alpha is not None:
        text.set_alpha(0.0)

    def undo() -> None:
        text.set_color(color)
        text.set_alpha(alpha)

    return undo


def _painted_without_text(fig: Figure) -> np.ndarray:
    """The root figure drawn with every text's ink hidden, as RGB over white.

    A renderer of its own at the figure's DPI, so the caller's canvas and
    its buffer are untouched; every colour is put back even when the draw
    fails. A transparent figure shows on white paper.
    """
    root = fig.get_figure(root=True) or fig
    width, height = root.bbox.size
    renderer = RendererAgg(width, height, root.dpi)  # type: ignore[no-untyped-call]
    undo: list[Callable[[], None]] = []
    try:
        # One by one, so a failure part-way still undoes those already hidden.
        undo.extend(_hide_ink(text) for text in root.findobj(Text))
        root.draw(renderer)
    finally:
        for step in reversed(undo):
            step()
    raw: np.ndarray = np.asarray(renderer.buffer_rgba())  # type: ignore[no-untyped-call]
    rgba = raw.astype(float) / 255.0
    alpha = rgba[..., 3:4]
    rgb: np.ndarray = rgba[..., :3] * alpha + (1.0 - alpha)
    return rgb


def _background_at(pixels: np.ndarray, box: _PixelBox) -> _RGB:
    """The per-channel median of the pixels inside ``box``.

    Many pixels rather than the one at the centre: a gridline or a contour
    line through the middle of a label is not its background.
    """
    top, bottom, left, right = box
    median = np.median(pixels[top:bottom, left:right].reshape(-1, 3), axis=0)
    return (float(median[0]), float(median[1]), float(median[2]))


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


def _readable(
    fig: Figure, renderer: RendererBase
) -> list[tuple[Text, _RGBA, Bbox]]:
    """The texts to read: visible, inked, with a finite box."""
    found = []
    for text in _visible_texts(fig):
        text_color = _rgba(text.get_color())
        if text_color is None or text_color[3] <= 0:
            continue
        box = _text_box(text, renderer)
        if box is None:
            continue
        found.append((text, text_color, box))
    return found


@register_check("TEXT_CONTRAST", order=80)
def check_text_contrast(
    fig: Figure, _renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text whose color contrast is below WCAG AA guidance."""
    groups: dict[tuple[Severity, str, str, float], _ContrastGroup] = {}

    readable = _readable(fig, _renderer)
    if not readable:
        return []
    pixels = _painted_without_text(fig)

    for text, text_color, box in readable:
        cells = _pixel_box(box, pixels.shape[0], pixels.shape[1])
        if cells is None:
            continue  # wholly off the canvas: nothing is drawn to read

        background = _background_at(pixels, cells)
        ratio = _contrast_ratio(text_color[:3], background)
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
