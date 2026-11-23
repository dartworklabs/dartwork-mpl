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


def test_oversized_colorbar_slot_leaves_a_blank_band():
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    data = np.arange(36).reshape(6, 6)
    ax.set(xlabel="Speed", ylabel="Torque")
    scale = fig.colorbar(ax.contourf(data), ax=ax, label="Rate")
    dm.simple_layout(fig)

    positions = [a.get_position().bounds for a in fig.axes]
    (finding,) = _of(dm.check(fig), "UNDERUSED_CANVAS")
    assert finding.artists == (ax, scale.ax)
    assert [a.get_position().bounds for a in fig.axes] == positions
    plt.close(fig)

    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.set(xlabel="Speed", ylabel="Torque")
    fig.colorbar(ax.contourf(data), ax=ax, label="Rate", fraction=0.05)
    dm.simple_layout(fig)
    assert "UNDERUSED_CANVAS" not in dm.check(fig).rules
    plt.close(fig)

    fig = plt.figure(figsize=dm.figsize("12cm", "standard"))
    grid = fig.add_gridspec(1, 2, width_ratios=[18, 1])
    ax, cax = fig.add_subplot(grid[0]), fig.add_subplot(grid[1])
    ax.set(xlabel="Speed", ylabel="Torque")
    fig.colorbar(ax.contourf(data), cax=cax, label="Rate")
    dm.simple_layout(fig)
    assert "UNDERUSED_CANVAS" not in dm.check(fig).rules
    plt.close(fig)


def test_column_space_counts_the_visible_descriptions():
    fig, ax = plt.subplots(figsize=dm.figsize("14cm", "wide"))
    ax.bar(0, 3, width=0.5)
    ax.bar(0, 5, bottom=3, width=0.5)
    ax.text(0.32, 1.5, "First group", va="center")
    ax.text(0.32, 5.5, "Second group", va="center")
    ax.set(xlim=(-0.35, 2), ylabel="Amount", xticks=[])
    ax.spines[["bottom", "top", "right"]].set_visible(False)
    dm.simple_layout(fig)
    (finding,) = _of(dm.check(fig), "UNDERUSED_CANVAS")
    assert finding.artists == (ax,)

    ax.text(2, 6.5, "Summary", va="center", ha="right")
    dm.simple_layout(fig)
    assert "UNDERUSED_CANVAS" not in dm.check(fig).rules
    plt.close(fig)


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


@pytest.mark.parametrize("name", ["wind_rose", "vertical_note", "korean_note"])
def test_a_note_that_runs_onto_a_dark_background_is_found(name: str):
    """The note reads on the canvas and is lost on the bars: the rule sees
    the part, in a polar Axes too, and says how much of the ink it is."""
    from tests.text_on_backgrounds import FAINT

    fig, (note,) = FAINT[name]()
    (f,) = _of(dm.check(fig), "TEXT_CONTRAST")
    assert f.artists == (note,)
    assert "% of its ink" in f.message and "all of its ink" not in f.message


def test_contour_numbers_on_dark_bands_are_found_and_the_readable_left():
    """Three of the five grey numbers sit on bands they cannot be read on."""
    from tests.text_on_backgrounds import contour_labels

    fig, labels = contour_labels()
    (f,) = _of(dm.check(fig), "TEXT_CONTRAST")
    assert {t.get_text() for t in f.artists} == {"5.0", "6.0", "7.0"}
    assert len(labels) == 5


def test_a_note_that_reads_over_a_point_cloud_is_not_found():
    """Points break the note up but it reads on each (6:1): no contrast
    finding, which would send the reader after the wrong defect."""
    from tests.text_on_backgrounds import point_cloud

    fig, _notes = point_cloud()
    assert "TEXT_CONTRAST" not in dm.check(fig).rules


@pytest.mark.parametrize("marks", ["scatter", "markers"])
def test_a_number_inside_a_point_is_read_against_the_point(marks: str):
    """White numbers in dark points read (#830: they were measured against
    the page, 1.00:1); the same numbers in the points' own colour do not."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "5cm"))
    xs, values = range(4), [81, 72, 66, 58]
    if marks == "scatter":
        ax.scatter(xs, [0] * 4, s=900, color="dc.blue8", lw=0, zorder=3)
    else:
        ax.plot(xs, [0] * 4, "o", ms=22, color="dc.blue8", zorder=3)
    numbers = [
        ax.text(x, 0, str(v), ha="center", va="center", color="white", zorder=4)
        for x, v in zip(xs, values, strict=True)
    ]
    ax.set(xlim=(-0.6, 3.6), ylim=(-1, 1))
    ax.axis("off")
    dm.simple_layout(fig)
    assert "TEXT_CONTRAST" not in dm.check(fig).rules
    for number in numbers:
        number.set_color("dc.blue9")
    (f,) = _of(dm.check(fig), "TEXT_CONTRAST")
    assert len(f.artists) == 4 and "all of its ink" in f.message


def test_a_halo_or_a_box_behind_a_text_is_what_its_ink_is_read_against():
    """White text on white paper is lost; with a dark outline or a dark box
    behind the glyphs it reads, and the rule says so."""
    from matplotlib import patheffects

    fig, ax = plt.subplots(figsize=dm.figsize("8cm", "standard"))
    ax.plot([0, 1], [0, 1])
    note = ax.text(0.5, 0.5, "Peak", color="white", fontsize=dm.fs(4))
    assert "TEXT_CONTRAST" in dm.check(fig).rules
    note.set_path_effects(
        [
            patheffects.Stroke(linewidth=3, foreground="black"),
            patheffects.Normal(),
        ]
    )
    assert "TEXT_CONTRAST" not in dm.check(fig).rules
    note.set_path_effects([])
    note.set_bbox({"facecolor": "black", "edgecolor": "none"})
    assert "TEXT_CONTRAST" not in dm.check(fig).rules


def _word(**style):
    """A bold word in the middle of a bare canvas."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "6cm"), dpi=120)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_axis_off()
    word = ax.text(
        0.5, 0.5, "STATUS", ha="center", va="center", color="#151515",
        fontsize=dm.fs(13), fontweight="bold", **style,
    )  # fmt: skip
    return fig, ax, word


def test_a_band_that_wipes_out_part_of_a_word_is_found_wherever_it_sits():
    """A dark band half an em wide takes a letter's worth of ink with it.
    It is found at every position along the word, not only where it
    happens to line up with a window counted from the word's start."""
    fig, ax, word = _word()
    fig.canvas.draw()
    box = word.get_window_extent()
    em = word.get_fontsize() * fig.dpi / 72
    assert "TEXT_CONTRAST" not in dm.check(fig).rules
    to_data = ax.transData.inverted()
    for step in range(12):
        left = box.x0 + em + step * em / 12
        (x0, _), (x1, _) = to_data.transform([(left, 0), (left + 0.52 * em, 0)])
        band = ax.axvspan(x0, x1, color="#151515", lw=0)
        assert "TEXT_CONTRAST" in dm.check(fig).rules, step
        band.remove()


def test_a_text_drawn_only_as_strokes_is_read_like_any_other():
    """``path_effects=[Stroke(...)]`` alone is how the text is painted: it
    is found over a block of its colour, and reads on the bare canvas."""
    from matplotlib import patheffects

    stroke = patheffects.Stroke(linewidth=0.7, foreground="#151515")
    fig, ax, _word_ = _word(path_effects=[stroke])
    assert "TEXT_CONTRAST" not in dm.check(fig).rules
    ax.axvspan(0.5, 1, color="#151515", lw=0)
    assert "TEXT_CONTRAST" in dm.check(fig).rules


def test_the_check_draws_the_figure_as_often_as_a_plain_draw():
    """``dm.check`` draws the figure once, like ``fig.canvas.draw()``: an
    artist of the user's own is drawn once more and a ``draw_event``
    callback runs once more, also when texts are read against what is
    behind them."""
    from matplotlib.artist import Artist

    from tests.text_on_backgrounds import korean_note

    class Counted(Artist):
        draws = 0

        def draw(self, renderer: object) -> None:
            self.draws += 1

    fig, _texts = korean_note()
    mine = Counted()
    fig.axes[0].add_artist(mine)
    events: list[object] = []
    fig.canvas.mpl_connect("draw_event", events.append)
    fig.canvas.draw()
    assert (mine.draws, len(events)) == (1, 1)
    assert "TEXT_CONTRAST" in dm.check(fig).rules
    assert (mine.draws, len(events)) == (2, 2)


@pytest.mark.parametrize(
    "name", ["wind_rose", "vertical_note", "contour_labels", "korean_note"]
)
def test_reading_what_is_behind_a_text_leaves_every_artist_as_it_was(name: str):
    """Reading what is behind the texts changes no colour, visibility,
    path effect or box, leaves no text marked stale (an annotation
    included: the wind rose's note), and the figure saves to the same
    bytes."""
    from tests.text_on_backgrounds import FAINT

    fig, _texts = FAINT[name]()

    def state() -> list[tuple[object, ...]]:
        return [
            (
                t.get_color(),
                t.get_alpha(),
                t.get_visible(),
                tuple(t.get_path_effects()),
                t.get_bbox_patch(),
                t.get_zorder(),
                t.stale,
            )
            for ax in fig.axes
            for t in ax.texts
        ]

    saved = _png(fig)  # a draw: nothing is stale after it
    before = state()
    assert "TEXT_CONTRAST" in dm.check(fig).rules
    assert state() == before and _png(fig) == saved


def test_a_text_rewritten_while_the_figure_is_drawn_is_not_judged():
    """A ``draw_event`` callback that rewrites a note (a clock, a frame
    counter) leaves the figure showing another text than the note now
    holds. Its ink cannot be read against that drawing: the rule says it
    did not run, and does not report ink that was never there."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 1])
    note = ax.text(0.1, 0.8, "frame 0")
    dm.simple_layout(fig)
    assert "TEXT_CONTRAST" not in dm.check(fig).skipped
    count: list[object] = []

    def tick(event: object) -> None:
        count.append(event)
        note.set_text(f"a much longer frame {len(count)}")

    fig.canvas.mpl_connect("draw_event", tick)
    found = dm.check(fig)
    assert "TEXT_CONTRAST" not in found.rules
    assert "TEXT_CONTRAST" in found.skipped


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


def test_a_manually_placed_group_name_needs_room_at_the_canvas_edge():
    """A flush group heading gets one warning while the layout note clears."""
    from matplotlib.transforms import blended_transform_factory

    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.barh(["Berlin", "Munich"], [6.1, 4.8])
    ax.set(xlabel="Change in vacancy (percentage points)", ylim=(-0.6, 2))
    heading = ax.text(
        0,
        1.6,
        "Germany",
        fontweight="bold",
        ha="left",
        transform=blended_transform_factory(fig.transFigure, ax.transData),
    )
    dm.add_note(fig, "Source: vacancy report")
    dm.simple_layout(fig)
    (finding,) = _of(dm.check(fig), "TEXT_AT_EDGE")
    assert finding.artists == (heading,) and finding.panels == (0,)
    heading.set_x(-0.05)
    result = dm.check(fig)
    assert "OVERFLOW" in result.rules and "TEXT_AT_EDGE" not in result.rules


def test_an_axisless_unit_chart_uses_more_room_on_a_shallower_canvas():
    """An equal-aspect grid needs a canvas close to its proportions."""
    from matplotlib.patches import Rectangle

    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("24cm", 0.6))
    for row in range(5):
        for col in range(22 - 4 * row):
            ax.add_patch(Rectangle((col, row), 0.8, 0.8, color="dc.blue4"))
    ax.set(xlim=(-0.1, 25), ylim=(-0.7, 7.2), aspect="equal")
    ax.set_axis_off()
    fig.suptitle("North America hosts 22 of the 58 startups")
    dm.simple_layout(fig)
    (finding,) = _of(dm.check(fig), "UNDERUSED_CANVAS")
    assert finding.artists == (ax,) and finding.panels == (0,)

    fig.set_size_inches(*dm.figsize("24cm", 0.24))
    dm.simple_layout(fig)
    assert "UNDERUSED_CANVAS" not in dm.check(fig).rules


def test_a_trend_line_through_a_point_name_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    x = np.array([1.0, 2.0, 3.0, 4.0])
    ax.scatter(x, 2 * x)
    ax.plot([0, 5], [0, 10], color="dc.gray5")  # the fit
    ax.set(xlabel="Year", ylabel="Count")
    struck = ax.text(2.5, 5.0, "Pentium", ha="center", va="center")
    clear = ax.annotate(
        "Core 2", (3.0, 6.0), textcoords="offset points", xytext=(6, -12)
    )
    boxed = ax.text(
        4.0, 8.0, "94 %", ha="center", va="center", bbox={"fc": "white"}
    )
    along = ax.text(1.5, 3.4, "Trend", rotation=30, ha="center", va="center")
    dm.simple_layout(fig)
    (finding,) = _of(dm.check(fig), "TEXT_ON_LINE")
    assert finding.artists == (struck,) and "'Pentium'" in finding.message
    assert clear not in finding.artists and boxed not in finding.artists
    assert along not in finding.artists  # the line's own name, set along it


def test_a_leader_that_ends_at_its_label_is_not_a_line_through_it():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.scatter([1, 2, 3], [1, 2, 3])
    ax.set(xlabel="Year", ylabel="Count", xlim=(0, 4), ylim=(0, 4))
    label = ax.text(2.6, 1.2, "Tool chest", ha="left", va="center")
    ax.plot([2.0, 2.58], [2.0, 1.2], color="dc.gray5", lw=dm.lw(-1))
    dm.simple_layout(fig)
    assert not _of(dm.check(fig), "TEXT_ON_LINE"), label


ITEMS = [
    "I know what is expected of me in my role this year",
    "My manager gives me feedback I can act on",
    "I have the tools and equipment my work needs",
    "Meetings I attend are a good use of my time",
]


def test_a_title_pushed_to_the_canvas_edge_is_found():
    def chart(place):
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
        ax.barh(ITEMS, [87, 74, 63, 31])
        ax.set_xlabel("Agree (%)")
        place(fig, ax, "Role clarity scores highest and meetings lowest")
        dm.simple_layout(fig)
        return fig

    (finding,) = _of(
        dm.check(chart(lambda fig, ax, s: ax.set_title(s))), "TEXT_AT_EDGE"
    )
    assert "right canvas edge" in finding.message
    assert not dm.check(chart(lambda fig, ax, s: fig.suptitle(s)))


def _zoomed(*, ticks_on_top: bool):
    """A flat trace with an inset above its zoom region, as an agent draws a
    spike: matplotlib's connectors leave the inset's lower corners."""
    t = np.linspace(0, 60, 600)
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", 0.7))
    ax.plot(t, -65 + np.sin(t / 5))
    ax.set(xlabel="Time (s)", ylabel="Voltage (mV)", ylim=(-80, 5))
    axins = ax.inset_axes((0.35, 0.5, 0.4, 0.42))
    axins.plot(t, -65 + np.sin(t / 5))
    axins.set(xlim=(41.0, 42.0), ylim=(-70, -60), ylabel="mV")
    if ticks_on_top:
        axins.xaxis.tick_top()
    ax.indicate_inset_zoom(axins)
    dm.simple_layout(fig)
    return fig


def test_a_zoom_connector_through_the_inset_labels_is_found():
    (finding,) = _of(dm.check(_zoomed(ticks_on_top=False)), "TEXT_ON_LINE")
    assert "zoom connector" in finding.message and "'41.0'" in finding.message
    # with the tick numbers on the inset's far side nothing is crossed
    assert not _of(dm.check(_zoomed(ticks_on_top=True)), "TEXT_ON_LINE")
