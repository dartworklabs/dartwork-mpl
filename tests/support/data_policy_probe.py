"""Trusted synthetic acceptance probe shared by installed Python and MCP execution."""


def probe():
    """Assert native policy values, diagnostics, identity and unchanged caller storage."""
    import re
    import sys
    import warnings
    from pathlib import Path

    import numpy as np

    import dartwork_mpl as dm
    import dartwork_mpl.validate as validation
    from dartwork_mpl.helpers import validate_data as legacy_alias

    package = Path(dm.__file__).resolve()
    assert package.is_relative_to(Path(sys.prefix).resolve()), package
    assert "site-packages" in package.parts, package
    assert dm.validate_data is validation.validate_data is legacy_alias
    assert dm.DataPolicyError is validation.DataPolicyError
    assert dm.DataPolicyWarning is validation.DataPolicyWarning
    assert issubclass(dm.DataPolicyError, ValueError)
    assert issubclass(dm.DataPolicyWarning, UserWarning)

    finite = np.arange(12, dtype=np.float32)[::2]
    finite.setflags(write=False)
    original = finite.copy()
    for policy in ("strict", "preserve", "clean"):
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter("always")
            pair = dm.validate_data(finite, policy=policy)
        assert type(pair) is tuple and len(pair) == 2
        assert pair[0] is finite and pair[1] is None
        assert pair[0].dtype == finite.dtype
        assert pair[0].strides == finite.strides
        assert np.shares_memory(pair[0], finite)
        assert not notices
    np.testing.assert_array_equal(finite, original)

    x = np.array([0.0, np.nan, 2.0, 3.0, 4.0])
    y = np.array([10.0, 11.0, np.inf, 13.0, 14.0])
    x.setflags(write=False)
    y.setflags(write=False)
    original_x, original_y = x.copy(), y.copy()
    issues = (("x", 1, "nan"), ("y", 2, "posinf"))
    all_indices = (("x", (0, 1, 2, 3, 4)), ("y", (0, 1, 2, 3, 4)))
    empty = (("x", ()), ("y", ()))
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        try:
            dm.validate_data(x, y, policy="strict")
        except dm.DataPolicyError as error:
            assert error.policy == "strict"
            assert error.alignment == "aligned"
            assert error.issues == issues
            assert error.removed_indices == empty
            assert error.kept_indices == all_indices
            assert error.proposed_removed_indices == empty
            assert len(str(error)) <= 1024
        else:
            raise AssertionError("strict accepted nonfinite observations")
    assert not notices

    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        preserved = dm.validate_data(x, y, policy="preserve")
    assert type(preserved) is tuple and len(preserved) == 2
    assert preserved[0] is x and preserved[1] is y
    assert len(notices) == 1
    diagnostic = notices[0].message
    assert isinstance(diagnostic, dm.DataPolicyWarning)
    assert diagnostic.policy == "preserve"
    assert diagnostic.alignment == "aligned"
    assert diagnostic.issues == issues
    assert diagnostic.removed_indices == empty
    assert diagnostic.kept_indices == all_indices
    assert diagnostic.proposed_removed_indices == empty
    assert "site-packages" not in Path(notices[0].filename).parts

    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        cleaned = dm.validate_data(
            x, y, require_same_length=False, policy="clean"
        )
    assert type(cleaned) is tuple and len(cleaned) == 2
    np.testing.assert_array_equal(cleaned[0], [0.0, 3.0, 4.0])
    np.testing.assert_array_equal(cleaned[1], [10.0, 13.0, 14.0])
    assert cleaned[0].dtype == x.dtype and cleaned[1].dtype == y.dtype
    assert not np.shares_memory(cleaned[0], x)
    assert not np.shares_memory(cleaned[1], y)
    assert len(notices) == 1
    diagnostic = notices[0].message
    assert isinstance(diagnostic, dm.DataPolicyWarning)
    assert diagnostic.policy == "clean" and diagnostic.alignment == "aligned"
    assert diagnostic.issues == issues
    assert diagnostic.removed_indices == (("x", (1, 2)), ("y", (1, 2)))
    assert diagnostic.kept_indices == (("x", (0, 3, 4)), ("y", (0, 3, 4)))
    assert diagnostic.proposed_removed_indices == empty
    assert len(str(diagnostic)) <= 1024
    np.testing.assert_array_equal(x, original_x)
    np.testing.assert_array_equal(y, original_y)

    independent_x = np.array([0.0, np.nan, 2.0, np.inf, 4.0])
    independent_y = np.array([10, 11, 12], dtype=np.uint16)
    before_x, before_y = independent_x.copy(), independent_y.copy()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        independent = dm.validate_data(
            independent_x,
            independent_y,
            require_same_length=False,
            policy="clean",
        )
    np.testing.assert_array_equal(independent[0], [0, 2, 4])
    assert independent[1] is independent_y
    diagnostic = notices[0].message
    assert len(notices) == 1 and diagnostic.alignment == "independent"
    assert diagnostic.issues == (("x", 1, "nan"), ("x", 3, "posinf"))
    assert diagnostic.removed_indices == (("x", (1, 3)), ("y", ()))
    assert diagnostic.kept_indices == (("x", (0, 2, 4)), ("y", (0, 1, 2)))
    np.testing.assert_array_equal(independent_x, before_x)
    np.testing.assert_array_equal(independent_y, before_y)

    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        try:
            dm.validate_data(x, y, min_points=4, policy="clean")
        except dm.DataPolicyError as error:
            assert error.policy == "clean" and error.alignment == "aligned"
            assert error.issues == issues
            assert error.removed_indices == empty
            assert error.kept_indices == all_indices
            assert error.proposed_removed_indices == (
                ("x", (1, 2)),
                ("y", (1, 2)),
            )
        else:
            raise AssertionError("clean accepted too few surviving points")
    assert not notices

    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        legacy = dm.validate_data(x, y)
    assert type(legacy) is tuple and len(legacy) == 2
    np.testing.assert_array_equal(legacy[0], [0, 3, 4])
    np.testing.assert_array_equal(legacy[1], [10, 13, 14])
    assert len(notices) == 2
    assert all(not isinstance(n.message, dm.DataPolicyWarning) for n in notices)
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        legacy_preserved = dm.validate_data(x, y, allow_nan=True)
    assert legacy_preserved[0] is x and legacy_preserved[1] is y
    assert not notices
    np.testing.assert_array_equal(x, original_x)
    np.testing.assert_array_equal(y, original_y)

    many = np.concatenate((np.full(1000, np.nan), [1.0, 2.0]))
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        result = dm.validate_data(many, policy="preserve")
    assert result[0] is many and len(notices) == 1
    diagnostic = notices[0].message
    assert diagnostic.issues == tuple(
        ("x", index, "nan") for index in range(1000)
    )
    assert diagnostic.removed_indices == (("x", ()),)
    assert diagnostic.kept_indices == (("x", tuple(range(1002))),)
    assert diagnostic.proposed_removed_indices == (("x", ()),)
    assert diagnostic.alignment == "single"
    assert len(str(diagnostic)) <= 1024
    assert "preserve" in str(diagnostic) and "1000" in str(diagnostic)
    assert len(re.findall(r"[xy]\[\d+\]", str(diagnostic))) <= 10
    assert "990" in str(diagnostic) and "omitted" in str(diagnostic)

    for policy in ("strict", "preserve", "clean"):
        try:
            dm.validate_data(x, allow_nan=True, policy=policy)
        except ValueError:  # noqa: PERF203 -- each policy must reject the conflict
            pass
        else:
            raise AssertionError(
                "explicit policy silently accepted allow_nan=True"
            )
    for unsupported in (np.array(3.0), np.array([1, 2], dtype=object)):
        try:
            dm.validate_data(unsupported, policy="preserve")
        except ValueError as error:  # noqa: PERF203 -- each scope must reject
            assert "x" in str(error)
        else:
            raise AssertionError(
                "explicit policy accepted unsupported data scope"
            )
    for invalid_minimum in (np.timedelta64(2, "D"), np.timedelta64("NaT")):
        try:
            dm.validate_data(finite, policy="clean", min_points=invalid_minimum)
        except ValueError as error:  # noqa: PERF203 -- temporal integers are not counts
            assert "min_points" in str(error)
        else:
            raise AssertionError("temporal scalar was accepted as min_points")
    return {
        "package": str(package),
        "policies": ["strict", "preserve", "clean", "omitted"],
    }
