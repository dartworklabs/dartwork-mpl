"""Shared helpers for validation checks that inspect tick labels."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from .._types import BBOX_ERRORS

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text
    from matplotlib.transforms import Bbox

__all__ = [
    "adjacent_bboxes_overlap",
    "iter_view_ticks",
    "parse_numeric_tick",
    "split_tick_affixes",
]

_NUMBER_RE = re.compile(
    r"[+\-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+\-]?\d+)?"
)
_THOUSANDS_COMMA_RE = re.compile(r"(?<=\d),(?=\d{3}(?:\D|$))")
_SPACES_RE = re.compile(r"\s+")


def _tick_in_view(
    tick: Text, ax_ext: Bbox, *, horizontal: bool, renderer: RendererBase
) -> bool:
    """True when the tick label's anchor lies inside the axes view.

    Matplotlib keeps out-of-range ticks on the artist tree (visible but
    clipped from the render). Their phantom extents inflate geometry-based
    tick checks, so exclude them.
    """
    try:
        ext = tick.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    if ext.width <= 0 or ext.height <= 0:
        return False
    if horizontal:
        anchor = (ext.x0 + ext.x1) / 2
        return bool(ax_ext.x0 - 0.5 <= anchor <= ax_ext.x1 + 0.5)
    anchor = (ext.y0 + ext.y1) / 2
    return bool(ax_ext.y0 - 0.5 <= anchor <= ax_ext.y1 + 0.5)


def iter_view_ticks(
    ax: Axes, axis: Literal["x", "y"], renderer: RendererBase
) -> Iterator[Text]:
    """Yield visible, non-empty tick labels whose anchors are in view."""
    try:
        ax_ext = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return

    horizontal = axis == "x"
    labels = ax.get_xticklabels() if horizontal else ax.get_yticklabels()
    for tick in labels:
        if not tick.get_visible() or not tick.get_text().strip():
            continue
        if _tick_in_view(
            tick, ax_ext, horizontal=horizontal, renderer=renderer
        ):
            yield tick


def _normalize_tick_text(text: str) -> str:
    normalized = text.strip().replace("\u2212", "-")
    normalized = _SPACES_RE.sub(" ", normalized)
    return _THOUSANDS_COMMA_RE.sub("", normalized)


def _looks_like_compact_category(
    prefix: str, number_str: str, suffix: str
) -> bool:
    """Filter compact labels such as ``Q1`` that are usually categories."""
    if suffix or " " in prefix or not prefix:
        return False
    if not number_str.lstrip("+-").isdigit():
        return False
    return any(ch.isalpha() for ch in prefix)


def split_tick_affixes(text: str) -> tuple[str, str, str] | None:
    """Split a rendered numeric tick into ``(prefix, number, suffix)``.

    The parser is intentionally shape-based: it accepts one numeric token
    with optional non-numeric text around it, normalizes thousands commas,
    and rejects math text or compact category labels such as ``Q1``.
    """
    normalized = _normalize_tick_text(text)
    if not normalized or "\\" in normalized:
        return None
    if normalized.startswith("$") and normalized.endswith("$"):
        return None

    matches = list(_NUMBER_RE.finditer(normalized))
    if len(matches) != 1:
        return None

    match = matches[0]
    prefix = normalized[: match.start()]
    number_str = match.group(0)
    suffix = normalized[match.end() :]
    if any(ch.isdigit() for ch in prefix + suffix):
        return None
    if _looks_like_compact_category(prefix, number_str, suffix):
        return None
    try:
        float(number_str)
    except ValueError:
        return None
    return prefix, number_str, suffix


def parse_numeric_tick(text: str) -> float | None:
    """Return the numeric value embedded in a rendered tick label."""
    parts = split_tick_affixes(text)
    if parts is None:
        return None
    try:
        return float(parts[1])
    except ValueError:
        return None


def adjacent_bboxes_overlap(
    bboxes: Sequence[Bbox], tol_px: float = 2.0
) -> bool:
    """Return True when adjacent bboxes overlap by more than ``tol_px``."""
    if len(bboxes) < 2:
        return False
    ordered = sorted(bboxes, key=lambda box: (box.x0, box.y0))
    for left, right in pairwise(ordered):
        x_overlap = min(left.x1, right.x1) - max(left.x0, right.x0)
        y_overlap = min(left.y1, right.y1) - max(left.y0, right.y0)
        if x_overlap > tol_px and y_overlap > tol_px:
            return True
    return False
