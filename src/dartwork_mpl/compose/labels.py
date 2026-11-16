"""The labels' public functions, given the preset's text and the ticks' numbers.

Label text is sized and weighted relative to the active preset (the style
slice's fs / fw), and a bar value label prints its value as its
axis's ticks print it (the ticks slice's scale and number text). The labels
slice takes both as arguments; these are the functions dm exposes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# ``label_axes`` has a parameter named ``labels``; the slice goes by another.
from dartwork_mpl import labels as labels_slice
from dartwork_mpl.style import fs, fw
from dartwork_mpl.ticks import number_text, tick_scale_of, value_label_decimals

if TYPE_CHECKING:
    from collections.abc import Iterable

    import numpy as np
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["add_note", "annotate_value", "label_axes", "label_bars"]

PRESET_TEXT = labels_slice.PresetText(size=fs, weight=fw)
TICK_TEXT = labels_slice.TickText(
    scale_of=tick_scale_of, decimals=value_label_decimals, number=number_text
)


def label_bars(
    ax: Axes, bars: BarContainer | Iterable[BarContainer] | None = None
) -> list[Text]:
    """Label each bar with its value, printed like the axis's ticks.

    One call for "put the values on the bars" / "막대에 값 표시"::

        ax.bar(months, energy_wh)
        dm.label_bars(ax)
        dm.simple_layout(fig)

    ``dm.fs(-1)``, ``dm.fw(1)``, the text colour, 3 pt beyond the bar end
    (negative bars below, ``barh`` left); the value in the axis's tick unit
    (``1.2억``, ``31%``), three significant digits on the largest value and
    the fewest decimals that print every value exactly. Stacked bars get
    each segment's value at its middle, in white or the text colour,
    whichever reads, and the stack's net beyond its end. ``dm.simple_layout``
    turns crowded labels vertical (vertical bars), hides those that still
    meet and segment labels their bar cannot hold, and grows an autoscaled
    value axis to hold them. ``bars``: only these containers (what
    ``ax.bar`` returns). Restyle a label after ``dm.simple_layout``.
    """
    return labels_slice.label_bars(
        ax, bars, preset=PRESET_TEXT, ticks=TICK_TEXT
    )


def annotate_value(ax: Axes, x: float, y: float, text: str) -> Text:
    """Label one data value, 3 points from its point.

    The first of above, below, right, left that stays inside the axes clear
    of the data and other text; else the least covered side inside the axes.
    A label that would leave the axes above its point moves sideways rather
    than below. ``dm.fs(-1)`` text, one weight step heavier (``dm.fw(1)``).
    """
    return labels_slice.annotate_value(ax, x, y, text, preset=PRESET_TEXT)


def label_axes(
    axes: Iterable[Axes] | np.ndarray, labels: list[str] | None = None
) -> list[Text]:
    """Panel letters (a, b, c, ...) at the top-left of each panel.

    Each letter's left edge sits on the outer edge of its panel's y-axis
    name (a grid column takes its leftmost), its baseline on the panel's
    title baseline (untitled: 4 pt above the top decoration, level with its
    row). ``dm.simple_layout`` places them again at the size it settles on.
    ``dm.fs(1)``; ``labels`` replaces the letters (``["(a)", "(b)"]``).
    """
    return labels_slice.label_axes(axes, labels, preset=PRESET_TEXT)


def add_note(fig: Figure, text: str) -> Text:
    """A source or note line at the figure's lower left, ``dm.fs(-1)``.

    ``dm.simple_layout`` keeps the plot above it, ``axes.labelpad`` apart::

        dm.add_note(fig, "Source: internal web logs")
    """
    return labels_slice.add_note(fig, text, preset=PRESET_TEXT)
