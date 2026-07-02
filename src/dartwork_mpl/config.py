"""Process-wide defaults for dartwork-mpl behaviour toggles.

Each public-API call site that exposes a boolean keyword whose default
matters across an entire project (rather than per-call) reads its
fallback from the :class:`Config` singleton :data:`config` here. Set it
once, near the top of your program (or in a notebook's first cell), and
every subsequent call across :mod:`~dartwork_mpl.layout` and
:mod:`~dartwork_mpl.io` honours the new default without you having to
thread the keyword through every call site.

The keyword argument on each function stays available for per-call
overrides — passing it explicitly always wins over the global default.

Example
-------
::

    import matplotlib.pyplot as plt
    import dartwork_mpl as dm

    # One-off: turn the orphan-tick adoption off project-wide.
    dm.config.adopt_orphan_tick_font = False

    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([1, 2, 3], [1, 4, 9])  # no axis label
    dm.simple_layout(fig)          # tick fonts left untouched

    # Per-call override is still honoured.
    dm.simple_layout(fig, adopt_orphan_tick_font=True)

    # Or scope the change to a block.
    with dm.config.override(adopt_orphan_tick_font=True):
        dm.save_formats(fig, "out", formats=("png",))
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, fields

__all__ = ["Config", "config"]


@dataclass(slots=True)
class Config:
    """Process-wide dartwork-mpl defaults.

    Slotted so a typo'd direct assignment (``dm.config.adopt_orphan_tick_fonts
    = False`` — note the plural) raises ``AttributeError`` instead of
    silently creating a dead attribute that never affects behaviour.

    Attributes
    ----------
    adopt_orphan_tick_font : bool, default ``True``
        Fallback default for the ``adopt_orphan_tick_font`` keyword on
        :func:`dartwork_mpl.simple_layout`, :func:`dartwork_mpl.save_formats`,
        and :func:`dartwork_mpl.save_and_show`. Each of those functions
        accepts ``True`` / ``False`` / ``None`` (the call-site default);
        ``None`` is read here. Set this to ``False`` to leave orphan-axis
        tick fonts alone everywhere by default. Per-call overrides
        (passing ``True`` / ``False`` explicitly) still win.
    warn_on_orphan_tick_adoption : bool, default ``False``
        When ``True``, emit a one-time :class:`UserWarning` every time
        orphan-tick font adoption mutates a figure (via
        :func:`dartwork_mpl.layout.adopt_axis_label_font` or its drivers
        :func:`~dartwork_mpl.simple_layout`, :func:`~dartwork_mpl.save_formats`,
        :func:`~dartwork_mpl.save_and_show`). Useful when debugging a
        figure whose ticks change unexpectedly after a save — or when
        running under matplotlib's ``constrained_layout``, where the
        font change can trigger a re-layout on the next draw. Default is
        off so the common path stays quiet.
    """

    adopt_orphan_tick_font: bool = True
    warn_on_orphan_tick_adoption: bool = False

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

            with dm.config.override(adopt_orphan_tick_font=False):
                dm.simple_layout(fig)   # adoption skipped just here
            dm.simple_layout(fig)        # adoption re-applied (back to default)
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
