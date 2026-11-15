"""Native legend behavior of ``optimize_legend``."""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from tests.support.mpl_observe import legend_ncols, pinned_legend_corner


@pytest.mark.parametrize(
    "count,cap,columns,outside",
    [
        (1, 0, 1, False),
        (3, -1, 1, False),
        (4, 3, 2, False),
        (6, 1, 1, False),
        (7, 3, 3, False),
        (8, 2, 2, False),
        (4, 1, 1, True),
        (7, 2, 2, True),
    ],
)
def test_native_columns_format_and_placement(count, cap, columns, outside):
    """Thresholds, caps and outside anchoring retain native legend state."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        for i in range(count):
            ax.plot([0, 1], [i, i + 1], label=f"s{i}", linewidth=dm.lw(0))
        assert (
            dm.optimize_legend(
                ax, "invalid" if outside else "lower left", cap, outside
            )
            is None
        )
        legend = ax.get_legend()
        assert legend_ncols(legend) == columns
        assert pinned_legend_corner(legend) == (
            "upper left" if outside else "lower left"
        )
        assert [t.get_text() for t in legend.get_texts()] == [
            f"s{i}" for i in range(count)
        ]
        assert all(t.get_fontsize() == dm.fs(-1) for t in legend.get_texts())
        assert legend.get_frame().get_alpha() == 0.95
        assert legend.get_frame().get_edgecolor() == mcolors.to_rgba(
            "oc.gray3", 0.95
        )
        assert not hasattr(legend, "_dm_collision_score")
        assert not hasattr(legend, "_dm_collision_free")
        if outside:
            assert legend.get_bbox_to_anchor().transformed(
                ax.transAxes.inverted()
            ).bounds == pytest.approx((1.02, 1, 0, 0))
    finally:
        plt.close(fig)


def test_empty_discoverable_handles_leave_explicit_legend_untouched():
    """An empty axes ignores invalid loc and preserves an explicit legend."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        assert dm.optimize_legend(ax, preferred_loc="invalid") is None
        assert ax.get_legend() is None
        (line,) = ax.plot([0, 1], [0, 1], linewidth=dm.lw(0))
        original = ax.legend([line], ["explicit"], loc="lower right")
        assert dm.optimize_legend(ax, preferred_loc="invalid") is None
        assert ax.get_legend() is original
        assert pinned_legend_corner(original) == "lower right"
        assert [t.get_text() for t in original.get_texts()] == ["explicit"]
    finally:
        plt.close(fig)


@pytest.mark.parametrize(
    "count,kwargs,error",
    [
        (1, {"preferred_loc": "invalid"}, ValueError),
        (4, {"max_cols": 0}, ValueError),
        (4, {"max_cols": -1}, ValueError),
        (7, {"max_cols": "two"}, TypeError),
    ],
)
def test_native_invalid_parameters_keep_exception_semantics(
    count, kwargs, error
):
    """Invalid locations/caps propagate native errors without pinning version prose."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        for i in range(count):
            ax.plot([0, 1], [i, i], label=f"s{i}", linewidth=dm.lw(0))
        with pytest.raises(error):
            dm.optimize_legend(ax, **kwargs)
    finally:
        plt.close(fig)
