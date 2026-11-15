"""``validate_data`` array and warning contracts."""

import inspect
import warnings

import numpy as np
import pytest

import dartwork_mpl.validate as owner


def test_cleanup_warnings_point_to_direct_caller_in_order():
    """A wrapper must not shift either cleanup warning away from the caller."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        owner.validate_data([1, np.nan, 2, 3], [1, 4, np.nan, 3])
    assert [
        (w.category, str(w.message), w.filename, w.lineno) for w in caught
    ] == [
        (UserWarning, "Removed 1 NaN/Inf values from data", __file__, line),
        (UserWarning, "Removed 1 NaN/Inf values from data", __file__, line),
    ]


def test_noncontiguous_arrays_keep_identity_and_storage():
    """Finite strided arrays are returned without copying or changing their strides."""
    x = np.arange(12, dtype=np.float32)[::2]
    before = x.copy()
    rx, ry = owner.validate_data(x, x)
    assert rx is ry is x
    assert np.shares_memory(rx, x)
    assert rx.strides == (8,)
    np.testing.assert_array_equal(x, before)


def test_object_none_and_nan_are_preserved_without_cleanup():
    """Object arrays retain their None/NaN entries and do not emit numeric warnings."""
    x = np.array([1, None, np.nan, "A"], dtype=object)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rx, ry = owner.validate_data(x)
    assert rx is x and ry is None
    assert rx[1] is None and np.isnan(rx[2]) and rx[3] == "A"
    assert not caught


def test_multidimensional_cleanup_keeps_flattening_and_partner_error():
    """Historical 2-D masks flatten x alone and reject an incompatible partner."""
    x = np.array([[1, np.nan], [2, 3.0]])
    with pytest.warns(UserWarning, match="Removed 1 NaN/Inf"):
        rx, ry = owner.validate_data(x)
    np.testing.assert_array_equal(rx, [1, 2, 3])
    assert ry is None
    with pytest.raises(IndexError, match="too many indices"):
        owner.validate_data(x, np.array([1.0, 2.0]))
