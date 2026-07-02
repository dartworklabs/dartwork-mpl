"""Data validation and cleaning utilities for dartwork-mpl agents.

This module provides functions for validating and cleaning data
before plotting.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np


def validate_data(
    x: Any,
    y: Any | None = None,
    require_same_length: bool = True,
    allow_nan: bool = False,
    min_points: int = 2,
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any] | None]:
    """Validate and clean input data for plotting.

    Parameters
    ----------
    x : Any
        X-axis data
    y : Any | None
        Y-axis data (optional for histograms, etc.)
    require_same_length : bool
        Whether x and y must have the same length
    allow_nan : bool
        Whether to allow NaN values
    min_points : int
        Minimum number of data points required

    Returns
    -------
    tuple[np.ndarray, np.ndarray | None]
        Cleaned x and y arrays

    Raises
    ------
    ValueError
        If validation fails

    Examples
    --------
    >>> x, y = validate_data([1, 2, 3], [4, 5, 6])
    >>> x_clean, _ = validate_data([1, 2, np.nan, 4], allow_nan=False)
    """
    # Convert to numpy arrays
    x = np.asarray(x)
    if y is not None:
        y = np.asarray(y)

    # Check minimum points
    if len(x) < min_points:
        raise ValueError(
            f"Need at least {min_points} data points, got {len(x)}"
        )

    # Check length matching
    if y is not None and require_same_length and len(x) != len(y):
        raise ValueError(f"Data length mismatch: x({len(x)}) != y({len(y)})")

    # Handle NaN/Inf values. ``np.isnan``/``np.isinf`` only accept
    # numeric dtypes — calling them on a categorical (string) array
    # raises ``TypeError``, so skip non-numeric arrays (which can't hold
    # NaN/Inf anyway). Masks are only cross-applied to the other array
    # when the two are aligned (same length); when
    # ``require_same_length=False`` and the lengths differ, applying x's
    # mask to a different-length y would mis-index or silently corrupt it.
    def _has_nan_or_inf(arr: np.ndarray[Any, Any]) -> bool:
        if not np.issubdtype(arr.dtype, np.number):
            return False
        return bool(np.any(np.isnan(arr)) or np.any(np.isinf(arr)))

    if not allow_nan:
        aligned = y is not None and len(x) == len(y)
        if _has_nan_or_inf(x):
            mask = ~(np.isnan(x) | np.isinf(x))
            removed = int((~mask).sum())
            if y is not None and aligned:
                y = y[mask]
            x = x[mask]
            aligned = y is not None and len(x) == len(y)
            warnings.warn(
                f"Removed {removed} NaN/Inf values from data", stacklevel=2
            )

        if y is not None and _has_nan_or_inf(y):
            mask = ~(np.isnan(y) | np.isinf(y))
            removed = int((~mask).sum())
            if aligned:
                x = x[mask]
            y = y[mask]
            warnings.warn(
                f"Removed {removed} NaN/Inf values from data", stacklevel=2
            )

    # Final check
    if len(x) < min_points:
        raise ValueError(
            f"After cleaning, only {len(x)} points remain (need {min_points})"
        )

    return x, y
