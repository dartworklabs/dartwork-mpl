"""fs, fw and lw step relative to the active rcParams (moved from the util tests)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.scale import fs, fw, lw


class TestFs:
    """Tests for fs() font size scaling."""

    def test_base_increment(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(0) == base
        assert fs(1) == base + 1
        assert fs(-1) == base - 1

    def test_large_offset(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(10) == base + 10


class TestFw:
    """Tests for fw() font weight scaling."""

    def test_integer_weight(self) -> None:
        """fw(n) should return base weight + 100*n for int weights."""
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = 300
            assert fw(0) == 300
            assert fw(1) == 400
            assert fw(-1) == 200
        finally:
            plt.rcParams["font.weight"] = original

    def test_string_weight_normal(self) -> None:
        """fw() should map 'normal' to 400."""
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = "normal"
            assert fw(0) == 400
            assert fw(1) == 500
        finally:
            plt.rcParams["font.weight"] = original

    def test_string_weight_bold(self) -> None:
        """fw() should map 'bold' to 700."""
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = "bold"
            assert fw(0) == 700
            assert fw(1) == 800
        finally:
            plt.rcParams["font.weight"] = original


class TestLw:
    """Tests for lw() line width scaling."""

    def test_base_increment(self) -> None:
        base = plt.rcParams["lines.linewidth"]
        assert lw(0) == base
        assert lw(1) == base + 1
        assert lw(-0.5) == base - 0.5


class TestSlideStep:
    """Under presentation presets a step is 2.6 pt (decision 5-A, 2026-11-03).

    Those presets are the scientific one with every point size x 2.6, so a
    1 pt step would be a 2.6x smaller nudge on a slide than in a journal
    column: a value label at ``fs(-1)`` would be 18.5 pt next to 18.2 pt
    ticks, and an emphasis line at ``lw(1)`` only 1.4x the base line.
    """

    def test_presentation_steps_by_k(self) -> None:
        import dartwork_mpl as dm

        dm.style.use("presentation")
        assert fs(0) == pytest.approx(19.5)
        assert fs(-1) == pytest.approx(16.9)
        assert lw(0) == pytest.approx(2.6)
        assert lw(1) == pytest.approx(5.2)

    def test_same_share_as_scientific(self) -> None:
        import dartwork_mpl as dm

        dm.style.use("scientific")
        paper = (fs(-1) / fs(0), lw(1) / lw(0))
        dm.style.use("presentation")
        assert (fs(-1) / fs(0), lw(1) / lw(0)) == pytest.approx(paper)

    def test_weight_steps_do_not_scale(self) -> None:
        import dartwork_mpl as dm

        dm.style.use("presentation")
        assert fw(1) - fw(0) == 100
