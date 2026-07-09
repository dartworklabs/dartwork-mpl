"""TEXT_CONTRAST: WCAG text/background contrast advisory check."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import matplotlib.colors as mcolors
from matplotlib.text import Text

from ..._luminance import _contrast_ratio
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._registry import register_check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

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


@dataclass
class _ContrastGroup:
    severity: Severity
    ratio: float
    threshold: float
    text_hex: str
    background_hex: str
    large_text: bool
    samples: list[str] = field(default_factory=list)
    count: int = 0

    def add_sample(self, sample: str) -> None:
        self.count += 1
        if len(self.samples) < _MAX_SAMPLES_PER_GROUP:
            self.samples.append(sample)


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


def _base_background_rgba(text: Text, fig: Figure) -> _RGBA:
    background: _RGBA = (1.0, 1.0, 1.0, 1.0)

    figure_color = _rgba(fig.get_facecolor())
    if figure_color is not None and figure_color[3] > 0:
        background = _composite(figure_color, background)

    axes = text.axes
    if axes is not None:
        axes_color = _rgba(axes.get_facecolor())
        if axes_color is not None and axes_color[3] > 0:
            background = _composite(axes_color, background)

    return background


def _text_center(
    text: Text, renderer: RendererBase
) -> tuple[float, float] | None:
    try:
        extent = text.get_window_extent(renderer)
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


def _patch_contains_point(
    patch: Any, renderer: RendererBase, point: tuple[float, float]
) -> bool:
    try:
        extent = patch.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    if extent.width <= 0 or extent.height <= 0:
        return False
    return bool(extent.contains(*point))


def _patch_background_rgba(
    text: Text, renderer: RendererBase, background: _RGBA
) -> _RGBA:
    axes = text.axes
    if axes is None:
        return background

    center = _text_center(text, renderer)
    if center is None:
        return background

    candidates: list[tuple[float, int, _RGBA]] = []
    for index, patch in enumerate(axes.patches):
        facecolor = _patch_facecolor(patch)
        if facecolor is None:
            continue
        if not _patch_contains_point(patch, renderer, center):
            continue
        candidates.append((float(patch.get_zorder()), index, facecolor))

    for _zorder, _index, facecolor in sorted(candidates):
        background = _composite(facecolor, background)
    return background


def _background_under_text(
    text: Text, fig: Figure, renderer: RendererBase
) -> _RGBA:
    background = _base_background_rgba(text, fig)
    return _patch_background_rgba(text, renderer, background)


def _background_rgba(text: Text, fig: Figure, renderer: RendererBase) -> _RGBA:
    background = _background_under_text(text, fig, renderer)

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
            groups[key] = group
        group.add_sample(_sample(text.get_text()))

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
                detail={
                    "ratio": round(group.ratio, 2),
                    "threshold": group.threshold,
                    "minimum_threshold": _LARGE_AA_THRESHOLD,
                    "sample": sample,
                    "samples": group.samples,
                    "count": group.count,
                    "text_color": group.text_hex,
                    "background_color": group.background_hex,
                    "large_text": group.large_text,
                    "omitted_groups": max(0, total_groups - _MAX_GROUPS),
                },
            )
        )

    return warnings
