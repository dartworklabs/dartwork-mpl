"""Comparison-report failure variants and their report.json shapes."""

from __future__ import annotations

import pytest

from dartwork_mpl._colors.verify import _comparison, _gates


def test_added_and_removed_leaves_report_the_absent_side_as_null() -> None:
    """Presence flags in report.json follow from the leaf's variant."""
    added = _comparison.AddedLeaf(path="/palette/x/0", candidate="#010203")
    removed = _comparison.RemovedLeaf(path="/palette/x/9", baseline=["a"])

    assert added.to_payload() == {
        "baseline": None,
        "baseline_present": False,
        "candidate": "#010203",
        "candidate_present": True,
        "path": "/palette/x/0",
    }
    assert removed.to_payload() == {
        "baseline": ["a"],
        "baseline_present": True,
        "candidate": None,
        "candidate_present": False,
        "path": "/palette/x/9",
    }


def test_a_present_null_leaf_differs_from_an_absent_one() -> None:
    """A JSON null that exists is not an absent leaf."""
    changed = _comparison.ChangedLeaf(path="/p", baseline=None, candidate=1)

    assert changed.to_payload()["baseline_present"] is True
    assert changed.to_payload()["baseline"] is None


def _threshold() -> _gates.ThresholdViolation:
    return _gates.ThresholdViolation(
        asset="amber",
        metric="/metrics/palette/amber/step_cv",
        rule="<=",
        observed=0.09,
        allowed=0.08,
        message="step CV regressed",
    )


@pytest.mark.parametrize(
    ("violation", "expected"),
    [
        (
            _comparison.QualityRegression(surface="palette", gate=_threshold()),
            {
                "asset": "amber",
                "baseline": 0.08,
                "candidate": 0.09,
                "code": "quality_regression",
                "message": "step CV regressed",
                "path": "/metrics/palette/amber/step_cv",
                "surface": "palette",
            },
        ),
        (
            _comparison.QualityRegression(
                surface="palette",
                gate=_gates.UnequalValues(
                    asset="amber", metric="/m", message="differs"
                ),
            ),
            {
                "asset": "amber",
                "baseline": 1.0,
                "candidate": 0.0,
                "code": "quality_regression",
                "message": "differs",
                "path": "/m",
                "surface": "palette",
            },
        ),
        (
            _comparison.QualityMetricInvalid(
                surface="palette",
                gate=_gates.InvalidMetric(
                    asset="amber", metric="/m", message="missing"
                ),
            ),
            {
                "asset": "amber",
                "baseline": 1.0,
                "candidate": 0.0,
                "code": "quality_metric_invalid",
                "message": "missing",
                "path": "/m",
                "surface": "palette",
            },
        ),
        (
            _comparison.CandidateQualityInvalid(
                gate=_gates.InvalidCandidate(message="ValueError: x")
            ),
            {
                "asset": "catalog",
                "baseline": 1.0,
                "candidate": 0.0,
                "code": "candidate_quality_invalid",
                "message": "ValueError: x",
                "path": "/candidate",
                "surface": "candidate",
            },
        ),
        (
            _comparison.ExactLeafMismatch(
                surface="palette",
                asset="amber",
                mismatch=_comparison.RemovedLeaf(
                    path="/palette/amber/9", baseline="#000000"
                ),
            ),
            {
                "asset": "amber",
                "baseline": "#000000",
                "candidate": None,
                "code": "exact_mismatch",
                "message": "candidate leaf differs from frozen v5",
                "path": "/palette/amber/9",
                "surface": "palette",
            },
        ),
    ],
    ids=[
        "regression",
        "unequal",
        "invalid-metric",
        "invalid-candidate",
        "exact",
    ],
)
def test_each_violation_variant_keeps_its_report_json_shape(
    violation: _comparison.Violation, expected: dict[str, object]
) -> None:
    """report.json keys and values are an output contract."""
    assert violation.to_payload() == expected


def test_violations_sort_by_code_then_location() -> None:
    """Reports list failures in one deterministic order."""
    exact = _comparison.ExactLeafMismatch(
        surface="palette",
        asset="amber",
        mismatch=_comparison.ChangedLeaf(path="/p", baseline=1, candidate=2),
    )
    regression = _comparison.QualityRegression(
        surface="palette", gate=_threshold()
    )
    invalid = _comparison.CandidateQualityInvalid(
        gate=_gates.InvalidCandidate(message="m")
    )

    ordered = sorted(
        (regression, exact, invalid), key=_comparison.violation_order
    )

    assert ordered == [invalid, exact, regression]
