"""``dm.legible``: make texts read on what is drawn behind them.

What a text sits on is only known once the figure is drawn, so this reads
it there (``geometry.backdrops``) and then does the least that makes the
text read: nothing, another colour, or an outline. What it did is read
from the drawn figure again, and a text that still does not read is put
back as it was. Each text it changes or gives up on is reported in one
line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, assert_never

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects
from matplotlib.axes import Axes
from matplotlib.colors import to_hex, to_rgb, to_rgba
from matplotlib.text import Text

from ..colorspace import LEGIBLE, Rgb
from ..geometry import Backdrop, backdrops
from ..hidden import axes_name
from . import decide
from .model import (
    DrawnOver,
    Halo,
    Ink,
    InkFacts,
    Leave,
    Mend,
    OwnAlpha,
    Recolour,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from matplotlib.figure import Figure
    from matplotlib.patheffects import AbstractPathEffect
    from matplotlib.typing import ColorType

LOG = logging.getLogger("dartwork_mpl.labels")


class Outline(patheffects.Stroke):
    """The halo ``dm.legible`` draws under a text's glyphs. A class of its
    own so that a later call replaces it and does not draw another."""


@dataclass(frozen=True)
class _Was:
    """A text's colour and path effects before ``dm.legible`` touched it."""

    colour: ColorType
    effects: tuple[AbstractPathEffect, ...]


def _figures(texts: Text | Iterable[Text]) -> dict[Figure, list[Text]]:
    """The asked texts by the root figure each is drawn in."""
    asked: list[object] = [texts] if isinstance(texts, Text) else list(texts)
    found: dict[Figure, list[Text]] = {}
    for text in asked:
        if not isinstance(text, Text):
            raise TypeError(
                "dm.legible takes a Text or several (what ax.text, "
                f"ax.annotate or ax.clabel returned), got {type(text).__name__}"
            )
        fig = text.get_figure(root=True)
        if fig is None:
            raise ValueError(
                f"dm.legible: {text.get_text()!r} is not drawn in a figure"
            )
        found.setdefault(fig, []).append(text)
    return found


def _placed(text: Text) -> bool:
    """``text`` is one the user placed in an Axes (``ax.text``,
    ``ax.annotate``, ``ax.clabel``, a bar label): what ``dm.check`` reads
    for ``TEXT_CONTRAST``. A title, an axis or tick label, a legend entry
    and a figure text are not."""
    ax = text.axes
    return ax is not None and any(text is other for other in ax.texts)


def _paper(text: Text) -> tuple[float, float, float]:
    """The face colour of ``text``'s Axes: the paper it was written on."""
    ax = text.axes
    face = (
        ax.get_facecolor()
        if ax is not None
        else mpl.rcParams["figure.facecolor"]
    )
    return to_rgb(face)


def _colours(text: Text) -> tuple[tuple[float, float, float], ...]:
    """The inks ``text`` may take: its own colour, the preset's text
    colour, the face colour of its Axes; each once, its own first."""
    own = to_rgb(text.get_color())
    preset = to_rgb(mpl.rcParams["text.color"])
    return tuple(dict.fromkeys((own, preset, _paper(text))))


def ink_facts(text: Text, behind: Backdrop) -> InkFacts:
    """``text`` against what is drawn behind it: as drawn, and in each of
    the inks it may take (its own, the preset's text colour, its Axes'
    face colour)."""
    colours = _colours(text)
    inks = tuple(
        Ink(Rgb.of(colour), behind.read_as(np.array(colour), LEGIBLE))
        for colour in colours
    )
    home = behind.home(np.array(colours[0]))
    return InkFacts(
        drawn=behind.read(LEGIBLE),
        inks=inks,
        home=Rgb(*(float(c) for c in home)),
        size=float(text.get_fontsize()),
        alpha=float(to_rgba(text.get_color(), text.get_alpha())[3]),
    )


def _draw_as(text: Text, plan: Mend, was: _Was) -> None:
    """``text`` as ``plan`` has it, from the look it had (``was``)."""
    text.set_color(was.colour)
    text.set_path_effects(list(was.effects))
    match plan:
        case Leave():
            pass
        case Recolour():
            text.set_color(plan.ink.hex())
        case Halo():
            halo = Outline(
                linewidth=2 * plan.side, foreground=plan.colour.hex()
            )
            kept = [e for e in was.effects if not isinstance(e, Outline)]
            text.set_path_effects([halo, *(kept or [patheffects.Normal()])])
        case _:
            assert_never(plan)


def _where(text: Text) -> str:
    """``"NW: 6.2% of hours" on Axes 0``: the text, cut, and its Axes."""
    short = " ".join(text.get_text().split())[:30]
    ax = text.axes
    name = f" on {axes_name(ax)}" if isinstance(ax, Axes) else ""
    return f'"{short}"{name}'


def _lost(facts: InkFacts) -> str:
    """How much of a text did not read, in the reader's terms."""
    drawn = facts.drawn
    return (
        f"{drawn.low:.0%} of its ink was under 3:1 on what is behind it "
        f"(down to {drawn.lowest.value:.1f}:1)"
    )


def _say(text: Text, facts: InkFacts, plan: Mend, was: _Was) -> None:
    """One line for a text that did not read: what was done to it, or why
    nothing was."""
    match plan:
        case Recolour():
            LOG.info(
                "drew %s in %s (it was %s): %s; text.set_color(...) after "
                "dm.legible keeps a colour of your own",
                _where(text),
                plan.ink.hex(),
                to_hex(was.colour),
                _lost(facts),
            )
        case Halo():
            LOG.info(
                "outlined %s in %s: %s and no one colour reads on every "
                "background it crosses; moving it onto one background "
                "reads flatter, or a box: text.set_bbox(...)",
                _where(text),
                plan.colour.hex(),
                _lost(facts),
            )
        case Leave():
            cause = decide.in_the_way(facts)
            match cause:
                case OwnAlpha():
                    why = (
                        f"its own alpha ({cause.alpha:.2f}) lets what is "
                        "behind it through in any colour; draw it opaque, "
                        "in a paler colour"
                    )
                case DrawnOver():
                    why = (
                        "something is drawn over it; give the text a "
                        "higher zorder, or move it"
                    )
                case _:
                    assert_never(cause)
            LOG.info(
                "left %s as it was, no colour or outline makes it read: "
                "%s, and %s",
                _where(text),
                _lost(facts),
                why,
            )
        case _:
            assert_never(plan)


def legible(texts: Text | Iterable[Text]) -> None:
    """Make texts read on what is drawn behind them.

    For the texts ``dm.check`` reports under ``TEXT_CONTRAST``: a note
    that runs over bars, contour numbers on dark and pale bands, a label
    on a cloud of points. Call it after ``dm.simple_layout``, when the
    figure has its final size, and check again::

        labels = ax.clabel(contours, fmt="%.1f")
        dm.simple_layout(fig)
        dm.legible(labels)

    Each text is read from the drawn figure, pixel by pixel, and gets the
    first of these that applies:

    1. it reads (what ``dm.check`` judges: no part of it under 3:1):
       nothing. A text that reads is never changed, whatever happens to
       the others handed over with it;
    2. one colour reads on everything behind it: that colour, among its
       own colour, the preset's text colour and the face colour of its
       Axes;
    3. no one colour does (it crosses pale and dark), or it is an accent
       colour lost only where it runs onto something: an outline behind
       the glyphs, 0.14 em wide, in the colour of the background it reads
       best on, so the outline vanishes there.

    The figure is then drawn and read again. A text that still does not
    read gets the next step, and one that nothing makes read (it is
    translucent, or something is drawn over it) is put back exactly as it
    was and named in one line. So calling it twice is the same as calling
    it once, and an outline is never drawn over an outline.

    It takes the texts placed in an Axes, the ones ``TEXT_CONTRAST``
    reports: what ``ax.text``, ``ax.annotate``, ``ax.clabel`` or a bar
    label returned. A title, an axis or tick label, a legend entry or a
    figure text handed over is left alone and said so in one line: its
    colour is the preset's, or its own setter's (``ax.set_title(...,
    color=...)``, ``ax.tick_params(labelcolor=...)``). A text is never
    moved or resized, and a box instead is ``text.set_bbox(...)``. An
    outlined text is saved as shapes, so a PDF no longer holds it as
    selectable text. Each change prints one ``dartwork-mpl:`` line
    (``dm.quiet()`` turns them off). Call it again after the figure's size
    or the data behind a text changes.
    """
    for fig, asked in _figures(texts).items():
        group = [t for t in asked if _placed(t)]
        if others := [t for t in asked if not _placed(t)]:
            LOG.info(
                "left %d text(s) alone (%s): dm.legible mends the texts "
                "placed in an Axes (ax.text, ax.annotate, ax.clabel); a "
                "title, a tick or axis label, a legend entry or a figure "
                "text takes its colour from the preset or its own setter "
                "(ax.set_title(..., color=...), "
                "ax.tick_params(labelcolor=...))",
                len(others),
                _where(others[0]),
            )
        read = backdrops(fig, group)
        facts = [ink_facts(t, b) for t, b in zip(group, read, strict=True)]
        was = [_Was(t.get_color(), tuple(t.get_path_effects())) for t in group]
        plans = [decide.mend(f) for f in facts]
        trying = [i for i, p in enumerate(plans) if not isinstance(p, Leave)]
        for i in trying:
            _draw_as(group[i], plans[i], was[i])
        # What was drawn is read again; a text that still does not read
        # gets the next step, and at the last one is put back as it was.
        while trying:
            again = backdrops(fig, [group[i] for i in trying])
            failed = [
                i
                for i, behind in zip(trying, again, strict=True)
                if not behind.read(LEGIBLE).reads
            ]
            if not failed:
                break
            for i in failed:
                plans[i] = decide.after(facts[i], plans[i])
                _draw_as(group[i], plans[i], was[i])
            trying = [i for i in trying if not isinstance(plans[i], Leave)]
        left = 0
        for text, fact, plan, look in zip(
            group, facts, plans, was, strict=True
        ):
            if fact.drawn.reads:
                left += 1
            else:
                _say(text, fact, plan, look)
        if left:
            LOG.info(
                "left %d of %d text(s) as drawn: they read on what is "
                "behind them",
                left,
                len(group),
            )
