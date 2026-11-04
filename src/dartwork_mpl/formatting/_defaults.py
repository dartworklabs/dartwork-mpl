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
out), so the numbers it fits are the numbers saved.
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from typing import Literal

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from matplotlib.axis import Axis
from matplotlib.figure import Figure

from ._axis_wide import AxisUnitFormatter, Unit
from ._decimals import fewest_exact_decimals

__all__ = [
    "DefaultNumberFormatter",
    "KoreanConciseDateFormatter",
    "apply_default_tick_format",
]

_SEPARATOR_FROM = 1_000.0
_UNIT_FROM = 1_000_000.0
_MAX_UNIT_DECIMALS = 2
_YEARS = (1_000.0, 2_999.0)


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
