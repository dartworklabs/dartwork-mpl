"""MIN_FONT_SIZE: text below the print legibility floor."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from matplotlib.text import Text

from .._types import Severity, VisualWarning
from ._registry import register_check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_min_font_size"]

_MIN_PT = 5.0  # Print legibility floor for figure-scale text.
_MAX_SAMPLES = 6
_SAMPLE_CHARS = 40


class _FontSample(TypedDict):
    sample: str
    size_pt: float


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


@register_check("MIN_FONT_SIZE", order=81)
def check_min_font_size(
    fig: Figure, _renderer: RendererBase
) -> list[VisualWarning]:
    """Detect visible text smaller than the minimum readable size."""
    samples: list[_FontSample] = []
    count = 0

    for text in _visible_texts(fig):
        size = float(text.get_fontsize())
        if size >= _MIN_PT:
            continue
        count += 1
        if len(samples) < _MAX_SAMPLES:
            samples.append(
                {"sample": _sample(text.get_text()), "size_pt": round(size, 2)}
            )

    if not samples:
        return []

    first = samples[0]
    extra = f" across {count} text items" if count > 1 else ""
    return [
        VisualWarning(
            severity=Severity.WARNING,
            check_id="MIN_FONT_SIZE",
            message=(
                f"Text size {first['size_pt']:.2f} pt is below the "
                f"{_MIN_PT:.1f} pt minimum{extra} "
                f"(sample: {first['sample']!r})"
            ),
            detail={
                "size_pt": first["size_pt"],
                "min_pt": _MIN_PT,
                "sample": first["sample"],
                "samples": samples,
                "count": count,
                "omitted": max(0, count - len(samples)),
            },
        )
    ]
