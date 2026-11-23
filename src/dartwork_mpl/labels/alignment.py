"""Align a chosen group of existing Matplotlib texts."""

from __future__ import annotations

import logging
from copy import copy
from functools import lru_cache, partial
from statistics import median_low
from typing import TYPE_CHECKING, assert_never
from weakref import WeakKeyDictionary, ref

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.text import Annotation, Text
from matplotlib.textpath import text_to_path
from matplotlib.transforms import Affine2D, IdentityTransform, Transform

from ..geometry import follows_mark, get_renderer
from ..vocab import (
    AlignCentre,
    AlignLeft,
    AlignRight,
    HAlign,
    NumericText,
    has_math,
)
from .aligned_rows import AlignedTextRow
from .alignment_layout import MeasuredRow, Piece, decimal_rows, numeric_minus
from .model import DecimalAlign, TextAlignment, text_alignment

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.transforms import Bbox
    from numpy.typing import ArrayLike


LOG = logging.getLogger("dartwork_mpl.labels")

_ALIGNED_ROWS: WeakKeyDictionary[Text, ref[AlignedTextRow]] = (
    WeakKeyDictionary()
)


def position(text: Text) -> tuple[float, float]:
    """A text's own anchor in display coordinates."""
    x, y = text.get_transform().transform(text.get_unitless_position())
    return float(x), float(y)


def anchor(text: Text, renderer: RendererBase) -> tuple[float, float]:
    """Resolve an annotation's text coordinates on the current backend."""
    if isinstance(text, Annotation):
        text.update_positions(renderer)
    return position(text)


def feature(box: Bbox, how: HAlign) -> float:
    """The selected edge or centre of a rendered extent."""
    match how:
        case AlignLeft():
            return float(box.x0)
        case AlignRight():
            return float(box.x1)
        case AlignCentre():
            return float((box.x0 + box.x1) / 2)
        case _:
            assert_never(how)


class SnapX(Transform):
    """Keep the input's native y mapping and use the shared display x."""

    @property
    def input_dims(self) -> int:
        """Read two coordinates."""
        return 2

    @property
    def output_dims(self) -> int:
        """Return two display coordinates."""
        return 2

    def __init__(self, original: Transform, x: Callable[[], float]) -> None:
        """Keep the original transform for y."""
        super().__init__()
        self.original = original
        self.x = x

    def transform_non_affine(self, values: ArrayLike) -> ArrayLike:
        """Replace just the display x coordinate."""
        result = self.original.transform(values)
        result[..., 0] = self.x()
        return result


def snap(text: Text, source: Text, x: Callable[[], float]) -> None:
    """Draw ``text`` with its anchor at display ``x``, at the height
    ``source`` (a copy of it as it was) gives it."""
    if isinstance(text, AlignedTextRow):
        origin = text.origin

        def moved(renderer: RendererBase) -> tuple[float, float]:
            return x(), origin(renderer)[1]

        text.origin = moved
    elif isinstance(text, Annotation) and isinstance(source, Annotation):

        def coords(renderer: RendererBase) -> Affine2D:
            source.xy = text.xy
            return Affine2D().translate(x(), anchor(source, renderer)[1])

        text.set_anncoords(coords)
        text.xyann = (0, 0)
    else:
        text.set_transform(SnapX(source.get_transform(), x))


def extent_anchor(text: Text, renderer: RendererBase) -> float:
    """The display x ``snap`` moves: a row of pieces starts there, any
    other text has its anchor there."""
    if isinstance(text, AlignedTextRow):
        return text.origin(renderer)[0]
    return anchor(text, renderer)[0]


def pin_x(text: Text, ax: Axes, outward: float, offset: float) -> None:
    """Keep the text's anchor ``offset`` points from the plot's right edge
    (``outward`` positive) or its left edge, wherever the layout puts it."""
    fig = ax.get_figure(root=True)
    assert fig is not None

    def x() -> float:
        edge = ax.bbox.x1 if outward > 0 else ax.bbox.x0
        return float(edge) + offset * fig.dpi / 72

    snap(text, copy(text), x)


def tick_side(
    fig: Figure, texts: Sequence[Text]
) -> AlignLeft | AlignRight | None:
    """Find the outside edge of a selected group of vertical axis labels."""
    selected = set(texts)
    for ax in fig.axes:
        ticks = (*ax.yaxis.get_major_ticks(), *ax.yaxis.get_minor_ticks())
        if selected <= {tick.label1 for tick in ticks}:
            return AlignLeft()
        if selected <= {tick.label2 for tick in ticks}:
            return AlignRight()
    return None


def snap_edges(
    texts: Sequence[Text],
    how: HAlign,
    renderer: RendererBase,
    outside: AlignLeft | AlignRight | None = None,
) -> bool:
    """Snap to the median edge (outermost for ticks), reporting movement."""
    sources = [copy(t) for t in texts]
    if outside is not None:
        for source in sources:
            transform = source.get_transform()
            if isinstance(transform, SnapX):
                source.set_transform(transform.original)
            native = (
                AlignRight() if isinstance(outside, AlignLeft) else AlignLeft()
            )
            source.set_horizontalalignment(native.mpl)
    edges = [feature(t.get_window_extent(renderer), how) for t in sources]
    if (
        outside is None
        and max(edges) - min(edges) <= 1e-9
        and all(t.get_horizontalalignment() == how.mpl for t in texts)
    ):
        return False
    match outside:
        case AlignLeft():
            target = min(edges)
        case AlignRight():
            target = max(edges)
        case None:
            target = median_low(edges)
        case _:
            assert_never(outside)
    index = edges.index(target)
    reference = sources[index]
    x0, _ = anchor(reference, renderer)
    fig = reference.get_figure(root=True)
    if fig is None:
        return False
    dx = (edges[index] - x0) * 72 / fig.dpi
    axes = reference.axes
    frame = axes.transAxes if axes is not None else fig.transFigure
    frac = frame.inverted().transform((x0, 0))[0]

    def x_at() -> float:
        if isinstance(reference, Annotation):
            x = float(frame.transform((frac, 0))[0])
        else:
            x = position(reference)[0]
        return x + dx * fig.dpi / 72

    for text, source in zip(texts, sources, strict=True):
        snap(text, source, x_at)
        text.set_horizontalalignment(how.mpl)

    return True


def width(font: FontProperties, text: str) -> float:
    """One run's unhinted advance in its actual font."""
    advance, _, _ = text_to_path.get_text_width_height_descent(
        text, font, False
    )
    return float(advance)


def run_width(
    renderer: RendererBase, dpi: float, font: FontProperties, text: str
) -> float:
    """Reserve authored spaces even when Agg hints surrounding glyphs wider."""
    if not isinstance(renderer, RendererAgg) or not text:
        return width(font, text)
    advance, _, _ = renderer.get_text_width_height_descent(text, font, False)
    rendered = float(advance) * 72 / dpi
    return max(rendered, width(font, text)) if text.isspace() else rendered


def row_artist(
    ax: Axes,
    text: Text,
    text_runs: NumericText,
    plan: tuple[Piece, ...],
    left: Callable[[RendererBase], float],
    offsets: Callable[[RendererBase], tuple[float, ...]],
) -> AlignedTextRow:
    """Copy the source's baseline and style into one measured row artist."""
    source = copy(text)
    fig = ax.get_figure(root=False)
    assert fig is not None
    probe = Text(text=text.get_text(), fontproperties=text.get_fontproperties())
    probe.set_figure(fig)

    def origin(renderer: RendererBase) -> tuple[float, float]:
        probe.set_verticalalignment(text.get_verticalalignment())
        actual = probe.get_window_extent(renderer).y0
        probe.set_verticalalignment("baseline")
        baseline = probe.get_window_extent(renderer).y0
        return left(renderer), anchor(source, renderer)[1] + float(
            actual - baseline
        )

    pieces: list[Annotation] = []
    for run in plan:
        piece = Annotation(
            run.text,
            (0, 0),
            (run.offset, 0),
            xycoords=IdentityTransform(),
            textcoords="offset points",
            annotation_clip=False,
        )
        piece.update_from(text)
        piece.set_horizontalalignment(run.align.mpl)
        piece.set_verticalalignment("baseline")
        piece.set_figure(fig)
        piece.axes = ax
        pieces.append(piece)
    return AlignedTextRow(
        text, numeric_minus(text_runs.text), tuple(pieces), origin, offsets
    )


def align_decimals(
    texts: list[Text], axes: Axes, fig: Figure, renderer: RendererBase
) -> list[Text]:
    """Keep one visible Text per row, with native runs for its stops."""
    rows = [NumericText.parse(t.get_text()) for t in texts]

    @lru_cache(maxsize=2)
    def plan_at(
        renderer: RendererBase, fonts: tuple[FontProperties, ...]
    ) -> tuple[tuple[Piece, ...], ...]:
        return decimal_rows(
            [
                MeasuredRow(row, partial(run_width, renderer, fig.dpi, font))
                for row, font in zip(rows, fonts, strict=True)
            ]
        )

    fonts = tuple(t.get_fontproperties().copy() for t in texts)
    if not (plans := plan_at(renderer, fonts)):
        return unchanged(
            texts, "the rows need matching, unambiguous numeric runs"
        )
    boxes = [float(t.get_window_extent(renderer).x0) for t in texts]
    index = boxes.index(median_low(boxes))
    reference = copy(texts[index])
    dx = (boxes[index] - anchor(reference, renderer)[0]) * 72 / fig.dpi

    def left(renderer: RendererBase) -> float:
        return anchor(reference, renderer)[0] + dx * fig.dpi / 72

    result: list[AlignedTextRow] = []

    def offsets(renderer: RendererBase, index: int) -> tuple[float, ...]:
        fonts = tuple(t.get_fontproperties().copy() for t in result)
        return tuple(piece.offset for piece in plan_at(renderer, fonts)[index])

    for i, (text, row, plan) in enumerate(zip(texts, rows, plans, strict=True)):
        new = row_artist(
            axes, text, row, plan, left, lambda r, i=i: offsets(r, i)
        )
        axes.add_artist(new)
        # add_artist supplies the Axes clip by default; an outside annotation
        # with no clip must still fit into the Axes' layout extents.
        new.update_from(text)
        new.set_transform(IdentityTransform())
        text.set_visible(False)
        _ALIGNED_ROWS[text] = ref(new)
        result.append(new)
    signs = sum(
        old.get_text() != new.get_text()
        for old, new in zip(texts, result, strict=True)
    )
    LOG.info(
        "aligned %d rows on decimal stops and normalised minus signs in %d rows",
        len(result),
        signs,
    )
    return list(result)


def visible_row(text: Text) -> Text:
    """Return a source's live decimal replacement, when it is still attached."""
    if (
        (replacement := _ALIGNED_ROWS.get(text)) is not None
        and (row := replacement()) is not None
        and isinstance(row.axes, Axes)
        and row.axes is text.axes
    ):
        return row
    return text


def unchanged(texts: list[Text], reason: str) -> list[Text]:
    """Report a skipped alignment without changing the input artists."""
    LOG.info("left %d texts in place because %s", len(texts), reason)
    return texts


def align_texts(texts: Iterable[Text], how: TextAlignment) -> list[Text]:
    """Align the edges or decimal stops of one horizontal group of texts.

    Mark labels stay at their marks. Tick edge alignment uses the current
    tick strings, so repeat it if a formatter or the ticks change. Decimal
    alignment returns the visible rows for subsequent styling and leaves
    other formats as drawn. Unsupported groups are reported and left alone.
    """
    mode = text_alignment(how)
    inputs = list(dict.fromkeys(texts))
    group = [visible_row(text) for text in inputs]
    if len(group) < 2:
        return unchanged(group, "alignment needs at least two texts")
    fig = group[0].get_figure(root=True)
    if fig is None or any(t.get_figure(root=True) is not fig for t in group):
        return unchanged(
            group, "the texts must still belong to the same figure"
        )
    if len({t.axes for t in group}) > 1:
        return unchanged(group, "the texts belong to different Axes")
    if any(follows_mark(t) for t in group):
        return unchanged(
            group, "their horizontal anchors follow individual marks"
        )
    outside = tick_side(fig, group)
    if (
        outside is None
        and group[0].axes is None
        and any(t not in fig.texts for t in group)
    ):
        return unchanged(
            group, "select tick labels on one side of one vertical axis"
        )
    aligned = [text for text in group if isinstance(text, AlignedTextRow)]
    if aligned:
        if not isinstance(mode, DecimalAlign):
            return unchanged(group, "some rows already have decimal stops")
        if len(aligned) == len(group) and all(
            t.source.get_text() == t.source_text for t in aligned
        ):
            return unchanged(
                group, "the rows are already aligned on decimal stops"
            )
        originals = [
            t.source if isinstance(t, AlignedTextRow) else t for t in group
        ]
        for row in aligned:
            row.remove()
        group = originals
    if any(
        not t.get_visible()
        or not t.get_text().strip()
        or t.get_rotation() != 0
        or len(t.get_text().splitlines()) != 1
        or t.get_usetex()
        or has_math(t.get_text())
        or (isinstance(t, Annotation) and t.arrow_patch is not None)
        for t in group
    ):
        return unchanged(
            group,
            "alignment needs visible, unrotated single-line text without math or arrows",
        )
    renderer = get_renderer(fig)
    match mode:
        case DecimalAlign():
            if not isinstance(axes := group[0].axes, Axes):
                return unchanged(
                    group, "decimal stops require rows placed on an Axes"
                )
            if any(t.get_bbox_patch() is not None for t in group):
                return unchanged(group, "decimal stops do not split boxed text")
            return align_decimals(group, axes, fig, renderer)
        case AlignLeft() | AlignRight() | AlignCentre():
            if not snap_edges(group, mode, renderer, outside):
                return unchanged(group, "they already share the requested edge")
            return group
        case _:
            assert_never(mode)
