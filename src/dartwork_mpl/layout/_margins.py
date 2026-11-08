"""Margin parsing and GridSpec edge arithmetic for ``simple_layout`` (no measurement)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ..units import Length

# Minimum slack between opposing GridSpec edges, in figure-fraction.
# Keeps left < right and bottom < top so the GridSpec rectangle stays
# valid even when the requested margins consume the whole figure.
_EDGE_EPSILON: float = 1e-3


# ─────────────────────────────────────────────────────────────────────
# margin parsing
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _PercentMargin:
    """A margin written as ``"<n>%"``: ``percent`` hundredths of the figure extent."""

    percent: float


@dataclass(frozen=True)
class _PhysicalMargin:
    """A margin given as a physical :class:`Length` (or a unit string)."""

    length: Length


@dataclass(frozen=True)
class _FractionMargin:
    """A margin given as a bare number: already a figure fraction."""

    fraction: float


_Margin: TypeAlias = _PercentMargin | _PhysicalMargin | _FractionMargin


def _parse_margin(value: Length | str | float | int) -> _Margin:
    """Parse one public margin spec into its :data:`_Margin` variant.

    Accepts a :class:`Length`; a ``"5%"`` percentage string; a unit string
    :class:`Length` parses (``"5mm"``, ``"0.5cm"``, ``"0.1in"``, ``"24pt"``);
    or a non-bool ``int`` / ``float`` figure fraction (``0.05`` = 5 %).
    Raises ``ValueError`` for an unparseable string and ``TypeError`` for
    any other type.
    """
    if isinstance(value, Length):
        return _PhysicalMargin(value)
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("%"):
            return _PercentMargin(float(s[:-1]))
        return _PhysicalMargin(Length(s))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _FractionMargin(float(value))
    raise TypeError(
        f"margin must be Length, str, or number; got {type(value).__name__}"
    )


def _margin_fraction(margin: _Margin, fig_extent_inch: float) -> float:
    """Return ``margin`` as a fraction of a figure extent of ``fig_extent_inch`` inches."""
    match margin:
        case _PercentMargin(percent=percent):
            return percent / 100.0
        case _PhysicalMargin(length=length):
            return length.inch / fig_extent_inch
        case _FractionMargin(fraction=fraction):
            return fraction


@dataclass(frozen=True)
class _Sides:
    """One value per figure edge (figure fractions for margins and reservations)."""

    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class _MarginSpec:
    """The margin of every edge, each side parsed once from ``simple_layout``'s arguments."""

    left: _Margin
    right: _Margin
    bottom: _Margin
    top: _Margin

    def fractions(self, fig_w_in: float, fig_h_in: float) -> _Sides:
        """Return the margins as figure fractions: left/right of the width, bottom/top of the height."""
        return _Sides(
            left=_margin_fraction(self.left, fig_w_in),
            right=_margin_fraction(self.right, fig_w_in),
            bottom=_margin_fraction(self.bottom, fig_h_in),
            top=_margin_fraction(self.top, fig_h_in),
        )


def _parse_margins(
    margin: Length | str | float | None,
    ml: Length | str | float | None,
    mr: Length | str | float | None,
    mt: Length | str | float | None,
    mb: Length | str | float | None,
) -> _MarginSpec:
    """Parse ``simple_layout``'s margins: each per-side value, else ``margin``.

    ``margin=None`` means no margin. Parses ``margin`` first, then ``ml``,
    ``mr``, ``mt``, ``mb``, so the first bad value in that order raises (see
    :func:`_parse_margin`).
    """
    base = _FractionMargin(0.0) if margin is None else _parse_margin(margin)

    def side(value: Length | str | float | None) -> _Margin:
        """Return the parsed per-side ``value``, or ``margin``'s when it is ``None``."""
        return base if value is None else _parse_margin(value)

    left, right, top, bottom = side(ml), side(mr), side(mt), side(mb)
    return _MarginSpec(left=left, right=right, bottom=bottom, top=top)


@dataclass(frozen=True)
class _GridEdges:
    """GridSpec ``left/right/bottom/top`` in figure fraction."""

    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class _LayoutStep:
    """One solver iteration: the new edges and the largest edge move in pixels."""

    edges: _GridEdges
    delta_px: float


def _solve_edges(
    overhang: _Sides,
    reserved: _Sides,
    margins: _Sides,
    last_edges: _GridEdges | None,
    fw_px: float,
    fh_px: float,
) -> _LayoutStep:
    """Compute GridSpec edges that put the axes content ``margins`` from each figure edge.

    Pure arithmetic, no measurement. ``overhang`` is how far the measured
    content sticks out of the axes boxes on each side and ``reserved`` the
    room figure-level artists claim, both in figure fraction. Edges are
    clamped into ``[0, 1]`` keeping ``_EDGE_EPSILON`` between opposite edges.
    ``delta_px`` is the largest edge move from ``last_edges`` in display
    pixels, or ``inf`` when there is no previous step.
    """
    new_l = reserved.left + margins.left + overhang.left
    new_r = (1.0 - reserved.right) - margins.right - overhang.right
    new_b = reserved.bottom + margins.bottom + overhang.bottom
    new_t = (1.0 - reserved.top) - margins.top - overhang.top

    # Sanity clamp: keep edges in [0, 1] and ensure at least
    # ``_EDGE_EPSILON`` slack between left/right and bottom/top.
    new_l = max(0.0, min(new_l, 1.0 - _EDGE_EPSILON))
    new_r = min(1.0, max(new_r, new_l + _EDGE_EPSILON))
    new_b = max(0.0, min(new_b, 1.0 - _EDGE_EPSILON))
    new_t = min(1.0, max(new_t, new_b + _EDGE_EPSILON))

    if last_edges is not None:
        delta_px = max(
            abs(new_l - last_edges.left) * fw_px,
            abs(new_r - last_edges.right) * fw_px,
            abs(new_b - last_edges.bottom) * fh_px,
            abs(new_t - last_edges.top) * fh_px,
        )
    else:
        delta_px = float("inf")

    return _LayoutStep(_GridEdges(new_l, new_r, new_b, new_t), delta_px)
