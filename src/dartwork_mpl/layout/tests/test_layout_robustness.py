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
import pytest

import dartwork_mpl as dm

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
