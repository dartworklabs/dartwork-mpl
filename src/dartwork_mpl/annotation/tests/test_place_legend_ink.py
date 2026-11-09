"""``place_legend`` keeps clear of the ink an artist draws, edges included, and of nothing else.

The placer read a scatter point by its marker size, a line's markers by
theirs, a patch and a filled area by their outline and an Axes text by its
glyphs: the edge each strokes half outside its outline and a text's
background box (``bbox=``) were left out, so the legend took the first spot
over them, while ``LEGEND_ON_DATA`` reads the scatter, marker and area edges
as drawn. It also kept clear of what is not drawn there: a line, scatter,
patch or text at alpha 0, clipped away, or a masked scatter point.

The oracle is the drawn pixels. The first spot is the upper right of the
plain figure (B). Each target either changes pixels inside B or not; after
``place_legend`` the legend covers none of the pixels the target draws, and
where the target draws none in B the legend takes B. A target drawn in B
keeps the legend away (the controls).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox, TransformedBbox

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

GRAY = "oc.gray7"


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _axes():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([0, 10], [1, 2], label="Low line")
    ax.plot([0, 10], [2, 3], label="Lower line")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    return fig, ax


def _first_spot() -> Bbox:
    """B: where ``place_legend`` puts the legend of the plain figure."""
    fig, ax = _axes()
    dm.place_legend(ax)
    box = ax.get_legend().get_window_extent(drawn_renderer(fig))
    plt.close(fig)
    return box


def _add(fig, ax, case: str, b: Bbox):
    """The target of ``case``, placed against B (display px)."""
    pt = fig.dpi / 72.0
    to_data = ax.transData.inverted()
    mid = (b.y0 + b.y1) / 2
    ((cx, cy),) = to_data.transform([((b.x0 + b.x1) / 2, mid)])
    left = b.x0 - 6 * pt  # a disc 3 pt across its radius, 6 pt from B
    ((lx, ly),) = to_data.transform([(left, mid)])
    away = TransformedBbox(Bbox.from_extents(0, 0, 10, 4), ax.transData)
    match case:
        # Ink the placer missed: an edge 7-8 pt past the outline it read.
        case "scatter_edge":
            return ax.scatter([lx], [ly], s=36, linewidths=14, color=GRAY)
        case "marker_edge":
            return ax.plot([lx], [ly], "o", ms=6, mew=14, color=GRAY)[0]
        case "patch_edge":
            ((x0, y0), (x1, y1)) = to_data.transform(
                [(b.x0 - 40 * pt, b.y0), (b.x0 - 3 * pt, b.y1)]
            )
            return ax.add_patch(
                Rectangle(
                    (x0, y0), x1 - x0, y1 - y0, fc="oc.gray3", ec=GRAY, lw=16
                )
            )
        case "text_box":
            ((tx, ty),) = to_data.transform([(b.x0 - 3 * pt, mid)])
            return ax.text(
                tx,
                ty,
                "Note",
                ha="right",
                va="center",
                bbox={
                    "boxstyle": "square",
                    "pad": 1.2,
                    "fc": "oc.gray2",
                    "ec": GRAY,
                },
            )
        case "area_edge":  # REPORT §7-6: a band clear of the corner, 24 pt edge
            band = [(6.5, 7.6), (10.5, 7.6), (10.5, 8.6), (6.5, 8.6)]
            return ax.add_collection(
                PolyCollection(
                    [band],
                    facecolors="oc.gray3",
                    edgecolors=GRAY,
                    linewidths=24,
                )
            )
        # Drawn nowhere in B.
        case "line_alpha0":
            return ax.plot([cx - 1, cx + 1], [cy, cy], lw=6, alpha=0)[0]
        case "line_clipped":
            line = ax.plot([cx - 1, cx + 1], [cy, cy], lw=6, color=GRAY)[0]
            line.set_clip_box(away)
            return line
        case "scatter_alpha0":
            return ax.scatter([cx], [cy], s=200, alpha=0)
        case "scatter_clipped":
            points = ax.scatter([cx], [cy], s=200, color=GRAY)
            points.set_clip_box(away)
            return points
        case "scatter_masked":
            xs = np.ma.masked_array([cx, 1.0], mask=[True, False])
            return ax.scatter(xs, [cy, 1.0], s=200, color=GRAY)
        case "patch_alpha0":
            return ax.add_patch(
                Rectangle((cx - 0.3, cy - 0.3), 0.6, 0.6, alpha=0)
            )
        case "text_alpha0":
            return ax.text(
                cx, cy, "Hidden note", ha="center", va="center", alpha=0
            )
        case "text_clipped":
            text = ax.text(cx, cy, "Clipped note", ha="center", va="center")
            text.set_clip_on(True)
            text.set_clip_box(away)
            return text
        # Controls: the same artists drawn in B.
        case "line_drawn":
            return ax.plot([cx - 1, cx + 1], [cy, cy], lw=6, color=GRAY)[0]
        case "scatter_drawn":
            return ax.scatter([cx], [cy], s=200, color=GRAY)
        case "patch_drawn":
            return ax.add_patch(
                Rectangle((cx - 0.3, cy - 0.3), 0.6, 0.6, fc=GRAY)
            )
        case "text_drawn":
            return ax.text(cx, cy, "Drawn note", ha="center", va="center")
    raise ValueError(case)


def _rgba(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _drawn(fig, ax, target, box: Bbox) -> int:
    """Pixels ``target`` draws inside ``box``, the legend (if any) hidden."""
    legend = ax.get_legend()
    if legend is not None:
        legend.set_visible(False)
    shown = _rgba(fig)
    target.set_visible(False)
    hidden = _rgba(fig)
    target.set_visible(True)
    if legend is not None:
        legend.set_visible(True)
    h = shown.shape[0]
    rows = slice(max(0, h - int(np.ceil(box.y1))), h - int(np.floor(box.y0)))
    cols = slice(max(0, int(np.floor(box.x0))), int(np.ceil(box.x1)))
    return int(np.any(shown[rows, cols] != hidden[rows, cols], axis=2).sum())


def _placed(fig, ax) -> Bbox:
    dm.place_legend(ax)
    return ax.get_legend().get_window_extent(drawn_renderer(fig))


def _clean(fig) -> bool:
    return dm.validate_figure(fig, checks=("LEGEND_ON_DATA",), quiet=True) == []


@pytest.mark.parametrize(
    "case",
    ["scatter_edge", "marker_edge", "patch_edge", "text_box", "area_edge"],
)
def test_the_legend_covers_none_of_the_edge_an_artist_draws(case: str) -> None:
    b = _first_spot()
    fig, ax = _axes()
    target = _add(fig, ax, case, b)
    assert _drawn(fig, ax, target, b) > 0  # the oracle: it draws in B
    box = _placed(fig, ax)
    assert _drawn(fig, ax, target, box) == 0
    assert _clean(fig)


@pytest.mark.parametrize(
    "case",
    [
        "line_alpha0",
        "line_clipped",
        "scatter_alpha0",
        "scatter_clipped",
        "scatter_masked",
        "patch_alpha0",
        "text_alpha0",
        "text_clipped",
    ],
)
def test_what_draws_nothing_in_the_first_spot_leaves_it_to_the_legend(
    case: str,
) -> None:
    b = _first_spot()
    fig, ax = _axes()
    target = _add(fig, ax, case, b)
    assert _drawn(fig, ax, target, b) == 0  # the oracle: nothing drawn in B
    box = _placed(fig, ax)
    assert np.allclose(box.extents, b.extents, atol=1.0)
    assert _clean(fig)


@pytest.mark.parametrize(
    "case", ["line_drawn", "scatter_drawn", "patch_drawn", "text_drawn"]
)
def test_what_draws_in_the_first_spot_keeps_the_legend_away(case: str) -> None:
    b = _first_spot()
    fig, ax = _axes()
    target = _add(fig, ax, case, b)
    assert _drawn(fig, ax, target, b) > 0  # the oracle: drawn in B
    box = _placed(fig, ax)
    assert _drawn(fig, ax, target, box) == 0
    assert not np.allclose(box.extents, b.extents, atol=1.0)
