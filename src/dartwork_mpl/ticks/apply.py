"""The layout's tick hooks, delegating to ``formatting`` until ``ticks`` is rebuilt."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.figure import Figure


def prepare(fig: Figure, *, numbers: bool = True) -> None:
    """Ready every axis of ``fig`` before the layout measures it, once per call.

    With ``numbers``, the library's tick numbers and dates on axes nobody
    formatted; always, the spine of each twin scale and the series colours
    of twin pairs (not number formats, so ``numbers=False`` keeps them).
    """
    from ..formatting import (
        apply_default_tick_format,
        apply_twin_colors,
        show_twin_spines,
    )

    if numbers:
        apply_default_tick_format(fig)
    show_twin_spines(fig)
    apply_twin_colors(fig)


def thin_dates(fig: Figure) -> bool:
    """Give crowded date axes fewer ticks at the fitted size; whether one changed."""
    from ..formatting import thin_crowded_date_ticks

    return bool(thin_crowded_date_ticks(fig))


def remember_dates(fig: Figure) -> Callable[[], None]:
    """Record the date tick counts :func:`thin_dates` may lower; the call puts them back."""
    from ..formatting import remember_date_ticks

    return remember_date_ticks(fig)
