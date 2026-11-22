"""``dm.check`` on real charts: what it finds, and that it changes nothing."""

from __future__ import annotations

import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.check import Finding, Findings


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return buf.getvalue()


def _of(found: Findings, rule: str) -> list[Finding]:
    return [f for f in found if f.rule == rule]


def _line_chart():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    x = np.arange(10)
    ax.plot(x, x**1.2, label="Revenue")
    ax.plot(x, 8 - 0.5 * x, label="Cost")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Amount (M USD)")
    dm.place_legend(ax)
    dm.simple_layout(fig, margin="1mm")
    return fig, ax


def test_a_laid_out_chart_is_clean_and_unchanged():
    fig, _ax = _line_chart()
    before = _png(fig)
    found = dm.check(fig)
    assert not found, found.report()
    assert _png(fig) == before
    assert str(found) == "dm.check: nothing stands out."


def test_a_legend_on_the_points_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    rng = np.random.default_rng(0)
    ax.scatter(rng.uniform(0, 1, 400), rng.uniform(0, 1, 400), label="Samples")
    ax.legend(loc="center")
    found = _of(dm.check(fig), "LEGEND_ON_DATA")
    assert found and "markers ('Samples')" in found[0].message
    assert found[0].artists == (ax.get_legend(),)


def test_text_past_the_edge_and_overlapping_text():
    fig, ax = _line_chart()
    long = ax.text(9, 5, "a note running far past the right edge")
    ax.text(2, 4, "Peak demand")
    ax.text(2.3, 4, "Peak supply")
    found = dm.check(fig)
    assert long in _of(found, "OVERFLOW")[0].artists
    assert "'Peak demand'" in _of(found, "OVERLAP")[0].message


def test_a_tight_grid_collides_across_panels():
    fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", "9cm"))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("Hour of day")
    fig.subplots_adjust(hspace=0)
    axes[1].set_title("Zone temperature", y=0.9)  # down onto the ticks above
    assert "CROSS_AXES_OVERLAP" in dm.check(fig).rules


def test_a_title_under_its_colorbar_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
    im = ax.imshow(np.arange(36).reshape(6, 6))
    ax.set_title(
        "Stocks and REITs moved together most closely of all six assets (0.72)"
    )
    cbar = fig.colorbar(im, ax=ax)
    dm.simple_layout(fig)
    found = _of(dm.check(fig), "CROSS_AXES_OVERLAP")
    assert found and cbar.ax in found[0].artists


def test_a_value_against_a_line_end_name_is_crowded():
    from tests.visual.scenarios import all_scenarios

    built = {s.name: s for s in all_scenarios()}
    ends = dm.check(built["line_ends_annotated"].build())
    assert "'19.4 TWh'" in _of(ends, "TEXT_CROWD")[0].message


def test_an_empty_grid_cell_is_found_but_not_a_twin():
    fig, axes = plt.subplots(1, 3, figsize=dm.figsize("15cm", "5cm"))
    axes[0].plot([0, 1], [0, 1])
    axes[0].twiny().set_xlabel("Second scale")
    axes[1].set_axis_off()  # hidden on purpose: no frame, no defect
    found = _of(dm.check(fig), "EMPTY_AXES")
    assert [f.panels for f in found] == [(2,)]


def test_an_axis_of_numbers_needs_a_name_but_not_dates_or_a_named_row():
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("15cm", "6cm"))
    days = np.arange("2026-01-01", "2026-03-01", dtype="datetime64[D]")
    for ax in axes:
        ax.plot(days, np.arange(days.size))
    axes[0].set_ylabel("Orders")
    assert "MISSING_AXIS_LABEL" not in dm.check(fig).rules
    axes[0].set_ylabel("")
    found = _of(dm.check(fig), "MISSING_AXIS_LABEL")
    assert [f.panels for f in found] == [(0,), (1,)]


def test_a_value_on_its_error_bar_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("10cm", "standard"))
    bars = ax.bar(["A", "B"], [3.1, 4.6], yerr=[0.4, 0.7], capsize=4)
    ax.bar_label(bars, fmt="%.1f")
    ax.set_ylabel("Yield (t/ha)")
    assert "VALUE_LABEL_ON_DATA" in dm.check(fig).rules


def test_a_letter_inside_its_plot_on_the_curve_is_found():
    # Titles too long to follow their letters put the letters inside.
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize_for(nrows=1, ncols=2))
    t = np.linspace(0, 10, 100)
    axes[0].plot(t, t)
    axes[1].plot(t, np.exp(-t / 3))
    axes[0].set_title("Response to the dose across all subjects of the trial")
    axes[1].set_title("Signal decay")
    for ax in axes:
        ax.set(xlabel="Time (s)", ylabel="Signal")
    dm.label_axes(axes)
    dm.simple_layout(fig)
    (f,) = _of(dm.check(fig), "LETTER_ON_DATA")
    assert f.panels == (1,)


@pytest.mark.parametrize("image", [False, True])
def test_white_text_on_a_pale_fill_is_found(image: bool):
    fig, ax = plt.subplots(figsize=dm.figsize("10cm", "standard"))
    if image:
        ax.imshow([[0.0, 1.0]], cmap="YlGnBu")
        ax.text(0, 0, "12", ha="center", va="center", color="white")
    else:
        bars = ax.bar(["A", "B"], [4.6, 3.9], color="dc.yellow3")
        ax.bar_label(bars, fmt="%.1f", label_type="center", color="white")
    found = _of(dm.check(fig), "TEXT_CONTRAST")
    assert found and found[0].panels == (0,)
    for t in ax.texts:
        t.set_color("black")
    assert "TEXT_CONTRAST" not in dm.check(fig).rules


def test_a_report_grid_on_slide_text_is_too_small_but_a_colorbar_is_not():
    dm.style.use("presentation")
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
    for ax in axes.flat:
        ax.plot(np.arange(12), np.arange(12))
        ax.set(title="North", xlabel="Month", ylabel="Sales (units)")
    dm.simple_layout(fig)
    assert "SMALL_PANEL" in dm.check(fig).rules
    surface = plt.figure(figsize=dm.figsize("12cm", "9cm"))
    ax3 = surface.add_subplot(projection="3d")
    grid = np.linspace(-2, 2, 20)
    xx, yy = np.meshgrid(grid, grid)
    surface.colorbar(ax3.plot_surface(xx, yy, xx * yy), shrink=0.4)
    assert "SMALL_PANEL" not in dm.check(surface).rules


def test_lines_without_visible_marks_leave_an_empty_panel():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    (line,) = ax.plot([1, 2, 3], [1, 3, 2], lw=0)
    ax.set(xlabel="x (s)", ylabel="y (m)")
    dm.simple_layout(fig)

    def empty() -> bool:
        findings = _of(dm.check(fig), "EMPTY_AXES")
        return any(f.artists == (ax,) for f in findings)

    assert empty()
    line.set_marker("o")
    assert not empty()
    line.set_marker("None")
    line.set_linewidth(dm.lw(0))
    line.set_alpha(0)
    assert empty()
    line.set_alpha(1)
    colour = line.get_color()
    line.set_color(ax.get_facecolor())
    assert empty()
    line.set_color(colour)
    ax.set_xlim(4, 5)
    assert empty()
    ax.set_xlim(1.5, 1.6)  # a segment crosses the view, with no vertex inside
    assert not empty()
    line.set_linewidth(0)
    ax.fill_between([1, 2, 3], [1, 3, 2], 1)
    assert not empty()


def test_an_annotation_just_below_the_title_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
    ax.plot([0, 10], [0, 10])
    ax.set(
        xlabel="x (s)", ylabel="y (m)", title="A title that states the point"
    )
    note = ax.text(5, 10.6, "today", ha="center", va="bottom")
    dm.simple_layout(fig)
    result = dm.check(fig)
    (f,) = _of(result, "TEXT_TOO_CLOSE")
    assert f.panels == (0,) and f.artists == (ax.title, note)
    assert "OVERLAP" not in result.rules


def test_an_inset_axis_label_is_checked_against_ticks_and_parent_frame():
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "wide"))
    ax.plot(np.arange(365), 40 + np.random.default_rng(0).normal(0, 1, 365))
    ax.set(xlabel="일 (day of year)", ylabel="일 최대 전력 (MW)")
    inset = ax.inset_axes([0.045, 0.55, 0.36, 0.38])
    inset.plot(np.arange(168), 48 + 3 * np.sin(np.arange(168) / 24 * 2 * np.pi))
    inset.tick_params(axis="y", labelsize=dm.fs(-2))
    label = inset.set_ylabel("시간당 (MW)", fontsize=dm.fs(-2))
    dm.simple_layout(fig)
    assert any(
        set(f.artists) == {ax, label} and f.panels == (0, 1)
        for f in _of(dm.check(fig), "CROSS_AXES_OVERLAP")
    )

    inset.set_ylabel(label.get_text(), labelpad=-8)
    ticks = set(inset.get_yticklabels())
    assert any(
        label in f.artists
        and ticks.intersection(f.artists)
        and f.panels == (1,)
        for f in _of(dm.check(fig), "OVERLAP")
    )
    ax.set_visible(False)
    assert not dm.check(fig)


def test_line_end_names_read_as_rows():
    """The line-end helper's standard row spacing is clear."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    for i, name in enumerate(("fastframe (ours)", "polars", "dask")):
        ax.plot([0, 10], [1, 9 + i * 0.01], label=name)
    ax.set(xlabel="Rows", ylabel="Runtime (ms)")
    dm.label_line_ends(ax)
    dm.simple_layout(fig)
    assert "TEXT_TOO_CLOSE" not in dm.check(fig).rules


def test_long_theta_labels_cross_the_disc():
    """Normal compass labels clear the disc that long radar labels cross."""
    fig = plt.figure(figsize=dm.figsize("9cm", "square"))
    ax = fig.add_subplot(projection="polar")
    ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    ax.plot(np.r_[ang, ang[0]], [9, 7, 8, 9, 8, 9, 6, 8, 9])
    ax.set_xticks(ang, ["E", "NE", "N", "NW", "W", "SW", "S", "SE"])
    dm.simple_layout(fig)
    assert "POLAR_TICK_ON_PLOT" not in dm.check(fig).rules
    ax.set_xticks(
        ang,
        [
            "Customer support",
            "NE",
            "N",
            "NW",
            "Value for money",
            "SW",
            "S",
            "SE",
        ],
    )
    (finding,) = _of(dm.check(fig), "POLAR_TICK_ON_PLOT")
    assert finding.panels == (0,)
    assert set(finding.artists) == {
        ax.get_xticklabels()[0],
        ax.get_xticklabels()[4],
    }


def test_ascii_minus_on_values_beside_unicode_ticks():
    """Only negative value labels using a different minus sign are flagged."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "5cm"))
    ax.barh(["Construction", "Textiles", "Chemicals"], [-7.5, -9.6, -12.4])
    values = {
        ax.text(v / 2, i, f"{v:+.1f}%", ha="center", va="center", color="white")
        for i, v in enumerate([-7.5, -9.6, -12.4])
    }
    ax.set_xlabel("Change from last year (%)")
    ax.text(
        0.1,
        0.1,
        r"Year-over-year 2014-2024, 2024-01-01, $10^{-4}$",
        transform=ax.transAxes,
    )
    dm.simple_layout(fig)
    (finding,) = _of(dm.check(fig), "MIXED_MINUS")
    assert set(finding.artists) == values
    assert finding.panels == (0,)
    with matplotlib.rc_context({"axes.unicode_minus": False}):
        assert "MIXED_MINUS" not in dm.check(fig).rules


def test_polar_radial_ticks_can_be_hidden_by_a_band():
    """A higher fill obscures radial ticks until the axis is raised."""
    fig = plt.figure(figsize=dm.figsize("10cm", "square"))
    ax = fig.add_subplot(projection="polar")
    theta = np.linspace(0, 2 * np.pi, 366)
    mean = 12 - 13 * np.cos(theta)
    ax.fill_between(theta, mean - 8, mean + 8, color="dc.blue2")
    ax.plot(theta, mean)
    ax.set_ylim(-18, 40)
    ax.set_rlabel_position(188)
    dm.simple_layout(fig)
    assert "RADIAL_TICK_COVERED" in dm.check(fig).rules
    ax.set_axisbelow(False)
    assert "RADIAL_TICK_COVERED" not in dm.check(fig).rules
