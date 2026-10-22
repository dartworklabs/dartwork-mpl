"""fs, fw and lw step relative to the active rcParams (moved from the util tests)."""

from __future__ import annotations

import matplotlib.pyplot as plt

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
