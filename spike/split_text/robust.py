"""The numbers behind the design: do the pieces stay where the text is?

``uv run python -m spike.split_text.robust [out_dir]`` prints them and
writes ``robust.txt`` beside the contact sheet. Every length is in points
(1 pt = 1/72 in), so dpi 100, 200, 300, PDF and SVG compare directly.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl.check.measure import measure

from . import cases, legible
from .columns import MINUS, TABLES, text_columns, width

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.artist import Artist
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

BACKENDS = (
    ("agg 100", "png", 100),
    ("agg 200", "png", 200),
    ("agg 300", "png", 300),
    ("pdf", "pdf", 72),
    ("svg", "svg", 72),
)
WORDS = ("NW: ", "6.2% ", "of ", "hours")
NOTE = "".join(WORDS)


def during_save(
    fig: Figure, fmt: str, dpi: int, read: Callable[[RendererBase, float], None]
) -> None:
    """Save ``fig`` to nowhere and call ``read(renderer, pt_per_px)`` while
    that backend's own renderer has just drawn it."""

    def on_draw(event) -> None:
        read(event.renderer, 72.0 / fig.dpi)

    cid = fig.canvas.mpl_connect("draw_event", on_draw)
    fig.savefig(io.BytesIO(), format=fmt, dpi=dpi)
    fig.canvas.mpl_disconnect(cid)


def ink_box(
    fig: Figure, artists: list[Artist], dpi: int, faintest: int = 48
) -> Bbox:
    """The box of what ``artists`` paint at ``dpi``, in points."""
    old = fig.dpi
    fig.set_dpi(dpi)
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    alone = RendererAgg(w, h, dpi)
    for a in artists:
        a.draw(alone)
    alpha = np.asarray(alone.buffer_rgba())[..., 3] > faintest
    rows, cols = np.nonzero(alpha)
    fig.set_dpi(old)
    k = 72.0 / dpi
    return Bbox.from_extents(
        cols.min() * k,
        (h - rows.max() - 1) * k,
        (cols.max() + 1) * k,
        (h - rows.min()) * k,
    )


# -- #812: the columns ----------------------------------------------------------


def columns_report() -> list[str]:
    """The forest plot's pieces against their Axes edge and each other."""
    dm.style.use("scientific")
    fig = cases.forest_after()
    ax = fig.axes[0]
    pieces = [p for table in TABLES[fig] for cell in table for p in cell.pieces]
    marks = [
        p
        for p in pieces
        if p.get_ha() == "left" and p.get_text().startswith(".")
    ]
    out = [f"#812 forest plot: 10 rows, 3 columns, {len(pieces)} pieces"]

    def edge(p: Text, box: Bbox) -> float:
        return {
            "left": box.x0,
            "right": box.x1,
            "center": (box.x0 + box.x1) / 2,
        }[p.get_ha()]

    for name, fmt, dpi in BACKENDS:
        got: dict[str, float] = {}

        def read(r: RendererBase, k: float, got=got) -> None:
            frame = ax.get_window_extent(r)
            worst = 0.0
            for p in pieces:
                side = frame.x1 if p.xy[0] == 1.0 else frame.x0
                at = (edge(p, p.get_window_extent(r)) - side) * k
                worst = max(worst, abs(at - p.xyann[0]))
            got["anchor"] = worst
            by_x: dict[float, list[float]] = {}
            for p in marks:
                by_x.setdefault(round(p.xyann[0], 6), []).append(
                    p.get_window_extent(r).x0 * k
                )
            got["marks"] = max(max(v) - min(v) for v in by_x.values())
            boxes = [p.get_window_extent(r) for p in pieces]
            canvas = fig.bbox
            got["left"] = (min(b.x0 for b in boxes) - canvas.x0) * k
            got["right"] = (canvas.x1 - max(b.x1 for b in boxes)) * k

        during_save(fig, fmt, dpi, read)
        out.append(
            f"  {name:8s} piece anchor vs Axes edge + its offset: max "
            f"{got['anchor']:.4f} pt; decimal marks of one column: spread "
            f"{got['marks']:.4f} pt; room to canvas edge left "
            f"{got['left']:.2f} / right {got['right']:.2f} pt"
        )
    out.append(
        "  (dm.simple_layout margin 1 mm = 2.83 pt: the columns are inside "
        "what it reserved)"
    )
    for dpi in (100, 200, 300):
        dots = [ink_box(fig, [p], dpi, faintest=0).x0 for p in marks]
        cols = np.array([round(p.xyann[0], 6) for p in marks])
        spread = max(
            np.ptp([d for d, c in zip(dots, cols, strict=True) if c == x])
            for x in np.unique(cols)
        )
        out.append(
            f"  agg {dpi}  ink of the decimal points in one column: spread "
            f"{spread:.3f} pt ({spread * dpi / 72:.2f} px)"
        )
    facts = measure(fig)
    found = dm.check(fig)
    out.append(
        f"  dm.check reads {len(facts.texts)} free texts for "
        f"{sum(len(t) for t in TABLES[fig])} cells; findings: "
        f"{sorted(set(found.rules)) or 'none'}"
    )
    plt.close(fig)
    return out


def flow_report() -> list[str]:
    """One row whose cell is the widest everywhere: the pieces should sit
    where one unsplit Text puts the same glyphs."""
    dm.style.use("scientific")
    cell = "-13.9 [-13.9, 2.5]"
    whole = cell.replace("-", MINUS)
    out = [f"#812 pieces of {cell!r} against the same string as one Text"]
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "4cm"))
    ax.plot([0, 1], [0, 1])
    pieces = text_columns(ax, [0.5], [[cell]])
    first = pieces[0]
    start = first.xyann[0] - width(first.get_text(), first.get_fontproperties())
    ref = ax.annotate(
        whole,
        xy=(1.0, 0.5),
        xycoords=ax.get_yaxis_transform(),
        xytext=(start, first.xyann[1]),
        textcoords="offset points",
        ha="left",
        va="baseline",
        annotation_clip=False,
        fontsize=first.get_fontsize(),
        color="red",
    )
    dm.simple_layout(fig)
    for name, fmt, dpi in BACKENDS:
        got: dict[str, float] = {}

        def read(r: RendererBase, k: float, got=got) -> None:
            union = Bbox.union([p.get_window_extent(r) for p in pieces])
            one = ref.get_window_extent(r)
            got["x0"], got["x1"] = (
                (union.x0 - one.x0) * k,
                (union.x1 - one.x1) * k,
            )

        during_save(fig, fmt, dpi, read)
        line = (
            f"  {name:8s} extent of the pieces minus the one Text: start "
            f"{got['x0']:+.3f} pt, end {got['x1']:+.3f} pt"
        )
        if fmt == "png":
            a, b = ink_box(fig, list(pieces), dpi), ink_box(fig, [ref], dpi)
            line += (
                f"; ink start {a.x0 - b.x0:+.3f}, end {a.x1 - b.x1:+.3f}, "
                f"baseline {a.y0 - b.y0:+.3f} pt"
            )
        out.append(line)
    plt.close(fig)
    return out


# -- #810: ways to place inline pieces ------------------------------------------


def scene(rotation: float) -> tuple[Figure, plt.Axes, Text]:
    """An Axes with the reference note at a data point."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.bar(["a", "b", "c"], [3, 5, 4])
    ref = ax.text(
        0.2,
        4.2,
        NOTE,
        rotation=rotation,
        rotation_mode="anchor",
        ha="left",
        va="baseline",
        color="red",
    )
    return fig, ax, ref


def starts(
    text: str, prop, measure_width: Callable[[str], float]
) -> list[float]:
    """Where each word of :data:`WORDS` starts in the unsplit string."""
    found, at = [], 0
    for word in WORDS:
        end = at + len(word)
        found.append(measure_width(text[:end]) - measure_width(word))
        at = end
    return found


def measured_once(ax, ref: Text, rotation: float, dpi: int) -> list[Text]:
    """Offsets from advances the Agg renderer reports at ``dpi``, kept."""
    fig = ax.get_figure()
    fig.set_dpi(dpi)
    r = fig.canvas.get_renderer()
    prop = ref.get_fontproperties()

    def w(s: str) -> float:
        return r.get_text_width_height_descent(s, prop, False)[0] * 72.0 / dpi

    return offset_pieces(ax, ref, rotation, starts(NOTE, prop, w))


def unhinted(ax, ref: Text, rotation: float) -> list[Text]:
    """Offsets from the unhinted metrics, as the columns use."""
    prop = ref.get_fontproperties()
    return offset_pieces(
        ax, ref, rotation, starts(NOTE, prop, lambda s: width(s, prop))
    )


def offset_pieces(
    ax, ref: Text, rotation: float, at: list[float]
) -> list[Text]:
    """One Annotation per word, each ``at`` points along the baseline."""
    t = np.deg2rad(rotation)
    return [
        ax.annotate(
            word,
            xy=ref.get_position(),
            xycoords="data",
            xytext=(a * np.cos(t), a * np.sin(t)),
            textcoords="offset points",
            rotation=rotation,
            rotation_mode="anchor",
            ha="left",
            va="baseline",
        )
        for word, a in zip(WORDS, at, strict=True)
    ]


def chained(ax, ref: Text, rotation: float) -> list[Text]:
    """matplotlib's own recipe: each word at the box of the one before."""
    pieces = [
        ax.text(
            *ref.get_position(),
            WORDS[0],
            rotation=rotation,
            rotation_mode="anchor",
            ha="left",
            va="baseline",
        )
    ]
    for word in WORDS[1:]:
        pieces.append(
            ax.annotate(
                word,
                xy=(1, 0),
                xycoords=pieces[-1],
                rotation=rotation,
                rotation_mode="anchor",
                ha="left",
                va="bottom",
            )
        )
    return pieces


def packed(ax, ref: Text, rotation: float) -> list[Artist]:
    """An ``HPacker`` of ``TextArea`` words in an ``AnnotationBbox``."""
    row = HPacker(
        children=[TextArea(w) for w in WORDS], pad=0, sep=0, align="baseline"
    )
    box = AnnotationBbox(
        row,
        ref.get_position(),
        xycoords="data",
        box_alignment=(0, 0),
        frameon=False,
        pad=0,
    )
    ax.add_artist(box)
    return [box]


def passes(ax, ref: Text, rotation: float) -> list[Text]:
    """One Text drawn once per word (:class:`legible.Passes`)."""
    text = ax.text(
        *ref.get_position(),
        NOTE,
        rotation=rotation,
        rotation_mode="anchor",
        ha="left",
        va="baseline",
    )
    spans = legible.spans(text, words=True)
    text.set_path_effects(
        [legible.Passes([(s, (0.0, 0.0, 0.0)) for s in spans])]
    )
    return [text]


def mechanisms_report() -> list[str]:
    """Each way to place the words of one note, against the unsplit note."""
    out = [
        f"#810 mechanisms: {len(WORDS)} words of {NOTE!r} against one Text, "
        "after dm.simple_layout; ink box of the pieces minus the Text's "
        "(start / end along x, pt)"
    ]
    ways: dict[str, Callable[..., list[Artist]]] = {
        "offsets measured once at dpi 100": lambda ax, ref, rot: measured_once(
            ax, ref, rot, 100
        ),
        "offsets from unhinted metrics": unhinted,
        "Annotation chain (xycoords=previous)": chained,
        "offsetbox HPacker / TextArea": packed,
        "one Text, one pass per word": passes,
    }
    for name, build in ways.items():
        for rotation in (0.0, 30.0):
            fig, ax, ref = scene(rotation)
            artists = build(ax, ref, rotation)
            fig.set_dpi(200)
            dm.simple_layout(fig)
            cells = []
            for dpi in (100, 200, 300):
                a, b = ink_box(fig, artists, dpi), ink_box(fig, [ref], dpi)
                cells.append(
                    f"{dpi}: {a.x0 - b.x0:+.2f} / {a.x1 - b.x1:+.2f}"
                    f" / y {a.y1 - b.y1:+.2f}"
                )
            ref.set_visible(False)
            facts = measure(fig)
            seen = sum(
                t.text.strip() in {w.strip() for w in WORDS} | {NOTE.strip()}
                for t in facts.texts
            )
            tight = ax.get_tightbbox(fig.canvas.get_renderer())
            extent = Bbox.union(
                [
                    a.get_window_extent(fig.canvas.get_renderer())
                    for a in artists
                ]
            )
            holds = bool(tight is not None and tight.x1 >= extent.x1 - 1)
            out.append(
                f"  {name:38s} rot {rotation:4.0f}: "
                + "; ".join(cells)
                + f" | dm.check reads {seen} text(s), layout box holds it: {holds}"
            )
            plt.close(fig)
    return out


def hinting_report() -> list[str]:
    """What drawing a text as an outline (any path effect) costs in Agg."""
    out = [
        "#810 a Text drawn through a path effect against the same Text drawn plainly (ink box, pt)"
    ]
    for dpi in (100, 200, 300):
        fig, ax, ref = scene(0.0)
        twin = ax.text(*ref.get_position(), NOTE, ha="left", va="baseline")
        twin.set_path_effects([legible.Probe()])
        fig.canvas.draw()
        a, b = ink_box(fig, [twin], dpi), ink_box(fig, [ref], dpi)
        out.append(
            f"  agg {dpi}: width {a.width - b.width:+.2f} pt of {b.width:.1f} "
            f"({(a.width - b.width) * dpi / 72:+.1f} px), height {a.height - b.height:+.2f} pt"
        )
        plt.close(fig)
    return out


def glue_report() -> list[str]:
    """The ink-per-shape fix, made once, read again at other sizes."""
    out = [
        "#810 ink per shape, fixed at 200 dpi, read again (share of ink under 3:1)"
    ]
    dm.style.use("report-kr")
    fig, note = cases.korean_note()
    before = legible.sample(fig, note)
    box = note.get_window_extent()
    legible.fix_auto(note, before)
    same = np.allclose(box.extents, note.get_window_extent().extents)
    out.append(
        f"  before {before.low:.1%}; the Text's extent unchanged by the fix: {same}"
    )
    for dpi in (100, 200, 300):
        fig.set_dpi(dpi)
        out.append(f"  dpi {dpi}: {legible.sample(fig, note).low:.1%}")
    fig.set_dpi(200)
    fig.set_size_inches(*dm.figsize("15cm", "7cm"))
    dm.simple_layout(fig)
    out.append(
        f"  resized to 15 x 7 cm and laid out again: {legible.sample(fig, note).low:.1%}"
    )
    plt.close(fig)
    return out


def main(out: Path) -> None:
    """Print every report and keep it beside the contact sheet."""
    dm.quiet()
    lines: list[str] = []
    for report in (
        columns_report,
        flow_report,
        mechanisms_report,
        hinting_report,
        glue_report,
    ):
        lines += [*report(), ""]
    text = "\n".join(lines)
    print(text)
    out.mkdir(parents=True, exist_ok=True)
    (out / "robust.txt").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else cases.OUT)
