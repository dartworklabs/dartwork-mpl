"""A fixed gap, in points, between the content of neighbouring panels (``simple_layout(gutter=...)``)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..units import Length
from ._content_extent import _axes_content_extent_px
from ._fit_labels import MAX_GAP_FRACTION, gap_fraction, record_spacing

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpec


def parse_gutter(value: Length | str | float | None) -> float | None:
    """``gutter`` in points: a :class:`Length`, a unit string or points."""
    if value is None:
        return None
    if isinstance(value, Length):
        points = value.pt
    elif isinstance(value, str):
        points = Length(value.strip()).pt
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        points = float(value)
    else:
        raise TypeError(
            f"gutter must be Length, str, number or None; got {type(value).__name__}"
        )
    if not math.isfinite(points) or points < 0:
        raise ValueError(f"gutter must be a finite length >= 0; got {value!r}")
    return float(points)


def _cell(ax: Axes) -> tuple[range, range] | None:
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    top = spec.get_topmost_subplotspec()
    return top.rowspan, top.colspan


def fit_gutter(
    fig: Figure,
    gs: GridSpec,
    scope: Sequence[Axes],
    gutter_pt: float,
    renderer: RendererBase,
) -> float:
    """Set the ``wspace`` / ``hspace`` of ``gs`` so the narrowest gap between
    the content of facing panels is ``gutter_pt``.

    Content is what ``simple_layout`` measures for an Axes (tick labels,
    axis names, titles, panel labels, legends); a colour bar's Axes counts
    with the panel whose cell it splits. Two panels face each other across
    a gap when one ends at that column (row) and the other starts after it
    and they share a row (column). Matplotlib gives every gap of a grid the
    same width, so the narrowest pair sets it. Returns the largest change of
    a gap, in pixels (0 when nothing moved).
    """
    frame = getattr(gs, "figure", None) or fig
    nrows, ncols = gs.get_geometry()
    bottoms, tops, lefts, rights = gs.get_grid_positions(frame)
    fw, fh = frame.bbox.width, frame.bbox.height
    target = gutter_pt * fig.dpi / 72.0
    boxes: list[tuple[range, range, tuple[float, float, float, float]]] = []
    for ax in scope:
        cell = _cell(ax)
        if cell is None:
            continue
        spec = ax.get_subplotspec()
        if (
            spec is None
            or spec.get_topmost_subplotspec().get_gridspec() is not gs
        ):
            continue
        extent = _axes_content_extent_px(ax, renderer, fig)
        if extent is not None:
            boxes.append((cell[0], cell[1], extent))
    moved = 0.0
    params = gs.get_subplot_params(frame)
    for key, n, total in (
        ("wspace", ncols, (rights[-1] - lefts[0]) * fw),
        ("hspace", nrows, (tops[0] - bottoms[-1]) * fh),
    ):
        if n < 2:
            continue
        narrowest: float | None = None
        for k in range(n - 1):
            for rows_a, cols_a, (_ax0, ax1, ay0, _ay1) in boxes:
                for rows_b, cols_b, (bx0, _bx1, _by0, by1) in boxes:
                    if key == "wspace":
                        if cols_a.stop - 1 != k or cols_b.start != k + 1:
                            continue
                        if not set(rows_a) & set(rows_b):
                            continue
                        gap = bx0 - ax1
                    else:
                        if rows_a.stop - 1 != k or rows_b.start != k + 1:
                            continue
                        if not set(cols_a) & set(cols_b):
                            continue
                        gap = ay0 - by1
                    narrowest = (
                        gap if narrowest is None else min(narrowest, gap)
                    )
        if narrowest is None:
            continue
        if key == "wspace":
            sep = (lefts[1] - rights[0]) * fw
        else:
            sep = (bottoms[0] - tops[1]) * fh
        want = sep + (target - narrowest)
        if abs(want - sep) < 0.05:
            continue
        value = gap_fraction(max(want, 0.0), total, n)
        if value is None:
            continue
        # Content that grows as the panels shrink (an axis name longer than
        # its panel, centred on it) has no gap that fits; stop where
        # ``space`` would.
        value = min(value, MAX_GAP_FRACTION)
        before = getattr(params, key)
        record_spacing(gs, key, value)
        cell = total / (n + value * (n - 1))
        old_cell = total / (n + before * (n - 1))
        moved = max(moved, abs(value * cell - before * old_cell))
    return moved
