"""Native array validation and cleaning, retaining historical input semantics."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

_Indices = tuple[tuple[str, tuple[int, ...]], ...]
_Issues = tuple[tuple[str, int, str], ...]


@dataclass(frozen=True)
class _PolicyDetails:
    """Complete immutable original-position accounting for one opt-in outcome."""

    policy: str
    alignment: str
    issues: _Issues
    removed_indices: _Indices
    kept_indices: _Indices
    proposed_removed_indices: _Indices
    failed: bool = False


def _diagnostic_text(details: _PolicyDetails) -> str:
    """Describe counts and at most ten original issue positions, never values."""
    counts = "; ".join(
        f"{name}: issues={sum(issue[0] == name for issue in details.issues)}, "
        f"removed={len(dict(details.removed_indices)[name])}, "
        f"kept={len(indices)}, "
        f"proposed_removed={len(dict(details.proposed_removed_indices)[name])}"
        for name, indices in details.kept_indices
    )
    shown = ", ".join(
        f"{name}[{index}]={kind}" for name, index, kind in details.issues[:10]
    )
    omitted = max(0, len(details.issues) - 10)
    # An aligned observation contributes once to the row total, even if both
    # arguments carry a nonfinite value at that position.
    rows = (
        len({index for _, index, _ in details.issues})
        if details.alignment == "aligned"
        else len(details.issues)
    )
    outcome = "rejected" if details.failed else "completed"
    return (
        f"Data policy {details.policy} {outcome} ({details.alignment}); "
        f"{counts}; affected rows={rows}; original indices: {shown}; "
        f"{omitted} issue indices omitted"
    )[:1024]


class _PolicyDiagnostic:
    """Expose tuple-backed diagnostic fields through read-only public properties."""

    _details: _PolicyDetails

    @property
    def policy(self) -> str:
        """Return the explicit policy selecting this outcome."""
        return self._details.policy

    @property
    def alignment(self) -> str:
        """Return whether original vectors were single, aligned or independent."""
        return self._details.alignment

    @property
    def issues(self) -> _Issues:
        """Return every nonfinite position, x then y in original index order."""
        return self._details.issues

    @property
    def removed_indices(self) -> _Indices:
        """Return committed removals, empty for retention and rejected outcomes."""
        return self._details.removed_indices

    @property
    def kept_indices(self) -> _Indices:
        """Return kept original positions, including all positions on rejection."""
        return self._details.kept_indices

    @property
    def proposed_removed_indices(self) -> _Indices:
        """Return candidate removals only when clean fails its surviving minimum."""
        return self._details.proposed_removed_indices


class DataPolicyError(_PolicyDiagnostic, ValueError):
    """Reject nonfinite data or an insufficient clean result with local diagnostics."""

    def __init__(self, details: _PolicyDetails) -> None:
        """Retain immutable diagnostic tuples and expose bounded safe error text."""
        self._details = details
        ValueError.__init__(self, _diagnostic_text(details))


class DataPolicyWarning(_PolicyDiagnostic, UserWarning):
    """Report successful explicit retention or removal of nonfinite observations."""

    def __init__(self, details: _PolicyDetails) -> None:
        """Retain immutable diagnostic tuples and expose bounded safe warning text."""
        self._details = details
        UserWarning.__init__(self, _diagnostic_text(details))


def _numeric_vector(
    value: Any, argument: str, policy: str
) -> np.ndarray[Any, Any]:
    """Parse an unmasked real numeric 1-D vector without coercion or cause disclosure."""
    scope = f"Data policy {policy}: {argument} requires an unmasked 1-D numeric vector (dtype kind i/u/f; counts unavailable)"
    if isinstance(value, np.ma.MaskedArray):
        raise ValueError(scope)
    try:
        result = np.asarray(value)
    except Exception:  # noqa: BLE001 — arbitrary array protocols can raise any exception.
        raise ValueError(
            f"Data policy {policy}: cannot convert {argument} to a supported numeric vector (counts unavailable)"
        ) from None
    if result.ndim != 1 or result.dtype.kind not in "iuf":
        raise ValueError(scope)
    return result


def _explicit_data_policy(
    x: Any,
    y: Any | None,
    require_same_length: bool,
    allow_nan: bool,
    min_points: int,
    policy: str,
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any] | None]:
    """Apply an opt-in numeric policy after validating all options and original shapes.

    Inputs are never written. Failures precede cleanup warnings; successful
    diagnostics describe complete original positions through immutable tuples.
    """
    # Bypass string-subclass presentation and equality hooks before use.
    policy = str.__str__(policy) if isinstance(policy, str) else ""
    if policy not in ("strict", "preserve", "clean"):
        raise ValueError(
            "Data policy must be None, strict, preserve or clean (counts unavailable)"
        )
    if allow_nan is not False:
        raise ValueError(
            f"Data policy {policy}: allow_nan must be the boolean False (counts unavailable)"
        )
    if type(require_same_length) is not bool:
        raise ValueError(
            f"Data policy {policy}: require_same_length must be bool (counts unavailable)"
        )
    if (
        isinstance(min_points, (bool, np.bool_, np.timedelta64))
        or not isinstance(min_points, (int, np.integer))
        or min_points <= 0
    ):
        raise ValueError(
            f"Data policy {policy}: min_points must be a positive integer excluding bool (counts unavailable)"
        )

    vectors = [("x", _numeric_vector(x, "x", policy))]
    if y is not None:
        vectors.append(("y", _numeric_vector(y, "y", policy)))
    aligned = len(vectors) == 2 and len(vectors[0][1]) == len(vectors[1][1])
    if y is not None and require_same_length and not aligned:
        raise ValueError(
            f"Data policy {policy}: original data length mismatch: x({len(vectors[0][1])}) != y({len(vectors[1][1])})"
        )
    for name, vector in vectors:
        if len(vector) < min_points:
            raise ValueError(
                f"Data policy {policy}: {name} has insufficient original points (count={len(vector)})"
            )

    finite = [np.isfinite(vector) for _, vector in vectors]
    if all(bool(mask.all()) for mask in finite):
        return vectors[0][1], vectors[1][1] if y is not None else None

    issues: list[tuple[str, int, str]] = []
    for (name, vector), mask in zip(vectors, finite, strict=True):
        for index in np.flatnonzero(~mask):
            kind = (
                "nan"
                if np.isnan(vector[index])
                else "posinf"
                if vector[index] > 0
                else "neginf"
            )
            issues.append((name, int(index), kind))
    empty = tuple((name, ()) for name, _ in vectors)
    original = tuple(
        (name, tuple(range(len(vector)))) for name, vector in vectors
    )
    alignment = (
        "single" if y is None else "aligned" if aligned else "independent"
    )
    details = _PolicyDetails(
        policy,
        alignment,
        tuple(issues),
        empty,
        original,
        empty,
        policy == "strict",
    )
    if policy == "strict":
        raise DataPolicyError(details)
    if policy == "preserve":
        warnings.warn(DataPolicyWarning(details), stacklevel=3)
        return vectors[0][1], vectors[1][1] if y is not None else None

    if aligned:
        union = finite[0] & finite[1]
        finite = [union, union]
    removed = tuple(
        (name, tuple(int(i) for i in np.flatnonzero(~mask)))
        for (name, _), mask in zip(vectors, finite, strict=True)
    )
    if any(int(mask.sum()) < min_points for mask in finite):
        raise DataPolicyError(
            _PolicyDetails(
                policy, alignment, tuple(issues), empty, original, removed, True
            )
        )
    kept = tuple(
        (name, tuple(int(i) for i in np.flatnonzero(mask)))
        for (name, _), mask in zip(vectors, finite, strict=True)
    )
    cleaned = [
        vector[mask] if not bool(mask.all()) else vector
        for (_, vector), mask in zip(vectors, finite, strict=True)
    ]
    warnings.warn(
        DataPolicyWarning(
            _PolicyDetails(
                policy, alignment, tuple(issues), removed, kept, empty
            )
        ),
        stacklevel=3,
    )
    return cleaned[0], cleaned[1] if y is not None else None


def validate_data(
    x: Any,
    y: Any | None = None,
    require_same_length: bool = True,
    allow_nan: bool = False,
    min_points: int = 2,
    *,
    policy: str | None = None,
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any] | None]:
    """Validate and clean input data for plotting.

    Parameters
    ----------
    x : Any
        X-axis data
    y : Any | None
        Y-axis data (optional for histograms, etc.)
    require_same_length : bool
        Whether x and y must have the same length. Originally equal-length
        inputs share removal masks; unequal inputs are cleaned independently.
    allow_nan : bool
        Whether to retain NaN/Inf values. The default filters them and aligned
        rows, which can close a missing-observation line gap. Use True for
        intentional gaps, with separate shape, alignment, infinity and domain
        checks; this option alone does not validate those properties.
    min_points : int
        Minimum number of data points required
    policy : str | None
        Opt into strict rejection, preserve retention, or clean removal of
        nonfinite values in unmasked numeric 1-D vectors. Explicit policies
        require allow_nan=False and validate each vector's minimum count.
        Nonfinite outcomes carry read-only original-index diagnostics through
        DataPolicyError or a single caller-level DataPolicyWarning. None keeps
        historical behavior, including supported shapes and warning semantics.

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
    if policy is not None:
        return _explicit_data_policy(
            x, y, require_same_length, allow_nan, min_points, policy
        )

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
    # when the original inputs are aligned (same length); when
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


# Preserve historical callable pickle resolution and public metadata.
validate_data.__module__ = "dartwork_mpl.helpers.data"
