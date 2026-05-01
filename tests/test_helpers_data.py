"""Behavioural tests for ``dartwork_mpl.helpers.data``."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from dartwork_mpl.helpers.data import validate_data


class TestValidateData:
    """Happy path inputs."""

    def test_accepts_lists(self) -> None:
        x, y = validate_data([1, 2, 3], [4, 5, 6])
        assert isinstance(x, np.ndarray)
        assert isinstance(y, np.ndarray)
        assert x.tolist() == [1, 2, 3]
        assert y.tolist() == [4, 5, 6]

    def test_accepts_numpy_arrays(self) -> None:
        x_in = np.array([1.0, 2.0, 3.0])
        y_in = np.array([10.0, 20.0, 30.0])
        x, y = validate_data(x_in, y_in)
        assert np.array_equal(x, x_in)
        assert np.array_equal(y, y_in)

    def test_accepts_tuples(self) -> None:
        x, y = validate_data((1, 2, 3, 4), (5, 6, 7, 8))
        assert x.tolist() == [1, 2, 3, 4]
        assert y is not None
        assert y.tolist() == [5, 6, 7, 8]

    def test_y_optional(self) -> None:
        x, y = validate_data([1, 2, 3])
        assert isinstance(x, np.ndarray)
        assert y is None


class TestValidateDataLengthChecks:
    """Length / min_points enforcement."""

    def test_min_points_violation_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            validate_data([1])  # default min_points=2

    def test_custom_min_points_enforced(self) -> None:
        with pytest.raises(ValueError, match="at least 5"):
            validate_data([1, 2, 3], min_points=5)

    def test_min_points_satisfied(self) -> None:
        # 4 >= 4, no raise.
        x, _ = validate_data([1, 2, 3, 4], min_points=4)
        assert len(x) == 4

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            validate_data([1, 2, 3], [1, 2])

    def test_length_mismatch_allowed_when_disabled(self) -> None:
        # ``require_same_length=False`` should silently accept differing
        # lengths so that callers (e.g. histograms) can use it.
        x, y = validate_data([1, 2, 3], [4, 5], require_same_length=False)
        assert len(x) == 3
        assert y is not None
        assert len(y) == 2


class TestValidateDataNaNHandling:
    """NaN / Inf cleanup branches."""

    def test_strips_nan_when_disallowed(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x, y = validate_data(
                [1.0, 2.0, float("nan"), 4.0],
                [1.0, 2.0, 3.0, 4.0],
                allow_nan=False,
            )
        assert np.isnan(x).sum() == 0
        assert y is not None
        assert len(x) == len(y) == 3

    def test_strips_inf_when_disallowed(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x, y = validate_data(
                [1.0, float("inf"), 3.0, 4.0],
                [1.0, 2.0, 3.0, 4.0],
                allow_nan=False,
            )
        assert np.isinf(x).sum() == 0
        assert y is not None
        assert len(x) == len(y) == 3

    def test_strips_nan_in_y_array(self) -> None:
        """NaN in y should also be removed and emit a warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            x, y = validate_data(
                [1.0, 2.0, 3.0, 4.0],
                [1.0, float("nan"), 3.0, 4.0],
                allow_nan=False,
            )
        assert any(issubclass(w.category, UserWarning) for w in caught), (
            "Expected a UserWarning when scrubbing NaN values."
        )
        assert y is not None
        assert np.isnan(y).sum() == 0
        assert len(x) == len(y) == 3

    def test_emits_warning_when_stripping(self) -> None:
        """The function must warn the caller about removed values."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            validate_data(
                [1.0, float("nan"), 3.0], [1.0, 2.0, 3.0], allow_nan=False
            )
        msgs = [str(w.message) for w in caught]
        assert any("Removed" in m and "NaN" in m for m in msgs)

    def test_allows_nan_when_requested(self) -> None:
        x, y = validate_data(
            [1.0, float("nan"), 3.0], [1.0, 2.0, 3.0], allow_nan=True
        )
        # NaN preserved, no warning, no scrub.
        assert np.isnan(x).any()
        assert y is not None
        assert len(x) == len(y) == 3

    def test_post_cleanup_min_points_violation_raises(self) -> None:
        """If too many points get scrubbed, the final length check fires."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(ValueError, match="After cleaning"):
                # 3 points, 2 are NaN -> only 1 remains, below default 2.
                validate_data(
                    [1.0, float("nan"), float("nan")],
                    [1.0, 2.0, 3.0],
                    allow_nan=False,
                )
