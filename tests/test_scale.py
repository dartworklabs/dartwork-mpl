"""Tests for scale module (fs, fw, lw)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.scale import fs, fw, lw


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
