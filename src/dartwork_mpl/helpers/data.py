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
) -> tuple[np.ndarray, np.ndarray | None]:
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
    if y is not None and require_same_length:
        if len(x) != len(y):
            raise ValueError(
                f"Data length mismatch: x({len(x)}) != y({len(y)})"
            )

    # Handle NaN/Inf values
    if not allow_nan:
        if np.any(np.isnan(x)) or np.any(np.isinf(x)):
            # Remove NaN/Inf
            mask = ~(np.isnan(x) | np.isinf(x))
            x = x[mask]
            if y is not None:
                y = y[mask]
            warnings.warn(
                f"Removed {(~mask).sum()} NaN/Inf values from data",
                stacklevel=2,
            )

        if y is not None:
            if np.any(np.isnan(y)) or np.any(np.isinf(y)):
                mask = ~(np.isnan(y) | np.isinf(y))
                x = x[mask]
                y = y[mask]
                warnings.warn(
                    f"Removed {(~mask).sum()} NaN/Inf values from data",
                    stacklevel=2,
                )

    # Final check
    if len(x) < min_points:
        raise ValueError(
            f"After cleaning, only {len(x)} points remain (need {min_points})"
        )

    return x, y
