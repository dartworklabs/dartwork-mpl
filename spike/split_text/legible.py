"""#810: one text over several backgrounds, and the ways to keep it readable.

What is behind a text is only known once the figure is drawn, so it is
read from the drawn canvas: the figure without the text's ink (``paper``)
and the text's ink alone (``mask``). Every candidate fix stays one native
``Text``: a colour, a box, or path effects. The ones that colour parts of
the text differently draw its outline once per part, clipped to that part
(:class:`Passes`), so the pieces cannot drift from the text: there is one
layout, done by matplotlib at every draw.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.collections import Collection, PathCollection
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
from matplotlib.path import Path
from matplotlib.transforms import Affine2D, Transform, TransformedPath

from .columns import width

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.text import Text

#: ``dm.check``'s threshold (WCAG large text).
MIN_CONTRAST = 3.0
#: Halo width on each side of the glyph, in em.
HALO_EM = 0.1
#: matplotlib's text path is laid out at this font size.
FONT_SCALE = 100.0
#: Slices along the text this long (em) are judged one by one.
SLICE_EM = 0.5
#: An ink at this contrast or more reads without effort (WCAG body text).
COMFORTABLE = 4.5
#: A slice with this share of its ink under 3:1 cannot be read.
FAINT_SLICE = 0.5
#: A colour that leaves less than this share of the ink under 3:1 reads.
CLEAN = 0.02

CANDIDATES = (
    "before",
    "single",
    "glyph",
    "word",
    "knockout",
    "box",
    "halo",
    "auto",
)

RGB = tuple[float, float, float]


def luminance(rgb: np.ndarray) -> np.ndarray:
    """WCAG relative luminance of sRGB values in 0-1 (last axis: channels)."""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """WCAG contrast of two colour arrays, pixel by pixel."""
    la, lb = luminance(a), luminance(b)
    return (np.maximum(la, lb) + 0.05) / (np.minimum(la, lb) + 0.05)


class Blank(patheffects.AbstractPathEffect):
    """Draws nothing: the text keeps its box and place, without its ink."""

    def draw_path(self, renderer, gc, tpath, affine, rgbFace=None):  # noqa: D102
        return


class Probe(patheffects.AbstractPathEffect):
    """Draws the text as it is and keeps the transform it was drawn with."""

    def __init__(self) -> None:
        """Nothing seen yet."""
        super().__init__()
        self.affine: Affine2D | None = None

    def draw_path(self, renderer, gc, tpath, affine, rgbFace=None):  # noqa: D102
        self.affine = affine.frozen()
        renderer.draw_path(gc, tpath, affine, rgbFace)


class Span:
    """A run of the text from ``start`` to ``end`` em along its baseline.

    It keeps its clip outline for as long as it lives: Agg remembers the
    last clip path by the object's id, so an outline made at each draw is
    taken for the one before it and every run is clipped to the first.
    """

    def __init__(self, start: float, end: float) -> None:
        """The run between two em marks."""
        self.start, self.end = start, end
        x0, x1 = start * FONT_SCALE, end * FONT_SCALE
        tall = 10 * FONT_SCALE
        self.box = Path(
            [(x0, -tall), (x1, -tall), (x1, tall), (x0, tall), (x0, -tall)]
        )

    def clip(self, affine: Transform) -> TransformedPath:
        """The run's column of the text, as the text is turned and placed."""
        return TransformedPath(self.box, affine)


@dataclass(frozen=True)
class Region:
    """What one drawn shape covers: a bar, a wedge, a contour band."""

    path: Path
    transform: Transform

    def clip(self, affine: Transform) -> TransformedPath:
        """The shape itself, wherever the figure puts it at this draw."""
        return TransformedPath(self.path, self.transform)


def signed_area(polygon: np.ndarray) -> float:
    """Twice the signed area of a closed polygon (positive: anticlockwise)."""
    x, y = polygon[:, 0], polygon[:, 1]
    return float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def outside(clips: list[TransformedPath], reach: float) -> Path:
    """Everything but ``clips``: a huge anticlockwise square with each
    outline cut out of it clockwise (the shapes must not overlap)."""
    square = np.array(
        [(-reach, -reach), (reach, -reach), (reach, reach), (-reach, reach)]
    )
    rings = [np.vstack([square, square[:1]])]
    for clip in clips:
        path, affine = clip.get_transformed_path_and_affine()
        polygons = affine.transform_path(path).to_polygons(closed_only=True)
        rings += [p if signed_area(p) < 0 else p[::-1] for p in polygons]
    return Path.make_compound_path(*(Path(r, closed=True) for r in rings))


class Passes(patheffects.AbstractPathEffect):
    """Draw the text in ``colour`` inside each part and in its own colour
    everywhere else: one text, several inks, one layout.

    Each pixel of ink is painted once. Painting the whole text first and
    the parts over it leaves the first colour as a fringe around them.
    """

    def __init__(self, parts: list[tuple[Span | Region, RGB]]) -> None:
        """``parts``: where the ink differs, and the ink there."""
        super().__init__()
        self.parts = parts
        self.rest: Path | None = None  # kept alive: see Span

    def draw_path(self, renderer, gc, tpath, affine, rgbFace=None):  # noqa: D102
        clips = [part.clip(affine) for part, _colour in self.parts]
        self.rest = outside(clips, 1e6)
        passes = [(TransformedPath(self.rest, Affine2D()), rgbFace)]
        passes += [
            (c, colour)
            for c, (_p, colour) in zip(clips, self.parts, strict=False)
        ]
        for clip, colour in passes:
            gc0 = renderer.new_gc()
            gc0.copy_properties(gc)
            gc0.set_clip_path(clip)
            if colour is not None:
                gc0.set_foreground(colour)
            renderer.draw_path(gc0, tpath, affine, colour)
            gc0.restore()


@dataclass(frozen=True)
class Sample:
    """One text on the drawn canvas: what is behind its ink, pixel by pixel.

    ``paper`` and ``shown`` are the colours behind and of every core ink
    pixel, ``pixels`` where each is (display px), ``along`` its place on
    the baseline in em, ``affine`` the transform the text was drawn with.
    """

    paper: np.ndarray
    shown: np.ndarray
    along: np.ndarray
    pixels: np.ndarray
    affine: Affine2D

    @property
    def ratios(self) -> np.ndarray:
        """The contrast of every ink pixel with what is behind it."""
        return ratio(self.shown, self.paper)

    @property
    def low(self) -> float:
        """The share of the ink under 3:1."""
        if not len(self.paper):
            return 0.0
        return float(np.mean(self.ratios < MIN_CONTRAST))

    @property
    def worst_slice(self) -> float:
        """The largest share under 3:1 of any half-em slice of the text."""
        bins = np.floor(self.along / SLICE_EM).astype(int)
        low = self.ratios < MIN_CONTRAST
        shares = [
            float(np.mean(low[bins == b]))
            for b in np.unique(bins)
            if np.count_nonzero(bins == b) >= 8
        ]
        return max(shares, default=0.0)

    def paper_of(self, start: float, end: float) -> np.ndarray:
        """The background pixels under the ink between two em marks."""
        return self.paper[(self.along >= start) & (self.along < end)]


def canvas_rgb(fig: Figure) -> np.ndarray:
    """The drawn figure as RGB in 0-1, over white."""
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba(), dtype=float) / 255.0
    alpha = rgba[..., 3:]
    return rgba[..., :3] * alpha + (1.0 - alpha)


def samples(fig: Figure, texts: list[Text]) -> list[Sample]:
    """Read ``texts`` from the canvas: their ink, and the figure without it.

    Two draws of the figure (with the texts' ink, and with only their
    halos and boxes), then each text alone. The spike swaps the texts'
    path effects for those draws and puts them back. A check may not touch
    the figure: it would draw the artists under the texts into a canvas of
    its own.
    """
    kept = [t.get_path_effects() for t in texts]
    # Drawn as outlines, like the ink masks below: hinted glyphs sit up to
    # a pixel away from their outline, which would read as "no contrast".
    for t, effects in zip(texts, kept, strict=True):
        t.set_path_effects(effects or [patheffects.Normal()])
    shown = canvas_rgb(fig)
    for t, effects in zip(texts, kept, strict=True):
        strokes = [e for e in effects if isinstance(e, patheffects.Stroke)]
        t.set_path_effects([*strokes, Blank()])
    paper = canvas_rgb(fig)
    height, width_px = shown.shape[:2]
    found: list[Sample] = []
    for t in texts:
        probe = Probe()
        t.set_path_effects([probe])
        alone = RendererAgg(width_px, height, fig.dpi)
        # Only the glyphs: not the text's box, not an annotation's arrow.
        extras = [
            a
            for a in (t.get_bbox_patch(), getattr(t, "arrow_patch", None))
            if a is not None and a.get_visible()
        ]
        for a in extras:
            a.set_visible(False)
        t.draw(alone)
        for a in extras:
            a.set_visible(True)
        ink = np.asarray(alone.buffer_rgba())[..., 3] > 0.8 * 255
        rows, cols = np.nonzero(ink)
        affine = probe.affine or Affine2D()
        xy = np.column_stack([cols + 0.5, height - rows - 0.5])
        along = (
            affine.inverted().transform(xy)[:, 0] / FONT_SCALE
            if len(xy)
            else np.zeros(0)
        )
        found.append(
            Sample(paper[rows, cols], shown[rows, cols], along, xy, affine)
        )
    for t, effects in zip(texts, kept, strict=True):
        t.set_path_effects(effects)
    fig.canvas.draw()
    return found


def sample(fig: Figure, text: Text) -> Sample:
    """:func:`samples` for one text."""
    return samples(fig, [text])[0]


def low_share(ink: RGB, paper: np.ndarray) -> float:
    """The share of ``paper`` on which ``ink`` is under 3:1."""
    return float(np.mean(ratio(np.array(ink), paper) < MIN_CONTRAST))


def readable(paper: np.ndarray, choices: tuple[RGB, ...]) -> RGB:
    """The first of ``choices`` that leaves the least of ``paper`` under 3:1
    (the text's own colour comes first, so it stays when it reads)."""
    if not len(paper):
        return choices[0]
    return min(choices, key=lambda ink: round(low_share(ink, paper), 2))


def inks(text: Text) -> tuple[RGB, RGB, RGB]:
    """The inks a fix chooses from: the text's own colour, the preset's
    text colour (its dark pole) and the paper of its Axes (its light one)."""
    ax = text.axes
    paper = (
        ax.get_facecolor()
        if ax is not None
        else mpl.rcParams["figure.facecolor"]
    )
    return (
        to_rgb(text.get_color()),
        to_rgb(mpl.rcParams["text.color"]),
        to_rgb(paper),
    )


def opposite(ink: RGB, choices: tuple[RGB, ...]) -> RGB:
    """The choice that contrasts most with ``ink``: its halo."""
    return max(choices, key=lambda c: float(ratio(np.array(c), np.array(ink))))


def spans(text: Text, *, words: bool) -> list[Span]:
    """The text's glyphs (or words) as runs along its baseline, in em."""
    s = text.get_text()
    prop = text.get_fontproperties()
    em = prop.get_size_in_points()
    starts = [
        i
        for i in range(1, len(s))
        if not words or (s[i - 1].isspace() and not s[i].isspace())
    ]
    edges = [0, *starts, len(s)]
    found = []
    for a, b in itertools.pairwise(edges):
        end = width(s[:b], prop)
        found.append(Span((end - width(s[a:b], prop)) / em, end / em))
    return found


def regions(text: Text) -> list[Region]:
    """The filled shapes drawn under ``text``, bottom first."""
    ax = text.axes
    if ax is None:
        return []
    found: list[tuple[float, Region]] = []
    for artist in (*ax.patches, *ax.collections):
        if not artist.get_visible() or artist.get_zorder() > text.get_zorder():
            continue
        if isinstance(artist, Patch):
            found.append(
                (
                    artist.get_zorder(),
                    Region(artist.get_path(), artist.get_transform()),
                )
            )
        elif isinstance(artist, Collection) and not isinstance(
            artist, PathCollection
        ):
            if not np.asarray(artist.get_facecolor()).size:
                continue  # contour lines fill nothing
            found += [
                (artist.get_zorder(), Region(p, artist.get_transform()))
                for p in artist.get_paths()
            ]
    return [r for _z, r in sorted(found, key=lambda zr: zr[0])]


def covered(region: Region, got: Sample) -> np.ndarray:
    """Which ink pixels ``region`` covers."""
    path = region.transform.transform_path(region.path)
    return path.contains_points(got.pixels)


def halo(text: Text, colour: RGB) -> patheffects.Stroke:
    """A stroke of ``colour`` behind the glyphs, :data:`HALO_EM` each side."""
    points = text.get_fontproperties().get_size_in_points()
    return patheffects.Stroke(linewidth=2 * HALO_EM * points, foreground=colour)


def describe(before: Sample, after: Sample) -> str:
    """One line: how much of the ink was, and is, under 3:1."""
    return (
        f"ink under 3:1: {before.low:.0%} -> {after.low:.0%}; worst half-em "
        f"slice {before.worst_slice:.0%} -> {after.worst_slice:.0%}; lowest "
        f"contrast {np.percentile(before.ratios, 2):.2f} -> "
        f"{np.percentile(after.ratios, 2):.2f}\n"
    )


def pooled(samples: list[Sample]) -> Sample:
    """Several texts read as one (a set of contour labels)."""
    return Sample(
        np.concatenate([g.paper for g in samples]),
        np.concatenate([g.shown for g in samples]),
        np.concatenate([g.along + 1000.0 * i for i, g in enumerate(samples)]),
        np.concatenate([g.pixels for g in samples]),
        samples[0].affine,
    )


def fix_single(text: Text, got: Sample) -> None:
    """One colour for the whole text: its own, the preset's or the paper's."""
    text.set_color(readable(got.paper, inks(text)))


def fix_spans(text: Text, got: Sample, *, words: bool) -> None:
    """Each glyph (or word) in the ink that reads on what is behind it."""
    choices = inks(text)
    parts: list[tuple[Span | Region, RGB]] = []
    for span in spans(text, words=words):
        colour = readable(got.paper_of(span.start, span.end), choices)
        if colour != choices[0]:
            parts.append((span, colour))
    text.set_path_effects([Passes(parts)])


def knockout(text: Text, got: Sample) -> list[tuple[Span | Region, RGB]]:
    """The shapes under the text and the ink for each: the ink with the
    most contrast there, except that where several are comfortable
    (4.5:1) the one that reads on most of the text wins, so the ink
    changes as seldom as it can."""
    choices = inks(text)
    reads = {
        ink: float(np.mean(ratio(np.array(ink), got.paper) >= MIN_CONTRAST))
        for ink in choices
    }
    order = tuple(sorted(choices, key=lambda ink: -reads[ink]))
    parts: list[tuple[Span | Region, RGB]] = []
    for region in regions(text):
        under = got.paper[covered(region, got)]
        if len(under) < 4:
            continue
        medians = {
            ink: float(np.median(ratio(np.array(ink), under))) for ink in order
        }
        easy = [ink for ink in order if medians[ink] >= COMFORTABLE]
        ink = easy[0] if easy else max(order, key=lambda i: medians[i])
        parts.append((region, ink))
    return parts


def fix_knockout(text: Text, got: Sample) -> None:
    """The ink changes exactly where the background does: the text is drawn
    again inside each shape under it, in the ink that reads there."""
    text.set_path_effects([Passes(knockout(text, got))])


def flat(
    text: Text, got: Sample, parts: list[tuple[Span | Region, RGB]]
) -> bool:
    """The shapes account for the text: with their inks, and the text's own
    on the rest, under :data:`CLEAN` of the ink stays under 3:1."""
    own = np.array(inks(text)[0])
    shown = np.tile(own, (len(got.paper), 1))
    for part, colour in parts:
        if isinstance(part, Region):
            shown[covered(part, got)] = colour
    return float(np.mean(ratio(shown, got.paper) < MIN_CONTRAST)) < CLEAN


def fix_box(text: Text, got: Sample) -> None:
    """A paper-coloured box behind the text."""
    text.set_bbox(
        {
            "boxstyle": "round,pad=0.2,rounding_size=0.15",
            "facecolor": inks(text)[2],
            "edgecolor": "none",
            "alpha": 0.85,
        }
    )


def fix_halo(text: Text, got: Sample) -> None:
    """An outline behind the glyphs, in the ink furthest from the text's."""
    choices = inks(text)
    text.set_path_effects(
        [halo(text, opposite(choices[0], choices)), patheffects.Normal()]
    )


def fix_auto(text: Text, got: Sample) -> str:
    """What the design proposes ``dm.legible`` does: nothing to a text that
    reads; one colour where one reads everywhere; over flat shapes the ink
    that reads on each; over anything else (a point cloud) a halo."""
    choices = inks(text)
    if got.worst_slice < FAINT_SLICE:
        return "left"
    best = readable(got.paper, choices)
    if low_share(best, got.paper) < CLEAN:
        text.set_color(best)
        return "recoloured"
    parts = knockout(text, got)
    if flat(text, got, parts):
        text.set_path_effects([Passes(parts)])
        return "ink per shape"
    text.set_path_effects(
        [halo(text, opposite(choices[0], choices)), patheffects.Normal()]
    )
    return "halo"


def apply(how: str, fig: Figure, texts: list[Text]) -> str:
    """Apply candidate ``how`` to ``texts``; the ink under 3:1 before and after."""
    before = samples(fig, texts)
    did: list[str] = []
    for text, got in zip(texts, before, strict=True):
        match how:
            case "before":
                pass
            case "single":
                fix_single(text, got)
            case "glyph":
                fix_spans(text, got, words=False)
            case "word":
                fix_spans(text, got, words=True)
            case "knockout":
                fix_knockout(text, got)
            case "box":
                fix_box(text, got)
            case "halo":
                fix_halo(text, got)
            case "auto":
                did.append(fix_auto(text, got))
            case _:
                raise ValueError(how)
    after = samples(fig, texts)
    faint_before = sum(g.worst_slice >= FAINT_SLICE for g in before)
    faint_after = sum(g.worst_slice >= FAINT_SLICE for g in after)
    chose = f" ({', '.join(did)})" if did else ""
    return (
        f"{len(texts)} text(s), partly illegible: {faint_before} -> "
        f"{faint_after}{chose}; " + describe(pooled(before), pooled(after))
    )
