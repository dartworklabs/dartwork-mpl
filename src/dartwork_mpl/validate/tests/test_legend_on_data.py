"""LEGEND_ON_DATA and the outside-size rule of LEGEND_OVERFLOW.

The oracle is what a reader sees once the figure is drawn: a legend box
lying on a line, a bar, a marker, a text, another legend or another
panel, by more than half a point. The negatives are legends in a free
corner, beside the data by a touch, outside the Axes, on top of their own
overlay Axes, and artists the reader cannot see.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity
from tests.support.mpl_observe import drawn_renderer

ID = "LEGEND_ON_DATA"


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _found(fig, *checks: str):
    return list(dm.validate_figure(fig, checks=checks or (ID,), quiet=True))


def _fig(width: str = "12cm"):
    return plt.subplots(figsize=dm.figsize(width, "standard"))


def _dense(ax, n: int = 5) -> None:
    """``n`` sine lines through the whole plot: every corner holds data."""
    x = np.linspace(0, 11, 60)
    for i in range(n):
        ax.plot(
            x,
            50 + 42 * np.sin(2 * np.pi * x / 6 + 2 * np.pi * i / n),
            label=f"Region {i + 1}",
        )


# ----------------------------------------------------------- must report
def test_a_legend_on_lines_is_reported() -> None:
    fig, ax = _fig()
    _dense(ax)
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.severity == Severity.WARNING
    assert w.detail["legend_axes"] == 0
    assert w.detail["covered"] == ["line"]
    assert w.detail["panels"] == [0]
    assert w.detail["legend_labels"][0] == "Region 1"
    assert w.message.startswith("Legend of axes[0] covers lines")


def test_a_legend_on_bars_is_reported() -> None:
    fig, ax = _fig()
    ax.bar(np.arange(6), [9, 9.5, 9.8, 9.6, 9.9, 9.7], label="Sales")
    ax.set_ylim(0, 10)
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["bar"]
    assert w.detail["artists"] == ["Sales"]


def test_a_legend_on_scatter_points_is_reported() -> None:
    fig, ax = _fig()
    grid = np.linspace(0, 10, 25)
    xs, ys = np.meshgrid(grid, grid)
    ax.scatter(xs.ravel(), ys.ravel(), s=12, label="Sites")
    ax.legend(loc="center")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["marker"]


def test_a_legend_on_a_value_label_is_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 10], [0, 1], label="Trend")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.text(9.6, 9.6, "Peak 9.6", ha="right", va="top")
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["text"]
    assert w.detail["artists"] == ["Peak 9.6"]


def test_twin_legends_on_each_other_are_both_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 0.1], label="Left series")
    twin = ax.twinx()
    twin.plot([0, 1], [0, 0.1], color="oc.red5", label="Right series")
    ax.legend(loc="upper right")
    twin.legend(loc="upper right")
    found = _found(fig)
    assert [w.detail["covered"] for w in found] == [["legend"], ["legend"]]
    assert [w.detail["artists"] for w in found] == [
        ["legend of axes[1]"],
        ["legend of axes[0]"],
    ]


def test_a_legend_on_the_twins_data_is_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 0.1], label="Low")
    twin = ax.twinx()
    _dense(twin, 3)
    twin.set_ylim(20, 80)  # the twin's lines run through every corner
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["legend_axes"] == 0
    assert w.detail["covered"] == ["line"]


def test_a_legend_reaching_into_the_next_panel_is_reported() -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    left.plot([0, 1], [0, 0.1], label="A series with a long name")
    right.plot([0, 1], [0, 0.1])
    left.legend(loc="center left", bbox_to_anchor=(0.9, 0.5))
    (w,) = _found(fig)
    assert w.detail["legend_axes"] == 0
    assert "panel" in w.detail["covered"]
    assert "axes[1]" in w.detail["artists"]


def test_a_figure_legend_over_the_panels_is_reported() -> None:
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    for ax in axs:
        _dense(ax, 3)
    fig.legend(*axs[0].get_legend_handles_labels(), loc="center")
    found = _found(fig)
    assert len(found) == 1
    (w,) = found
    assert w.detail["legend_axes"] is None
    assert w.message.startswith("Figure legend covers")
    assert w.detail["panels"]  # the panel(s) whose lines it covers


# ------------------------------------------- filled areas: violins, bands
def _violin_with_a_long_tail(ax):
    """One violin at the right edge whose thin lower tail runs into the
    lower-right corner, as advanced/violin's last region did, and a
    ``Median`` marker for the legend."""
    rng = np.random.default_rng(7)
    data = np.concatenate([rng.normal(72, 5, 400), [41.0, 43.0]])
    (body,) = ax.violinplot([data], positions=[3], showextrema=False)["bodies"]
    ax.scatter(
        [3], [np.median(data)], color="white", edgecolor="k", label="Median"
    )
    ax.set(xlim=(0.5, 3.4), ylim=(40, 100))
    return body


def _meets_path(fig, legend, area) -> bool:
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    return any(
        area.get_transform()
        .transform_path(path)
        .intersects_bbox(box, filled=True)
        for path in area.get_paths()
    )


def test_a_legend_on_a_violins_thin_tail_is_reported() -> None:
    fig, ax = _fig()
    body = _violin_with_a_long_tail(ax)
    legend = ax.legend(loc="lower right", frameon=False)
    assert _meets_path(
        fig, legend, body
    )  # precondition: the tail runs under it
    found = _found(fig)
    assert [w.detail["covered"] for w in found] == [["area"]]
    assert found[0].message.startswith("Legend of axes[0] covers areas")


def test_a_legend_across_a_bands_edges_is_reported() -> None:
    """A band thinner than the legend: the legend hides where it starts and ends."""
    fig, ax = _fig()
    ax.fill_between([0, 10], 4.8, 5.2, color="oc.gray2", label="Range")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.plot([], [], label="Mean")
    ax.legend(loc="center")
    found = _found(fig)
    assert [w.detail["covered"] for w in found] == [["area"]]
    assert found[0].detail["artists"] == ["Range"]


def test_a_legend_holding_a_whole_area_is_reported() -> None:
    fig, ax = _fig()
    ax.fill_between([4.8, 5.2], 4.9, 5.1, color="oc.gray6", label="Spot")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.plot([], [], label="Mean")
    ax.legend(loc="center")
    found = _found(fig)
    assert [w.detail["covered"] for w in found] == [["area"]]


def test_a_legend_beside_a_filled_band_is_clean() -> None:
    fig, ax = _fig()
    ax.fill_between([0, 10], 0, 4, color="oc.gray2", label="Range")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.legend(loc="upper right")
    assert _found(fig) == []


def test_a_legend_inside_a_region_that_fills_the_plot_is_clean() -> None:
    """Regions tiling the plot (a phase diagram): inside one region's plain
    interior the legend hides none of the regions' shapes."""
    fig, ax = _fig()
    x = np.linspace(0, 10, 50)
    low, high = 2 + 0.3 * x, 5 + 0.3 * x
    ax.fill_between(x, 0, low, color="oc.teal1", label="Solid")
    ax.fill_between(x, low, high, color="oc.violet1", label="Liquid")
    ax.fill_between(x, high, 14, color="oc.orange1", label="Gas")
    ax.set(xlim=(0, 10), ylim=(0, 14))
    ax.legend(loc="upper left")
    assert _found(fig) == []


@pytest.mark.parametrize(
    ("face", "edge"),
    [("none", "none"), ("none", "k")],
    ids=["no_ink", "outline"],
)
def test_an_area_counts_by_the_ink_it_draws_under_the_legend(
    face: str, edge: str
) -> None:
    """No face and no edge draws nothing; an outline draws only its edge,
    which runs well clear of a legend in its middle."""
    fig, ax = _fig()
    ax.fill_between(
        [0, 10], 0.5, 9.5, facecolor=face, edgecolor=edge, label="Box"
    )
    ax.set(xlim=(-1, 11), ylim=(-1, 11))
    ax.plot([], [], label="Mean")
    ax.legend(loc="center")
    assert _found(fig) == []


def test_an_outline_counts_where_its_edge_runs_under_the_legend() -> None:
    fig, ax = _fig()
    ax.fill_between(
        [0, 10], 0.5, 5, facecolor="none", edgecolor="k", label="Box"
    )
    ax.set(xlim=(-1, 11), ylim=(-1, 11))
    ax.plot([], [], label="Mean")
    ax.legend(loc="center")  # straddles the outline's top edge at y = 5
    found = _found(fig)
    assert [w.detail["covered"] for w in found] == [["area"]]


def test_meshes_and_contours_are_still_not_data() -> None:
    fig, ax = _fig()
    x, y = np.meshgrid(np.linspace(0, 1, 20), np.linspace(0, 1, 20))
    ax.contourf(x, y, x + y)
    ax.plot([], [], label="Mean")
    ax.legend(loc="center")
    assert _found(fig) == []


def _area_in_the_legend(mode: str):
    """A polygon inside a centred legend that ``mode`` keeps from drawing:
    clipped away by its clip box or clip path, or transparent beside an
    opaque polygon of the same collection (review of #660)."""
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    legend = ax.legend(
        handles=[Patch(facecolor="dc.blue5", label="Area")], loc="center"
    )
    fig.canvas.draw()
    to_data = ax.transData.inverted()
    x0, y0, x1, y1 = to_data.transform_bbox(legend.get_window_extent()).extents
    hidden = [
        (x0 + 0.01, y0 + 0.01),
        (x1 - 0.01, y0 + 0.01),
        (x1 - 0.01, y1 - 0.01),
        (x0 + 0.01, y1 - 0.01),
    ]
    visible = [(0.1, 0.1), (0.2, 0.1), (0.2, 0.2), (0.1, 0.2)]
    if mode == "mixed_alpha":
        coll = PolyCollection(
            [hidden, visible],
            facecolors=[(0, 0, 1, 0), (0, 0, 1, 1)],
            edgecolors="none",
        )
    else:
        coll = PolyCollection(
            [hidden], facecolors=["dc.blue5"], edgecolors="none"
        )
    ax.add_collection(coll)
    if mode == "clip_box":
        coll.set_clip_box(Bbox.from_bounds(0, 0, 1, 1))
    if mode == "clip_path":
        coll.set_clip_path(
            Rectangle((0.05, 0.05), 0.1, 0.1, transform=ax.transData)
        )
    return fig, coll, visible


@pytest.mark.parametrize("mode", ["clip_box", "clip_path", "mixed_alpha"])
def test_an_area_that_draws_nothing_under_the_legend_does_not_count(
    mode: str,
) -> None:
    """The oracle: removing the polygon under the legend changes no pixel."""
    fig, coll, visible = _area_in_the_legend(mode)
    fig.canvas.draw()
    before = np.asarray(fig.canvas.buffer_rgba()).copy()
    found = _found(fig)
    if mode == "mixed_alpha":
        coll.set_verts([visible])
        coll.set_facecolors([(0, 0, 1, 1)])
    else:
        coll.set_visible(False)
    fig.canvas.draw()
    assert np.array_equal(before, np.asarray(fig.canvas.buffer_rgba()))
    assert _kinds(found) == []


def _kinds(found) -> list[tuple[str, object]]:
    """Each finding's check and what it covers (``None`` for a failed check)."""
    return [(w.check_id, (w.detail or {}).get("covered")) for w in found]


_BAND = [(0, 4.95), (10, 4.95), (10, 5.05), (0, 5.05)]  # thinner than it
_FAR = [(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)]


def _two_polygons(alphas, *, polygons=(_BAND, _FAR), hatch_only=False):
    """One collection, a band through a centred legend and a square far
    from it, with one artist alpha per polygon; ``hatch_only`` draws them
    by a hatch alone (no face, no edge)."""
    fig, ax = _fig()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    style = (
        {"facecolors": "none", "edgecolors": "none", "hatch": "//"}
        if hatch_only
        else {"facecolors": "oc.gray6", "edgecolors": "none"}
    )
    ax.add_collection(PolyCollection(list(polygons), alpha=alphas, **style))
    ax.plot([], [], label="Mean")
    ax.legend(loc="center")
    return fig


def test_an_area_with_one_alpha_per_polygon_is_measured() -> None:
    """``alpha=[0.4, 0.8]`` is an array: read per polygon, the band under
    the legend draws and is reported (the check does not fail)."""
    assert _kinds(_found(_two_polygons([0.4, 0.8]))) == [(ID, ["area"])]


def test_a_polygon_at_alpha_zero_in_an_alpha_array_does_not_count() -> None:
    assert _kinds(_found(_two_polygons([0.0, 1.0]))) == []


def test_a_legend_handle_with_one_alpha_per_point_is_read() -> None:
    """A scatter's alpha array reaches its legend handle; with the entry
    text drawing nothing the handle decides whether the legend inks, and
    the check reads it instead of failing (Codex on #660)."""
    fig, ax = _fig()
    ax.plot([0, 10], [5, 5], label="_flat")
    ax.scatter([20, 21], [20, 21], alpha=[0.3, 0.6], label="Points")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.legend(loc="center", frameon=False, labelcolor="none")
    assert _kinds(_found(fig)) == [(ID, ["line"])]


def test_a_hatch_at_alpha_zero_in_an_alpha_array_does_not_count() -> None:
    """The oracle: the hatched band at alpha 0 draws no pixel (the figure
    equals one with the far square alone)."""

    def pixels(fig) -> np.ndarray:
        fig.canvas.draw()
        return np.asarray(fig.canvas.buffer_rgba()).copy()

    fig = _two_polygons([0.0, 1.0], hatch_only=True)
    alone = _two_polygons([1.0], polygons=(_FAR,), hatch_only=True)
    assert np.array_equal(pixels(fig), pixels(alone))
    assert _kinds(_found(fig)) == []
    lit = _two_polygons([1.0, 1.0], hatch_only=True)
    assert _kinds(_found(lit)) == [(ID, ["area"])]  # drawn, it counts


# ----------------------------------------------------------- must not report
def test_a_legend_in_a_free_corner_is_clean() -> None:
    fig, ax = _fig()
    ax.plot([0, 10], [0, 2], label="Low")
    ax.plot([0, 10], [1, 3], label="Lower")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.legend(loc="upper left")
    assert _found(fig) == []


def _line_near_the_legend_bottom(overlap_pt: float):
    """A horizontal data line whose stroke overlaps the legend by ``overlap_pt``."""
    fig, ax = _fig()
    ax.plot([0, 10], [9, 9.5], label="Top")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    legend = ax.legend(loc="upper left")
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    width_pt = 1.0
    half = width_pt / 2 * fig.dpi / 72.0
    y_px = box.y0 - half + overlap_pt * fig.dpi / 72.0
    to_data = ax.transData.inverted()
    ((_x, y),) = to_data.transform([(box.x0, y_px)])
    ax.plot([0, 10], [y, y], lw=width_pt, color="oc.gray5", label="_ref")
    return fig


def test_a_touch_of_half_a_point_is_not_a_cover() -> None:
    assert _found(_line_near_the_legend_bottom(0.25)) == []


def test_more_than_half_a_point_is_a_cover() -> None:
    (w,) = _found(_line_near_the_legend_bottom(1.0))
    assert w.detail["covered"] == ["line"]
    assert w.detail["artists"] == [""]  # the line has no legend label


def _band_under_the_legend(overlap_pt: float, edge_pt: float):
    """A band from the bottom whose top outline, stroked ``edge_pt`` wide
    (0: no edge), reaches ``overlap_pt`` into the legend's bottom."""
    fig, ax = _fig()
    ax.plot([], [], label="Mean")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    legend = ax.legend(loc="upper left")
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    half = edge_pt / 2 * fig.dpi / 72.0
    y_px = box.y0 - half + overlap_pt * fig.dpi / 72.0
    ((_x, y),) = ax.transData.inverted().transform([(box.x0, y_px)])
    ax.fill_between(
        [0, 10],
        0,
        y,
        facecolor="oc.gray2",
        edgecolor="oc.gray6",
        linewidth=edge_pt,
        label="Band",
    )
    return fig


@pytest.mark.parametrize("edge_pt", [0.0, 2.0], ids=["no_edge", "edge_2pt"])
def test_an_area_outline_within_half_a_point_is_a_touch(edge_pt: float) -> None:
    assert _found(_band_under_the_legend(0.25, edge_pt)) == []


@pytest.mark.parametrize("edge_pt", [0.0, 2.0], ids=["no_edge", "edge_2pt"])
def test_an_area_outline_more_than_half_a_point_in_is_a_cover(
    edge_pt: float,
) -> None:
    """The edge's stroke counts: 2 pt wide, its path stays 0 pt below the
    legend while the stroke reaches 1 pt into it."""
    found = _found(_band_under_the_legend(1.0, edge_pt))
    assert [w.detail["covered"] for w in found] == [["area"]]


def test_a_legend_above_the_axes_is_clean() -> None:
    fig, ax = _fig()
    _dense(ax)
    dm.place_legend(ax, loc="above")
    dm.simple_layout(fig)
    assert _found(fig) == []


def test_hidden_data_and_hidden_legends_do_not_count() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 0.1], label="Shown")
    hidden = ax.plot([0, 1], [1, 1], label="Hidden")[0]
    hidden.set_visible(False)
    ax.set(xlim=(0, 1), ylim=(0, 1.05))
    ax.legend(loc="upper right")
    assert _found(fig) == []
    _dense(ax)
    ax.legend(loc="upper right").set_visible(False)
    assert _found(fig) == []


def test_a_legend_inside_an_overlay_axes_is_drawn_over_the_panel_below() -> (
    None
):
    """An Axes added on top of a panel: its own legend is not on that panel."""
    fig, ax = _fig()
    _dense(ax)
    overlay = fig.add_axes((0.55, 0.55, 0.3, 0.3))
    overlay.plot([0, 1], [0, 0.1], label="Detail")
    overlay.set(xlim=(0, 1), ylim=(0, 1))
    overlay.legend(loc="upper left")
    assert _found(fig) == []


def _flat_line_under_centre(ax) -> None:
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0.5, 0.5], label="Series")


def test_a_legend_that_draws_nothing_is_not_reported() -> None:
    """No frame and no entry, or every part at alpha 0: nothing covers the line."""
    fig, ax = _fig()
    _flat_line_under_centre(ax)
    ax.legend([], [], loc="center", frameon=False)
    assert _found(fig) == []

    fig, ax = _fig()
    _flat_line_under_centre(ax)
    legend = ax.legend(loc="center")
    legend.get_frame().set_alpha(0)
    for text in legend.get_texts():
        text.set_alpha(0)
    for handle in legend.legend_handles:
        handle.set_alpha(0)
    assert _found(fig) == []


def test_a_frameless_legend_with_entries_is_still_reported() -> None:
    fig, ax = _fig()
    _flat_line_under_centre(ax)
    ax.legend(loc="center", frameon=False)
    (w,) = _found(fig)
    assert w.detail["covered"] == ["line"]


@pytest.mark.parametrize(
    "kind", ["line_color_none", "line_no_stroke", "patch_none"]
)
def test_a_legend_with_no_rendered_ink_does_not_cover_data(kind: str) -> None:
    """A legend identical to removing it cannot obscure the line.

    Review 2 (648-R1), moved here as the reviewer wrote it.
    """
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "9cm"))
    try:
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.plot([0, 1], [0.5, 0.5])
        handle = (
            Patch(facecolor="none", edgecolor="none")
            if kind == "patch_none"
            else Line2D([], [], color="none")
        )
        if kind == "line_no_stroke":
            handle.set(color="black", linestyle="None", marker="None")
        legend = ax.legend(
            handles=[handle], labels=["Invisible"], loc="center", frameon=False
        )
        for text in legend.get_texts():
            text.set_color("none")
        fig.canvas.draw()
        before = np.asarray(fig.canvas.buffer_rgba()).copy()
        found = dm.validate_figure(fig, checks=["LEGEND_ON_DATA"], quiet=True)
        legend.remove()
        fig.canvas.draw()
        assert np.array_equal(before, np.asarray(fig.canvas.buffer_rgba()))
        assert found == []
    finally:
        plt.close(fig)


def _draws(fig, artist) -> bool:
    """The oracle: whether removing ``artist`` changes the drawn pixels."""
    fig.canvas.draw()
    before = np.asarray(fig.canvas.buffer_rgba()).copy()
    artist.remove()
    fig.canvas.draw()
    return not np.array_equal(before, np.asarray(fig.canvas.buffer_rgba()))


def _away(ax, method: str, **kw):
    """A data artist drawn outside the view, to serve as a handle."""
    if method == "fill_between":
        return ax.fill_between([5, 6], [5, 5], [6, 6], **kw)
    if method == "scatter":
        return ax.scatter([5], [5], **kw)
    return ax.errorbar([5], [5], yerr=[0.2], **kw)


# Each handle type drawing ink, or none, by what it strokes, fills, marks or
# hatches; data artists become legend Rectangles, PathCollections and
# errorbar lines (whose first artist may draw nothing while the bars do).
_HANDLES = {
    "line_colour_alpha0_alpha1": (
        True,
        lambda ax: Line2D([], [], color=(0, 0, 0, 0), alpha=1),
    ),
    "line_width0": (False, lambda ax: Line2D([], [], color="k", linewidth=0)),
    "marker_hollow_no_edge": (
        False,
        lambda ax: Line2D(
            [],
            [],
            linestyle="None",
            marker="o",
            markerfacecolor="none",
            markeredgewidth=0,
        ),
    ),
    "marker_only": (
        True,
        lambda ax: Line2D([], [], linestyle="None", marker="o", color="k"),
    ),
    "patch_hatch_only": (
        True,
        lambda ax: Patch(facecolor="none", edgecolor="none", hatch="//"),
    ),
    "patch_hatch_colour_none": (
        False,
        lambda ax: Patch(
            facecolor="none", edgecolor="none", hatch="//", hatchcolor="none"
        ),
    ),
    "patch_edge_width0": (
        False,
        lambda ax: Patch(facecolor="none", edgecolor="k", linewidth=0),
    ),
    "poly_none": (
        False,
        lambda ax: _away(
            ax, "fill_between", facecolor="none", edgecolor="none"
        ),
    ),
    "poly_face": (
        True,
        lambda ax: _away(ax, "fill_between", facecolor="k", edgecolor="none"),
    ),
    "poly_hatch_only": (
        True,
        lambda ax: _away(
            ax, "fill_between", facecolor="none", edgecolor="none", hatch="//"
        ),
    ),
    "scatter_none": (
        False,
        lambda ax: _away(ax, "scatter", facecolors="none", edgecolors="none"),
    ),
    "scatter_size0": (False, lambda ax: _away(ax, "scatter", s=0, color="k")),
    "scatter_edge_width0": (
        False,
        lambda ax: _away(
            ax, "scatter", facecolors="none", edgecolors="k", linewidths=0
        ),
    ),
    "scatter_edge_only": (
        True,
        lambda ax: _away(
            ax, "scatter", facecolors="none", edgecolors="k", linewidths=1
        ),
    ),
    "scatter_drawn": (True, lambda ax: _away(ax, "scatter", color="k")),
    "errorbar_none": (
        False,
        lambda ax: _away(ax, "errorbar", color="none", ecolor="none"),
    ),
    "errorbar_bars_only": (
        True,
        lambda ax: _away(
            ax, "errorbar", color="k", linestyle="None", marker="None"
        ),
    ),
    # The entry's first artist (the bars) draws nothing; its line does.
    "errorbar_line_only": (
        True,
        lambda ax: _away(ax, "errorbar", color="k", ecolor="none"),
    ),
}


@pytest.mark.parametrize("case", list(_HANDLES))
def test_a_legend_counts_when_its_handle_draws_ink(case: str) -> None:
    ink, make = _HANDLES[case]
    fig, ax = _fig()
    _flat_line_under_centre(ax)
    legend = ax.legend(
        handles=[make(ax)], labels=["Entry"], loc="center", frameon=False
    )
    for text in legend.get_texts():
        text.set_color("none")
    found = _found(fig)
    assert _draws(fig, legend) is ink
    assert bool(found) is ink


@pytest.mark.parametrize(
    ("part", "colour", "alpha", "ink"),
    [
        ("entry", (1, 0, 0, 0), 1, True),
        ("entry", "red", 0, False),
        ("entry", (1, 0, 0, 0), None, False),
        ("title", (1, 0, 0, 0), 1, True),
        ("title", "red", 0, False),
        ("title", "none", None, False),
    ],
)
def test_a_legend_text_draws_by_its_own_alpha_over_its_colour(
    part: str, colour, alpha, ink: bool
) -> None:
    fig, ax = _fig()
    _flat_line_under_centre(ax)
    legend = ax.legend(
        handles=[Line2D([], [], color="none")],
        labels=["Entry"],
        loc="center",
        frameon=False,
        title="Heading",
    )
    legend.get_title().set_color("none")
    for text in legend.get_texts():
        text.set_color("none")
    shown = legend.get_title() if part == "title" else legend.get_texts()[0]
    shown.set_color(colour)
    shown.set_alpha(alpha)
    found = _found(fig)
    assert _draws(fig, legend) is ink
    assert bool(found) is ink


def _text_under_legend(**text_kw):
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0.05, 0.05], label="Low")
    text = ax.text(0.5, 0.5, "Centre note", ha="center", va="center", **text_kw)
    ax.legend(loc="center")
    return fig, text


def test_a_text_is_compared_where_it_is_drawn() -> None:
    """A text clipped away or drawn at alpha 0 is not under the legend."""
    from matplotlib.transforms import Bbox

    fig, _text = _text_under_legend()
    assert [w.detail["covered"] for w in _found(fig)] == [["text"]]
    fig, text = _text_under_legend(clip_on=True)
    text.set_clip_box(Bbox.from_bounds(0, 0, 1, 1))  # display px: nowhere
    assert _found(fig) == []
    fig, _text = _text_under_legend(alpha=0)
    assert _found(fig) == []


def test_text_alpha_overrides_color_alpha_in_legend_obstacles() -> None:
    """The same visible text must be seen by both validation checks.

    Review 2 (648-R2), moved here as the reviewer wrote it.
    """
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "9cm"))
    try:
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.plot([0, 1], [0.05, 0.05], label="Series")
        ax.text(
            0.5,
            0.5,
            "123",
            ha="center",
            va="center",
            color=(1, 0, 0, 0),
            alpha=1,
            fontsize=22,
        )
        legend = ax.legend(loc="center")
        found = dm.validate_figure(fig, checks=["LEGEND_ON_DATA"], quiet=True)
        legend.remove()
        ax.lines[0].set_ydata([0.5, 0.5])
        assert dm.validate_figure(
            fig, checks=["VALUE_LABEL_ON_DATA"], quiet=True
        )
        assert any("text" in w.detail["covered"] for w in found)
    finally:
        plt.close(fig)


@pytest.mark.parametrize(
    ("alpha", "ink"), [(None, False), (0, False), (0.5, True), (1, True)]
)
def test_a_text_under_a_legend_counts_by_its_own_alpha_over_its_colour(
    alpha, ink: bool
) -> None:
    """A colour at alpha 0 draws once the text's own alpha replaces it."""
    fig, text = _text_under_legend(color=(1, 0, 0, 0), alpha=alpha)
    covered = [w.detail["covered"] for w in _found(fig)]
    assert covered == ([["text"]] if ink else [])
    text.axes.get_legend().remove()
    assert _draws(fig, text) is ink


def test_an_annotation_counts_by_its_text_not_its_arrow() -> None:
    """The arrow points at the data on purpose; the empty corner it spans is free."""
    fig, ax = _fig()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.plot([0, 1], [0, 0.5], label="Low")
    ax.annotate(
        "Note", (9.5, 9.5), xytext=(1, 1), arrowprops={"arrowstyle": "->"}
    )
    ax.legend(loc="center")
    assert _found(fig) == []
    ax.texts[0].set_position((5, 5))  # the text itself under the legend
    assert [w.detail["covered"] for w in _found(fig)] == [["text"]]


def test_an_inset_legend_and_inset_data_are_measured() -> None:
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0, 0.05], label="Main")
    inset = ax.inset_axes((0.5, 0.5, 0.45, 0.45))
    _dense(inset, 3)
    inset.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["legend_axes"] == 0
    assert w.detail["legend_inset"] == [0]
    assert w.detail["covered"] == ["line"]  # the inset's lines, not a panel
    assert w.message.startswith("Legend of axes[0].insets[0] covers lines")


def test_a_legend_on_an_inset_is_reported_as_a_panel() -> None:
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0, 0.05], label="Main")
    inset = ax.inset_axes((0.5, 0.5, 0.5, 0.5))  # reaches the corner
    inset.plot([0, 1], [0, 1])
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["legend_inset"] == []
    assert "panel" in w.detail["covered"] and "line" in w.detail["covered"]
    assert "axes[0].insets[0]" in w.detail["artists"]
    assert w.detail["panels"] == [0]


# ----------------------------------------------------------- fixes
def test_the_fixes_name_the_placements_that_keep_a_legend_off_the_data() -> (
    None
):
    fig, ax = _fig()
    _dense(ax)
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    suggestions = dm.validate_fixes.get_fix_suggestions(w)
    assert any("dm.place_legend(ax)" in s for s in suggestions)
    assert any("dm.label_line_ends(ax)" in s for s in suggestions)


# ------------------------------------------- LEGEND_OVERFLOW, outside size
def _names(n: int) -> list[str]:
    return [f"Region {i + 1}, seasonally adjusted" for i in range(n)]


def test_an_outside_legend_larger_than_half_its_plot_is_reported() -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))
    for i, name in enumerate(_names(16)):
        ax.plot([0, 1], [i, i + 1], label=name)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    dm.simple_layout(fig)
    found = _found(fig, "LEGEND_OVERFLOW")
    outside = [w for w in found if "outside_ratio" in w.detail]
    assert len(outside) == 1
    (w,) = outside
    assert w.detail["axes_index"] == 0
    assert 0.5 < w.detail["outside_ratio"] < 1.0
    assert w.detail["threshold"] == 0.5
    assert "the size of its plot" in w.message
    suggestions = dm.validate_fixes.get_fix_suggestions(w)
    assert "dm.label_line_ends(ax)" in suggestions[0]


def test_a_small_outside_legend_is_not_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 1], label="One")
    ax.plot([0, 1], [1, 0], label="Two")
    dm.place_legend(ax, loc="right")
    dm.simple_layout(fig)
    assert _found(fig, "LEGEND_OVERFLOW") == []


def _grow_figure_legend(fig, ax, plot_area: float) -> float:
    """Add a figure legend, two entries at a time, until it is 55 % of ``plot_area``."""
    handles = [ax.plot([], [])[0] for _ in range(40)]
    share = 0.0
    for n in range(2, 41, 2):
        names = [f"Series {i + 1}" for i in range(n)]
        legend = fig.legend(handles[:n], names, loc="center", ncols=2)
        box = legend.get_window_extent(drawn_renderer(fig))
        share = box.width * box.height / plot_area
        if share > 0.55:
            assert fig.bbox.y0 <= box.y0 and box.y1 <= fig.bbox.y1
            return share
        legend.remove()
    return share


def _sized(fig) -> list[int | None]:
    return [
        w.detail["axes_index"]
        for w in _found(fig, "LEGEND_OVERFLOW")
        if "outside_ratio" in w.detail
    ]


def test_a_figure_legend_larger_than_half_the_panels_is_reported() -> None:
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("12cm", "wide"))
    axs[0].set_position((0.05, 0.3, 0.2, 0.4))
    axs[1].set_position((0.75, 0.3, 0.2, 0.4))
    renderer = drawn_renderer(fig)
    area = sum(
        box.width * box.height
        for box in (ax.get_window_extent(renderer) for ax in axs)
    )
    share = _grow_figure_legend(fig, axs[0], area)
    assert 0.55 < share < 1.0
    assert _sized(fig) == [None]


def test_a_twin_pair_counts_its_plot_box_once() -> None:
    """A figure legend's share is of the panels, not of every twin Axes.

    The legend is grown until it is 55-100 % of the one plot box: counted
    once it is reported, counted twice (Axes and twin) it would not be.
    """
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.set_position((0.3, 0.3, 0.4, 0.4))
    twin = ax.twinx()
    ax.plot([0, 1], [0, 1])
    twin.plot([0, 1], [1, 0], color="oc.red5")
    plot = ax.get_window_extent(drawn_renderer(fig))
    share = _grow_figure_legend(fig, ax, plot.width * plot.height)
    assert 0.55 < share < 1.0
    assert _sized(fig) == [None]
