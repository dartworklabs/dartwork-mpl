"""Opt-in numeric data policies expose original positions without altering inputs."""

import inspect
import re
import warnings

import numpy as np
import pytest

import dartwork_mpl as dm
import dartwork_mpl.helpers as helpers
import dartwork_mpl.validate as owner


@pytest.mark.parametrize("policy", ["strict", "preserve", "clean"])
@pytest.mark.parametrize("dtype", [np.int16, np.uint32, np.float32, np.float64])
def test_finite_strided_vectors_retain_identity_dtype_and_storage(
    policy, dtype
):
    """No-removal success preserves exact ndarray identity and storage properties."""
    x = np.arange(12, dtype=dtype)[::-2]
    with warnings.catch_warnings(record=True) as caught:
        result = dm.validate_data(x, x, policy=policy)
    assert isinstance(result, tuple) and len(result) == 2
    assert result[0] is result[1] is x
    assert result[0].dtype == dtype and result[0].strides == x.strides
    assert np.shares_memory(result[0], x)
    assert not caught


def test_strict_rejects_all_original_nonfinite_positions_without_warning():
    """Strict rejection records x then y in original order and performs no cleanup."""
    x = np.array([np.nan, 1, np.inf, 3, -np.inf])
    y = np.array([2, -np.inf, 4, np.nan, 6])
    before = (x.copy(), y.copy())
    with warnings.catch_warnings(record=True) as caught:
        with pytest.raises(dm.DataPolicyError) as rejected:
            dm.validate_data(x, y, policy="strict")
    error = rejected.value
    assert isinstance(error, ValueError)
    assert error.policy == "strict" and error.alignment == "aligned"
    assert error.issues == (
        ("x", 0, "nan"),
        ("x", 2, "posinf"),
        ("x", 4, "neginf"),
        ("y", 1, "neginf"),
        ("y", 3, "nan"),
    )
    assert (
        error.removed_indices
        == error.proposed_removed_indices
        == (("x", ()), ("y", ()))
    )
    assert error.kept_indices == (
        ("x", (0, 1, 2, 3, 4)),
        ("y", (0, 1, 2, 3, 4)),
    )
    assert not caught
    np.testing.assert_array_equal(x, before[0])
    np.testing.assert_array_equal(y, before[1])


def test_preserve_keeps_nan_and_infinities_and_warns_at_caller():
    """Retention preserves all numeric values and reports a single caller warning."""
    x = np.array([np.nan, np.inf, -np.inf, 1])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        result = dm.validate_data(x, policy="preserve")
    assert result == (x, None)
    assert len(caught) == 1
    warning = caught[0]
    assert warning.filename == __file__ and warning.lineno == line
    assert isinstance(warning.message, dm.DataPolicyWarning)
    assert warning.message.policy == "preserve"
    assert warning.message.alignment == "single"
    assert warning.message.kept_indices == (("x", (0, 1, 2, 3)),)
    assert (
        warning.message.removed_indices
        == warning.message.proposed_removed_indices
        == (("x", ()),)
    )


def test_clean_aligned_union_records_finite_partner_removals():
    """Equal original lengths share the complete union even with length checks off."""
    x = np.array([0, np.nan, 2, 3, 4.0])
    y = np.array([10, 11, np.inf, 13, 14.0])
    with pytest.warns(dm.DataPolicyWarning) as caught:
        rx, ry = dm.validate_data(
            x, y, require_same_length=False, policy="clean"
        )
    np.testing.assert_array_equal(rx, [0, 3, 4])
    np.testing.assert_array_equal(ry, [10, 13, 14])
    record = caught[0].message
    assert record.removed_indices == (("x", (1, 2)), ("y", (1, 2)))
    assert record.kept_indices == (("x", (0, 3, 4)), ("y", (0, 3, 4)))
    assert record.proposed_removed_indices == (("x", ()), ("y", ()))
    assert record.issues == (("x", 1, "nan"), ("y", 2, "posinf"))
    assert len(caught) == 1


def test_clean_unequal_original_vectors_stay_independent_when_sizes_converge():
    """Cleaning one vector cannot create alignment with an originally unequal peer."""
    x = np.array([1, np.nan, 2, 3.0])
    y = np.array([10, np.inf, 30.0])
    with pytest.warns(dm.DataPolicyWarning) as caught:
        rx, ry = dm.validate_data(
            x, y, require_same_length=False, policy="clean"
        )
    np.testing.assert_array_equal(rx, [1, 2, 3])
    np.testing.assert_array_equal(ry, [10, 30])
    assert caught[0].message.alignment == "independent"
    assert caught[0].message.kept_indices == (("x", (0, 2, 3)), ("y", (0, 2)))


def test_failed_clean_proposes_masks_without_claiming_success_or_warning():
    """A rejected candidate exposes complete proposed removal while retaining original records."""
    x = np.array([0, np.nan, 2.0])
    y = np.array([10, 11, np.inf])
    with warnings.catch_warnings(record=True) as caught:
        with pytest.raises(dm.DataPolicyError) as rejected:
            dm.validate_data(x, y, policy="clean")
    record = rejected.value
    assert record.removed_indices == (("x", ()), ("y", ()))
    assert record.kept_indices == (("x", (0, 1, 2)), ("y", (0, 1, 2)))
    assert record.proposed_removed_indices == (("x", (1, 2)), ("y", (1, 2)))
    assert record.issues == (("x", 1, "nan"), ("y", 2, "posinf"))
    assert not caught
    np.testing.assert_array_equal(x, [0, np.nan, 2])
    np.testing.assert_array_equal(y, [10, 11, np.inf])


@pytest.mark.parametrize("policy", ["strict", "preserve", "clean"])
def test_independent_y_must_meet_original_minimum(policy):
    """Opt-in minimum validation applies separately to every supplied vector."""
    with pytest.raises(ValueError, match="y"):
        dm.validate_data(
            [1, 2, 3], [1], require_same_length=False, policy=policy
        )


@pytest.mark.parametrize("value", [True, np.bool_(False), 0, "false", None])
@pytest.mark.parametrize("policy", ["strict", "preserve", "clean"])
def test_explicit_allow_nan_requires_exact_false_before_input_inspection(
    value, policy
):
    """No boolean conflict or false-like placeholder silently overrides policy."""
    with pytest.raises(ValueError, match="allow_nan"):
        dm.validate_data(ExplosiveArray(), allow_nan=value, policy=policy)


@pytest.mark.parametrize(
    "options",
    [
        {"policy": "STRICT"},
        {"policy": []},
        {"policy": np.array(["clean", "strict"])},
        {"policy": "clean", "require_same_length": 1},
        {"policy": "clean", "require_same_length": np.bool_(True)},
        {"policy": "clean", "min_points": True},
        {"policy": "clean", "min_points": 0},
        {"policy": "clean", "min_points": 1.5},
    ],
)
def test_invalid_options_raise_safe_value_error_before_conversion(options):
    """Unknown policies and malformed options are rejected without rendering input."""
    with pytest.raises(ValueError) as caught:
        dm.validate_data(ExplosiveArray(), **options)
    assert "SECRET" not in str(caught.value)
    assert len(str(caught.value)) <= 1024


class ExplosiveArray:
    """A conversion failure whose private cause must never enter diagnostics."""

    def __array__(self, *args, **kwargs):
        """Raise an exception containing a synthetic sensitive payload."""
        raise RuntimeError("SECRET-conversion-payload")

    def __repr__(self):
        """Make accidental interpolation observable."""
        return "SECRET-repr-payload"


@pytest.mark.parametrize("policy", ["strict", "preserve", "clean"])
@pytest.mark.parametrize(
    "minimum", [np.timedelta64(1, "D"), np.timedelta64("NaT")]
)
def test_temporal_scalar_cannot_bypass_positive_integer_minimum(
    policy, minimum
):
    """NumPy's integer-subclass timedeltas cannot disable minimum-count checks."""
    with warnings.catch_warnings(record=True) as caught:
        with pytest.raises(ValueError, match="min_points"):
            dm.validate_data(
                [np.nan, np.inf], policy=policy, min_points=minimum
            )
    assert not caught


def test_conversion_failure_suppresses_private_cause_and_repr():
    """Conversion errors expose only a safe argument-specific message."""
    with pytest.raises(ValueError, match="x") as caught:
        dm.validate_data(ExplosiveArray(), policy="clean")
    assert "SECRET" not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


@pytest.mark.parametrize(
    "value",
    [
        np.ma.array([1, 2, 3], mask=[0, 1, 0]),
        np.array([1, None], dtype=object),
        ["1", "2"],
        [True, False],
        [1j, 2j],
        np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[D]"),
        [[1, 2], [3, 4]],
        1,
    ],
)
@pytest.mark.parametrize("argument", ["x", "y"])
def test_unsupported_scope_is_rejected_for_each_argument(value, argument):
    """Opt-in mode never discards masks, casts unsupported dtypes, or flattens dimensions."""
    kwargs = {argument: value}
    if argument == "y":
        kwargs["x"] = [1, 2]
    with pytest.raises(ValueError, match=argument):
        dm.validate_data(**kwargs, policy="clean")


def test_length_error_precedes_policy_cleanup_and_numpy_integer_threshold_is_valid():
    """Original lengths determine validity before nonfinite policy work."""
    with pytest.raises(ValueError, match="length"):
        dm.validate_data([np.nan, 2], [1, 2, 3], policy="strict")
    result = dm.validate_data([1, 2], min_points=np.int64(2), policy="strict")
    np.testing.assert_array_equal(result[0], [1, 2])


def test_clean_only_copies_vectors_requiring_removal():
    """Independent finite peers keep identity when another vector needs cleaning."""
    x = np.array([1, 2.0])
    y = np.array([3, np.nan, 4.0])
    with pytest.warns(dm.DataPolicyWarning):
        rx, ry = dm.validate_data(
            x, y, require_same_length=False, policy="clean"
        )
    assert rx is x and not np.shares_memory(ry, y)


def test_diagnostics_are_complete_immutable_bounded_and_public_only_on_owners():
    """Large local records remain complete while text limits disclosure and output size."""
    x = np.full(5000, np.nan)
    with pytest.raises(dm.DataPolicyError) as caught:
        dm.validate_data(x, policy="strict")
    record = caught.value
    assert len(record.issues) == len(record.kept_indices[0][1]) == 5000
    assert "strict" in str(record) and "5000" in str(record)
    assert "4990" in str(record) and "omitted" in str(record)
    assert len(str(record)) <= 1024
    assert len(re.findall(r"[xy]\[\d+\]", str(record))) == 10
    for name in (
        "policy",
        "alignment",
        "issues",
        "removed_indices",
        "kept_indices",
        "proposed_removed_indices",
    ):
        with pytest.raises(AttributeError):
            setattr(record, name, ())
    assert isinstance(record.issues, tuple) and isinstance(
        record.issues[0], tuple
    )
    assert dm.DataPolicyError is owner.DataPolicyError
    assert dm.DataPolicyWarning is owner.DataPolicyWarning
    for name in ("DataPolicyError", "DataPolicyWarning"):
        assert dm.__all__.count(name) == owner.__all__.count(name) == 1
        assert not hasattr(helpers, name)


def test_seeded_masks_preserve_original_order_input_storage_and_partition():
    """Generated equal and unequal inputs obey union masks and exact index partitions."""
    rng = np.random.default_rng(20261104)
    for aligned in (True, False):
        for _ in range(40):
            size = int(rng.integers(4, 35))
            x = rng.normal(size=size)
            y = rng.normal(size=size if aligned else size + 1)
            x[rng.integers(0, size)] = np.nan
            y[rng.integers(0, len(y))] = rng.choice([np.inf, -np.inf])
            before = (x.copy(), y.copy())
            finite_x, finite_y = np.isfinite(x), np.isfinite(y)
            expected_x = finite_x & finite_y if aligned else finite_x
            expected_y = expected_x if aligned else finite_y
            with pytest.warns(dm.DataPolicyWarning) as caught:
                rx, ry = dm.validate_data(
                    x, y, require_same_length=False, policy="clean"
                )
            np.testing.assert_array_equal(rx, x[expected_x])
            np.testing.assert_array_equal(ry, y[expected_y])
            np.testing.assert_array_equal(x, before[0])
            np.testing.assert_array_equal(y, before[1])
            record = caught[0].message
            for name, original, valid in (
                ("x", x, expected_x),
                ("y", y, expected_y),
            ):
                removed = dict(record.removed_indices)[name]
                kept = dict(record.kept_indices)[name]
                assert set(removed).isdisjoint(kept)
                assert sorted((*removed, *kept)) == list(range(len(original)))
                assert kept == tuple(np.flatnonzero(valid))


class SensitivePolicy(str):
    """A valid string value with hostile presentation hooks must remain safe."""

    def __format__(self, spec):
        """Expose accidental use of caller-controlled formatting."""
        return "SECRET-policy-format-" * 200

    def __str__(self):
        """Expose accidental use of caller-controlled string conversion."""
        return "SECRET-policy-string"


def test_policy_string_subclass_never_controls_diagnostic_text():
    """Accepted policy values are normalized before any diagnostic formatting."""
    with pytest.raises(ValueError) as caught:
        dm.validate_data(
            [1, 2], allow_nan=True, policy=SensitivePolicy("strict")
        )
    assert "SECRET" not in str(caught.value)
    assert len(str(caught.value)) <= 1024
    with pytest.raises(dm.DataPolicyError) as caught:
        dm.validate_data([np.nan, 2], policy=SensitivePolicy("strict"))
    assert type(caught.value.policy) is str
    assert caught.value.policy == "strict"
    assert "SECRET" not in str(caught.value)


def test_failed_independent_clean_checks_y_survivors_and_original_indices():
    """A sufficient x cannot conceal an independent y falling below its minimum."""
    x = np.array([1, 2, 3, 4.0])
    y = np.array([1, np.nan, np.inf])
    with warnings.catch_warnings(record=True) as caught:
        with pytest.raises(dm.DataPolicyError) as rejected:
            dm.validate_data(x, y, require_same_length=False, policy="clean")
    assert not caught
    record = rejected.value
    assert record.alignment == "independent"
    assert record.removed_indices == (("x", ()), ("y", ()))
    assert record.proposed_removed_indices == (("x", ()), ("y", (1, 2)))
    assert record.kept_indices == (("x", (0, 1, 2, 3)), ("y", (0, 1, 2)))


def test_aligned_diagnostic_row_count_deduplicates_shared_issues():
    """Two nonfinite values in the same original row count as one affected row."""
    with pytest.warns(dm.DataPolicyWarning) as caught:
        dm.validate_data([1, np.nan, 3], [1, np.inf, 3], policy="clean")
    assert "affected rows=1;" in str(caught[0].message)
    assert caught[0].message.removed_indices == (("x", (1,)), ("y", (1,)))
