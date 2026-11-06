"""Behavioural tests for ``dartwork_mpl.helpers.labels``."""

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes

import dartwork_mpl as dm
from dartwork_mpl.helpers.labels import optimize_legend
from tests.support.mpl_observe import legend_ncols, pinned_legend_corner


@pytest.fixture
def ax() -> Axes:
    """Use a supported preset and physical size with registered colours."""
    dm.style.use("scientific")
    _fig, axes = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    return axes


class TestOptimizeLegend:
    """Legend column heuristics + outside placement."""

    def test_no_handles_returns_silently(self, ax: Axes) -> None:
        """Empty axes need no legend and return without error."""
        # No labelled artists -> get_legend_handles_labels returns empty.
        optimize_legend(ax)
        assert ax.get_legend() is None

    def test_creates_legend_when_handles_exist(self, ax: Axes) -> None:
        """Registered input creates a legend at the requested location."""
        ax.plot(
            [0, 1], [0, 1], label="series", color="oc.blue5", linewidth=dm.lw(0)
        )
        optimize_legend(ax, preferred_loc="upper right")
        legend = ax.get_legend()
        assert legend is not None
        assert pinned_legend_corner(legend) == "upper right"  # requested above
        assert [text.get_text() for text in legend.get_texts()] == ["series"]

    def test_few_items_use_single_column(self, ax: Axes) -> None:
        """At most three series use a single legend column."""
        for i in range(3):
            ax.plot(
                [0, 1],
                [i, i],
                label=f"s{i}",
                color="oc.blue5",
                linewidth=dm.lw(0),
            )
        optimize_legend(ax)
        legend = ax.get_legend()
        assert legend is not None
        assert legend_ncols(legend) == 1

    def test_medium_items_use_two_columns(self, ax: Axes) -> None:
        """4-6 series -> ncol=2."""
        for i in range(5):
            ax.plot(
                [0, 1],
                [i, i],
                label=f"s{i}",
                color="oc.blue5",
                linewidth=dm.lw(0),
            )
        optimize_legend(ax)
        legend = ax.get_legend()
        assert legend is not None
        assert legend_ncols(legend) == 2

    def test_many_items_capped_at_max_cols(self, ax: Axes) -> None:
        """>6 series -> ncol=min(3, max_cols)."""
        for i in range(8):
            ax.plot(
                [0, 1],
                [i, i],
                label=f"s{i}",
                color="oc.blue5",
                linewidth=dm.lw(0),
            )
        optimize_legend(ax, max_cols=2)
        legend = ax.get_legend()
        assert legend is not None
        # max_cols=2 should cap at 2 even with 8 series.
        assert legend_ncols(legend) == 2

    def test_outside_placement_sets_anchor(self, ax: Axes) -> None:
        """Outside legends use an upper-left anchor beyond the axes."""
        ax.plot(
            [0, 1], [0, 1], label="series", color="oc.blue5", linewidth=dm.lw(0)
        )
        optimize_legend(ax, outside=True)
        legend = ax.get_legend()
        assert legend is not None
        assert pinned_legend_corner(legend) == "upper left"
        anchor = legend.get_bbox_to_anchor().transformed(
            ax.transAxes.inverted()
        )
        assert anchor.x0 == pytest.approx(1.02)
        assert anchor.y0 == pytest.approx(1.0)
