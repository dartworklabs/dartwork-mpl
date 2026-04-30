"""Smoke tests for ``dartwork_mpl.helpers.data``."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from dartwork_mpl.helpers.data import validate_data


class TestValidateData:
    def test_accepts_lists(self) -> None:
        x, y = validate_data([1, 2, 3], [4, 5, 6])
        assert isinstance(x, np.ndarray)
        assert isinstance(y, np.ndarray)
        assert x.tolist() == [1, 2, 3]
        assert y.tolist() == [4, 5, 6]

    def test_y_optional(self) -> None:
        x, y = validate_data([1, 2, 3])
        assert isinstance(x, np.ndarray)
        assert y is None

    def test_min_points_violation_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_data([1])  # default min_points=2

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_data([1, 2, 3], [1, 2])

    def test_strips_nan_when_disallowed(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x, y = validate_data(
                [1.0, 2.0, float("nan"), 4.0],
                [1.0, 2.0, 3.0, 4.0],
                allow_nan=False,
            )
        assert np.isnan(x).sum() == 0
        assert len(x) == len(y) == 3

    def test_allows_nan_when_requested(self) -> None:
        x, y = validate_data(
            [1.0, float("nan"), 3.0], [1.0, 2.0, 3.0], allow_nan=True
        )
        # NaN preserved.
        assert np.isnan(x).any()
        assert len(x) == len(y) == 3
