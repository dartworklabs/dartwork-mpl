"""The face a mathtext string is drawn in, when its first family lacks the text.

Plain text falls back glyph by glyph along ``font.family``. Mathtext does
not: it draws everything outside ``$…$`` in the one face its first family
resolves to. Under a Korean preset that family is Latin, so the Hangul of
``"면적 (m$^2$)"`` would be missing. :func:`lead_math_faces` moves the first
family of the text's own list that has every such character to the front.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from matplotlib import cbook, font_manager
from matplotlib.text import Text

from ..edgecase import settle
from .decide import lead_plan
from .edges import FACE_EDGES
from .model import Candidate, MathText

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties

LOG = logging.getLogger("dartwork_mpl.font")

# An unescaped dollar sign: the parts between them alternate text and math.
DOLLAR = re.compile(r"(?<!\\)\$")


def outside_math(string: str) -> str:
    """The characters of ``string`` that mathtext draws as text."""
    return "".join("".join(DOLLAR.split(string)[0::2]).split())


def covers(prop: FontProperties, family: str, chars: str) -> bool:
    """Whether the face ``family`` resolves to has every one of ``chars``."""
    one = prop.copy()
    one.set_family(family)
    try:
        path = font_manager.findfont(one, fallback_to_default=False)  # pyright: ignore[reportUnknownMemberType]
    except ValueError:
        return False
    charmap = font_manager.get_font(path).get_charmap()  # pyright: ignore[reportUnknownMemberType]
    return all(ord(c) in charmap for c in chars)


def is_mathtext(text: Text) -> bool:
    """Whether matplotlib parses this text's string as mathtext."""
    return (
        not text.get_usetex()
        and text.get_parse_math()
        and bool(cbook.is_math_text(text.get_text()))
    )


def lead_math_faces(fig: Figure) -> None:
    """Give each mathtext string of ``fig`` a first family that has the
    characters around its math; say which texts changed."""
    for text in fig.findobj(Text):
        if not is_mathtext(text):
            continue
        families: list[str] = list(text.get_fontfamily())  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        chars = outside_math(text.get_text())
        prop = text.get_fontproperties()
        facts = MathText(
            tuple(Candidate(f, covers(prop, f, chars)) for f in families)
        )
        lead = settle(facts, lead_plan(facts), FACE_EDGES).plan.index
        if lead == 0:
            continue
        text.set_fontfamily(  # pyright: ignore[reportUnknownMemberType]
            [families[lead], *families[:lead], *families[lead + 1 :]]
        )
        LOG.info(
            'drew "%s" in %s: mathtext draws the text around $…$ in one '
            "font, and %s lacks some of it; write the symbol itself (m², "
            "η) instead of $…$ to keep %s for the rest",
            text.get_text(),
            families[lead],
            families[0],
            families[0],
        )
