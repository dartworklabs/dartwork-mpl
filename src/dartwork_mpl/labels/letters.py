"""Panel letters (a, b, c, ...) placed from what each panel draws.

One placement holds for a whole figure: each letter at its plot's left
spine with its title right after it, left-aligned (a run), or, when one
run is wider than its plot, every letter inside its plot at the top left
with the titles left as they were. ``label_axes`` places them for the
figure as drawn then; ``settle_panels`` places them again at every step of
``dm.simple_layout``, so titles set or changed after ``label_axes`` are
read there, and ``report_panels`` says when the letters went inside.
"""

from __future__ import annotations

import logging
import string
import weakref
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..geometry import (
    CentreTitle,
    LeftTitle,
    RightTitle,
    TitleLoc,
    axes_titles,
    record_panel_letters,
)
from ..hidden import axes_name
from ..vocab import AlignCentre, AlignLeft, HAlign, parse_halign
from . import decide
from .given import PresetText
from .measure import drawn_renderer, panel, px_per_pt
from .model import Inside, PanelsFacts, Placement, Run

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

LOG = logging.getLogger("dartwork_mpl.labels")


@dataclass(eq=False)
class LetterGroup:
    """The letters one ``label_axes`` call placed (``members``: each panel
    with its letter, read by ``check``)."""

    members: list[tuple[Axes, Annotation]]


@dataclass(frozen=True)
class Placed:
    """A figure's last placement and its panels, in the order decided."""

    where: Placement
    axes: tuple[Axes, ...]


# The groups of letters ``label_axes`` placed, by root Figure.
GROUPS: weakref.WeakKeyDictionary[Figure, list[LetterGroup]] = (
    weakref.WeakKeyDictionary()
)

#: The placement each root Figure's letters last took.
PLACED: weakref.WeakKeyDictionary[Figure, Placed] = weakref.WeakKeyDictionary()

#: The offset (pt) the slice last gave each letter; one that differs was
#: moved by the caller and stays where they put it.
OFFSETS: weakref.WeakKeyDictionary[Annotation, tuple[float, float]] = (
    weakref.WeakKeyDictionary()
)

#: Where a title starts and how it aligns, as matplotlib draws it unless
#: someone set them; and what the slice last set on a title it moved.
TITLE_DEFAULTS: dict[TitleLoc, tuple[float, HAlign]] = {
    CentreTitle(): (0.5, AlignCentre()),
    LeftTitle(): (0.0, AlignLeft()),
}
MOVED: weakref.WeakKeyDictionary[Text, tuple[float, HAlign]] = (
    weakref.WeakKeyDictionary()
)


def _moved(text: Annotation) -> bool:
    last = OFFSETS.get(text)
    return last is not None and tuple(text.xyann) != last


def _letters(n: int) -> list[str]:
    """a, b, ..., z, aa, ab, ..."""
    out: list[str] = []
    for i in range(n):
        chars, k = "", i
        while k >= 0:
            chars = string.ascii_lowercase[k % 26] + chars
            k = k // 26 - 1
        out.append(chars)
    return out


def _shown(text: Text) -> bool:
    return text.get_visible() and bool(text.get_text().strip())


def _free(title: Text, loc: TitleLoc) -> bool:
    """Nobody but this slice set where ``title`` starts or how it aligns
    (``set_title`` puts the alignment back, not the start)."""
    x = float(title.get_position()[0])
    ha = parse_halign(title.get_horizontalalignment())
    default = TITLE_DEFAULTS[loc]
    last = MOVED.get(title)
    starts = [default[0], *([last[0]] if last else [])]
    aligns = [default[1], *([last[1]] if last else [])]
    return x in starts and ha in aligns


def _titles(ax: Axes) -> tuple[Text | None, Text | None]:
    """The title that follows the letter in a run (the centre one, else a
    left one, if nobody placed it), and a right title, which stays."""
    titles = axes_titles(ax)
    joined = next(
        (
            t
            for loc in (CentreTitle(), LeftTitle())
            if (t := titles.get(loc)) is not None
            and _shown(t)
            and _free(t, loc)
        ),
        None,
    )
    right = titles.get(RightTitle())
    return joined, right if right is not None and _shown(right) else None


def _restore(ax: Axes) -> bool:
    """Put back the titles of ``ax`` a run moved, unless someone else has;
    whether one moved."""
    moved = False
    for loc, title in axes_titles(ax).items():
        if title in MOVED and _free(title, loc):
            title.set_x(TITLE_DEFAULTS[loc][0])
            title.set_horizontalalignment(TITLE_DEFAULTS[loc][1].mpl)
            del MOVED[title]
            moved = True
    return moved


def _join(ax: Axes, title: Text, left_px: float) -> bool:
    """Start ``title`` at ``left_px``, left-aligned; whether it moved."""
    x = float(ax.transAxes.inverted().transform((left_px, 0.0))[0])
    old = float(title.get_position()[0])
    was = parse_halign(title.get_horizontalalignment())
    title.set_x(x)
    title.set_horizontalalignment(AlignLeft.mpl)
    MOVED[title] = (x, AlignLeft())
    return abs(old - x) > 1e-6 or was != AlignLeft()


def _place(fig: Figure, renderer: RendererBase) -> bool:
    """Put every letter of ``fig`` where the figure's placement says;
    whether one moved."""
    live = [
        (ax, t)
        for group in GROUPS.get(fig, [])
        for ax, t in group.members
        if t.axes is ax and t in ax.texts and not _moved(t)
    ]
    if not live:
        return False
    titles = [_titles(ax) for ax, _t in live]
    k = px_per_pt(live[0][0])
    facts = PanelsFacts(
        tuple(
            panel(ax, t, renderer, joined, apart)
            for (ax, t), (joined, apart) in zip(live, titles, strict=True)
        ),
        k,
    )
    where = decide.placement(facts)
    PLACED[fig] = Placed(where, tuple(ax for ax, _t in live))
    letters = decide.place_letters(facts, where)
    moved = False
    for (ax, text), (joined, _apart), p, left, base, start in zip(
        live,
        titles,
        facts.panels,
        letters.lefts,
        letters.baselines,
        letters.titles,
        strict=True,
    ):
        if start is not None and joined is not None:
            moved = _join(ax, joined, start) or moved
        else:
            moved = _restore(ax) or moved
        dx = (left - p.corner[0]) / k
        dy = (base - p.corner[1]) / k
        old = text.xyann
        if (
            text not in OFFSETS
            or abs(old[0] - dx) > 1e-3
            or abs(old[1] - dy) > 1e-3
        ):
            text.xyann = (dx, dy)
            OFFSETS[text] = (dx, dy)
            moved = True
    return moved


def settle_panels(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_axes`` letters from the panels as drawn now; whether one moved."""
    return _place(fig.get_figure(root=True), renderer)


def report_panels(fig: Figure) -> None:
    """Say when the last placement put the letters of ``fig`` inside."""
    placed = PLACED.get(fig.get_figure(root=True))
    if placed is None or not LOG.isEnabledFor(logging.INFO):
        return
    match placed.where:
        case Inside(panel=i):
            LOG.info(
                "put the panel letters inside their plots, top left: the "
                "letter and title of %s were wider than its plot; shorten "
                "the titles or widen the figure to keep each letter before "
                "its title",
                axes_name(placed.axes[i]),
            )
        case Run():
            pass


def label_axes(
    axes: Iterable[Axes] | np.ndarray,
    labels: list[str] | None = None,
    *,
    preset: PresetText,
) -> list[Text]:
    """``dm.label_axes``, its letters sized by ``preset``."""
    axes = (
        list(np.asarray(axes, dtype=object).flat)
        if isinstance(axes, np.ndarray)
        else list(axes)
    )
    labels = _letters(len(axes)) if labels is None else labels
    members = [
        (
            ax,
            ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                label,
                xy=(0.0, 1.0),
                xycoords="axes fraction",
                xytext=(0.0, 0.0),
                textcoords="offset points",
                annotation_clip=False,
                fontsize=preset.size(1),
                fontweight=preset.weight(3),
                verticalalignment="baseline",
                horizontalalignment="left",
            ),
        )
        for ax, label in zip(axes, labels, strict=False)
    ]
    if not members:
        return []
    fig = members[0][0].get_figure(root=True)
    if fig is None:
        return [t for _ax, t in members]
    GROUPS.setdefault(fig, []).append(LetterGroup(members))
    record_panel_letters(fig, members)
    renderer = drawn_renderer(members[0][0])
    for _round in range(2):  # a row aligns on its placed letters
        if not _place(fig, renderer):
            break
        renderer = drawn_renderer(members[0][0])
    return [t for _ax, t in members]
