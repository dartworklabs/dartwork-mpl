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
    def test_x_axis_rotation_sets_right_alignment(self, rotation: int) -> None:
        fig, ax = _axes()
        ax.set_xticks(np.arange(5))
        ax.set_xticklabels(["A_long", "B_long", "C_long", "D_long", "E_long"])
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

    def test_x_axis_rotation_emits_no_set_ticklabels_warning(self) -> None:
        """The pre-patch implementation called
        ``set_xticklabels(get_xticklabels(), ...)`` which emits
        matplotlib's FixedLocator deprecation UserWarning whenever the
        axis uses a non-FixedLocator (e.g. a CategoricalLocator from
        ax.bar with string labels). The fix iterates over the existing
        Text artists, mutating them in place, which preserves the
        locator and silences the warning.
        """
        import warnings

        fig, ax = _axes()
        # ax.bar with string labels installs a CategoricalLocator, the
        # exact path that triggered the warning pre-patch.
        ax.bar(["A", "B", "C", "D", "E"], [1, 2, 3, 4, 5])
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            dm.rotate_tick_labels(ax, axis="x", rotation=45)
        plt.close(fig)


class TestAvoidTickOverlap:
    def test_dense_x_labels_are_thinned(self) -> None:
        fig, ax = _axes()
        labels = [f"very-long-label-{i}" for i in range(12)]
        ax.plot(range(len(labels)), range(len(labels)))
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)

        dm.avoid_tick_overlap(ax, max_visible=5)

        visible = [
            t for t in ax.get_xticklabels() if t.get_visible() and t.get_text()
        ]
        assert len(visible) <= 5
        assert visible[0].get_text() == labels[0]
        assert visible[-1].get_text() == labels[-1]
        plt.close(fig)


class TestRecommendTickDecimals:
    def test_integer_steps_need_no_decimals(self) -> None:
        assert dm.recommend_tick_decimals([0, 5, 10]) == 0

    def test_fractional_step_uses_minimum_required_decimals(self) -> None:
        assert dm.recommend_tick_decimals([0, 2.5, 5.0]) == 0
        assert dm.recommend_tick_decimals([0, 0.5, 1.0]) == 1
        assert dm.recommend_tick_decimals([0, 0.01, 0.02]) == 2

    def test_caps_at_four_decimals(self) -> None:
        assert dm.recommend_tick_decimals([0, 0.00001, 0.00002]) == 4

    def test_ignores_duplicate_and_nonfinite_values(self) -> None:
        assert dm.recommend_tick_decimals([0, 0, float("nan"), 1]) == 0


class TestFormatAxisSiBoundaries:
    """Boundary-value tests for ``format_axis_si``.

    The formatter is expected to:
    - Switch SI prefix at exactly 1e3, 1e6, 1e9, 1e12.
    - Honour ``decimals`` for both magnitude and the zero-tick label.
    - Carry the sign for negative values.
    """

    @pytest.mark.parametrize(
        "value,decimals,expected",
        [
            (999, 1, "999.0"),
            (1000, 1, "1.0k"),
            (999_999, 1, "1000.0k"),
            (1_000_000, 1, "1.0M"),
            (1_000_000_000, 1, "1.0G"),
            (1_000_000_000_000, 1, "1.0T"),
            (-1_500_000_000, 1, "-1.5G"),
            (-1500, 0, "-2k"),
        ],
    )
    def test_magnitude_and_sign(
        self, value: float, decimals: int, expected: str
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_si(ax, axis="y", decimals=decimals)
        formatter = ax.yaxis.get_major_formatter()
        # FuncFormatter's call signature is (value, pos).
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_zero_respects_decimals(self) -> None:
        """``format_axis_si(ax, decimals=2)`` must format the zero
        tick as ``"0.00"`` so it visually aligns with neighbouring
        ticks like ``"1.50k"``. The pre-fix implementation returned
        the literal string ``"0"``."""
        fig, ax = _axes()
        dm.format_axis_si(ax, axis="y", decimals=2)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(0, 0) == "0.00"
        plt.close(fig)


class TestFormatAxisCurrencyMultibyte:
    """``format_axis_currency`` must accept multibyte Unicode currency
    symbols (₩, €, ¥) without UnicodeEncodeError on PNG save and the
    rendered tick label must literally contain the symbol."""

    @pytest.mark.parametrize(
        "symbol,position,expected_substring",
        [
            ("₩", "prefix", "₩1,000"),
            ("€", "suffix", "1,000€"),
            ("¥", "prefix", "¥1,000"),
        ],
    )
    def test_symbol_renders_in_tick_label(
        self, symbol: str, position: str, expected_substring: str, tmp_path
    ) -> None:
        fig, ax = _axes()
        ax.plot([0, 1, 2], [500, 1000, 1500])
        dm.format_axis_currency(ax, axis="y", symbol=symbol, position=position)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(1000, 0) == expected_substring

        # PNG round-trip must not raise UnicodeEncodeError on the
        # backend's text rendering path.
        out_path = tmp_path / f"currency_{ord(symbol):x}.png"
        fig.savefig(out_path)
        assert out_path.exists()
        assert out_path.stat().st_size > 1024
        plt.close(fig)


class TestFormatAxisMillionsZeroDecimals:
    """Boundary-value tests for ``format_axis_millions``.

    The existing zero-tick short-circuit returns the literal ``"0"``
    regardless of ``decimals``. The patch in this task makes it honour
    ``decimals`` so the zero tick aligns visually with neighbouring
    millions-scale ticks.
    """

    @pytest.mark.parametrize(
        "value,decimals,suffix,expected",
        [
            (1_000_000, 1, "M", "1.0M"),
            (1_500_000, 1, "M", "1.5M"),
            (1_500_000, 0, "M", "2M"),
            (-1_500_000, 1, "M", "-1.5M"),
            (1_000_000, 2, " mn", "1.00 mn"),
        ],
    )
    def test_magnitude_sign_and_suffix(
        self, value: float, decimals: int, suffix: str, expected: str
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_millions(ax, axis="y", suffix=suffix, decimals=decimals)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_zero_respects_decimals(self) -> None:
        """``format_axis_millions(ax, decimals=2)`` must format the
        zero tick as ``"0.00"`` so it visually aligns with neighbouring
        ticks like ``"1.50M"``. The pre-fix implementation returned
        the literal string ``"0"``."""
        fig, ax = _axes()
        dm.format_axis_millions(ax, axis="y", decimals=2)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(0, 0) == "0.00"
        plt.close(fig)


class TestFormatAxisBillionsZeroDecimals:
    """Boundary-value tests for ``format_axis_billions``.

    Same pattern as ``TestFormatAxisMillionsZeroDecimals`` but applied
    to the billions formatter. The pre-fix zero short-circuit ignores
    ``decimals`` and breaks visual tick alignment for charts that span
    billions-scale values.
    """

    @pytest.mark.parametrize(
        "value,decimals,suffix,expected",
        [
            (1_000_000_000, 1, "B", "1.0B"),
            (1_500_000_000, 1, "B", "1.5B"),
            (1_500_000_000, 0, "B", "2B"),
            (-1_500_000_000, 1, "B", "-1.5B"),
            (1_000_000_000, 2, " bn", "1.00 bn"),
        ],
    )
    def test_magnitude_sign_and_suffix(
        self, value: float, decimals: int, suffix: str, expected: str
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_billions(ax, axis="y", suffix=suffix, decimals=decimals)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_zero_respects_decimals(self) -> None:
        """``format_axis_billions(ax, decimals=2)`` must format the
        zero tick as ``"0.00"`` so it visually aligns with neighbouring
        ticks like ``"1.50B"``. The pre-fix implementation returned
        the literal string ``"0"``."""
        fig, ax = _axes()
        dm.format_axis_billions(ax, axis="y", decimals=2)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(0, 0) == "0.00"
        plt.close(fig)


class TestFormatAxisCurrencyNegativeSign:
    """Negative-value sign placement for ``format_axis_currency``.

    Convention: the minus sign sits OUTSIDE the currency symbol
    (``-$1,000``, ``-€1,000``), not INSIDE (``$-1,000``). The pre-fix
    implementation did ``f"{symbol}{formatted}"`` which placed the
    minus sign between the symbol and the magnitude when
    ``position="prefix"``.
    """

    @pytest.mark.parametrize(
        "value,position,symbol,expected",
        [
            (-1000, "prefix", "$", "-$1,000"),
            (-1500, "prefix", "₩", "-₩1,500"),
            (-1000, "suffix", "€", "-1,000€"),
            (1000, "prefix", "$", "$1,000"),
            (0, "prefix", "$", "$0"),
        ],
    )
    def test_sign_outside_symbol(
        self, value: float, position: str, symbol: str, expected: str
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_currency(ax, axis="y", symbol=symbol, position=position)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_negative_zero_decimals_does_not_show_minus(self) -> None:
        """``x=0`` must format as ``"$0.00"``, not ``"-$0.00"``. Python's
        formatter treats ``-0.0`` as negative; the implementation must
        suppress the sign when the magnitude rounds to zero so that the
        zero tick label looks identical to a positive zero."""
        fig, ax = _axes()
        dm.format_axis_currency(
            ax, axis="y", symbol="$", position="prefix", decimals=2
        )
        formatter = ax.yaxis.get_major_formatter()
        # exact zero
        assert formatter(0.0, 0) == "$0.00"
        # negative zero (e.g. from floating-point arithmetic)
        assert formatter(-0.0, 0) == "$0.00"
        plt.close(fig)


class TestFormatAxisNoNegativeZero:
    """Small negatives must not render as '-0.0M'/'-0.0B' (2026-07 audit)."""

    def test_millions_small_negative_is_bare_zero(self) -> None:
        fig, ax = _axes()
        dm.format_axis_millions(ax, axis="y", decimals=1)
        fmt = ax.yaxis.get_major_formatter()
        assert fmt(-40_000, 0) == "0.0"
        plt.close(fig)

    def test_billions_small_negative_is_bare_zero(self) -> None:
        fig, ax = _axes()
        dm.format_axis_billions(ax, axis="y", decimals=1)
        fmt = ax.yaxis.get_major_formatter()
        assert fmt(-40_000_000, 0) == "0.0"
        plt.close(fig)
