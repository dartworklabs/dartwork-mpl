"""A letter on a panel that draws nothing on its left keeps the named
panels' spine distance only where the gap already holds it.

Smoke round 5 (2026-11-14, s04 turn 4, #722): four panels in one row on a
slide, y axis shared. Panels b to d have no y-axis name and no tick labels,
and their letters took panel a's distance from the spine (58.8 pt: a's name
and tick labels at slide sizes) in a gap of 26 pt. The layout parted the
panels to hold the letters: 4.56 cm panels became 2.37 cm, ``wspace`` 1.44,
and title b still ran 2.9 pt into letter c. The host looked at the figure
and threw the row away. The rule (owner's standing decision for the round,
2026-11-14): the distance is kept where the room for it is already there;
where keeping it would part the panels, the letter stands on its own
panel's left spine. A report grid with room draws as before.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

TOL_PT = 0.25
CM = 2.54
ZONES = ["Open office", "Meeting rooms", "Server room", "Lobby"]


@pytest.fixture(autouse=True)
def _close():
    """Every figure here is closed afterwards."""
    yield
    plt.close("all")


def _shared_grid(
    preset: str,
    nrows: int,
    ncols: int,
    *,
    letters: bool = True,
    titles: tuple[str, ...] = tuple(ZONES),
    name: str = "Indoor temp (°C)",
    figsize: tuple[float, float] | None = None,
):
    """Panels sharing both axes, the y name on the first column only: the
    s04 figure. Returns the figure, its Axes and the letters (or none)."""
    dm.style.use(preset)
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=figsize or dm.figsize_for(nrows=nrows, ncols=ncols),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    for i, ax in enumerate(axes.flat):
        ax.plot(range(24), [21 + i * 0.5 + (h % 12) / 6 for h in range(24)])
        ax.set_title(titles[i % len(titles)])
    for ax in axes[-1]:
        ax.set_xlabel("Hour")
    if name:
        for ax in axes[:, 0]:
            ax.set_ylabel(name)
    texts = dm.label_axes(axes) if letters else []
    dm.simple_layout(fig)
    return fig, axes, texts


def _reach_pt(fig, axes, texts) -> list[float]:
    """Each letter's left edge, in points left of its panel's left spine."""
    renderer = drawn_renderer(fig)
    return [
        (ax.get_window_extent(renderer).x0 - t.get_window_extent(renderer).x0)
        * 72.0
        / fig.dpi
        for ax, t in zip(axes.flat, texts, strict=True)
    ]


def _panel_widths_cm(fig, axes) -> list[float]:
    """The width of every panel as drawn, in centimetres."""
    fig.canvas.draw()
    return [
        ax.get_position().width * fig.get_figwidth() * CM for ax in axes.flat
    ]


class TestNoRoom:
    """Keeping the named distance would part the panels: the own spine."""

    def test_slide_row_keeps_its_panels_as_wide_as_without_letters(
        self,
    ) -> None:
        """Short titles, so no title is in a letter's way: the letters cost
        the panels nothing (the named distance halved them)."""
        short = ("N", "E", "S", "W")
        bare_fig, bare_axes, _ = _shared_grid(
            "presentation", 1, 4, letters=False, titles=short
        )
        bare = _panel_widths_cm(bare_fig, bare_axes)
        fig, axes, _texts = _shared_grid("presentation", 1, 4, titles=short)
        assert _panel_widths_cm(fig, axes) == pytest.approx(bare, abs=0.01)

    def test_slide_row_with_long_titles_keeps_most_of_its_panels(self) -> None:
        """The s04 row as asked (titles as wide as the panels): what parts
        the panels now is only the letters' own room on the title line.
        They were 2.37 cm of the 4.56 cm they are without letters."""
        bare_fig, bare_axes, _ = _shared_grid(
            "presentation", 1, 4, letters=False
        )
        bare = min(_panel_widths_cm(bare_fig, bare_axes))
        fig, axes, _texts = _shared_grid("presentation", 1, 4)
        assert min(_panel_widths_cm(fig, axes)) >= 0.85 * bare

    def test_slide_row_letters_stand_on_their_own_spines(self) -> None:
        """Short titles, so no title is in a letter's way: b, c and d start
        on their own left spine; a stays on the outer edge of its name."""
        fig, axes, texts = _shared_grid(
            "presentation", 1, 4, titles=("N", "E", "S", "W")
        )
        reach = _reach_pt(fig, axes, texts)
        assert reach[0] > 40.0  # the name and the tick labels at slide sizes
        assert reach[1:] == pytest.approx([0.0, 0.0, 0.0], abs=TOL_PT)

    def test_slide_row_leaves_no_letter_on_a_title(self) -> None:
        """The reported overlap (title b 2.9 pt into letter c) is gone."""
        fig, _axes, _texts = _shared_grid("presentation", 1, 4)
        warnings = {
            w.check_id
            for w in dm.validate_figure(fig, quiet=True)
            if w.severity.value == "WARNING"
        }
        assert "CROSS_AXES_OVERLAP" not in warnings

    def test_a_column_decides_together(self) -> None:
        """Report 2 x 2 with room, but for the upper left title, which runs
        past its panel into the gap: b has no room, and d, which has, goes
        with it. A column's letters start at one x."""
        fig, axes, texts = _shared_grid(
            "report",
            2,
            2,
            titles=(
                "Winter weekday electric load of the office and laboratory wings",
                "Spring",
                "Summer",
                "Autumn",
            ),
        )
        renderer = drawn_renderer(fig)
        title = axes[0, 0].title.get_window_extent(renderer)
        assert title.x1 > axes[0, 0].get_window_extent(renderer).x1  # the shape
        reach = _reach_pt(fig, axes, texts)
        assert reach[2] > 15.0  # c stays on the outer edge of its name
        assert [reach[1], reach[3]] == pytest.approx([0.0, 0.0], abs=TOL_PT)

    def test_row_with_no_name_anywhere(self) -> None:
        """No y name in the call: an inner panel with nothing on its left
        and no room for where a name would be also takes its spine."""
        fig, axes, texts = _shared_grid(
            "presentation", 1, 4, titles=("N", "E", "S", "W"), name=""
        )
        reach = _reach_pt(fig, axes, texts)
        assert reach[0] > 20.0  # past a's tick labels, where a name would be
        assert reach[1:] == pytest.approx([0.0, 0.0, 0.0], abs=TOL_PT)

    def test_a_second_layout_draws_the_same_letters(self) -> None:
        """``simple_layout`` twice: no letter and no panel moves."""
        fig, axes, texts = _shared_grid("presentation", 1, 4)
        first = [v for t in texts for v in t.xyann]
        widths = _panel_widths_cm(fig, axes)
        dm.simple_layout(fig)
        assert [v for t in texts for v in t.xyann] == pytest.approx(
            first, abs=1e-3
        )
        assert _panel_widths_cm(fig, axes) == pytest.approx(widths, abs=1e-3)


class TestRoom:
    """The gap already holds the distance: every letter keeps it."""

    @pytest.mark.parametrize(
        ("preset", "nrows", "ncols"),
        [("report", 2, 2), ("report", 1, 3), ("scientific", 1, 2)],
    )
    def test_grid_with_room_keeps_one_distance(
        self, preset: str, nrows: int, ncols: int
    ) -> None:
        """Report 2 x 2 (smoke e07), 1 x 3 and a paper pair: one spine
        distance for every letter, and the panels as wide as without."""
        bare_fig, bare_axes, _ = _shared_grid(
            preset, nrows, ncols, letters=False
        )
        bare = _panel_widths_cm(bare_fig, bare_axes)
        fig, axes, texts = _shared_grid(preset, nrows, ncols)
        reach = _reach_pt(fig, axes, texts)
        assert reach[0] > 15.0
        assert reach == pytest.approx([reach[0]] * len(reach), abs=TOL_PT)
        assert _panel_widths_cm(fig, axes) == pytest.approx(bare, abs=0.01)

    def test_panel_with_tick_labels_keeps_the_distance(self) -> None:
        """Nothing shared, names on the left column only: the right column
        draws tick labels, so its letters keep the named distance and sit
        above those labels, as before."""
        dm.style.use("report")
        fig, axes = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
        for i, ax in enumerate(axes.flat):
            ax.plot(range(24), [1000 * (i + 1) + 30 * h for h in range(24)])
            ax.set_title(ZONES[i])
        for ax in axes[:, 0]:
            ax.set_ylabel("Supply flow (m³/h)")
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        reach = _reach_pt(fig, axes, texts)
        assert reach[0] > 20.0
        assert reach == pytest.approx([reach[0]] * 4, abs=TOL_PT)
