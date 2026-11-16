"""Panel letters (a, b, c, ...) placed from what each panel draws."""

from __future__ import annotations

import string
import weakref
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..geometry import record_panel_letters
from . import decide
from .given import PresetText
from .measure import drawn_renderer, panel, px_per_pt
from .model import PanelsFacts

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure


@dataclass(eq=False)
class LetterGroup:
    """The letters one ``label_axes`` call placed (``members``: each panel
    with its letter, read by ``check``)."""

    members: list[tuple[Axes, Annotation]]


# The groups of letters ``label_axes`` placed, by root Figure.
GROUPS: weakref.WeakKeyDictionary[Figure, list[LetterGroup]] = (
    weakref.WeakKeyDictionary()
)


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


def _place_letters(group: LetterGroup, renderer: RendererBase) -> bool:
    """Put each letter of ``group`` where the rule says; whether one moved."""
    live = [
        (ax, t) for ax, t in group.members if t.axes is ax and t in ax.texts
    ]
    if not live:
        return False
    k = px_per_pt(live[0][0])
    facts = PanelsFacts(tuple(panel(ax, t, renderer) for ax, t in live), k)
    letters = decide.align_letters(facts, decide.letter_lefts(facts))
    moved = False
    for (_ax, text), p, left, base in zip(
        live, facts.panels, letters.lefts, letters.baselines, strict=True
    ):
        dx = (left - p.corner[0]) / k
        dy = (base - p.corner[1]) / k
        old = text.xyann
        if abs(old[0] - dx) > 1e-3 or abs(old[1] - dy) > 1e-3:
            text.xyann = (dx, dy)
            moved = True
    return moved


def settle_panels(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_axes`` letters from the panels as drawn now; whether one moved."""
    moved = False
    for group in GROUPS.get(fig.get_figure(root=True), []):
        moved = _place_letters(group, renderer) or moved
    return moved


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
                fontweight="normal",
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
    group = LetterGroup(members)
    GROUPS.setdefault(fig, []).append(group)
    record_panel_letters(fig, group.members)
    renderer = drawn_renderer(members[0][0])
    for _round in range(2):  # a row or column aligns on its placed letters
        if not _place_letters(group, renderer):
            break
        renderer = drawn_renderer(members[0][0])
    return [t for _ax, t in members]
