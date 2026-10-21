"""Tests for scale module (fs, fw, lw)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.scale import dpi, fs, fw, lw


class TestFs:
    """Tests for fs() font size scaling."""

    def test_base_returns_base(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(0) == base

    def test_positive_offset(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(2) == base + 2

    def test_negative_offset(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(-1) == base - 1

    def test_float_offset(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(0.5) == pytest.approx(base + 0.5)


class TestFw:
    """Tests for fw() font weight scaling."""

    def test_integer_weight(self) -> None:
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = 400
            assert fw(0) == 400
            assert fw(1) == 500
            assert fw(-1) == 300
        finally:
            plt.rcParams["font.weight"] = original

    def test_string_weight_normal(self) -> None:
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = "normal"
            assert fw(0) == 400
        finally:
            plt.rcParams["font.weight"] = original

    def test_string_weight_bold(self) -> None:
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = "bold"
            assert fw(0) == 700
        finally:
            plt.rcParams["font.weight"] = original

    def test_float_step_returns_int(self) -> None:
        # A fractional step must still return an int (the -> int contract);
        # previously `100 * 0.5` made the result a float.
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = 400
            result = fw(0.5)
            assert isinstance(result, int)
            assert result == 450
        finally:
            plt.rcParams["font.weight"] = original


class TestLw:
    """Tests for lw() line width scaling."""

    def test_base_returns_base(self) -> None:
        base = plt.rcParams["lines.linewidth"]
        assert lw(0) == base

    def test_positive_offset(self) -> None:
        base = plt.rcParams["lines.linewidth"]
        assert lw(1) == base + 1

    def test_negative_float_offset(self) -> None:
        base = plt.rcParams["lines.linewidth"]
        assert lw(-0.3) == pytest.approx(base - 0.3)


class TestDpi:
    """Tests for dpi() DPI ladder scaling."""

    def test_base_returns_savefig_dpi(self) -> None:
        original = plt.rcParams["savefig.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = 100
            assert dpi() == 100.0
            assert dpi(0) == 100.0
        finally:
            plt.rcParams["savefig.dpi"] = original

    def test_positive_step_adds_fifty(self) -> None:
        original = plt.rcParams["savefig.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = 100
            assert dpi(1) == 150.0
            assert dpi(2) == 200.0
        finally:
            plt.rcParams["savefig.dpi"] = original

    def test_negative_step_subtracts_fifty(self) -> None:
        original = plt.rcParams["savefig.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = 100
            assert dpi(-1) == 50.0
        finally:
            plt.rcParams["savefig.dpi"] = original

    def test_negative_step_clamped_to_one(self) -> None:
        """A very large negative step can't drive DPI to zero or below —
        savefig refuses values < 1, so the helper clamps."""
        original = plt.rcParams["savefig.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = 100
            assert dpi(-100) == 1.0
        finally:
            plt.rcParams["savefig.dpi"] = original

    def test_fractional_step(self) -> None:
        original = plt.rcParams["savefig.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = 100
            assert dpi(0.5) == 125.0
        finally:
            plt.rcParams["savefig.dpi"] = original

    def test_string_figure_sentinel_falls_back_to_figure_dpi(self) -> None:
        """matplotlib accepts ``savefig.dpi="figure"`` to mean "use
        figure.dpi"; the helper resolves that to a real number so the
        ladder still works."""
        original_save = plt.rcParams["savefig.dpi"]
        original_fig = plt.rcParams["figure.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = "figure"
            plt.rcParams["figure.dpi"] = 120
            assert dpi(0) == 120.0
            assert dpi(1) == 170.0
        finally:
            plt.rcParams["savefig.dpi"] = original_save
            plt.rcParams["figure.dpi"] = original_fig

    def test_string_numeric_savefig_dpi_resolves(self) -> None:
        """Some preset files set ``savefig.dpi`` as a quoted string;
        the helper must parse them just like the float path."""
        original = plt.rcParams["savefig.dpi"]
        try:
            plt.rcParams["savefig.dpi"] = "200"
            assert dpi() == 200.0
            assert dpi(1) == 250.0
        finally:
            plt.rcParams["savefig.dpi"] = original

    def test_exposed_at_package_root(self) -> None:
        import dartwork_mpl as dm

        assert hasattr(dm, "dpi")
        assert "dpi" in dm.__all__
        assert dm.dpi(0) == dpi(0)
