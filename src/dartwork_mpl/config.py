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

    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([1, 2, 3], [1, 4, 9])  # no axis label
    dm.simple_layout(fig)          # tick fonts left untouched by default

    # Opt in for one call.
    dm.simple_layout(fig, adopt_orphan_tick_font=True)

    # Or scope the opt-in to a block.
    with dm.config.override(adopt_orphan_tick_font=True):
        dm.save_formats(fig, "out", formats=("png",))
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

    Slotted so a typo'd direct assignment (``dm.config.adopt_orphan_tick_fonts
    = False`` — note the plural) raises ``AttributeError`` instead of
    silently creating a dead attribute that never affects behaviour.

    Attributes
    ----------
    adopt_orphan_tick_font : bool, default ``False``
        Fallback default for the ``adopt_orphan_tick_font`` keyword on
        :func:`dartwork_mpl.simple_layout`, :func:`dartwork_mpl.save_formats`,
        and :func:`dartwork_mpl.save_and_show`. Each of those functions
        accepts ``True`` / ``False`` / ``None`` (the call-site default);
        ``None`` is read here. Set this to ``True`` to make orphan-axis
        tick fonts adopt the axis-label font everywhere. Per-call overrides
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
    tick_years : {2, 4}, default ``2``
        Digits of the year in tick labels on axes nobody formatted (x axes
        whose data are integer years, ticked on whole years, and date axes,
        via ``dm.simple_layout``) and in
        ``dm.format_axis_dates``: ``24``, ``24.01``, ``24.Q1``. An axis whose
        two-digit years would repeat (a century in view) prints four on its
        own. ``4`` is the four-digit option (``2024``, ``2024.01``):
        ``with dm.config.override(tick_years=4):`` around the code from
        figure creation to the last ``dm.simple_layout``, or assign it.
    date_style : {"period", "concise"}, default ``"period"``
        Date tick words on the same axes: ``"period"`` writes every tick as
        a whole date (``23.01``, ``23.01.15``, quarterly data ``23.Q1``);
        ``"concise"`` writes matplotlib's concise words (``23, May, Sep``;
        ``23년, 5월`` in Korean figures; quarters ``23, Q2``). With
        ``tick_years=4`` it is matplotlib's own concise formatter
        (``2023, May, Sep``; ``2023년, 5월``).
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
    twin_colors : {"series", "neutral"}, default ``"series"``
        Axis colours of ``twinx`` / ``twiny`` pairs, set by
        ``dm.simple_layout``. ``"series"``: a side whose series all draw
        one colour that no series on the other scale shares gets that colour
        on its spine and tick marks (at least 3:1 against the background)
        and the same hue darkened to 4.5:1 on its tick labels and axis
        label; single axes stay as they are. The full rules are in the
        docstring of ``dartwork_mpl.formatting._twin_colors``. A colour you
        set on any part of a side (spine, tick marks, tick labels, axis
        label) makes that whole side yours: its other parts keep the
        preset's colours, and the other side still takes its series colour.
        A colour set after a layout is kept; one set before the first layout
        that equals the preset default (``"black"``) cannot be told from the
        default and is painted, so use ``"neutral"`` for such figures.
        ``"neutral"`` keeps the preset's axis colours on twins too
        (``dm.config.twin_colors = "neutral"``, or
        ``with dm.config.override(twin_colors="neutral"):``); a figure laid
        out before gets them back on its next ``dm.simple_layout``. Any other
        value raises ``ValueError`` where it is read.
    legend_fallback : {"auto", "above", "right", "below", "inside"}, default ``"auto"``
        Where :func:`dartwork_mpl.place_legend` puts a legend with no side
        named when no inside spot is free of data. ``"auto"`` takes, among
        the sides no other panel sits beyond, the one that leaves the larger
        plot (above unless another side takes at least 10 % and 5 % of the
        plot less); ``"above"`` / ``"right"`` / ``"below"`` always that
        side; ``"inside"`` keeps the legend in the spot that covers the
        fewest series (``dm.validate_figure`` then reports
        ``LEGEND_ON_DATA``). Any other value raises ``ValueError`` where it
        is read.
    legend_wrap : bool, default ``True``
        Let :func:`dartwork_mpl.place_legend` break long entry names at
        spaces when the legend outside its Axes would otherwise run past the
        Axes along its side or take more than 60 % of the plot (on a side
        named right or left, also when it is wider than 40 % of the Axes); a
        trailing bracketed unit stays whole. A better fit comes first;
        among ways that fit as well, more lines per name are taken only for
        at least 5 % of the canvas more plot. ``False`` keeps every name on
        one line.
    fit_labels : bool | tuple[str, ...], default ``True``
        What ``dm.simple_layout`` may do when text still collides once the
        margins fit: ``True`` every step (``"axis_labels"``, ``"space"``,
        ``"wrap"``, ``"rotate"``), ``False`` none, a tuple of step names
        only those (``with dm.config.override(fit_labels=False):``, or
        assign it). A ``fit_labels=`` argument wins per call. A figure laid
        out before gets what it fitted undone on its next
        ``dm.simple_layout``. Unknown step names raise ``ValueError`` where
        it is read, steps that are not strings ``TypeError``. The rules are
        in the docstring of ``dartwork_mpl.layout._fit_labels``.
    """

    adopt_orphan_tick_font: bool = False
    warn_on_orphan_tick_adoption: bool = False
    tick_years: Literal[2, 4] = 2
    date_style: Literal["period", "concise"] = "period"
    number_ladder: Literal["auto", "si", "myriad"] = "auto"
    twin_colors: Literal["series", "neutral"] = "series"
    legend_fallback: Literal["auto", "above", "right", "below", "inside"] = (
        "auto"
    )
    legend_wrap: bool = True
    fit_labels: bool | tuple[str, ...] = True

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

            with dm.config.override(adopt_orphan_tick_font=True):
                dm.simple_layout(fig)   # adoption enabled just here
            dm.simple_layout(fig)        # adoption skipped (back to default)
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
