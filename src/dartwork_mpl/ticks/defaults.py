"""Process-wide defaults for the library's own tick text (``dm.config``).

``dm.config.tick_years`` and ``dm.config.number_ladder`` are read wherever
this slice writes default tick labels. Set them once, or scope them with
``with dm.config.override(tick_years=4): ...``.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, fields, replace

from .model import Digits, NumberLadder

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
        via ``dm.simple_layout``): ``24``, ``24.01``, ``24.Q1``. An axis whose
        two-digit years would repeat (a century in view) prints four on its
        own. ``4`` is the four-digit option (``2024``, ``2024.01``):
        ``with dm.config.override(tick_years=4):`` around the code from
        figure creation to the last ``dm.simple_layout``, or assign it.
    number_ladder : {"auto", "si", "myriad"}, default ``"auto"``
        Unit ladder for large numbers: the one-unit tick labels of axes
        nobody formatted (from 1,000,000).
        ``"auto"`` picks 만/억/조/경 when the figure's axis labels, titles or
        legends hold Hangul (``0.2조 … 1.0조``) and SI k/M/G/T otherwise
        (``0.2T … 1.0T``); ``"si"`` always uses k/M/G/T and ``"myriad"``
        always uses 만/억/조/경. Any other value raises ``ValueError`` where
        it is read.
        ``"si"`` is the option for k/M/G/T in Korean figures too
        (``with dm.config.override(number_ladder="si"):``, or assign it).
    """

    tick_years: Digits = 2
    number_ladder: NumberLadder = "auto"

    @contextmanager
    def override(
        self,
        *,
        tick_years: Digits | None = None,
        number_ladder: NumberLadder | None = None,
        **unknown: object,
    ) -> Generator[None]:
        """Temporarily override one or more defaults inside a ``with`` block.

        Restores every overridden field to its previous value on exit —
        including the exception path. Raises :class:`AttributeError` for
        any keyword that is not an existing :class:`Config` field, so a
        typo can't silently shadow the singleton with a new attribute.

        Parameters
        ----------
        tick_years, number_ladder
            The defaults to change inside the block (``None``: unchanged).
        **unknown
            Any other keyword raises :class:`AttributeError`.

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
        if unknown:
            known = {f.name for f in fields(self)}
            raise AttributeError(
                f"dm.config has no attribute(s): {sorted(unknown)}. "
                f"Known fields: {sorted(known)}."
            )
        saved = replace(self)
        if tick_years is not None:
            self.tick_years = tick_years
        if number_ladder is not None:
            self.number_ladder = number_ladder
        try:
            yield
        finally:
            if tick_years is not None:
                self.tick_years = saved.tick_years
            if number_ladder is not None:
                self.number_ladder = saved.number_ladder


#: Process-wide :class:`Config` singleton. Mutate its attributes (or use
#: :meth:`Config.override`) to change the default of every dartwork-mpl
#: call site that reads it. Reachable as ``dm.config``.
config = Config()
