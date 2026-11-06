"""Native legend behavior and historical callable compatibility survive ownership moves."""

import inspect
import pickle

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl import annotation, helpers
from dartwork_mpl.helpers import labels
from tests.support.mpl_observe import legend_corner, legend_ncols

# Protocol 4 global reference produced before annotation owned the implementation.
OLD_PICKLE = (
    b"\x80\x04\x953\x00\x00\x00\x00\x00\x00\x00"
    b"\x8c\x1bdartwork_mpl.helpers.labels\x94\x8c\x0foptimize_legend\x94\x93\x94."
)


def test_public_aliases_preserve_signature_and_historical_pickle():
    """The new owner and three old paths expose one pickle-compatible callable."""
    assert "optimize_legend" in annotation.__all__
    f = annotation.optimize_legend
    assert (
        f
        is dm.optimize_legend
        is helpers.optimize_legend
        is labels.optimize_legend
    )
    assert str(inspect.signature(f)) == (
        "(ax: 'Axes', preferred_loc: 'str' = 'best', max_cols: 'int' = 3, "
        "outside: 'bool' = False) -> 'None'"
    )
    assert f.__annotations__ == {
        "ax": "Axes",
        "preferred_loc": "str",
        "max_cols": "int",
        "outside": "bool",
        "return": "None",
    }
    assert f.__module__ == "dartwork_mpl.helpers.labels"
    assert f.__name__ == f.__qualname__ == "optimize_legend"
    assert pickle.loads(OLD_PICKLE) is f
    assert pickle.dumps(f, protocol=4) == OLD_PICKLE


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
        assert legend_corner(legend) == (
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
        assert legend_corner(original) == "lower right"
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
