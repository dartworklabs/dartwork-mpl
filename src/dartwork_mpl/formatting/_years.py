"""Year helpers: what counts as a year axis, where its ticks go, how they read.

Two-digit years (``16, 18, 20``) are the default tick text on year axes. A
year axis is decided from the plotted data (:func:`year_data`: integers in
1900-2099), never from the ticks or the label text, because the ticks move
when ``dm.simple_layout`` refits the margins. On such an axis
:class:`WholeYearLocator` puts every tick on a whole year and
:class:`YearTickFormatter` prints it, four digits when two visible years would
print alike (``1900`` and ``2000``); a tick that is not a whole year (a zoom
between two years) gets no label rather than a rounded one. What someone asked
of matplotlib's own locator or formatter in place (``ax.locator_params``,
``ax.ticklabel_format``) carries over (:func:`requested_params`,
:func:`requested_format`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axis import Axis

__all__ = [
    "WholeYearLocator",
    "YearTickFormatter",
    "requested_format",
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
    """Whether plotted values are years: two or more, all integers in 1900-2099.

    Vectorised, cheapest test first: the range (``min`` / ``max``; a NaN or
    infinity fails it) rejects most non-year data in one pass, then one
    in-place pass checks every value is whole.
    """
    data = np.asarray(values, dtype=float).ravel()
    if data.size < 2:
        return False
    low, high = float(data.min()), float(data.max())
    if not (_FIRST_YEAR <= low < high <= _LAST_YEAR):
        return False  # out of range, NaN, or one value only
    off = np.rint(data)
    np.subtract(data, off, out=off)
    np.abs(off, out=off)
    return bool((off <= _WHOLE_TOL).all())


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


def requested_format(formatter: ticker.Formatter) -> dict[str, Any]:
    """The settings someone changed on matplotlib's own tick formatter.

    ``ax.ticklabel_format(axis="x", useOffset=False)`` and the
    ``set_useOffset`` / ``set_scientific`` / ``set_powerlimits`` /
    ``set_useMathText`` / ``set_useLocale`` calls behind it edit the default
    ``ScalarFormatter`` in place, leaving ``isDefault_majfmt`` set. Returns
    each setting that differs from a fresh ``ScalarFormatter``, keyed as
    :class:`YearTickFormatter` takes it (``useOffset``: ``False``, ``True``
    or a fixed offset; ``scientific``; ``powerlimits``; ``useMathText``;
    ``useLocale``); ``{}`` for any other formatter. A value equal to
    matplotlib's default (``useOffset=True``) cannot be told from no request.
    """
    if type(formatter) is not ticker.ScalarFormatter:
        return {}
    fresh = ticker.ScalarFormatter()
    asked: dict[str, Any] = {}
    if not formatter.get_useOffset() and formatter.offset:
        asked["useOffset"] = formatter.offset  # a fixed offset
    elif formatter.get_useOffset() != fresh.get_useOffset():
        asked["useOffset"] = formatter.get_useOffset()
    # No public getters for these two (matplotlib 3.11).
    mine, base = vars(formatter), vars(fresh)
    if mine["_scientific"] != base["_scientific"]:
        asked["scientific"] = mine["_scientific"]
    if tuple(mine["_powerlimits"]) != tuple(base["_powerlimits"]):
        asked["powerlimits"] = tuple(mine["_powerlimits"])
    if formatter.get_useMathText() != fresh.get_useMathText():
        asked["useMathText"] = formatter.get_useMathText()
    if formatter.get_useLocale() != fresh.get_useLocale():
        asked["useLocale"] = formatter.get_useLocale()
    return asked


class YearTickFormatter(ticker.ScalarFormatter):
    """Whole years as two digits (``24``) or four (``2024``).

    ``suffix`` is appended to every year (``"년"``). Each :meth:`set_locs`
    (every draw) reads the ticks in view: with ``digits=2`` the years print
    four digits when two would repeat (``1900, 2000``; ``2000 … 2100``).
    Every whole tick is a year, the ``2100`` at the edge of data reaching
    2099 included. What a draw with a tick between years prints is decided
    from the axis's locator at that draw, so a locator set later counts:

    - under :class:`WholeYearLocator` (whole years except in a view under
      two years) that tick gets no label;
    - under any other locator (``MaxNLocator``, ``AutoLocator``, pinned
      ``set_xticks``) every tick prints its plain value (``2005.0,
      2007.5``), no offset, never a rounded year; with every tick in view a
      whole year, the years.

    It is matplotlib's ``ScalarFormatter`` without an offset (``useOffset``
    defaults to ``False``), so ``ax.ticklabel_format`` and its setters work
    on it; the keywords set the same settings at construction (what
    :func:`requested_format` read off matplotlib's formatter). A year label
    already has no offset and no exponent, so ``useOffset=False`` and
    ``style="plain"`` keep the years. When the settings would give the ticks
    in view an exponent or an offset (``scilimits=(0, 0)``,
    ``useOffset=2000``), every tick prints as matplotlib's ScalarFormatter
    prints it, corner label included, on the same whole-year ticks.

    The cursor readout (:meth:`format_data_short`) is the value itself
    (``2007.53``), as matplotlib's number axes write it: a cursor sits
    between years. Like matplotlib's ScalarFormatter it formats an axis's
    ticks: give it one (``set_axis``) before formatting.
    """

    def __init__(
        self,
        digits: Literal[2, 4],
        suffix: str = "",
        *,
        useOffset: bool | float = False,  # matplotlib's keyword names
        scientific: bool | None = None,
        powerlimits: tuple[int, int] | None = None,
        useMathText: bool | None = None,
        useLocale: bool | None = None,
    ) -> None:
        if digits not in (2, 4):
            raise ValueError(f"digits must be 2 or 4, got {digits!r}")
        super().__init__(
            useOffset=useOffset, useMathText=useMathText, useLocale=useLocale
        )
        if scientific is not None:
            self.set_scientific(scientific)
        if powerlimits is not None:
            self.set_powerlimits(powerlimits)
        self.digits = digits
        self.suffix = suffix
        self._four = digits == 4
        self._numbers = False

    def set_locs(self, locs: Sequence[float]) -> None:
        """Choose years (two or four digits) or numbers from the ticks in view.

        Matplotlib's ScalarFormatter settles the offset, exponent and
        decimals first; the years stand unless those put an offset or an
        exponent on the ticks.
        """
        axis = self.axis
        if axis is None:
            raise ValueError("YearTickFormatter needs an axis: call set_axis")
        values = [float(v) for v in locs]
        super().set_locs(values)
        low, high = sorted(float(v) for v in axis.get_view_interval())
        shown = [v for v in values if low <= v <= high]
        ours = isinstance(axis, Axis) and isinstance(
            axis.get_major_locator(), WholeYearLocator
        )
        between = not all(_whole(v) for v in shown)
        self._numbers = bool(self.get_offset()) or (between and not ours)
        years = [round(v) for v in shown if _whole(v)]
        self._four = self.digits == 4 or two_digits_repeat(years)

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One tick's label: the year, a number, or nothing."""
        if self._numbers:
            return str(super().__call__(x, pos))
        if not _whole(float(x)):
            return ""
        year = round(x)
        body = f"{year}" if self._four else f"{year % 100:02d}"
        return f"{body}{self.suffix}"
