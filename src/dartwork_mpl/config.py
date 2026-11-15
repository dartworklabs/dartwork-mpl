"""Process-wide defaults for the library's own tick text.

``dm.config.tick_years`` and ``dm.config.number_ladder`` are read by the
``ticks`` slice wherever it writes default tick labels. Set them once, or
scope them with ``with dm.config.override(tick_years=4): ...``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, fields
from typing import Literal

__all__ = ["Config", "config"]


@dataclass(slots=True)
class Config:
    """Process-wide dartwork-mpl defaults.

    Slotted so a typo'd direct assignment (``dm.config.tick_year
    = 4`` — no "s") raises ``AttributeError`` instead of
    silently creating a dead attribute that never affects behaviour.

    Attributes
    ----------
    tick_years : {2, 4}, default ``2``
        Digits of the year in tick labels on axes nobody formatted (x axes
        whose data are integer years, ticked on whole years, and date axes,
        via ``dm.simple_layout``) and in
        ``dm.format_axis_dates``: ``24``, ``24.01``, ``24.Q1``. An axis whose
        two-digit years would repeat (a century in view) prints four on its
        own. ``4`` is the four-digit option (``2024``, ``2024.01``):
        ``with dm.config.override(tick_years=4):`` around the code from
        figure creation to the last ``dm.simple_layout``, or assign it.
    number_ladder : {"auto", "si", "myriad"}, default ``"auto"``
        Unit ladder for large numbers: the one-unit tick labels of axes
        nobody formatted (from 1,000,000) and ``dm.axis_unit(ladder="auto")``.
        ``"auto"`` picks 만/억/조/경 when the figure's axis labels, titles or
        legends hold Hangul (``0.2조 … 1.0조``) and SI k/M/G/T otherwise
        (``0.2T … 1.0T``); ``"si"`` always uses k/M/G/T and ``"myriad"``
        always uses 만/억/조/경. Any other value raises ``ValueError`` where
        it is read.
        ``"si"`` is the option for k/M/G/T in Korean figures too
        (``with dm.config.override(number_ladder="si"):``, or assign it).
    """

    tick_years: Literal[2, 4] = 2
    number_ladder: Literal["auto", "si", "myriad"] = "auto"

    @contextmanager
    def override(self, **overrides: object) -> Iterator[None]:
        """Temporarily override one or more defaults inside a ``with`` block.

        Restores every overridden field to its previous value on exit —
        including the exception path. Raises :class:`AttributeError` for
        any keyword that is not an existing :class:`Config` field, so a
        typo can't silently shadow the singleton with a new attribute.

        Parameters
        ----------
        **overrides
            ``field_name=value`` pairs. Every name must already exist on
            :class:`Config`.

        Yields
        ------
        None
            The block runs with the overridden defaults active.

        Example
        -------
        ::

            with dm.config.override(tick_years=4):
                dm.simple_layout(fig)   # four-digit years just here
        """
        known = {f.name for f in fields(self)}
        unknown = set(overrides) - known
        if unknown:
            raise AttributeError(
                f"dm.config has no attribute(s): {sorted(unknown)}. "
                f"Known fields: {sorted(known)}."
            )
        saved = {name: getattr(self, name) for name in overrides}
        for name, value in overrides.items():
            setattr(self, name, value)
        try:
            yield
        finally:
            for name, value in saved.items():
                setattr(self, name, value)


#: Process-wide :class:`Config` singleton. Mutate its attributes (or use
#: :meth:`Config.override`) to change the default of every dartwork-mpl
#: call site that reads it. Reachable as ``dm.config``.
config = Config()
