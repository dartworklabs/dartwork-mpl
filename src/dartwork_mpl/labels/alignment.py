"""Align a chosen group of existing Matplotlib texts."""

from __future__ import annotations

from copy import copy
from functools import partial
from statistics import median_low
from typing import TYPE_CHECKING, assert_never

from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text
from matplotlib.textpath import text_to_path
from matplotlib.transforms import Affine2D, IdentityTransform, Transform

from ..geometry import AlignedTextRow, get_renderer
from ..vocab import (
    AlignCentre,
    AlignLeft,
    AlignRight,
    HAlign,
    NumericText,
    has_math,
)
from .alignment_layout import MeasuredRow, Piece, decimal_rows
from .model import DecimalAlign, TextAlignment, text_alignment

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from matplotlib.backend_bases import RendererBase
    from matplotlib.font_manager import FontProperties
    from matplotlib.transforms import Bbox
    from numpy.typing import ArrayLike


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


def snap_edges(
    texts: Sequence[Text], how: HAlign, renderer: RendererBase
) -> None:
    """Use a median edge, minimizing total horizontal movement."""
    edges = [feature(t.get_window_extent(renderer), how) for t in texts]
    index = edges.index(median_low(edges))
    reference = copy(texts[index])
    x0, _ = anchor(reference, renderer)
    fig = reference.get_figure(root=True)
    if fig is None:
        return
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

    for text in texts:
        if isinstance(text, Annotation):
            source = copy(text)

            def coords(
                renderer: RendererBase, source: Text = source
            ) -> Affine2D:
                return Affine2D().translate(x_at(), anchor(source, renderer)[1])

            text.set_anncoords(coords)
            text.xyann = (0, 0)
        else:
            text.set_transform(SnapX(text.get_transform(), x_at))
        text.set_horizontalalignment(how.mpl)


def width(font: FontProperties, text: str) -> float:
    """One run's unhinted advance in its actual font."""
    advance, _, _ = text_to_path.get_text_width_height_descent(
        text, font, False
    )
    return float(advance)


def row_artist(
    ax: Axes,
    text: Text,
    measured: MeasuredRow,
    plan: tuple[Piece, ...],
    left: Callable[[RendererBase], float],
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
    return AlignedTextRow(text, measured.text.text, tuple(pieces), origin)


def align_decimals(texts: list[Text], renderer: RendererBase) -> list[Text]:
    """Keep one visible Text per row, with native runs for its stops."""
    axes = texts[0].axes
    fig = texts[0].get_figure(root=True)
    if (
        fig is None
        or not isinstance(axes, Axes)
        or any(
            t.axes is not axes or t.get_bbox_patch() is not None for t in texts
        )
    ):
        return texts
    rows = [
        MeasuredRow(
            NumericText.parse(t.get_text()),
            partial(width, t.get_fontproperties()),
        )
        for t in texts
    ]
    if not (plans := decimal_rows(rows)):
        return texts
    boxes = [float(t.get_window_extent(renderer).x0) for t in texts]
    index = boxes.index(median_low(boxes))
    reference = copy(texts[index])
    dx = (boxes[index] - anchor(reference, renderer)[0]) * 72 / fig.dpi

    def left(renderer: RendererBase) -> float:
        return anchor(reference, renderer)[0] + dx * fig.dpi / 72

    result: list[Text] = []
    for text, row, plan in zip(texts, rows, plans, strict=True):
        new = row_artist(axes, text, row, plan, left)
        axes.add_artist(new)
        # add_artist supplies the Axes clip by default; an outside annotation
        # with no clip must still fit into the Axes' layout extents.
        new.update_from(text)
        new.set_transform(IdentityTransform())
        text.set_visible(False)
        result.append(new)
    return result


def align_texts(texts: Iterable[Text], how: TextAlignment) -> list[Text]:
    """Align existing text horizontally without changing its row or content.

    Left, right and center align the original artists, including tick labels.
    Decimal aligns all numeric runs of a column of Axes texts. It hides the
    inputs and returns the drawn rows, one Text per input. A decimal group
    with no matching numeric shape is left as drawn. Supply visible,
    unrotated single lines without annotation arrows.
    """
    group = list(dict.fromkeys(texts))
    mode = text_alignment(how)
    if len(group) < 2:
        return group
    fig = group[0].get_figure(root=True)
    if fig is None or any(t.get_figure(root=True) is not fig for t in group):
        raise ValueError("Align texts drawn in the same figure")
    if any(
        not t.get_visible()
        or not t.get_text().strip()
        or t.get_rotation() != 0
        or len(t.get_text().splitlines()) != 1
        or isinstance(t, AlignedTextRow)
        or (isinstance(t, Annotation) and t.arrow_patch is not None)
        for t in group
    ):
        return group
    renderer = get_renderer(fig)
    match mode:
        case DecimalAlign():
            if any(t.get_usetex() or has_math(t.get_text()) for t in group):
                return group
            return align_decimals(group, renderer)
        case AlignLeft() | AlignRight() | AlignCentre():
            snap_edges(group, mode, renderer)
            return group
        case _:
            assert_never(mode)
