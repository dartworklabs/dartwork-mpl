"""``dm.simple_layout`` on realistic charts, as users call it."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm

DEPARTMENTS = [
    "Customer Support",
    "Product Engineering",
    "Sales Operations",
    "Human Resources",
    "Finance and Legal",
    "Marketing Analytics",
]


def content(fig: Figure):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    boxes = [ax.get_tightbbox(renderer) for ax in fig.axes]
    return (
        min(b.x0 for b in boxes),
        max(b.x1 for b in boxes),
        min(b.y0 for b in boxes),
        max(b.y1 for b in boxes),
    )


def line_chart(**kw) -> Figure:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"), **kw)
    ax.plot(np.arange(10), np.arange(10) ** 2)
    ax.set_xlabel("Week")
    ax.set_ylabel("Signups (thousands)")
    ax.set_title("Signups")
    return fig


@pytest.mark.parametrize(
    ("margin", "mm"), [(0, 0.0), ("0mm", 0.0), ("0.1mm", 0.1), ("5mm", 5.0)]
)
def test_content_sits_the_margin_from_every_edge(margin, mm) -> None:
    fig = line_chart()
    dm.simple_layout(fig, margin=margin)
    x0, x1, y0, y1 = content(fig)
    w, h = fig.bbox.width, fig.bbox.height
    px = mm / 25.4 * fig.dpi
    for gap in (x0, w - x1, y0, h - y1):
        assert gap == pytest.approx(px, abs=1.0)


def test_a_second_call_draws_the_same() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))
    ax.bar(DEPARTMENTS[:4], [1, 2, 3, 4])
    dm.simple_layout(fig)
    first = (
        ax.get_position().bounds,
        [t.get_text() for t in ax.get_xticklabels()],
    )
    dm.simple_layout(fig)
    assert (
        ax.get_position().bounds,
        [t.get_text() for t in ax.get_xticklabels()],
    ) == first


def test_crowded_category_names_wrap() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    ax.bar(DEPARTMENTS, [34, 58, 41, 17, 22, 29])
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert any("\n" in t.get_text() for t in ax.get_xticklabels())


def test_crowded_numbers_turn() -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "standard"))
    ax.bar([f"{v:,}" for v in range(100_000, 1_300_000, 100_000)], range(12))
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in ax.get_xticklabels()} == {90.0}


@pytest.mark.parametrize("angle", [30.0, 45.0, 90.0])
def test_tick_labels_the_caller_turned_stay_turned(angle: float) -> None:
    # #749: labels turned by hand with rotation_mode="xtick" read as the
    # layout's own turn, and the layout laid them flat again.
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(["North", "South", "East", "West"], [1, 2, 3, 4])
    ax.tick_params(axis="x", rotation=angle, rotation_mode="xtick")
    dm.simple_layout(fig)
    dm.simple_layout(fig)
    assert {
        (t.get_rotation(), t.get_rotation_mode()) for t in ax.get_xticklabels()
    } == {(angle, "xtick")}


def test_suptitle_and_note_keep_their_edges() -> None:
    fig = line_chart()
    fig.suptitle("Quarterly signups")
    note = dm.add_note(fig, "Source: internal CRM")
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    ax_box = fig.axes[0].get_tightbbox(renderer)
    assert fig._suptitle.get_window_extent(renderer).y0 >= ax_box.y1  # type: ignore[union-attr]
    assert note.get_window_extent(renderer).y1 <= ax_box.y0


def test_a_figure_pyplot_does_not_manage() -> None:
    fig = Figure(figsize=dm.figsize("9cm", "standard"))
    ax = fig.add_subplot()
    ax.plot([1, 2, 3])
    ax.set_ylabel("A label that needs room")
    before = ax.get_position().bounds
    dm.simple_layout(fig)
    assert ax.get_position().bounds != before


def test_grid_with_colorbar_and_shared_axes() -> None:
    fig, axes = plt.subplots(
        2, 2, figsize=dm.figsize("13cm", "square"), sharex=True
    )
    for ax in axes.flat:
        im = ax.imshow(np.arange(25).reshape(5, 5))
        ax.set_ylabel("Row")
    fig.colorbar(im, ax=axes, label="Value")
    dm.simple_layout(fig)
    x0, x1, y0, y1 = content(fig)
    assert x0 >= -0.5 and y0 >= -0.5
    assert x1 <= fig.bbox.width + 0.5 and y1 <= fig.bbox.height + 0.5


def test_a_title_wider_than_the_canvas_keeps_the_plot() -> None:
    # #783: the plot shrank by the title's excess each step, to 0.001.
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
    ax.imshow(np.arange(25).reshape(5, 5))
    ax.set_title("Stocks and REITs moved together most")
    dm.simple_layout(fig)
    fig.canvas.draw()
    frame = ax.get_window_extent(fig.canvas.get_renderer())  # type: ignore[attr-defined]
    assert min(frame.width, frame.height) / fig.dpi * 25.4 > 60.0


def test_a_gap_that_cannot_part_the_titles_stays() -> None:
    # #722: each wider gap narrowed the plots, the titles stood out further,
    # and the row ended at 0.5 cm plots with the titles still overlapping.
    dm.style.use("report")
    fig, axes = plt.subplots(
        1, 3, figsize=dm.figsize("12cm", "4cm"), sharey=True
    )
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_title("Quarterly revenue by region and channel")
    dm.simple_layout(fig)
    assert axes[0].get_gridspec().wspace is None
    assert axes[0].get_position().width * 12.0 > 2.0  # cm


def test_grid_rows_part_for_their_tick_labels_and_titles() -> None:
    # #787: a slide grid needs hspace 1.99; the rows stayed at 0.2.
    dm.style.use("presentation")
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
    for ax in axes.flat:
        ax.plot(range(1, 13), range(12))
        ax.set(title="Returns", xlabel="Month", ylabel="Sales (units)")
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    for ax in fig.axes:
        texts = [*ax.get_xticklabels(), ax.xaxis.label]
        for other in fig.axes:
            frame = other.get_window_extent(renderer)
            assert other is ax or not any(
                t.get_window_extent(renderer).overlaps(frame) for t in texts
            )
    plot_mm = min(ax.get_window_extent(renderer).height for ax in fig.axes)
    assert plot_mm / fig.dpi * 25.4 > 15.0


def test_a_figure_with_parasite_axes_is_left_as_it_was(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # #750: parasite axes stay where they were made while the host moves,
    # so each step shrank the plot again, to 0.001 of the canvas.
    from mpl_toolkits.axes_grid1 import host_subplot

    fig = plt.figure(figsize=dm.figsize("13cm", "standard"))
    host = host_subplot(111)
    twin = host.twinx()
    host.plot([1, 2, 3], [1, 2, 3])
    twin.plot([1, 2, 3], [10, 30, 20])
    twin.set_ylabel("Temperature (°C)")
    before = host.get_position().bounds
    with caplog.at_level("INFO", logger="dartwork_mpl.layout"):
        dm.simple_layout(fig)
    assert host.get_position().bounds == pytest.approx(before)
    assert "use ax.twinx() instead" in caplog.text


def test_left_alone() -> None:
    empty = plt.figure()
    dm.simple_layout(empty)  # no Axes: nothing to do, no warning

    manual = plt.figure()
    manual.add_axes((0.1, 0.1, 0.8, 0.8))
    with pytest.warns(UserWarning, match="no GridSpec"):
        dm.simple_layout(manual)


def test_a_twin_shows_the_spine_its_scale_ticks_on() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    twin = ax.twinx()
    im = ax.imshow(np.eye(3))
    bar = fig.colorbar(im, ax=ax)
    dm.simple_layout(fig)
    assert twin.spines["right"].get_visible()
    assert not ax.spines["right"].get_visible()
    sides = ("left", "right", "bottom", "top")
    assert not any(bar.ax.spines[s].get_visible() for s in sides)


def test_a_spine_hidden_after_the_layout_stays_hidden() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    twin = ax.twinx()
    dm.simple_layout(fig)
    twin.spines["right"].set_visible(False)
    dm.simple_layout(fig)
    assert not twin.spines["right"].get_visible()


def test_long_radar_names_stand_outside_the_circle() -> None:
    dm.style.use("report")
    names = [
        "Battery life",
        "Camera quality",
        "Display",
        "Performance",
        "Build quality",
        "Customer support",
        "Value for money",
    ]
    angles = np.linspace(0, 2 * np.pi, len(names), endpoint=False)
    fig, ax = plt.subplots(
        figsize=dm.figsize("12cm", "wide"), subplot_kw={"projection": "polar"}
    )
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.plot(np.r_[angles, angles[0]], [9, 7, 8, 9, 8, 9, 6, 9])
    ax.set_xticks(angles, names)
    assert "POLAR_TICK_ON_PLOT" in dm.check(fig).rules
    dm.simple_layout(fig)
    assert not dm.check(fig)
    sides = {t.get_text(): t.get_ha() for t in ax.get_xticklabels()}
    assert sides["Customer support"] == "right"  # left of the plot
    assert sides["Camera quality"] == "left"
    assert sides["Battery life"] == "center"
    plt.close(fig)


def test_short_and_placed_angle_labels_stay_as_they_are() -> None:
    dm.style.use("report")
    fig, (plain, placed) = plt.subplots(
        1,
        2,
        figsize=dm.figsize("17cm", "8cm"),
        subplot_kw={"projection": "polar"},
    )
    plain.plot(np.linspace(0, 2 * np.pi, 50), np.linspace(0, 1, 50))
    names = ["Customer support", "Build quality", "Value for money"]
    placed.set_xticks(np.linspace(0, 2 * np.pi, 3, endpoint=False), names)
    for label in placed.get_xticklabels():
        label.set_ha("left")  # the author's own placement
    dm.simple_layout(fig)
    assert {t.get_ha() for t in plain.get_xticklabels()} == {"center"}
    assert {t.get_ha() for t in placed.get_xticklabels()} == {"left"}
    plt.close(fig)
