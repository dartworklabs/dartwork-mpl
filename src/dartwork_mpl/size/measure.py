"""Facts the canvas decision reads from outside the slice.

The active preset says which page the figure is for; matplotlib says how wide
category names are once drawn as tick labels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

import matplotlib as mpl
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

from ..style import active_presets, load_style_dict
from .model import Family, NameWidths, Page

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase

REPORT_FONT_PT = 8.0
FAMILIES = {
    "scientific": Family.PAPER,
    "presentation": Family.SLIDES,
    "poster": Family.POSTER,
    **dict.fromkeys(("report", "web", "minimal", "dark"), Family.REPORT),
}


def active_page() -> Page:
    """The page of the first preset in force that names one; a report page
    when none does. A poster scales its text by its font over 8 pt."""
    for name in active_presets():
        base = name.removesuffix("-kr")
        family = FAMILIES.get(base)
        match family:
            case None:
                continue
            case Family.POSTER:
                font_pt = float(load_style_dict(f"font-{base}")["font.size"])
                return Page(family, font_pt / REPORT_FONT_PT)
            case Family.REPORT | Family.PAPER | Family.SLIDES:
                return Page(family)
            case _:
                assert_never(family)
    return Page()


def name_widths(names: tuple[str, ...]) -> NameWidths | None:
    """Each name's width as the active rc draws it as an x tick label.

    Laid out as the tick label itself is (``xtick.labelsize``, the rc font,
    math, ``text.usetex``) on an Agg renderer at the figure dpi, so the same
    names give the same widths every time. ``None`` for fewer than two names
    or when matplotlib could not draw one (``text.usetex`` without TeX).
    """
    if len(names) < 2:
        return None
    dpi = float(mpl.rcParams["figure.dpi"])
    figure = Figure(dpi=dpi)
    renderer: RendererBase = RendererAgg(1, 1, dpi)
    widths: list[float] = []
    size = 0.0
    for name in names:
        label = Text(0, 0, name, fontsize=mpl.rcParams["xtick.labelsize"])
        label.set_figure(figure)
        try:
            box = label.get_window_extent(renderer)
        except (RuntimeError, ValueError, OSError):
            return None
        widths.append(float(box.width) * 72.0 / dpi)
        size = float(label.get_fontsize())
    return NameWidths(tuple(widths), size)
