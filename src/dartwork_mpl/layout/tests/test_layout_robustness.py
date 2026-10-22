"""simple_layout keeps side titles, figure text and 3-D axes in view (#523).

``set_title(loc="left")`` titles were not measured, a left-aligned
suptitle reserved the *left* edge, text pinned to one axes edge collapsed
the axes, and mplot3d tick labels were read at bogus positions, so common
agent-written figures broke without a warning.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl import layout

PRESETS = ("scientific", "report", "presentation")
TOL_PX = 0.5
OVERSIZED = "A headline far too long for any canvas these tests draw. " * 3


def _extent(fig, artist):
    fig.canvas.draw()
    return artist.get_window_extent(fig.canvas.get_renderer())


def _outside_canvas(fig, artist) -> bool:
    ext = _extent(fig, artist)
    canvas = fig.bbox
    return bool(
        ext.x0 < canvas.x0 - TOL_PX
        or ext.y0 < canvas.y0 - TOL_PX
        or ext.x1 > canvas.x1 + TOL_PX
        or ext.y1 > canvas.y1 + TOL_PX
    )


def _flagged(fig, text: str) -> bool:
    """Whether validate_figure names ``text`` in an overflow finding."""
    found = dm.validate_figure(
        fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
    )
    return any(w.detail.get("text") == text for w in found)


def _line_figure(width: str = "13cm"):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    ax.plot([1, 3, 2])
    return fig, ax


class TestSideTitles:
    @pytest.mark.parametrize("loc", ["left", "center", "right"])
    def test_title_stays_on_canvas(self, loc: str) -> None:
        fig, ax = _line_figure()
        title = ax.set_title("Revenue has doubled", loc=loc)
        dm.simple_layout(fig)
        assert not _outside_canvas(fig, title)
        plt.close(fig)

    def test_left_title_reserves_the_same_room_as_a_centre_title(self) -> None:
        tops = {}
        for loc in ("left", "center"):
            fig, ax = _line_figure()
            ax.set_title("Revenue has doubled", loc=loc)
            dm.simple_layout(fig)
            tops[loc] = ax.get_position().y1
            plt.close(fig)
        assert tops["left"] == pytest.approx(tops["center"], abs=1e-3)

    @pytest.mark.parametrize("loc", ["left", "center", "right"])
    def test_oversized_title_is_reported_not_chased(self, loc: str) -> None:
        """A title wider than the canvas cannot fit; the layout must not
        shrink the axes chasing it, and the checks must report it."""
        widths = {}
        for headline in ("Short", OVERSIZED):
            fig, ax = _line_figure("9cm")
            ax.set_title(headline, loc=loc)
            dm.simple_layout(fig)
            widths[headline] = ax.get_position().width
            flagged = _flagged(fig, OVERSIZED)
            plt.close(fig)
        assert widths[OVERSIZED] == pytest.approx(widths["Short"], abs=1e-3)
        assert flagged

    @pytest.mark.parametrize("kind", ["text", "annotate"])
    def test_subtitle_pinned_left_does_not_collapse_the_axes(
        self, kind: str
    ) -> None:
        """Main shrank the axes to 0.001 of the canvas chasing a subtitle
        anchored at the axes' left edge."""
        widths = {}
        for subtitle in (None, OVERSIZED):
            fig, ax = _line_figure("9cm")
            if subtitle and kind == "text":
                ax.text(0, 1.02, subtitle, transform=ax.transAxes)
            elif subtitle:
                ax.annotate(subtitle, xy=(0, 1.02), xycoords="axes fraction")
            dm.simple_layout(fig)
            widths[subtitle] = ax.get_position().width
            flagged = _flagged(fig, OVERSIZED)
            plt.close(fig)
        assert widths[OVERSIZED] == pytest.approx(widths[None], abs=1e-3)
        assert flagged


def _nearest_edge(fig, art, x0f, x1f, y0f, y1f) -> str:
    """The edge rule on main: the nearest canvas edge by distance."""
    dists = {"left": x0f, "right": 1 - x1f, "bottom": y0f, "top": 1 - y1f}
    return min(dists, key=lambda k: dists[k])


class TestFigureTextEdges:
    def _report(self):
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot(np.arange(12), np.linspace(10, 21, 12))
        ax.set_xlabel("Month")
        ax.set_ylabel("Revenue")
        return fig, ax

    def _content(self, fig, ax):
        return _extent(fig, ax).union(
            [_extent(fig, ax.yaxis.label), _extent(fig, ax.xaxis.label)]
        )

    def test_left_aligned_suptitle_and_subtitle_reserve_the_top(self) -> None:
        fig, ax = self._report()
        fig.suptitle("Revenue doubled in a year", x=0.01, ha="left")
        subtitle = fig.text(0.01, 0.92, "Monthly revenue", va="top")
        dm.simple_layout(fig)
        # Main measured the suptitle as a left-edge artist: x0 0.38.
        assert ax.get_position().x0 < 0.15
        content = self._content(fig, ax)
        assert content.y1 <= _extent(fig, subtitle).y0 + TOL_PX
        plt.close(fig)

    def test_bottom_left_source_note_reserves_the_bottom(self) -> None:
        fig, ax = self._report()
        note = fig.text(0.01, 0.01, "Source: internal", va="bottom")
        dm.simple_layout(fig)
        assert ax.get_position().x0 < 0.15
        assert _extent(fig, ax.xaxis.label).y0 >= _extent(fig, note).y1 - TOL_PX
        plt.close(fig)

    def test_supylabel_still_reserves_the_left(self) -> None:
        fig, ax = self._report()
        sup = fig.supylabel("Shared y")
        dm.simple_layout(fig)
        assert _extent(fig, ax.yaxis.label).x0 >= _extent(fig, sup).x1 - TOL_PX
        assert ax.get_position().y1 > 0.9
        plt.close(fig)

    def test_rotated_side_note_reserves_the_right(self) -> None:
        fig, ax = self._report()
        note = fig.text(
            0.99, 0.5, "Side note", rotation=90, ha="right", va="center"
        )
        dm.simple_layout(fig)
        assert self._content(fig, ax).x1 <= _extent(fig, note).x0 + TOL_PX
        assert ax.get_position().y1 > 0.9
        plt.close(fig)

    @pytest.mark.parametrize(
        "place",
        [
            {"x": 0.5, "y": 0.5, "s": "DRAFT", "ha": "center", "va": "center"},
            {"x": 0.01, "y": 0.49, "s": "(b)", "va": "top"},
        ],
        ids=["central-overlay", "mid-height-side-label"],
    )
    def test_text_off_the_edge_bands_keeps_the_nearest_edge(
        self, place, monkeypatch
    ) -> None:
        positions = []
        for rule in (None, _nearest_edge):
            if rule is not None:
                monkeypatch.setattr(layout, "_reservation_edge", rule)
            fig, ax = self._report()
            fig.text(**place)
            dm.simple_layout(fig)
            positions.append(ax.get_position().bounds)
            plt.close(fig)
        assert positions[0] == pytest.approx(positions[1], abs=1e-9)

    def test_text_outside_the_layout_reserves_nothing(self) -> None:
        positions = []
        for add_note in (False, True):
            fig, ax = self._report()
            if add_note:
                fig.text(0.01, 0.01, "Not in layout").set_in_layout(False)
            dm.simple_layout(fig)
            positions.append(ax.get_position().bounds)
            plt.close(fig)
        assert positions[0] == pytest.approx(positions[1], abs=1e-9)


class TestAxes3D:
    def _surface(self, preset: str):
        dm.style.use(preset)
        fig = plt.figure(figsize=dm.figsize("13cm", "square"))
        ax = fig.add_subplot(111, projection="3d")
        grid = np.linspace(-2, 2, 20)
        x, y = np.meshgrid(grid, grid)
        ax.plot_surface(x, y, np.exp(-(x**2 + y**2)))
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z (energy)")
        return fig, ax

    @pytest.mark.parametrize("preset", PRESETS)
    def test_3d_axes_fill_the_canvas(self, preset: str) -> None:
        fig, ax = self._surface(preset)
        ax.set_title("Surface")
        dm.simple_layout(fig)
        pos = ax.get_position()
        # Main shrank the axes to 0.001 x 0.001 of the canvas.
        assert pos.width > 0.6
        assert pos.height > 0.6
        assert not _outside_canvas(fig, ax.title)
        plt.close(fig)

    @pytest.mark.parametrize(("elev", "azim"), [(35, -120), (10, 30)])
    def test_turned_camera_keeps_axis_labels_on_canvas(
        self, elev: float, azim: float
    ) -> None:
        fig, ax = self._surface("report")
        ax.view_init(elev=elev, azim=azim)
        dm.simple_layout(fig)
        for label in (ax.xaxis.label, ax.yaxis.label, ax.zaxis.label):
            assert not _outside_canvas(fig, label), label.get_text()
        assert ax.get_position().width > 0.5
        plt.close(fig)

    @pytest.mark.parametrize("loc", ["center", "left", "right"])
    def test_oversized_title_is_reported_not_chased(self, loc: str) -> None:
        """The 3-D path used the native tight bbox, title included, and
        collapsed the axes to 0.001 x 0.001 chasing an oversized title."""
        widths = {}
        for headline in ("Short", OVERSIZED):
            dm.style.use("scientific")
            fig = plt.figure(figsize=dm.figsize("13cm", "square"))
            ax = fig.add_subplot(projection="3d")
            ax.plot([0, 1], [0, 1], [0, 1])
            ax.set(xlabel="x", ylabel="y", zlabel="z")
            ax.set_title(headline, loc=loc)
            dm.simple_layout(fig)
            widths[headline] = ax.get_position().width
            flagged = _flagged(fig, OVERSIZED)
            plt.close(fig)
        assert widths["Short"] > 0.6
        assert widths[OVERSIZED] == pytest.approx(widths["Short"], abs=1e-3)
        assert flagged
