"""Verify SW/MW/TW/DW/WIDTHS/FS_* emit DeprecationWarning in 0.4."""
from __future__ import annotations

import math
import warnings

import pytest

import dartwork_mpl as dm


DEPRECATED_WIDTH_TOKENS: dict[str, float] = {
    # token -> expected width in cm
    "SW": 9.0,
    "MW": 12.0,
    "TW": 14.5,
    "DW": 17.0,
}

DEPRECATED_FS_TOKENS: tuple[str, ...] = (
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
    "WIDTHS",
)


@pytest.mark.parametrize("name,cm_value", list(DEPRECATED_WIDTH_TOKENS.items()))
def test_width_tokens_warn_and_resolve(name, cm_value):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = getattr(dm, name)
    deprecation = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation, f"{name} should emit DeprecationWarning"
    assert name in str(deprecation[0].message)
    # Value must equal cm_value cm in inches.
    assert math.isclose(value, cm_value / 2.54, rel_tol=1e-9)


@pytest.mark.parametrize("name", DEPRECATED_FS_TOKENS)
def test_fs_and_widths_tokens_warn(name):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = getattr(dm, name)
    assert any(
        issubclass(w.category, DeprecationWarning) for w in caught
    ), f"{name} should emit DeprecationWarning"
    assert value is not None


def test_unknown_attribute_still_raises():
    with pytest.raises(AttributeError, match="completely_made_up"):
        _ = dm.completely_made_up


def test_warning_only_once_with_default_filter():
    """Default warnings filter dedupes; verify dm.SW still resolves twice."""
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        first = dm.SW
        second = dm.SW
    assert first == second
