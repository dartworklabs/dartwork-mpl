"""``simple_layout`` lays out every SubFigure inside its own box.

It used to fit one grid, the first Axes', and wrote edges measured as
fractions of the canvas into that SubFigure's grid, whose fractions are of
the SubFigure: tick labels ran off the canvas, a neighbour's axis name lay
on a plot and SubFigure titles sat under the panels, while the other
SubFigures kept matplotlib's placement. Now each grid is fitted in the box
of the (Sub)Figure that holds it, as a lone grid is fitted on the canvas:
flush with the canvas edges it touches, the panel gap (``_TARGET_EM``)
from a neighbouring SubFigure unless the caller parted them, clear of the
titles above it, its own ladder (wrap / space / rotate / pad) included.

The oracles are measured on the drawn figure: text past the canvas, text
of one Axes (or a figure-level text) on another Axes' plot or text, the
plot area against matplotlib's own placement, and where each grid's
content ends.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import axes_decoration_extents
from dartwork_mpl.layout._content_extent import _axes_content_extent_px

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.text import Text

SCENES = [
    "row_1x2_12cm",
    "row_1x2",
    "col_2x1",
    "nested",
    "mixed_grids",
    "sub_suptitles",
    "root_and_sub_suptitles",
    "width_ratios",
]


@pytest.fixture(autouse=True)
def _style() -> Iterator[None]:
    dm.style.use("report")
    yield
    plt.close("all")


def _wide_ticks(ax: Axes) -> None:
    ax.plot([0, 1e6], [0, 1])
    ax.set(xlabel="A long horizontal axis name [units]", ylabel="Share [-]")


def _tall_ticks(ax: Axes) -> None:
    ax.plot([0, 1], [0, 123456789])
    ax.set(xlabel="Distance [km]", ylabel="A long vertical axis name [units]")


def _small(ax: Axes, title: str | None = None) -> None:
    ax.plot([0, 1, 2], [3, 1, 2])
    ax.set(xlabel="Time [h]", ylabel="Load [kW]")
    if title:
        ax.set_title(title)


def _scene(name: str) -> Figure:
    """The design note's scenes (REPORT-6 §11): SubFigures side by side,
    stacked, nested, holding different grids, titled, and parted by the
    caller's ``width_ratios`` / ``wspace``."""
    width = "12cm" if name == "row_1x2_12cm" else "17cm"
    if name == "col_2x1":
        fig = plt.figure(figsize=dm.figsize("12cm", "tall"))
        top, bottom = fig.subfigures(2, 1)
        _wide_ticks(top.subplots())
        _small(bottom.subplots(), title="Measured load")
        return fig
    fig = plt.figure(figsize=dm.figsize(width, "wide"))
    if name == "width_ratios":
        left, right = fig.subfigures(1, 2, width_ratios=[2, 1], wspace=0.05)
    else:
        left, right = fig.subfigures(1, 2)
    if name in ("row_1x2_12cm", "row_1x2", "width_ratios"):
        _wide_ticks(left.subplots())
        _tall_ticks(right.subplots())
    elif name == "nested":
        _tall_ticks(left.subplots())
        for sub in right.subfigures(2, 1):
            _small(sub.subplots())
    elif name == "mixed_grids":
        _tall_ticks(left.subplots())
        for ax in right.subplots(2, 2).flat:
            _small(ax)
    else:
        _small(left.subplots())
        _small(right.subplots())
        if name == "root_and_sub_suptitles":
            fig.suptitle(
                "Measured electric load at both sites in the winter of 2025"
            )
        left.suptitle("(a) Site A")
        right.suptitle("(b) Site B")
    return fig


def _texts(ax: Axes) -> list[Bbox]:
    renderer = ax.get_figure(root=True).canvas.get_renderer()  # type: ignore[union-attr]
    boxes = list(axes_decoration_extents(ax, renderer))
    titles: list[Text] = [ax.title, ax._left_title, ax._right_title]  # type: ignore[attr-defined]
    boxes += [
        t.get_window_extent(renderer)
        for t in titles
        if t.get_visible() and t.get_text().strip()
    ]
    return [b for b in boxes if b.width > 0 and b.height > 0]


def _figure_texts(holder: Figure | SubFigure) -> list[Text]:
    """Figure-level texts of ``holder`` and its SubFigures, each once
    (matplotlib keeps a suptitle in ``texts`` too)."""
    found: list[Text] = []
    for t in (getattr(holder, "_suptitle", None), *holder.texts):
        if (
            t is not None
            and all(t is not seen for seen in found)
            and t.get_visible()
            and t.get_text().strip()
        ):
            found.append(t)
    for sub in holder.subfigs:
        found += _figure_texts(sub)
    return found


def _area(a: Bbox, b: Bbox) -> float:
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return float(w * h) if w > 0 and h > 0 else 0.0


def _measure(fig: Figure) -> dict[str, float]:
    """Text past the canvas (largest, px), text on another Axes' plot or
    text and figure-level text on any (px^2), and the plot share (%)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    w, h = fig.bbox.width, fig.bbox.height
    axes = [ax for ax in fig.axes if ax.get_visible()]
    frames = [ax.get_window_extent(renderer) for ax in axes]
    texts = [_texts(ax) for ax in axes]
    tops = [t.get_window_extent(renderer) for t in _figure_texts(fig)]
    past = max(
        [0.0]
        + [
            max(0.0, -b.x0, b.x1 - w, -b.y0, b.y1 - h)
            for b in [*tops, *(b for ts in texts for b in ts)]
        ]
    )
    cross = 0.0
    for i in range(len(axes)):
        for j in range(len(axes)):
            if i != j:
                cross += sum(_area(t, frames[j]) for t in texts[i])
            if j > i:
                cross += sum(_area(t, u) for t in texts[i] for u in texts[j])
    for k, top in enumerate(tops):
        parts = [
            p for f, ts in zip(frames, texts, strict=True) for p in (f, *ts)
        ]
        cross += sum(_area(top, p) for p in parts)
        cross += sum(_area(top, other) for other in tops[k + 1 :])
    plot = sum(f.width * f.height for f in frames) / (w * h) * 100
    return {"past": past, "cross": cross, "plot": plot}


def _content(fig: Figure, holder: Figure | SubFigure) -> Bbox:
    """Where the content of the Axes ``holder`` holds itself ends, as the
    layout measures it (a lone grid's content is flush with the canvas)."""
    renderer = fig.canvas.get_renderer()
    boxes = []
    for ax in fig.axes:
        if ax.get_figure(root=False) is holder:
            ext = _axes_content_extent_px(ax, renderer, fig)
            if ext is not None:
                x0, x1, y0, y1 = ext
                boxes.append(Bbox.from_extents(x0, y0, x1, y1))
    return Bbox.union(boxes)


def _holders(fig: Figure) -> list[Figure | SubFigure]:
    found: list[Figure | SubFigure] = []

    def walk(holder: Figure | SubFigure) -> None:
        if any(ax.get_figure(root=False) is holder for ax in fig.axes):
            found.append(holder)
        for sub in holder.subfigs:
            walk(sub)

    walk(fig)
    return found


@pytest.mark.parametrize("name", SCENES)
def test_every_subfigure_is_laid_out_in_its_own_box(name: str) -> None:
    untouched = _measure(_scene(name))
    fig = _scene(name)
    dm.simple_layout(fig)
    got = _measure(fig)
    assert got["past"] <= 0.5
    assert got["cross"] < 1.0
    assert got["plot"] > untouched["plot"]
    for ax in fig.axes:  # every grid was fitted, not the first one alone
        gs = ax.get_gridspec()
        assert gs is not None
        assert None not in (gs.left, gs.right, gs.bottom, gs.top), ax
        _assert_useful_plot(ax)


def _assert_useful_plot(ax: Axes) -> None:
    """A plot keeps a useful share of its holder's box: not one collapsed
    to the solver's clamp, which "content inside the box" alone misses."""
    holder = ax.get_figure(root=False)
    assert holder is not None
    frame = ax.get_window_extent()
    assert frame.width > 0.25 * holder.bbox.width, ax
    assert frame.height > 0.25 * holder.bbox.height, ax


@pytest.mark.parametrize("use_all_axes", [True, False])
def test_a_grid_named_by_gs_keeps_a_useful_plot(use_all_axes: bool) -> None:
    """``gs=`` on one SubFigure's grid with the default ``use_all_axes``
    measured the sibling SubFigure's Axes in this box's fractions and
    clamped the plot to 0.001 of it (review of #666, F1)."""
    fig = _scene("row_1x2")
    left = fig.subfigs[0]
    ax = next(a for a in fig.axes if a.get_figure(root=False) is left)
    dm.simple_layout(fig, gs=ax.get_gridspec(), use_all_axes=use_all_axes)
    fig.canvas.draw()
    _assert_useful_plot(ax)
    assert _measure(fig)["past"] <= 0.5


def test_a_title_only_parent_clears_the_figure_title() -> None:
    """A SubFigure that holds only nested SubFigures still has its own
    title placed under the figure title (review of #666, F2)."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    left.suptitle("Site A title")
    fig.suptitle("Root title covering both sites and their local headings")
    for sub in left.subfigures(2, 1):
        _small(sub.subplots())
    _small(right.subplots())
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    root = fig._suptitle.get_window_extent(renderer)  # type: ignore[union-attr]
    own = left._suptitle.get_window_extent(renderer)  # type: ignore[union-attr]
    assert not root.overlaps(own)
    assert _measure(fig)["cross"] < 1.0


def test_a_grid_named_by_gs_places_its_subfigure_title() -> None:
    """``gs=`` places the library-owned titles above that grid as well
    (review of #666, F3)."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    ax = left.subplots()
    _small(ax)
    _small(right.subplots())
    left.suptitle("Site A title")
    fig.suptitle("Root title covering both sites and their local headings")
    dm.simple_layout(fig, gs=ax.get_gridspec(), use_all_axes=False)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    root = fig._suptitle.get_window_extent(renderer)  # type: ignore[union-attr]
    own = left._suptitle.get_window_extent(renderer)  # type: ignore[union-attr]
    assert not root.overlaps(own)


def test_a_subfigure_title_clears_every_text_above_it() -> None:
    """Moved under the figure title, a SubFigure title met the subtitle
    under it and stayed there (Codex on #666): it moves until it clears
    every text above it."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    _small(left.subplots())
    _small(right.subplots())
    title = fig.suptitle("Measured electric load at both sites")
    fig.canvas.draw()
    under = title.get_window_extent(fig.canvas.get_renderer()).y0 - 2.0
    fig.text(
        0.5,
        under / fig.bbox.height,
        "A subtitle right under the figure title, as wide as both panel titles",
        ha="center",
        va="top",
    )
    left.suptitle("(a) Site A")
    right.suptitle("(b) Site B")
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = _figure_texts(fig)
    assert len(texts) == 4
    boxes = [t.get_window_extent(renderer) for t in texts]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not a.overlaps(b)
    assert _measure(fig)["cross"] < 1.0


def test_a_subfigure_is_fitted_as_the_same_figure_alone() -> None:
    """The decision's own words: a SubFigure's grid is fitted as a lone
    figure of its size with the same content is, on the canvas sides."""
    fig = _scene("row_1x2")
    dm.simple_layout(fig)
    fig.canvas.draw()
    left = fig.subfigs[0]
    ax = next(a for a in fig.axes if a.get_figure(root=False) is left)
    box, frame = left.bbox, ax.get_window_extent(fig.canvas.get_renderer())
    alone = plt.figure(
        figsize=(box.width / fig.dpi, box.height / fig.dpi), dpi=fig.dpi
    )
    lone_ax = alone.subplots()
    _wide_ticks(lone_ax)
    dm.simple_layout(alone)
    alone.canvas.draw()
    lone = lone_ax.get_window_extent(alone.canvas.get_renderer())
    assert frame.x0 - box.x0 == pytest.approx(lone.x0, abs=1.0)
    assert frame.y0 - box.y0 == pytest.approx(lone.y0, abs=1.0)
    assert box.y1 - frame.y1 == pytest.approx(alone.bbox.y1 - lone.y1, abs=1.0)


def _panel_gap_px(fig: Figure) -> float:
    return 0.5 * float(mpl.rcParams["font.size"]) * fig.dpi / 72.0


@pytest.mark.parametrize("name", ["row_1x2", "row_1x2_12cm", "col_2x1"])
def test_subfigures_face_each_other_a_panel_gap_apart(name: str) -> None:
    fig = _scene(name)
    dm.simple_layout(fig)
    fig.canvas.draw()
    first, second = (_content(fig, h) for h in _holders(fig))
    gap = first.y0 - second.y1 if name == "col_2x1" else second.x0 - first.x1
    assert gap >= _panel_gap_px(fig) - 1.0


def test_the_callers_width_ratios_and_wspace_are_kept() -> None:
    fig = _scene("width_ratios")
    boxes = [tuple(sub.bbox.extents) for sub in fig.subfigs]
    dm.simple_layout(fig)
    assert [tuple(sub.bbox.extents) for sub in fig.subfigs] == boxes
    left, right = (_content(fig, h) for h in _holders(fig))
    # The caller parted them: nothing is added to their own gap.
    parted = fig.subfigs[1].bbox.x0 - fig.subfigs[0].bbox.x1
    assert parted > 1.0
    assert right.x0 - left.x1 <= parted + 1.0


def _png(fig: Figure) -> bytes:
    out = io.BytesIO()
    fig.savefig(out, format="png", dpi=100)
    return out.getvalue()


@pytest.mark.parametrize(
    "name", ["nested", "mixed_grids", "root_and_sub_suptitles"]
)
def test_a_second_layout_draws_the_same(name: str) -> None:
    fig = _scene(name)
    dm.simple_layout(fig)
    once = _png(fig)
    dm.simple_layout(fig)
    assert _png(fig) == once


def test_without_the_ladder_each_subfigure_is_still_fitted() -> None:
    fig = _scene("row_1x2_12cm")
    dm.simple_layout(fig, fit_labels=False)
    got = _measure(fig)
    assert got["past"] <= 0.5
    assert got["cross"] < 1.0


def test_a_subfigure_title_the_library_placed_moves_under_the_figure_title() -> (
    None
):
    fig = _scene("root_and_sub_suptitles")
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    root = fig._suptitle.get_window_extent(renderer)  # type: ignore[union-attr]
    for sub in fig.subfigs:
        title = sub._suptitle.get_window_extent(renderer)  # type: ignore[union-attr]
        assert title.y1 <= root.y0


def test_a_subfigure_title_the_caller_placed_stays() -> None:
    fig = _scene("root_and_sub_suptitles")
    fig.subfigs[0].suptitle("(a) Site A", y=0.9)
    dm.simple_layout(fig)
    assert fig.subfigs[0]._suptitle.get_position()[1] == 0.9  # type: ignore[union-attr]


def test_a_grid_named_by_gs_is_fitted_in_its_subfigure() -> None:
    """``gs=`` names one SubFigure's grid: that grid alone is fitted, in its
    own box; the other SubFigure is left as it was."""
    fig = _scene("row_1x2_12cm")
    left, right = fig.subfigs
    right_ax = next(ax for ax in fig.axes if ax.get_figure(root=False) is right)
    before = tuple(right_ax.get_position().bounds)
    left_ax = next(ax for ax in fig.axes if ax.get_figure(root=False) is left)
    dm.simple_layout(fig, gs=left_ax.get_gridspec())
    fig.canvas.draw()
    assert tuple(right_ax.get_position().bounds) == before
    content = _content(fig, left)
    assert content.x0 >= fig.bbox.x0 - 0.5
    assert content.x1 <= left.bbox.x1 + 0.5


def test_a_figure_without_subfigures_fits_as_before() -> None:
    """The control: one grid on the canvas, flush and clear (true on main;
    at 12 cm this grid keeps an overlap of its own, a matter of the grid's
    ladder and not of SubFigures)."""
    fig, (a, b) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    _wide_ticks(a)
    _tall_ticks(b)
    dm.simple_layout(fig)
    got = _measure(fig)
    assert got["past"] <= 0.5
    assert got["cross"] < 1.0
