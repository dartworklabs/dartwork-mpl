"""Year helpers: what counts as a year axis, where its ticks go, how they read.

Two-digit years (``16, 18, 20``) are the default tick text on year axes. A
year axis is decided from the plotted data (:func:`year_data`: integers in
1900-2099), never from the ticks or the label text, because the ticks move
when ``dm.simple_layout`` refits the margins. On such an axis
:class:`WholeYearLocator` puts every tick on a whole year and
:class:`YearTickFormatter` prints it, four digits when two visible years would
print alike (``1900`` and ``2000``); a tick that is not a whole year (a zoom
between two years) gets no label rather than a rounded one.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt

__all__ = [
    "WholeYearLocator",
    "YearTickFormatter",
    "requested_params",
    "two_digits_repeat",
    "whole_years",
    "year_data",
]

_FIRST_YEAR = 1900
_LAST_YEAR = 2099
# Bar centres are rebuilt as x + width / 2, a few ulps off the year.
_WHOLE_TOL = 1e-6


def _whole(value: float) -> bool:
    # Finite first: round() of an infinity raises; NaN is not finite.
    return math.isfinite(value) and abs(value - round(value)) <= _WHOLE_TOL


def _whole_year(value: float) -> bool:
    return _FIRST_YEAR <= value <= _LAST_YEAR and _whole(value)


def year_data(values: npt.ArrayLike) -> bool:
    """Whether plotted values are years: two or more, all integers in 1900-2099."""
    data = np.asarray(values, dtype=float).ravel()
    if len(np.unique(data)) < 2:
        return False
    return all(_whole_year(float(v)) for v in data)


def whole_years(ticks: Sequence[float]) -> bool:
    """Whether there are ticks and every one is a whole year in 1900-2099."""
    return bool(ticks) and all(_whole_year(float(t)) for t in ticks)


def two_digits_repeat(years: Sequence[int]) -> bool:
    """Whether two distinct years share their last two digits."""
    seen: dict[int, int] = {}
    return any(seen.setdefault(year % 100, year) != year for year in years)


# MaxNLocator settings someone can change on matplotlib's own locator in
# place (``ax.locator_params``, ``locator.set_params``), which leaves
# ``isDefault_majloc`` set; the year locator carries them over.
_CARRIED = {
    "nbins": "_nbins",
    "steps": "_steps",
    "prune": "_prune",
    "symmetric": "_symmetric",
    "min_n_ticks": "_min_n_ticks",
}
_YEAR_STEPS = (1, 2, 5, 10)


def _same(a: object, b: object) -> bool:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return bool(np.array_equal(np.asarray(a), np.asarray(b)))
    return a == b


def requested_params(locator: ticker.Locator) -> dict[str, Any]:
    """The settings someone changed on matplotlib's own tick locator.

    ``ax.locator_params(axis="x", nbins=3)`` and
    ``ax.xaxis.get_major_locator().set_params(...)`` edit the default
    ``AutoLocator`` in place. Returns each ``nbins``, ``steps``, ``prune``,
    ``symmetric`` or ``min_n_ticks`` that differs from a fresh
    ``AutoLocator``; ``{}`` for a locator that is not a ``MaxNLocator``.
    """
    if not isinstance(locator, ticker.MaxNLocator):
        return {}
    mine, fresh = vars(locator), vars(ticker.AutoLocator())
    return {
        name: mine.get(attr)
        for name, attr in _CARRIED.items()
        if not _same(mine.get(attr), fresh.get(attr))
    }


class WholeYearLocator(ticker.MaxNLocator):
    """Ticks on whole years, every 1, 2, 5, 10, 20, 50 … years.

    Matplotlib's tick count for the axis length (``nbins="auto"``) on whole
    numbers only, so annual data never ticks ``2007.5``. ``requested``
    MaxNLocator settings (from :func:`requested_params`: ``nbins=3`` asked
    of matplotlib's locator) replace the defaults; ticks stay whole. Every
    later :meth:`set_params` (``ax.locator_params``) is a request too.
    ``dm.simple_layout`` lowers an unrequested ``nbins`` (:meth:`thin`) when
    the labels end up closer than one em; a requested one is kept. A view
    narrower than two whole years falls back to fractions, which
    :class:`YearTickFormatter` leaves unlabelled.
    """

    requested: frozenset[str] = frozenset()

    def __init__(self, **requested: Any) -> None:
        super().__init__(
            **{
                "nbins": "auto",
                "steps": list(_YEAR_STEPS),
                **requested,
                "integer": True,
            }
        )
        self.requested = frozenset(requested)

    def set_params(self, **kwargs: Any) -> None:
        """Set MaxNLocator parameters; each one set here is a request."""
        super().set_params(**kwargs)
        self.requested = self.requested | frozenset(kwargs)

    @property
    def nbins(self) -> int | Literal["auto"]:
        """The tick-count ceiling (``"auto"``: from the axis length)."""
        count: int | Literal["auto"] = vars(self)["_nbins"]
        return count

    def thin(self, nbins: int | Literal["auto"]) -> None:
        """Set the library's own ``nbins`` (layout thinning), not a request."""
        ticker.MaxNLocator.set_params(self, nbins=nbins)


class YearTickFormatter(ticker.Formatter):
    """Whole years as two digits (``24``) or four (``2024``).

    For year axes, under :class:`WholeYearLocator` or whole years someone
    pinned. ``suffix`` is appended to every year (``"년"``). Each
    :meth:`set_locs` (every draw) reads the whole years in view: with
    ``digits=2`` they print four digits when two would repeat (``1900,
    2000``; ``2000 … 2100``). Every whole tick is a year, the ``2100`` at the
    edge of data reaching 2099 included; a tick between years gets no label.
    The cursor readout (:meth:`format_data_short`) is the value itself
    (``2007.53``), as matplotlib's number axes write it: a cursor sits
    between years.
    """

    def __init__(self, digits: Literal[2, 4], suffix: str = "") -> None:
        if digits not in (2, 4):
            raise ValueError(f"digits must be 2 or 4, got {digits!r}")
        self.digits = digits
        self.suffix = suffix
        self._four = digits == 4
        self._cursor = ticker.ScalarFormatter()

    def set_axis(self, axis: Any) -> None:
        """Attach this formatter (and its cursor readout) to ``axis``."""
        super().set_axis(axis)
        self._cursor.set_axis(axis)

    def set_locs(self, locs: Sequence[float]) -> None:
        """Choose two or four digits from the whole years in view."""
        values = [float(v) for v in locs]
        super().set_locs(values)
        axis = getattr(self, "axis", None)
        if axis is not None:
            low, high = sorted(float(v) for v in axis.get_view_interval())
            values = [v for v in values if low <= v <= high]
        years = [round(v) for v in values if _whole(v)]
        self._four = self.digits == 4 or two_digits_repeat(years)

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One tick's label: the year, or nothing between years."""
        if not _whole(float(x)):
            return ""
        year = round(x)
        body = f"{year}" if self._four else f"{year % 100:02d}"
        return f"{body}{self.suffix}"

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Labels for the ticks, the year digits chosen over those in view."""
        self.set_locs(values)
        return [self(value, i) for i, value in enumerate(values)]

    def format_data_short(self, value: float) -> str:
        """The cursor readout: the value at the axis's resolution."""
        if getattr(self._cursor, "axis", None) is None:
            return f"{value:g}"
        return str(self._cursor.format_data_short(value))
