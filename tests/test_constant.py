"""Tests for constant module (SW, DW) — both deprecated in 0.4.0."""

from __future__ import annotations

import pytest

from dartwork_mpl.constant import DW, SW
from dartwork_mpl.util import cm2in


class TestConstants:
    """Tests for figure width constants."""

    def test_sw_equals_cm2in_9(self) -> None:
        # cm2in is deprecated in 0.4.0; this test verifies the legacy
        # equivalence still holds for back-compat.
        with pytest.warns(DeprecationWarning):
            expected = cm2in(9)
        assert SW == pytest.approx(expected)

    def test_dw_equals_cm2in_17(self) -> None:
        with pytest.warns(DeprecationWarning):
            expected = cm2in(17)
        assert DW == pytest.approx(expected)

    def test_sw_positive(self) -> None:
        assert SW > 0

    def test_dw_greater_than_sw(self) -> None:
        assert DW > SW

    def test_sw_is_float(self) -> None:
        assert isinstance(SW, float)

    def test_dw_is_float(self) -> None:
        assert isinstance(DW, float)
