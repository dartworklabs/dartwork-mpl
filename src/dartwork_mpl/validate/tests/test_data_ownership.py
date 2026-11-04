"""Native validation retains historical callable and array contracts after ownership moves."""

import inspect
import pickle
import typing
import warnings

import numpy as np
import pytest

import dartwork_mpl as dm
import dartwork_mpl.helpers as helpers
import dartwork_mpl.helpers.data as old
import dartwork_mpl.validate as owner


def test_owner_surface_preserves_historical_callable_and_metadata():
    """All import paths and a pre-move pickle resolve to the same native callable."""
    f = getattr(owner, "validate_data", None)
    assert f is old.validate_data is helpers.validate_data is dm.validate_data
    assert f.__module__ == "dartwork_mpl.helpers.data"
    assert f.__name__ == f.__qualname__ == "validate_data"
    assert (
        str(inspect.signature(f))
        == "(x: 'Any', y: 'Any | None' = None, require_same_length: 'bool' = True, allow_nan: 'bool' = False, min_points: 'int' = 2) -> 'tuple[np.ndarray[Any, Any], np.ndarray[Any, Any] | None]'"
    )
    assert f.__defaults__ == (None, True, False, 2)
    assert f.__annotations__ == {
        "x": "Any",
        "y": "Any | None",
        "require_same_length": "bool",
        "allow_nan": "bool",
        "min_points": "int",
        "return": "tuple[np.ndarray[Any, Any], np.ndarray[Any, Any] | None]",
    }
    assert typing.get_type_hints(f) == {
        "x": typing.Any,
        "y": typing.Any | None,
        "require_same_length": bool,
        "allow_nan": bool,
        "min_points": int,
        "return": tuple[
            np.ndarray[typing.Any, typing.Any],
            np.ndarray[typing.Any, typing.Any] | None,
        ],
    }
    for namespace in (dm, helpers, owner):
        assert namespace.__all__.count("validate_data") == 1
    assert old.__all__ == ["validate_data"]
    assert (
        pickle.loads(
            bytes.fromhex(
                "8004952f000000000000008c1964617274776f726b5f6d706c2e68656c706572732e64617461948c0d76616c69646174655f646174619493942e"
            )
        )
        is f
    )


def test_cleanup_warnings_point_to_direct_caller_in_order():
    """A wrapper must not shift either cleanup warning away from the caller."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        old.validate_data([1, np.nan, 2, 3], [1, 4, np.nan, 3])
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
    rx, ry = old.validate_data(x, x)
    assert rx is ry is x
    assert np.shares_memory(rx, x)
    assert rx.strides == (8,)
    np.testing.assert_array_equal(x, before)


def test_object_none_and_nan_are_preserved_without_cleanup():
    """Object arrays retain their None/NaN entries and do not emit numeric warnings."""
    x = np.array([1, None, np.nan, "A"], dtype=object)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rx, ry = old.validate_data(x)
    assert rx is x and ry is None
    assert rx[1] is None and np.isnan(rx[2]) and rx[3] == "A"
    assert not caught


def test_multidimensional_cleanup_keeps_flattening_and_partner_error():
    """Historical 2-D masks flatten x alone and reject an incompatible partner."""
    x = np.array([[1, np.nan], [2, 3.0]])
    with pytest.warns(UserWarning, match="Removed 1 NaN/Inf"):
        rx, ry = old.validate_data(x)
    np.testing.assert_array_equal(rx, [1, 2, 3])
    assert ry is None
    with pytest.raises(IndexError, match="too many indices"):
        old.validate_data(x, np.array([1.0, 2.0]))
