"""The legend slice's types, and the one place a caller's ``loc`` becomes one.

Geometry is in display pixels of the figure being placed: a :class:`Box` is a
window extent, a :class:`Size` a legend's width and height. What only the
figure can answer (how big a legend of these entries is, whether a box meets
data ink, where a name breaks) reaches the decisions as a measuring function
in the facts, so ``decide`` and ``edges`` stay free of matplotlib.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, Literal, TypedDict, TypeVar

from .sides import SIDES, Side

#: Room kept between a legend box and the nearest data ink, in points.
CLEARANCE_PT = 2.0
#: A one-column legend taller than this share of the Axes is tried last.
TALL_SHARE = 0.55


LocName = Literal[
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
    "outside upper left",
    "outside upper center",
    "outside upper right",
    "outside right upper",
    "outside right center",
    "outside right lower",
    "outside lower right",
    "outside lower center",
    "outside lower left",
    "outside left lower",
    "outside left center",
    "outside left upper",
]
"""A ``loc`` matplotlib names (``"outside ..."``: figure legends only)."""


#: Every :data:`LocName`, to read a caller's string against.
LOC_NAMES: tuple[LocName, ...] = (
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
    "outside upper left",
    "outside upper center",
    "outside upper right",
    "outside right upper",
    "outside right center",
    "outside right lower",
    "outside lower right",
    "outside lower center",
    "outside lower left",
    "outside left lower",
    "outside left center",
    "outside left upper",
)

MatplotlibLoc = LocName | tuple[float, float] | int
"""A ``loc`` as matplotlib takes it: a name, an anchor point or a code."""


@dataclass(frozen=True)
class Columns:
    """A legend's column count, at least one."""

    n: int

    def __post_init__(self) -> None:
        """Reject fewer than one column."""
        if self.n < 1:
            raise ValueError(f"a legend has at least one column (got {self.n})")


@dataclass(frozen=True)
class Request:
    """What the caller asked ``place_legend`` for.

    ``side`` is ``None`` for ``loc="best"``; ``columns`` an explicit
    ``ncol`` / ``ncols``; ``anchored`` a caller ``bbox_to_anchor`` /
    ``bbox_transform``, which keeps a ``best`` legend inside.
    """

    side: Side | None
    columns: Columns | None = None
    anchored: bool = False


@dataclass(frozen=True)
class Best:
    """``loc="best"``: inside where it covers no data, else outside."""


@dataclass(frozen=True)
class Passed:
    """Any other ``loc``: matplotlib's, handed to it unchanged."""

    loc: MatplotlibLoc


Placement = Best | Side | Passed
"""What a caller's ``loc`` asks for."""


AskedLoc = str | tuple[float, float] | int
"""A ``loc`` as a caller passes it: a word, or matplotlib's point or code."""


def parse_loc(loc: AskedLoc) -> Placement:
    """``loc`` as the best spot, an outside side, or matplotlib's own.

    A string that is neither raises ``ValueError`` here, before any legend
    is removed; a point or a code goes to matplotlib as it is.
    """
    if not isinstance(loc, str):
        return Passed(loc)
    if loc == "best":
        return Best()
    side = next((s for s in SIDES if s.word == loc), None)
    if side is not None:
        return side
    for name in LOC_NAMES:
        if name == loc:
            return Passed(name)
    words = ", ".join(repr(w) for w in ("best", *(s.word for s in SIDES)))
    raise ValueError(
        f"loc must be {words} or a matplotlib loc such as 'upper left' "
        f"(got {loc!r})"
    )


#: The caller keywords that anchor a legend themselves.
CALLER_ANCHOR = ("bbox_to_anchor", "bbox_transform")


class LegendStyle(TypedDict, total=False):
    """The ``Legend`` keywords a caller styles a legend with, plain values.

    The keywords whose values are matplotlib objects (colours, an anchor
    box, a font) are added by ``measure.LegendKeywords``; matplotlib still
    takes any other keyword it knows at run time. ``loc`` and the column
    count are the placing functions' own parameters.
    """

    fontsize: float | str | None
    title: str | None
    title_fontsize: float | None
    frameon: bool | None
    fancybox: bool | None
    shadow: bool | dict[str, object] | None
    framealpha: float | None
    linewidth: float | None
    borderpad: float | None
    labelspacing: float | None
    handlelength: float | None
    handleheight: float | None
    handletextpad: float | None
    borderaxespad: float | None
    columnspacing: float | None
    markerscale: float | None
    markerfirst: bool
    numpoints: int | None
    scatterpoints: int | None
    scatteryoffsets: Sequence[float] | None
    reverse: bool
    mode: Literal["expand"] | None
    alignment: Literal["center", "left", "right"]
    draggable: bool


LabelColourWord = Literal[
    "linecolor", "markerfacecolor", "mfc", "markeredgecolor", "mec"
]
"""A ``labelcolor`` that takes each entry's colour from its handle."""

Inherit = Literal["inherit"]
"""A legend frame colour taken from ``axes.facecolor`` / ``axes.edgecolor``."""

K = TypeVar("K", bound=LegendStyle)
"""The caller's keyword dict, as the shell types it."""


@dataclass(frozen=True)
class Keywords(Generic[K]):
    """The caller's legend keywords, read once.

    ``rest`` goes to matplotlib; ``columns`` is an explicit ``ncol`` /
    ``ncols``; ``anchor`` the first caller keyword that anchors the legend
    (``bbox_to_anchor``, ``bbox_transform``), if any.
    """

    rest: K
    columns: Columns | None
    anchor: str | None

    @property
    def anchored(self) -> bool:
        """The caller anchored the legend."""
        return self.anchor is not None


def parse_columns(ncols: object, ncol: object) -> Columns | None:
    """An explicit ``ncols`` (``ncol`` wins, as in matplotlib), or ``None``."""
    asked = ncols if ncol is None else ncol
    if asked is None:
        return None
    if isinstance(asked, bool) or not isinstance(asked, int):
        raise TypeError(f"ncols must be an int (got {type(asked).__name__})")
    return Columns(asked)


def parse_keywords(kw: K, kept: K, columns: Columns | None) -> Keywords[K]:
    """The caller's keywords over the ``kept`` settings of a rebuilt legend.

    A caller ``fontsize`` or ``prop`` replaces the kept font size.
    """
    base = kept.copy()
    if "fontsize" in kw or "prop" in kw:
        base.pop("fontsize", None)
    rest = base | kw
    anchor = next((k for k in CALLER_ANCHOR if k in rest), None)
    return Keywords(rest, columns, anchor)


def trial_keywords(kw: K) -> K:
    """The keywords a trial legend is built with: not ``draggable``."""
    rest = kw.copy()
    rest.pop("draggable", None)
    return rest
