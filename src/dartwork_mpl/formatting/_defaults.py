"""The library's tick numbers on axes nobody formatted.

Left to matplotlib, an axis prints ``1750`` and ``34000`` without separators
and ``0.5 … 2.5`` under a ``1e6`` corner label, so every agent or person
installs a formatter of their own and the same data reads differently from
figure to figure. :func:`apply_default_tick_format` settles it once:

- an axis whose visible ticks reach 1,000 gets thousands separators
  (``1,750``; ``34,000``) and the fewest exact decimals;
- from one million the axis takes the largest tick's SI unit (``0.5M …
  2.5M``), as ``dm.format_axis_si`` does, unless that needs more than two
  decimals;
- smaller axes (``0, 250 … 750``; ``0.5, 1.0``), x axes whose ticks all sit
  in 1000-2999 (years), log and category axes, colorbars and any axis with a
  formatter someone chose keep theirs;
- date axes are concise in every preset (``date.converter: concise``:
  ``2024, Mar, May … 2025``); when the figure's axis labels, titles or legend
  are Korean they read ``2024년, 3월, 5월 … 2025년`` so a Korean figure does
  not mix in English month names.

``dm.simple_layout`` calls it before measuring (``format_ticks=False`` opts
out), so the numbers it fits are the numbers saved. After fitting it calls
:func:`thin_crowded_date_ticks`: matplotlib picks date ticks from the date
range alone, so on a narrow axis concise labels run into each other
(``2021년 5월 9월 2022년``); the locator then takes fewer ticks until
neighbouring labels are one em apart.
"""

from __future__ import annotations

import datetime
import re
import warnings
from collections.abc import Sequence
from itertools import pairwise
from typing import Any, Literal

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from matplotlib.axis import Axis
from matplotlib.figure import Figure
from matplotlib.text import Text

from ._axis_wide import AxisUnitFormatter, Unit
from ._decimals import fewest_exact_decimals

__all__ = [
    "DefaultNumberFormatter",
    "KoreanConciseDateFormatter",
    "apply_default_tick_format",
    "thin_crowded_date_ticks",
]

_SEPARATOR_FROM = 1_000.0
_UNIT_FROM = 1_000_000.0
_MAX_UNIT_DECIMALS = 2
_YEARS = (1_000.0, 2_999.0)
# Neighbouring date labels keep at least this many ems between them.
_MIN_DATE_GAP_EM = 1.0


class DefaultNumberFormatter(AxisUnitFormatter):
    """Thousands separators below one million, the largest tick's unit above."""

    def __init__(self, ladder: Sequence[Unit]) -> None:
        super().__init__(ladder, "max")

    def _axis_unit(self, values: Sequence[float]) -> Unit:
        top = max(abs(v) for v in values)
        if top < _UNIT_FROM * (1 - 1e-9):
            return self._ladder[0]
        unit = self._max_unit(top)
        scaled = [abs(v) / unit.factor for v in values]
        if fewest_exact_decimals(scaled) > _MAX_UNIT_DECIMALS:
            return self._ladder[0]
        return unit


_TITLE_LOCS: tuple[Literal["left", "center", "right"], ...] = (
    "left",
    "center",
    "right",
)
_HANGUL = re.compile("[\uac00-\ud7a3]")
# "03월" -> "3월", "08일" -> "8일": Korean dates drop the zero padding.
_PADDED = re.compile(r"(?<!\d)0(\d)(?=[월일])")


class KoreanConciseDateFormatter(mdates.ConciseDateFormatter):
    """Matplotlib's concise date ticks with Korean year, month and day units."""

    def __init__(
        self,
        locator: mdates.DateLocator,
        tz: datetime.tzinfo | str | None = None,
    ) -> None:
        super().__init__(  # type: ignore[no-untyped-call]
            locator,
            tz=tz,
            formats=["%Y년", "%m월", "%d일", "%H:%M", "%H:%M", "%S.%f"],
            zero_formats=["", "%Y년", "%m월", "%m월 %d일", "%H:%M", "%H:%M"],
            offset_formats=[
                "",
                "%Y년",
                "%Y년 %m월",
                "%Y년 %m월 %d일",
                "%Y년 %m월 %d일",
                "%Y년 %m월 %d일 %H:%M",
            ],
        )

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Format the ticks, without zero padding before 월 and 일."""
        labels: list[str] = super().format_ticks(values)  # type: ignore[no-untyped-call]
        return [_PADDED.sub(r"\1", label) for label in labels]

    def get_offset(self) -> str:
        """The corner label, without zero padding before 월 and 일."""
        offset: str = super().get_offset()  # type: ignore[no-untyped-call]
        return _PADDED.sub(r"\1", offset)


def _korean_labels(fig: Figure) -> bool:
    """Whether the figure's axis labels, titles or legends are Korean."""
    texts: list[str] = []
    for ax in fig.axes:
        texts += [ax.get_xlabel(), ax.get_ylabel()]
        texts += [ax.get_title(loc=loc) for loc in _TITLE_LOCS]
        legend = ax.get_legend()
        if legend is not None:
            texts += [t.get_text() for t in legend.get_texts()]
    for legend in fig.legends:
        texts += [t.get_text() for t in legend.get_texts()]
    for name in ("_suptitle", "_supxlabel", "_supylabel"):
        artist = getattr(fig, name, None)
        if artist is not None:
            texts.append(artist.get_text())
    return any(_HANGUL.search(t) for t in texts)


def _visible_ticks(axis: Axis) -> list[float]:
    low, high = sorted(float(v) for v in axis.get_view_interval())
    return [
        float(t) for t in axis.get_majorticklocs() if low <= float(t) <= high
    ]


def _untouched(axis: Axis) -> bool:
    # Exactly matplotlib's default: a subclass or another formatter was chosen.
    return type(axis.get_major_formatter()) is ticker.ScalarFormatter


def apply_default_tick_format(fig: Figure) -> int:
    """Install the library's tick numbers on every axis nobody formatted.

    Returns the number of axes changed. Safe to call again: an axis that
    already carries the default formatter is no longer ``ScalarFormatter``.
    """
    from . import _SI_LADDER  # defined after this module is imported

    changed = 0
    korean = _korean_labels(fig)
    for ax in fig.axes:
        if (
            ax.name != "rectilinear"
            or getattr(ax, "_colorbar", None) is not None
        ):
            continue
        for which, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            fmt = axis.get_major_formatter()
            if korean and type(fmt) is mdates.ConciseDateFormatter:
                locator = axis.get_major_locator()
                if isinstance(locator, mdates.DateLocator):
                    axis.set_major_formatter(
                        KoreanConciseDateFormatter(locator, tz=fmt._tz)
                    )
                    changed += 1
                continue
            if not _untouched(axis) or axis.get_scale() != "linear":
                continue
            ticks = _visible_ticks(axis)
            if not ticks or max(abs(t) for t in ticks) < _SEPARATOR_FROM:
                continue
            if which == "x" and all(_YEARS[0] <= t <= _YEARS[1] for t in ticks):
                continue  # years: 2024, not 2,024
            axis.set_major_formatter(DefaultNumberFormatter(_SI_LADDER))
            changed += 1
    return changed


def _date_label_gap_em(
    axis: Axis, locs: Sequence[float], fig: Figure, renderer: Any
) -> float:
    """Smallest gap between neighbouring tick labels, in ems of their font."""
    if len(locs) < 2:
        return float("inf")
    ax = axis.axes
    label = axis.get_major_ticks(1)[0].label1
    labels = axis.get_major_formatter().format_ticks(list(locs))
    along_x = axis is ax.xaxis
    if along_x:
        transform = ax.get_xaxis_transform()
        points = [(v, 0.0) for v in locs]
    else:
        transform = ax.get_yaxis_transform()
        points = [(0.0, v) for v in locs]
    centres = transform.transform(points)[:, 0 if along_x else 1]
    spans = []
    for centre, text in zip(centres, labels, strict=True):
        probe = Text(0, 0, text, fontproperties=label.get_fontproperties())
        probe.set_figure(fig)
        box = probe.get_window_extent(renderer)
        half = (box.width if along_x else box.height) / 2
        spans.append((centre - half, centre + half))
    spans.sort()
    gap = min(b[0] - a[1] for a, b in pairwise(spans))
    em_px = label.get_fontproperties().get_size_in_points() * fig.dpi / 72.0
    return float(gap / em_px)


def _visible_locs(
    axis: Axis, locator: mdates.AutoDateLocator
) -> list[float] | None:
    """Ticks inside the view, or ``None`` when matplotlib would warn."""
    low, high = sorted(float(v) for v in axis.get_view_interval())
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            locs = locator()
        except UserWarning:
            return None  # no interval gives this few ticks
    return [float(v) for v in locs if low <= float(v) <= high]


def _converter_locator(locator: ticker.Locator) -> bool:
    """Whether the locator is the one matplotlib's date converter made."""
    if type(locator) is not mdates.AutoDateLocator:
        return False
    fresh = mdates.AutoDateLocator()  # type: ignore[no-untyped-call]
    return (
        locator.minticks == fresh.minticks
        and locator.maxticks == fresh.maxticks
        and bool(locator.interval_multiples)
    )


def thin_crowded_date_ticks(fig: Figure) -> int:
    """Give a crowded concise date axis fewer ticks; return the axes changed.

    Acts only on axes matplotlib's date converter set up (an
    ``AutoDateLocator`` with its default tick counts and concise labels)
    whose labels are not rotated, so a locator someone configured, or one
    already thinned, is kept.
    Each step lowers the locator's tick ceiling, skipping ceilings
    matplotlib cannot meet; the first that keeps neighbouring labels
    :data:`_MIN_DATE_GAP_EM` ems apart with two or more ticks wins. An axis
    with no such ceiling is left as it was.
    """
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    changed = 0
    for ax in fig.axes:
        if ax.name != "rectilinear":
            continue
        for axis in (ax.xaxis, ax.yaxis):
            locator = axis.get_major_locator()
            if not _converter_locator(locator) or not isinstance(
                axis.get_major_formatter(), mdates.ConciseDateFormatter
            ):
                continue
            assert isinstance(locator, mdates.AutoDateLocator)
            label = axis.get_major_ticks(1)[0].label1
            if axis is ax.xaxis and label.get_rotation() % 180:
                continue
            locs = _visible_locs(axis, locator)
            if (
                locs is None
                or _date_label_gap_em(axis, locs, fig, renderer)
                >= _MIN_DATE_GAP_EM
            ):
                continue
            original = (locator.minticks, dict(locator.maxticks))
            for ceiling in range(max(locator.maxticks.values()) - 1, 1, -1):
                locator.maxticks = dict.fromkeys(locator.maxticks, ceiling)
                locator.minticks = min(original[0], ceiling - 1)
                candidate = _visible_locs(axis, locator)
                if candidate is None or len(candidate) < 2 or candidate == locs:
                    continue
                gap = _date_label_gap_em(axis, candidate, fig, renderer)
                if gap >= _MIN_DATE_GAP_EM:
                    changed += 1
                    break
            else:
                locator.minticks, locator.maxticks = original
    return changed
