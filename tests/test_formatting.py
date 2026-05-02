"""Tests for dartwork_mpl.formatting axis tick formatters."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm


def _axes():
    fig, ax = plt.subplots()
    return fig, ax


class TestFormatAxisPercent:
    def test_smoke(self) -> None:
        fig, ax = _axes()
        ax.plot([0, 1], [0.1, 0.5])
        dm.format_axis_percent(ax, axis="y")
        # Formatter applied — tick formatter type check
        fmt = ax.yaxis.get_major_formatter()
        assert fmt is not None
        plt.close(fig)

    @pytest.mark.parametrize("decimals", [0, 1, 2])
    def test_decimals(self, decimals: int) -> None:
        fig, ax = _axes()
        dm.format_axis_percent(ax, axis="y", decimals=decimals)
        plt.close(fig)

    def test_unknown_axis_is_silent_noop(self) -> None:
        """Unknown ``axis`` values fall through — the implementation
        checks ``axis in ('x', 'y', 'both')`` and does nothing otherwise.

        This pins the current behaviour so a future change that starts
        raising on unknown input is a deliberate, reviewed decision.
        """
        fig, ax = _axes()
        default_formatter = ax.yaxis.get_major_formatter()
        dm.format_axis_percent(ax, axis="z")  # type: ignore[arg-type]
        # The default formatter on ``ax.yaxis`` is unchanged.
        assert ax.yaxis.get_major_formatter() is default_formatter
        plt.close(fig)


class TestFormatAxisThousands:
    def test_smoke(self) -> None:
        fig, ax = _axes()
        ax.plot([0, 1], [1000, 2_000_000])
        dm.format_axis_thousands(ax, axis="y")
        plt.close(fig)


class TestFormatAxisMillions:
    def test_smoke(self) -> None:
        fig, ax = _axes()
        ax.plot([0, 1], [1e6, 5e6])
        dm.format_axis_millions(ax, axis="y")
        plt.close(fig)


class TestFormatAxisBillions:
    def test_smoke_with_suffix(self) -> None:
        fig, ax = _axes()
        ax.plot([0, 1], [1e9, 5e9])
        dm.format_axis_billions(ax, axis="y", suffix="B")
        plt.close(fig)


class TestFormatAxisCurrency:
    def test_prefix(self) -> None:
        fig, ax = _axes()
        dm.format_axis_currency(ax, axis="y", symbol="$", position="prefix")
        plt.close(fig)

    def test_suffix(self) -> None:
        fig, ax = _axes()
        dm.format_axis_currency(ax, axis="y", symbol="€", position="suffix")
        plt.close(fig)


class TestFormatAxisSi:
    def test_smoke(self) -> None:
        fig, ax = _axes()
        ax.semilogx([1, 1e9], [0, 1])
        dm.format_axis_si(ax, axis="x")
        plt.close(fig)


class TestRotateTickLabels:
    @pytest.mark.parametrize("rotation", [0, 30, 45, 90])
    def test_rotation(self, rotation: int) -> None:
        fig, ax = _axes()
        ax.set_xticks(np.arange(5))
        ax.set_xticklabels(["A", "B", "C", "D", "E"])
        dm.rotate_tick_labels(ax, axis="x", rotation=rotation)
        # Side-effect: rotation saved on each tick label
        for label in ax.get_xticklabels():
            assert label.get_rotation() == rotation
        plt.close(fig)


class TestRotateTickLabelsAlignment:
    """rotate_tick_labels must set ha='right' for non-trivial rotations
    on the x-axis so labels anchor at their tick — leaving ha='center'
    causes labels to drift left of their tick and overflow the figure."""

    @pytest.mark.parametrize("rotation", [30, 45, 60, 90])
    def test_x_axis_rotation_sets_right_alignment(
        self, rotation: int
    ) -> None:
        fig, ax = _axes()
        ax.set_xticks(np.arange(5))
        ax.set_xticklabels(
            ["A_long", "B_long", "C_long", "D_long", "E_long"]
        )
        dm.rotate_tick_labels(ax, axis="x", rotation=rotation)
        for label in ax.get_xticklabels():
            assert label.get_horizontalalignment() == "right", (
                f"rotation={rotation} should anchor at right, "
                f"got {label.get_horizontalalignment()!r}"
            )
        plt.close(fig)

    def test_x_axis_zero_rotation_leaves_alignment_center(self) -> None:
        fig, ax = _axes()
        ax.set_xticks(np.arange(3))
        ax.set_xticklabels(["a", "b", "c"])
        dm.rotate_tick_labels(ax, axis="x", rotation=0)
        for label in ax.get_xticklabels():
            assert label.get_horizontalalignment() == "center"
        plt.close(fig)

    def test_x_axis_rotation_emits_no_set_ticklabels_warning(
        self,
    ) -> None:
        """The fix replaces set_xticklabels(get_xticklabels(), ...) with
        per-label .set_rotation/.set_horizontalalignment so matplotlib's
        FixedLocator warning no longer fires."""
        import warnings

        fig, ax = _axes()
        ax.set_xticks(np.arange(5))
        ax.set_xticklabels(["A", "B", "C", "D", "E"])
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            dm.rotate_tick_labels(ax, axis="x", rotation=45)
        plt.close(fig)
