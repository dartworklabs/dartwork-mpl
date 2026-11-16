"""What a default canvas is asked for and planned as.

A request names the chart's kind (:class:`CanvasKind`), its density hints,
its panel grid and its category names; the active preset gives its
:class:`Page`. The plan is a :class:`Canvas`.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from typing import ClassVar, Protocol, runtime_checkable

from ..length import Length, cm
from .model import ASPECTS, STANDARD, Aspect, FigureSize, Grid, count


@dataclass(frozen=True)
class KindSpec:
    """A kind's base width and aspect, and whether density hints move it."""

    width: Length
    aspect: Aspect
    fixed: bool = False  # density hints do not move it
    absolute: bool = False  # the same physical size under every preset


# The report tiers: 17 cm is the A4 text width with 2 cm margins.
NARROW, MEDIUM, BROAD, WIDEST = cm(9), cm(12), cm(14.5), cm(17)
REPORT_TIERS = (NARROW, MEDIUM, BROAD, WIDEST)


@dataclass(frozen=True)
class HalfBody:
    """Under a slide title: half the body."""


@dataclass(frozen=True)
class SquareBody:
    """Under a slide title: a square as tall as the body."""


@dataclass(frozen=True)
class ByPositions:
    """Under a slide title: as wide as its x positions and series need."""


@dataclass(frozen=True)
class WholeBody:
    """Under a slide title: the whole body."""


#: How a kind's chart sits under a slide title.
SlideFit = HalfBody | SquareBody | ByPositions | WholeBody


@dataclass(frozen=True)
class DefaultCanvas:
    """Lines, bars, areas, scatter, distributions."""

    word: ClassVar[str] = "default"
    spec: ClassVar[KindSpec] = KindSpec(MEDIUM, STANDARD)
    slide: ClassVar[SlideFit] = ByPositions()
    flat_names: ClassVar[bool] = True


@dataclass(frozen=True)
class GroupedCanvas:
    """``n_series`` bars side by side in each of ``n_points`` groups."""

    word: ClassVar[str] = "grouped"
    spec: ClassVar[KindSpec] = KindSpec(MEDIUM, STANDARD)
    slide: ClassVar[SlideFit] = ByPositions()
    flat_names: ClassVar[bool] = True


@dataclass(frozen=True)
class BarhCanvas:
    """Horizontal bars: room for long category names."""

    word: ClassVar[str] = "barh"
    spec: ClassVar[KindSpec] = KindSpec(BROAD, STANDARD)
    slide: ClassVar[SlideFit] = WholeBody()
    flat_names: ClassVar[bool] = False


@dataclass(frozen=True)
class CompactCanvas:
    """Insets, half-width panels."""

    word: ClassVar[str] = "compact"
    spec: ClassVar[KindSpec] = KindSpec(NARROW, STANDARD)
    slide: ClassVar[SlideFit] = HalfBody()
    flat_names: ClassVar[bool] = False


@dataclass(frozen=True)
class MatrixCanvas:
    """Heatmaps, correlation matrices."""

    word: ClassVar[str] = "matrix"
    spec: ClassVar[KindSpec] = KindSpec(MEDIUM, ASPECTS["square"], fixed=True)
    slide: ClassVar[SlideFit] = SquareBody()
    flat_names: ClassVar[bool] = False


@dataclass(frozen=True)
class DenseCanvas:
    """Long dense timelines."""

    word: ClassVar[str] = "dense"
    spec: ClassVar[KindSpec] = KindSpec(WIDEST, ASPECTS["cinema"], fixed=True)
    slide: ClassVar[SlideFit] = WholeBody()
    flat_names: ClassVar[bool] = False


@dataclass(frozen=True)
class StripCanvas:
    """A full-width strip, e.g. one dashboard row."""

    word: ClassVar[str] = "strip"
    spec: ClassVar[KindSpec] = KindSpec(WIDEST, Aspect(0.45), fixed=True)
    slide: ClassVar[SlideFit] = WholeBody()
    flat_names: ClassVar[bool] = False


@dataclass(frozen=True)
class SlideCanvas:
    """The body of a 16:9 slide under its title."""

    word: ClassVar[str] = "slide"
    spec: ClassVar[KindSpec] = KindSpec(
        cm(23.4), Aspect(10.5 / 23.4), fixed=True, absolute=True
    )
    slide: ClassVar[SlideFit] = WholeBody()
    flat_names: ClassVar[bool] = False


@dataclass(frozen=True)
class FullSlideCanvas:
    """A whole 10 in 16:9 slide, 25.4 x 14.29 cm. A larger slide (13.33 in)
    would show the same text 25 % smaller on screen."""

    word: ClassVar[str] = "full_slide"
    spec: ClassVar[KindSpec] = KindSpec(
        cm(25.4), ASPECTS["slide"], fixed=True, absolute=True
    )
    slide: ClassVar[SlideFit] = WholeBody()
    flat_names: ClassVar[bool] = False


#: What a chart draws, as far as its default canvas cares. ``word`` is how
#: a caller names it (``kind="barh"``); ``spec`` its report width and aspect;
#: ``slide`` how it sits under a slide title; ``flat_names``: its category
#: names are widened to stand flat.
CanvasKind = (
    DefaultCanvas
    | GroupedCanvas
    | BarhCanvas
    | CompactCanvas
    | MatrixCanvas
    | DenseCanvas
    | StripCanvas
    | SlideCanvas
    | FullSlideCanvas
)
CANVAS_KINDS: tuple[CanvasKind, ...] = (
    DefaultCanvas(),
    GroupedCanvas(),
    BarhCanvas(),
    CompactCanvas(),
    MatrixCanvas(),
    DenseCanvas(),
    StripCanvas(),
    SlideCanvas(),
    FullSlideCanvas(),
)


def parse_canvas_kind(value: object) -> CanvasKind:
    """The kind named ``value``; ``ValueError`` listing the kinds if none."""
    for kind in CANVAS_KINDS:
        if kind.word == value:
            return kind
    known = ", ".join(sorted(k.word for k in CANVAS_KINDS))
    raise ValueError(f"unknown canvas kind {value!r}; use one of: {known}")


@runtime_checkable
class Items(Protocol):
    """A value read for its items, in order."""

    def __iter__(self) -> Iterator[object]:
        """The items."""
        ...


_ORDERED = "in axis order (a list, tuple, array or index)"


def parse_names(labels: object) -> tuple[str, ...]:
    """Category names as strings, in axis order; ``()`` for ``None``."""
    if labels is None:
        return ()
    if isinstance(labels, str | bytes):
        raise TypeError(
            f"labels must be the category names {_ORDERED}, not one string; "
            f"got {labels!r}"
        )
    kind = type(labels).__name__
    if isinstance(labels, AbstractSet | Mapping):
        raise TypeError(
            f"labels must be the category names {_ORDERED}; a {kind} has "
            "none, so pass list(...) of the names in the order they are plotted"
        )
    if not isinstance(labels, Items):
        raise TypeError(
            f"labels must be the category names {_ORDERED}; got "
            f"{kind} {labels!r}"
        )
    return tuple(str(label) for label in labels)


@dataclass(frozen=True)
class CanvasRequest:
    """A request for a default canvas: the chart's kind and density hints."""

    kind: CanvasKind = field(default_factory=DefaultCanvas)
    n_points: int | None = None
    n_series: int | None = None
    dual_axis: bool = False
    grid: Grid = field(default_factory=Grid)
    names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject a count that is not a non-negative int."""
        if self.n_points is not None:
            count("n_points", self.n_points, 0)
        if self.n_series is not None:
            count("n_series", self.n_series, 0)


@dataclass(frozen=True)
class Report:
    """A report or web page: the 9 to 17 cm tiers."""


@dataclass(frozen=True)
class Paper:
    """A journal page: one or two columns."""


@dataclass(frozen=True)
class Slides:
    """A 16:9 slide."""


@dataclass(frozen=True)
class Poster:
    """A poster: the report tiers scaled with its font."""


#: The page a preset draws for.
Family = Report | Paper | Slides | Poster


@dataclass(frozen=True)
class Page:
    """The active preset's page: its family and how much its text is scaled.

    ``scale`` is the preset's body font over the report's 8 pt (1.0 except on
    posters), so text fills the same share of a canvas on every page.
    """

    family: Family = Report()
    scale: float = 1.0


@dataclass(frozen=True)
class NameWidths:
    """Category names as the active preset draws them as x tick labels."""

    widths_pt: tuple[float, ...]
    size_pt: float  # the tick label font size


@dataclass(frozen=True)
class Canvas:
    """A planned canvas: a width and a height, the height maybe a share."""

    width: Length
    height: Aspect | Length

    def size(self) -> FigureSize:
        """The canvas as a :class:`FigureSize`."""
        if isinstance(self.height, Length):
            return FigureSize(self.width, self.height)
        return FigureSize(
            self.width, Length(inch=self.width.inch * self.height.ratio)
        )


@dataclass(frozen=True)
class CanvasFacts:
    """Everything the canvas decision and its edge cases read."""

    request: CanvasRequest
    page: Page
    names: NameWidths | None = None
