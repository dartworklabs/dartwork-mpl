"""The labels' public functions, given the preset's text and the ticks' numbers.

Label text is sized and weighted relative to the active preset (the style
slice's fs / fw), and a bar value label prints its value as its
axis's ticks print it (the ticks slice's scale and number text). The labels
slice takes both as arguments; these are the functions dm exposes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Unpack

# ``label_axes`` has a parameter named ``labels``; the slice goes by another.
from dartwork_mpl import labels as labels_slice
from dartwork_mpl.style import fs, fw
from dartwork_mpl.ticks import number_text, tick_scale_of, value_label_decimals

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    import numpy as np
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    from matplotlib.typing import ColorType

    from dartwork_mpl.labels import LetterStyle, NoteStyle, TextStyle

__all__ = [
    "add_note",
    "annotate_corner",
    "annotate_value",
    "label_axes",
    "label_bars",
    "label_hline",
]

PRESET_TEXT = labels_slice.PresetText(size=fs, weight=fw)
TICK_TEXT = labels_slice.TickText(
    scale_of=tick_scale_of, decimals=value_label_decimals, number=number_text
)


def label_bars(
    ax: Axes,
    bars: BarContainer | Iterable[BarContainer] | None = None,
    *,
    where: str = "auto",
    total: str | Literal[False] = "auto",
    crowded: str = "rotate",
    decimals: int | None = None,
    fmt: str | Callable[[float], object] | None = None,
    color: ColorType | None = None,
    sign: str = "-",
) -> list[Text]:
    """Label each bar with its value, printed like the axis's ticks.

    One call for "put the values on the bars" / "막대에 값 표시"::

        ax.bar(months, energy_wh)
        dm.label_bars(ax)
        dm.simple_layout(fig)

    ``dm.fs(-1)``, ``dm.fw(1)``, the text colour, 3 pt beyond the bar end
    (negative bars below, ``barh`` left; past an error bar's cap); the value
    in the axis's tick unit (``33G``, ``31%``, ``$800``; plain under
    ``dm.axis_unit``), three significant digits on the largest value and
    the fewest decimals that print every value exactly. Stacked bars get each
    segment's value at its middle and the stack's net beyond its end; a
    label on its bar takes white or the text colour, whichever reads.
    ``dm.simple_layout`` turns crowded labels vertical (vertical bars),
    hides those that still meet from the last bar, and grows an
    autoscaled value axis to hold them. Calling this again on the same bars
    replaces their labels; restyle a label after ``dm.simple_layout``.

    ``where``: ``"auto"``, ``"outside"``, ``"inside"`` (while the bar holds
    the label), ``"center"``. ``total``: ``"auto"``, ``"only"``, ``False``.
    ``crowded``: ``"rotate"`` or ``"skip"`` (hide every other label).
    ``decimals``: a fixed count. ``fmt``: a ``{}`` template (``"${}B"``,
    ``"{:+.1f}%"``) or a callable of the value in the tick unit. ``color``:
    any colour, or ``"series"`` (labels off their bar in the bar's colour,
    made readable). ``sign="+"`` signs rises too (``+30``).
    """
    return labels_slice.label_bars(
        ax,
        bars=bars,
        where=where,
        total=total,
        crowded=crowded,
        decimals=decimals,
        fmt=fmt,
        color=color,
        sign=sign,
        preset=PRESET_TEXT,
        ticks=TICK_TEXT,
    )


def annotate_value(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    *,
    side: str = "auto",
    offset_pt: float = 3.0,
    fontsize: float | None = None,
    **kw: Unpack[NoteStyle],
) -> Text:
    """Label one data value, ``offset_pt`` points from its point.

    ``side="auto"`` takes the first of above, below, right, left that stays
    inside the axes clear of the data and other text; else the least
    covered side inside the axes. A label that would leave the axes above
    its point moves sideways rather than below. ``dm.fs(-1)`` text, one
    weight step heavier (``dm.fw(1)``); keywords go to ``ax.annotate``.
    """
    return labels_slice.annotate_value(
        ax,
        x,
        y,
        text,
        side=side,
        offset_pt=offset_pt,
        fontsize=fontsize,
        preset=PRESET_TEXT,
        **kw,
    )


def annotate_corner(
    ax: Axes,
    text: str,
    *,
    loc: str = "upper left",
    inset_pt: float = 3.0,
    avoid_overlap: bool = True,
    fontsize: float | None = None,
    **kw: Unpack[NoteStyle],
) -> Text:
    """Narrative text inside an axes corner, ``inset_pt`` points in.

    With ``avoid_overlap`` the first corner clear of the data and other
    text wins, ``loc`` first, then upper left, upper right, lower left,
    lower right. ``dm.fs(-2)`` text; keywords go to ``ax.annotate``.
    """
    return labels_slice.annotate_corner(
        ax,
        text,
        loc=loc,
        inset_pt=inset_pt,
        avoid_overlap=avoid_overlap,
        fontsize=fontsize,
        preset=PRESET_TEXT,
        **kw,
    )


def label_hline(
    ax: Axes,
    y: float,
    text: str,
    *,
    x: str | float = "right",
    side: str = "above",
    gap_pt: float = 2.0,
    fontsize: float | None = None,
    **kw: Unpack[NoteStyle],
) -> Text:
    """A label against the horizontal line at ``y``, ``gap_pt`` points off it.

    ``x``: the drawn line's ``"right"`` / ``"left"`` end or ``"center"``, an
    axes fraction, or ``"auto"`` (the clearer end). ``dm.fs(-2)`` text.
    """
    return labels_slice.label_hline(
        ax,
        y,
        text,
        x=x,
        side=side,
        gap_pt=gap_pt,
        fontsize=fontsize,
        preset=PRESET_TEXT,
        **kw,
    )


def label_axes(
    axes: Iterable[Axes] | np.ndarray,
    labels: list[str] | None = None,
    fontsize: float | None = None,
    fontweight: str = "normal",
    x: float | str = "auto",
    y: float | None = None,
    **kwargs: Unpack[LetterStyle],
) -> list[Text]:
    """Panel letters (a, b, c, ...) at the top-left of each panel.

    ``x="auto"`` (default) places each letter from what its panel draws:
    its left edge on the outer edge of the panel's y-axis name (a grid
    column takes its leftmost), its baseline on the panel's title baseline
    (untitled: 4 pt above the top decoration, level with its row).
    ``dm.simple_layout`` places them again at the size it settles on. A
    number is an Axes-relative left edge; ``y`` an Axes-relative bottom.
    ``fontsize`` defaults to ``dm.fs(1)``; keywords go to the texts.
    """
    return labels_slice.label_axes(
        axes,
        labels=labels,
        fontsize=fontsize,
        fontweight=fontweight,
        x=x,
        y=y,
        preset=PRESET_TEXT,
        **kwargs,
    )


def add_note(fig: Figure, text: str, **kw: Unpack[TextStyle]) -> Text:
    """A source or note line at the figure's lower left, ``dm.fs(-1)``.

    ``dm.simple_layout`` keeps the plot above it, ``axes.labelpad`` apart::

        dm.add_note(fig, "Source: internal web logs")
    """
    return labels_slice.add_note(fig, text, preset=PRESET_TEXT, **kw)
