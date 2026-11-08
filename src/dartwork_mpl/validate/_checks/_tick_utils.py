"""Shared helpers for validation checks that inspect tick labels."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from ..._figure_geometry import drawn_tick_labels
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


def iter_view_ticks(
    ax: Axes, axis: Literal["x", "y"], renderer: RendererBase
) -> Iterator[Text]:
    """Yield the major tick labels with text that matplotlib draws.

    A label counts when :func:`~dartwork_mpl._figure_geometry.drawn_tick_labels`
    says matplotlib draws it: its tick lies in the view interval (with
    matplotlib's 1e-10 relative slack) on a visible Axes whose axis is on.
    Matplotlib keeps the other labels on the artist tree, visible and
    positioned, but never draws them; a box test would count a y label
    just above the limit (its centre-baseline box reaches into the view)
    and miss a turned first label whose box leaves the plot. Labels come in
    ``get_xticklabels`` order: bottom / left ones, then top / right.
    """
    labels = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
    drawn = {id(label) for label in drawn_tick_labels(ax, axis)}
    for tick in labels:
        if id(tick) not in drawn or not tick.get_text().strip():
            continue
        try:
            ext = tick.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width > 0 and ext.height > 0:
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
