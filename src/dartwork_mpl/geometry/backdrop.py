"""What is drawn behind a text's ink, read while the figure is drawn once.

What a text sits on (bars, contour bands, a cloud of points) is only known
once the figure is drawn. :func:`draw` draws it one time, as
``fig.canvas.draw()`` does, with a renderer that paints two Agg canvases
at once, and nothing in the figure is changed, hidden or restyled:

- *shown*: the figure as it is. It is the canvas' own renderer when the
  figure has an Agg canvas, so the canvas holds the drawn figure afterwards
  as after ``fig.canvas.draw()``;
- the *paper*: the same draw calls without the glyphs of any text. A
  text's own box is drawn, and a halo (a stroked path effect under a
  filled one) is drawn as a plate of its colour, because that is what the
  reader sees the ink against.

The figure's artists are drawn that once and its ``draw_event`` fires that
once. Each asked text is then drawn alone, by its own ``draw``, onto a
third canvas that keeps only its glyphs: the pixels it paints there are
the text's ink. The colour of each ink pixel is what *shown* holds there,
without the paper that shows through where the glyphs do not fill the
pixel, and the colour behind it is the paper's. Text is drawn as
matplotlib draws it, so rotation, mathtext, several lines, clipping, a
text's alpha, path effects that paint parts of it in different colours and
whatever is drawn over it are read as drawn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.backend_bases import RendererBase
from matplotlib.backends.backend_agg import FigureCanvasAgg, RendererAgg
from matplotlib.colors import to_rgba
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..colorspace import (
    Colours,
    Legibility,
    Places,
    Ratio,
    contrasts,
    legibility,
)
from .model import GlyphGroup, Group, MathMode, OtherGroup, parse_group
from .renderer import BBOX_ERRORS

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import numpy.typing as npt
    from matplotlib.backend_bases import GraphicsContextBase
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.path import Path
    from matplotlib.text import Text
    from matplotlib.transforms import Affine2DBase, Transform
    from matplotlib.typing import ColorType, LineStyleType
    from numpy.typing import ArrayLike

    #: What an ``agg_filter`` is: an image and its dpi in, the filtered
    #: image and where it goes out.
    Filter = Callable[
        [npt.NDArray[np.float64], float],
        tuple[npt.NDArray[np.float64], float, float],
    ]

#: A text is judged in windows this long along its baseline (em) ...
WINDOW_EM = 0.5
#: ... and one line high (em), so one line of several is not averaged away.
LINE_EM = 1.2
#: A pixel is ink when the glyphs cover it at least this much of their peak.
INK = 0.8
#: The crop around a text's box (px): antialiasing.
PAD = 3
#: What a text paints beyond its box (a stroke, an italic's overhang) stays
#: within this (em).
SPILL_EM = 0.3
#: matplotlib lays a text's outline out at this font size (``TextToPath``),
#: so the scale of its transform times this is the text's em in px.
FONT_SCALE = 100.0
#: A halo this far beyond the glyphs (em) is a background for them.
PLATE_EM = 0.04
#: Backgrounds within this share of the best contrast are where a text is
#: at home.
HOME = 0.9


@dataclass(frozen=True)
class Backdrop:
    """One text's ink on the drawn figure, pixel by pixel.

    ``ink`` is the colour each ink pixel is painted in as the figure shows
    it (the text's colour through its alpha, whatever a path effect paints
    there, whatever is drawn over it) and ``paper`` the colour behind it.
    ``pixels`` is where each is (display px, y up) and ``places`` where
    along the text: how far along the direction it is written in, in
    half-em windows, and which line. ``alpha`` is the text's own opacity.
    A text that paints nothing (clipped away, off the canvas) has no rows.
    """

    ink: Colours
    paper: Colours
    pixels: npt.NDArray[np.float64]
    places: Places
    alpha: float

    def read(self, floor: Ratio) -> Legibility:
        """How much of the text reads at ``floor``: the colours it is
        painted in against what is behind them. A colour that reaches the
        floor on a flat background reads at any size and resolution."""
        return legibility(self.ink, self.paper, self.places, floor)

    def read_as(self, colour: Colours, floor: Ratio) -> Legibility:
        """How much of it would read were it painted ``colour``, through
        the text's own alpha."""
        ink = colour * self.alpha + self.paper * (1.0 - self.alpha)
        return legibility(ink, self.paper, self.places, floor)

    def home(self, colour: Colours) -> Colours:
        """The colour of the background ink of ``colour`` reads best on,
        among those behind the text: the middle one of the pixels within a
        tenth of the best contrast. No ink: white."""
        if not len(self.paper):
            return np.ones(3)
        ratios = contrasts(colour, self.paper)
        best = ratios >= HOME * float(np.quantile(ratios, 0.98))
        return np.asarray(np.median(self.paper[best], axis=0), dtype=float)


@dataclass(frozen=True)
class _Line:
    """One line of a text as a renderer was asked to draw it: what it
    says and where (px)."""

    says: str
    x: float
    y: float

    @classmethod
    def of(cls, says: str, x: float, y: float) -> _Line:
        """The line, its place rounded to a hundredth of a pixel."""
        return cls(says, round(x, 2), round(y, 2))


@dataclass(frozen=True)
class _Outline:
    """One draw of a text's outline, kept until the text ends."""

    gc: GraphicsContextBase
    path: Path
    transform: Transform
    face: ColorType | None


@dataclass(frozen=True)
class _Ended:
    """The outlines of a text that has ended: its ``ink``, and the draws
    that lie ``under`` it."""

    ink: tuple[_Outline, ...] = ()
    under: tuple[_Outline, ...] = ()


@dataclass
class _Parts:
    """What the text being drawn has painted so far.

    matplotlib brackets a text's glyphs with a ``"text"`` group and its
    box with a ``"patch"`` group inside it. A text drawn through path
    effects arrives as outlines, each effect drawing the same outline in
    turn. The last draw of an outline is the text's ink (a fill, or the
    stroke of a text that is only stroked); the draws before it lie under
    it (a halo). Which is which shows only when the text ends, so the
    draws are held until then.
    """

    groups: list[Group] = field(default_factory=list[Group])
    held: list[_Outline] = field(default_factory=list[_Outline])

    @property
    def glyphs(self) -> bool:
        """Directly inside a text: what is drawn now is its glyphs."""
        return bool(self.groups) and isinstance(self.groups[-1], GlyphGroup)

    def open(self, name: str) -> None:
        """Enter the group ``name``."""
        self.groups.append(parse_group(name))

    def hold(
        self,
        canvas: RendererBase,
        gc: GraphicsContextBase,
        path: Path,
        transform: Transform,
        face: ColorType | None,
    ) -> None:
        """Keep one draw of an outline. The caller restores ``gc`` after
        its call, so a copy is held."""
        kept = canvas.new_gc()
        kept.copy_properties(gc)
        self.held.append(_Outline(kept, path, transform, face))

    def close(self) -> _Ended:
        """Leave the group; the held draws, sorted, when it was a text."""
        if not self.groups:
            return _Ended()
        match self.groups.pop():
            case GlyphGroup():
                held, self.held = self.held, []
                last = {id(draw.path): n for n, draw in enumerate(held)}
                return _Ended(
                    ink=tuple(
                        draw
                        for n, draw in enumerate(held)
                        if last[id(draw.path)] == n
                    ),
                    under=tuple(
                        draw
                        for n, draw in enumerate(held)
                        if last[id(draw.path)] != n
                    ),
                )
            case OtherGroup():
                return _Ended()


def _carries(halo: _Outline, px_per_pt: float) -> bool:
    """Whether a stroke under a text's ink is a background for it: it
    reaches :data:`PLATE_EM` beyond the glyphs. A thinner one is a
    hairline around them and puts nothing behind the ink."""
    side = halo.gc.get_linewidth() * px_per_pt / 2
    along = halo.transform.transform([(0.0, 0.0), (1.0, 0.0)])
    em = FONT_SCALE * float(np.linalg.norm(along[1] - along[0]))
    return side >= PLATE_EM * em


class _Twice(RendererAgg):
    """Draws a figure onto two Agg canvases in one pass: ``shown`` gets
    every call, each of ``papers`` every call but the glyphs of a text.

    It is an Agg renderer, so an artist that lays itself out for Agg
    (hinted text widths) is drawn as on the figure's canvas, and it
    measures text as one. It paints nothing of its own: the canvas it is
    built with is one pixel and every call is passed on. Once ``papers``
    is emptied it only passes on to ``shown``: matplotlib leaves each text
    holding the renderer it was last drawn with, and this one then holds
    no canvas of its own.
    """

    def __init__(
        self,
        shown: RendererAgg,
        paper: RendererAgg,
        columns: int,
        rows: int,
        dpi: float,
    ) -> None:
        """A renderer the size of ``shown``."""
        super().__init__(1, 1, dpi)
        self.width, self.height = columns, rows
        self.bbox = Bbox.from_bounds(0, 0, columns, rows)
        self.shown = shown
        self.papers = [paper]
        self.px_per_pt = dpi / 72.0
        self.parts = _Parts()
        self.lines: dict[int, _Line] = {}
        # matplotlib's Agg renderer binds these on the instance, over the
        # methods of a subclass: they are bound again, to both canvases.
        self.draw_markers = self.markers
        self.draw_path_collection = self.path_collection
        self.draw_quad_mesh = self.quad_mesh
        self.draw_gouraud_triangles = self.gouraud_triangles
        self.draw_image = self.image

    # ------------------------------------------------ groups and glyphs
    def open_group(self, s: str, gid: str | None = None) -> None:
        """Remember the group being drawn."""
        self.parts.open(s)

    def close_group(self, s: str) -> None:
        """Leave the group; a text's halo goes onto the paper as a plate:
        its outline filled with the stroke's colour, which is what the
        reader sees the ink against. A hairline and a fill under the ink
        (a shadow) put nothing behind it and are left out."""
        ended = self.parts.close()
        for paper in self.papers:
            for under in ended.under:
                if _carries(under, self.px_per_pt):
                    paper.draw_path(
                        under.gc,
                        under.path,
                        under.transform,
                        under.gc.get_rgb(),
                    )

    def draw_text(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        s: str,
        prop: FontProperties,
        angle: float,
        ismath: MathMode = False,
        mtext: Text | None = None,
    ) -> None:
        """Glyphs are not paper. What a text was drawn as is remembered."""
        if mtext is not None:
            self.lines[id(mtext)] = _Line.of(s, x, y)
        self.shown.draw_text(gc, x, y, s, prop, angle, ismath, mtext)

    def draw_tex(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        s: str,
        prop: FontProperties,
        angle: float,
        *,
        mtext: Text | None = None,
    ) -> None:
        """Glyphs are not paper. What a text was drawn as is remembered."""
        if mtext is not None:
            self.lines[id(mtext)] = _Line.of(s, x, y)
        self.shown.draw_tex(gc, x, y, s, prop, angle, mtext=mtext)

    def draw_path(
        self,
        gc: GraphicsContextBase,
        path: Path,
        transform: Transform,
        rgbFace: ColorType | None = None,
    ) -> None:
        """Everything but a text's outlines goes onto the paper as it is.
        The outlines of a text drawn through path effects are held until
        the text ends."""
        self.shown.draw_path(gc, path, transform, rgbFace)
        for paper in self.papers:
            if self.parts.glyphs:
                self.parts.hold(paper, gc, path, transform, rgbFace)
            else:
                paper.draw_path(gc, path, transform, rgbFace)

    # ------------------------------------------------ everything else, twice
    def each(self, call: Callable[[RendererAgg], None]) -> None:
        """``call`` on every canvas."""
        for canvas in (self.shown, *self.papers):
            call(canvas)

    def markers(
        self,
        gc: GraphicsContextBase,
        marker_path: Path,
        marker_trans: Transform,
        path: Path,
        trans: Transform,
        rgbFace: ColorType | None = None,
    ) -> None:
        """``draw_markers`` on every canvas."""
        self.each(
            lambda canvas: canvas.draw_markers(
                gc, marker_path, marker_trans, path, trans, rgbFace
            )
        )

    def path_collection(
        self,
        gc: GraphicsContextBase,
        master_transform: Transform,
        paths: Sequence[Path],
        all_transforms: Sequence[ArrayLike],
        offsets: ArrayLike | Sequence[ArrayLike],
        offset_trans: Transform,
        facecolors: ColorType | Sequence[ColorType],
        edgecolors: ColorType | Sequence[ColorType],
        linewidths: float | Sequence[float],
        linestyles: LineStyleType | Sequence[LineStyleType],
        antialiaseds: bool | Sequence[bool],
        urls: str | Sequence[str],
        offset_position: object,
        *,
        hatchcolors: ColorType | Sequence[ColorType] | None = None,
    ) -> None:
        """``draw_path_collection`` on every canvas."""
        self.each(
            lambda canvas: canvas.draw_path_collection(
                gc,
                master_transform,
                paths,
                all_transforms,
                offsets,
                offset_trans,
                facecolors,
                edgecolors,
                linewidths,
                linestyles,
                antialiaseds,
                urls,
                offset_position,
                hatchcolors=hatchcolors,
            )
        )

    def quad_mesh(
        self,
        gc: GraphicsContextBase,
        master_transform: Transform,
        meshWidth: int,
        meshHeight: int,
        coordinates: ArrayLike,
        offsets: ArrayLike | Sequence[ArrayLike],
        offsetTrans: Transform,
        facecolors: Sequence[ColorType],
        antialiased: bool,
        edgecolors: Sequence[ColorType] | ColorType | None,
    ) -> None:
        """``draw_quad_mesh`` on every canvas."""
        # matplotlib's stub leaves meshWidth and meshHeight untyped.
        self.each(
            lambda canvas: canvas.draw_quad_mesh(  # pyright: ignore[reportUnknownMemberType]
                gc,
                master_transform,
                meshWidth,
                meshHeight,
                coordinates,
                offsets,
                offsetTrans,
                facecolors,
                antialiased,
                edgecolors,
            )
        )

    def gouraud_triangles(
        self,
        gc: GraphicsContextBase,
        triangles_array: ArrayLike,
        colors_array: ArrayLike,
        transform: Transform,
    ) -> None:
        """``draw_gouraud_triangles`` on every canvas."""
        self.each(
            lambda canvas: canvas.draw_gouraud_triangles(
                gc, triangles_array, colors_array, transform
            )
        )

    def image(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        im: ArrayLike,
        transform: Affine2DBase | None = None,
    ) -> None:
        """``draw_image`` on every canvas."""
        self.each(lambda canvas: canvas.draw_image(gc, x, y, im))

    def start_filter(self) -> None:
        """On every canvas (an artist with an ``agg_filter``)."""
        self.each(lambda canvas: canvas.start_filter())

    def stop_filter(self, post_processing: Filter) -> None:
        """On every canvas."""
        # matplotlib ships no types for its Agg renderer's filter function.
        self.each(lambda canvas: canvas.stop_filter(post_processing))  # pyright: ignore[reportUnknownMemberType]

    # ------------------------------------------------ the pixels are shown's
    def buffer_rgba(self) -> memoryview:
        """The pixels of ``shown``."""
        return self.shown.buffer_rgba()

    def tostring_argb(self) -> bytes:
        """The pixels of ``shown``."""
        return self.shown.tostring_argb()

    def clear(self) -> None:
        """Blank every canvas."""
        self.each(lambda canvas: canvas.clear())


class _Glyphs(RendererAgg):
    """Draws only a text's ink: no box, no halo, no annotation arrow."""

    def __init__(self, columns: int, rows: int, dpi: float) -> None:
        """A blank canvas of that size."""
        super().__init__(columns, rows, dpi)
        self.parts = _Parts()
        self.lines: dict[int, _Line] = {}

    def draw_text(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        s: str,
        prop: FontProperties,
        angle: float,
        ismath: MathMode = False,
        mtext: Text | None = None,
    ) -> None:
        """Draw the glyphs and remember what the text was drawn as."""
        if mtext is not None:
            self.lines[id(mtext)] = _Line.of(s, x, y)
        super().draw_text(gc, x, y, s, prop, angle, ismath, mtext)

    def draw_tex(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        s: str,
        prop: FontProperties,
        angle: float,
        *,
        mtext: Text | None = None,
    ) -> None:
        """Draw the glyphs and remember what the text was drawn as."""
        if mtext is not None:
            self.lines[id(mtext)] = _Line.of(s, x, y)
        super().draw_tex(gc, x, y, s, prop, angle, mtext=mtext)

    def open_group(self, s: str, gid: str | None = None) -> None:
        """Remember the group being drawn."""
        self.parts.open(s)

    def close_group(self, s: str) -> None:
        """Leave the group; a text's ink is drawn now that it is known."""
        for ink in self.parts.close().ink:
            super().draw_path(ink.gc, ink.path, ink.transform, ink.face)

    def draw_path(
        self,
        gc: GraphicsContextBase,
        path: Path,
        transform: Transform,
        rgbFace: ColorType | None = None,
    ) -> None:
        """Only the outlines of a text drawn through path effects, held
        until the text ends."""
        if self.parts.glyphs:
            self.parts.hold(self, gc, path, transform, rgbFace)


def _over_white(rgba: npt.NDArray[np.uint8]) -> npt.NDArray[np.float64]:
    """8-bit straight RGBA as colours in 0-1 composited over white, as a
    saved figure shows them."""
    colours = rgba.astype(float) / 255.0
    alpha = colours[..., 3:]
    return colours[..., :3] * alpha + (1.0 - alpha)


def _places(
    text: Text, pixels: npt.NDArray[np.float64], px_per_pt: float
) -> Places:
    """Where along ``text`` each of its ink pixels lies: how far along the
    direction it is written in (half-em windows), and which line."""
    em = float(text.get_fontsize()) * px_per_pt
    angle = np.deg2rad(float(text.get_rotation()))
    along = pixels[:, 0] * np.cos(angle) + pixels[:, 1] * np.sin(angle)
    across = pixels[:, 1] * np.cos(angle) - pixels[:, 0] * np.sin(angle)
    line = np.floor((across - across.min()) / (LINE_EM * em))
    return np.column_stack([along / (WINDOW_EM * em), line])


@dataclass(frozen=True)
class Drawn:
    """A figure drawn once (:func:`draw`): as it is, and without glyphs.

    ``renderer`` is what its artists were drawn with; it measures text as
    the figure's canvas does. ``lines`` is what each text was drawn as,
    where matplotlib says which text a line belongs to (a text of one
    line without path effects).
    """

    renderer: RendererBase
    shown: RendererAgg
    paper: RendererAgg
    dpi: float
    lines: dict[int, _Line]

    def crop(self, text: Text, rows: int, columns: int) -> tuple[slice, slice]:
        """The rows and columns of the canvas that hold all ``text``
        paints. It is measured with the figure's renderer, which is also
        the renderer matplotlib leaves it holding. An annotation is
        measured as its words: its own extent takes in the arrow and
        places it anew, which marks it stale."""
        try:
            if isinstance(text, Annotation):
                box = MplText.get_window_extent(text, self.renderer)
            else:
                box = text.get_window_extent(self.renderer)
        except BBOX_ERRORS:
            return slice(0, rows), slice(0, columns)
        if not np.isfinite(box.extents).all():
            return slice(0, rows), slice(0, columns)
        spill = PAD + SPILL_EM * float(text.get_fontsize()) * self.dpi / 72.0
        top = int(np.clip(rows - box.y1 - spill, 0, rows))
        bottom = int(np.clip(rows - box.y0 + spill, 0, rows))
        left = int(np.clip(box.x0 - spill, 0, columns))
        right = int(np.clip(box.x1 + spill, 0, columns))
        return slice(top, bottom), slice(left, right)

    def backdrops(self, texts: Sequence[Text]) -> list[Backdrop]:
        """Each of ``texts`` against what the figure draws behind it.

        Each is drawn once more, alone, onto a canvas that keeps only its
        glyphs; nothing else of the figure is drawn again and no artist is
        changed. The work for one text is that of its own box. A text
        that no longer says what the figure drew, or stands elsewhere, is
        not read: ``RuntimeError``.
        """
        if not texts:
            return []
        shown = np.asarray(self.shown.buffer_rgba())
        paper = np.asarray(self.paper.buffer_rgba())
        rows, columns = shown.shape[:2]
        glyphs = _Glyphs(columns, rows, self.dpi)
        mask = np.asarray(glyphs.buffer_rgba())
        found: list[Backdrop] = []
        for text in texts:
            glyphs.parts = _Parts()
            glyphs.lines.clear()
            text.draw(glyphs)
            for key, line in glyphs.lines.items():
                if self.lines.get(key, line) != line:
                    # A draw_event callback or an animation rewrote it:
                    # the figure shows another text than this one.
                    raise RuntimeError(
                        f"{text.get_text()!r} changed while the figure was "
                        "drawn, so it cannot be read against that drawing"
                    )
            at_rows, at_cols = self.crop(text, rows, columns)
            cover = mask[at_rows, at_cols, 3].astype(float) / 255.0
            mask[at_rows, at_cols] = 0
            alpha = float(to_rgba(text.get_color(), text.get_alpha())[3])
            peak = float(cover.max()) if cover.size else 0.0
            if not peak:
                none = np.zeros((0, 3))
                found.append(
                    Backdrop(none, none, np.zeros((0, 2)), none[:, :2], alpha)
                )
                continue
            r, c = np.nonzero(cover >= INK * peak)
            behind = _over_white(paper[at_rows, at_cols][r, c])
            seen = _over_white(shown[at_rows, at_cols][r, c])
            # Without the paper that shows through where the glyphs do not
            # fill the pixel: the colour the ink is painted in.
            filled = np.clip(cover[r, c] / max(alpha, 0.05), 0.05, 1.0)
            ink = np.clip(behind + (seen - behind) / filled[:, None], 0.0, 1.0)
            pixels = np.column_stack(
                [at_cols.start + c + 0.5, rows - (at_rows.start + r) - 0.5]
            )
            places = _places(text, pixels, self.dpi / 72.0)
            found.append(Backdrop(ink, behind, pixels, places, alpha))
        return found


def draw(fig: Figure) -> Drawn:
    """Draw ``fig`` once, as ``fig.canvas.draw()`` does, keeping the paper
    under its texts.

    ``fig`` is a root Figure. Its artists are drawn one time and its
    ``draw_event`` fires one time; the draw lays the figure out as any
    draw does, so positions are current afterwards. A figure with an Agg
    canvas is drawn onto that canvas; another one (a vector canvas, a
    plain Figure) onto an Agg canvas of its size and dpi. Errors of the
    figure's own artists propagate.
    """
    canvas = fig.canvas
    if isinstance(canvas, FigureCanvasAgg):
        shown = canvas.get_renderer()
    else:
        width, height = fig.bbox.size
        shown = RendererAgg(width, height, fig.dpi)
    shown.clear()
    rows, columns = np.asarray(shown.buffer_rgba()).shape[:2]
    paper = RendererAgg(columns, rows, fig.dpi)
    both = _Twice(shown, paper, columns, rows, fig.dpi)
    fig.draw(both)
    both.papers.clear()
    # A window showing the canvas shows what was just drawn on it.
    canvas.blit()
    return Drawn(both, shown, paper, fig.dpi, both.lines)


def backdrops(fig: Figure, texts: Sequence[Text]) -> list[Backdrop]:
    """Each of ``texts`` against what ``fig``, their root Figure, draws
    behind it: :func:`draw`, then :meth:`Drawn.backdrops`. No texts:
    nothing is drawn."""
    if not texts:
        return []
    return draw(fig).backdrops(texts)
