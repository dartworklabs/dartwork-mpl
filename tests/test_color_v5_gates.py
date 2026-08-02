"""Tests for colors._gates — A7 hard gates."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import cast

import pytest

from dartwork_mpl._colors import _compatibility_metrics as oracle
from dartwork_mpl._colors import _gates, _ssot
from dartwork_mpl._colors._catalog import (
    CatalogSnapshot,
    compile_candidate_snapshot,
)
from dartwork_mpl._colors._gates import (
    GateReport,
    GateViolation,
    check_all,
    gate_cycle,
    gate_cyclic_cmap,
    gate_div_cmap,
    gate_ladder,
    gate_seq_cmap,
    load_quality_baseline,
)
from dartwork_mpl._colors._ssot import load_color_v6_ssot


@pytest.fixture(scope="module")
def candidate_catalog() -> CatalogSnapshot:
    """Compile the live candidate exactly once for all mutation gates."""
    return compile_candidate_snapshot()


@pytest.fixture(scope="module")
def quality_baseline() -> Mapping[str, object]:
    """Load the independently pinned raw v5 quality authority."""
    return load_quality_baseline()


def test_row_contracts_use_validated_v6_accessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load gate contracts without a second repo-relative SSOT file path."""
    authority = load_color_v6_ssot()
    calls = 0

    def load_authority() -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return authority

    monkeypatch.setattr(_ssot, "load_color_v6_ssot", load_authority)
    monkeypatch.setattr(
        _gates,
        "_V6_SSOT_PATH",
        Path("/does-not-exist/color_v6_ssot.json"),
        raising=False,
    )

    contracts = _gates._load_row_contracts()

    assert calls == 1
    assert contracts is authority["row_contracts"]


def _mapping(value: object, label: str) -> Mapping[str, object]:
    """Narrow one string-keyed baseline mapping for test expectations."""
    assert isinstance(value, Mapping), label
    assert all(isinstance(key, str) for key in value), label
    return cast(Mapping[str, object], value)


def _baseline_number(baseline: Mapping[str, object], *path: str) -> float:
    """Read one finite non-boolean raw number from the pinned baseline."""
    value: object = baseline
    for component in path:
        value = _mapping(value, ".".join(path))[component]
    assert isinstance(value, int | float) and not isinstance(value, bool)
    result = float(value)
    assert math.isfinite(result)
    return result


def _with_row(
    rows: Mapping[str, Sequence[str]], name: str, row: Sequence[str]
) -> dict[str, tuple[str, ...]]:
    """Return a detached named-row mapping with one replacement."""
    return {
        row_name: tuple(row if row_name == name else values)
        for row_name, values in rows.items()
    }


def _require_violation(
    report: GateReport, *, asset: str, metric: str, rule: str
) -> GateViolation:
    """Select one named failure and enforce its raw numeric contract."""
    matches = tuple(
        violation
        for violation in report.violations
        if violation.asset == asset and violation.metric == metric
    )
    assert len(matches) == 1, report.violations
    violation = matches[0]
    assert violation.rule == rule
    assert violation.message
    assert math.isfinite(violation.observed)
    assert math.isfinite(violation.allowed)
    return violation


def test_palette_ladders_pass(v5_ssot):
    for fam, row in v5_ssot["palette"].items():
        g = gate_ladder(row)
        assert g["mono"], fam
        assert g["cv"] <= 0.08, (fam, g["cv"])


def test_historical_cycle_search_floors_pass(v5_ssot):
    pal = v5_ssot["palette"]
    hexes = [pal[f][k] for f, k in v5_ssot["cycle_default"]["spec"]]
    g = gate_cycle(hexes)
    assert g["common_min"] >= 10.0  # historical Octave search criterion
    assert g["tritan"] >= 8.0  # historical Octave tritan search criterion


def test_gate_detects_violations():
    # 인위 실패: 비단조 사다리
    bad = ["#f0f0f0", "#101010", "#e0e0e0"] + ["#808080"] * 7
    assert not gate_ladder(bad)["mono"]
    # 인위 실패: 붕괴 cycle (tab10류 red-green) — deutan에서 common 게이트 실패
    assert gate_cycle(["#d62728", "#2ca02c", "#1f77b4"])["common_min"] < 10.0


def test_check_all_uses_frozen_cycle_baseline_despite_rounding(
    v5_ssot, quality_baseline: Mapping[str, object]
) -> None:
    """Use the known Octave baseline, not an unknown-asset or 10/8 gate.

    ``gate_cycle`` rounds its display floors to 1 decimal, so a true minimum of
    9.9626 rounds up to 10.0. ``check_all`` must compare the unrounded result to
    Octave's frozen per-asset baseline rather than the historical 10/8 search
    criteria. This fixture must use a known alias so that an unknown-asset
    failure cannot mask the metric assertion.
    """
    pal = v5_ssot["palette"]
    shipped = {
        "cycle_default": [
            pal[f][k] for f, k in v5_ssot["cycle_default"]["spec"]
        ],
        "cycle_print": [pal[f][k] for f, k in v5_ssot["cycle_print"]["spec"]],
    }
    # ["#333333", "#515151"]: common-CVD min ≈ 9.9626 → rounds to 10.0.
    probe = ["#333333", "#515151"]
    g = gate_cycle(probe)
    assert g["common_min"] == 10.0  # rounded display hides the sub-floor
    assert 9.95 <= g["common_min_raw"] < 10.0  # raw exposes it

    common_baseline = _baseline_number(
        quality_baseline, "metrics", "cycles", "octave", "common_min_delta_e00"
    )
    tritan_baseline = _baseline_number(
        quality_baseline, "metrics", "cycles", "octave", "tritan_min_delta_e00"
    )
    assert common_baseline > 10.0
    assert tritan_baseline > 8.0

    baseline_metrics = _mapping(quality_baseline["metrics"], "metrics")
    baseline_cycles = _mapping(baseline_metrics["cycles"], "cycles")
    candidate_quality = oracle.categorical_quality(probe)
    report = GateReport(
        violations=_gates.evaluate_quality_metrics(
            {"cycles": {"octave": baseline_cycles["octave"]}},
            {"cycles": {"octave": candidate_quality}},
            {},
        )
    )
    violation = _require_violation(
        report,
        asset="octave",
        metric="/metrics/cycles/octave/common_min_delta_e00",
        rule=">=",
    )
    assert violation.observed == g["common_min_raw"]
    assert violation.allowed == common_baseline

    assert check_all({}, shipped, {}) == []
    failures = check_all({}, {"cycle_default": probe}, {})
    assert failures
    assert all("no frozen asset baseline" not in item for item in failures)
    assert any(
        "/metrics/cycles/octave/common_min_delta_e00" in item
        and f": {g['common_min_raw']} >= {common_baseline}" in item
        for item in failures
    )


def test_cmap_gates_pass_ssot(v5_ssot):
    sw = v5_ssot["colormaps"]["swatches_32"]
    gexp = v5_ssot["colormaps"]["gates"]
    for name, hexes in sw.items():
        exp = gexp[name]
        if "apex_pct" in exp:
            assert gate_div_cmap(hexes)["apex_pct"] == 50.0, name
        elif "seam_ratio" in exp:
            assert gate_cyclic_cmap(hexes)["seam_ratio"] <= 1.5, name
        else:
            g = gate_seq_cmap(hexes)
            assert g["mono"] and g["gray_mono"], name


def test_gate_violation_is_frozen_sortable_and_raw() -> None:
    """Keep shared gate decisions deterministic and mutation-proof."""
    later = GateViolation(
        asset="zeta",
        metric="/metric/zeta",
        observed=2.0,
        allowed=1.0,
        rule="<=",
        message="zeta regressed",
    )
    earlier = GateViolation(
        asset="alpha",
        metric="/metric/alpha",
        observed=0.0,
        allowed=1.0,
        rule=">=",
        message="alpha regressed",
    )

    assert tuple(sorted((later, earlier))) == (earlier, later)
    with pytest.raises(FrozenInstanceError):
        earlier.metric = "/mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        pytest.param("observed", True, TypeError, id="observed-bool"),
        pytest.param("allowed", False, TypeError, id="allowed-bool"),
        pytest.param("observed", float("nan"), ValueError, id="observed-nan"),
        pytest.param("allowed", float("inf"), ValueError, id="allowed-inf"),
    ],
)
def test_gate_violation_rejects_non_raw_numbers(
    field: str, value: object, error: type[Exception]
) -> None:
    """Reject booleans and non-finite sentinels from decision values."""
    values: dict[str, object] = {
        "asset": "amber",
        "metric": "/metrics/palette/amber/step_cv",
        "observed": 0.09,
        "allowed": 0.08,
        "rule": "<=",
        "message": "step CV regressed",
    }
    values[field] = value

    with pytest.raises(error):
        GateViolation(**values)  # type: ignore[arg-type]


def test_gate_report_sorts_and_freezes_violations() -> None:
    """Expose one sorted tuple as the shared build/report decision."""
    later = GateViolation(
        asset="zeta",
        metric="/metric/zeta",
        observed=2.0,
        allowed=1.0,
        rule="<=",
        message="zeta regressed",
    )
    earlier = GateViolation(
        asset="alpha",
        metric="/metric/alpha",
        observed=0.0,
        allowed=1.0,
        rule=">=",
        message="alpha regressed",
    )

    report = GateReport(violations=(later, earlier))

    assert report.violations == (earlier, later)
    assert not report.passed
    with pytest.raises(FrozenInstanceError):
        report.violations = ()  # type: ignore[misc]


def test_evaluate_catalog_accepts_the_exact_candidate(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Keep the frozen v5-compatible candidate green under every raw gate."""
    report = _gates.evaluate_catalog(candidate_catalog, quality_baseline)

    assert report.passed
    assert report.violations == ()


def test_evaluate_catalog_fails_closed_on_baseline_schema_corruption(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Raise on baseline authority corruption instead of weakening a gate."""
    corrupted = deepcopy(dict(quality_baseline))
    corrupted["schema"] = "dartwork-mpl.color-quality/corrupt"

    with pytest.raises(
        oracle.OracleValidationError, match="quality payload schema"
    ):
        _gates.evaluate_catalog(candidate_catalog, corrupted)


def test_evaluate_catalog_fails_closed_on_baseline_metric_corruption(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Reject schema-valid metric edits that would silently relax a floor."""
    corrupted = deepcopy(dict(quality_baseline))
    metrics = cast(dict[str, object], corrupted["metrics"])
    palette = cast(dict[str, object], metrics["palette"])
    amber = cast(dict[str, object], palette["amber"])
    amber["step_cv"] = 1e-9

    with pytest.raises(oracle.OracleValidationError, match="semantic SHA-256"):
        _gates.evaluate_catalog(candidate_catalog, corrupted)


def test_check_all_adapts_the_shared_asset_baseline_policy(
    candidate_catalog: CatalogSnapshot,
) -> None:
    """Keep the compatibility runner from applying a weaker global policy."""
    shipped = list(candidate_catalog.palette["amber"])
    mutated = list(shipped)
    mutated[0] = "#fbf3dc"

    assert check_all({"amber": shipped}, {}, {}) == []
    failures = check_all({"amber": mutated}, {}, {})

    assert failures
    assert any("/metrics/palette/amber/step_cv" in item for item in failures)


def test_check_all_does_not_compare_direct_rows_to_full_lut_topology(
    candidate_catalog: CatalogSnapshot,
) -> None:
    """Accept shipped direct-32 cyclic/diverging rows without a false gate."""
    rows = candidate_catalog.cmaps_preview_32

    assert (
        check_all(
            {},
            {},
            {
                "div.blue_red": list(rows["blue_red"]),
                "cyc.hue": list(rows["hue"]),
            },
        )
        == []
    )


def test_evaluate_catalog_names_sequential_direction_regression(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Encode an ordered-family direction flip as a numeric equality gate."""
    row = candidate_catalog.palette["amber"]
    mutated = replace(
        candidate_catalog,
        palette=_with_row(
            candidate_catalog.palette, "amber", tuple(reversed(row))
        ),
    )

    report = _gates.evaluate_catalog(mutated, quality_baseline)

    violation = _require_violation(
        report,
        asset="amber",
        metric="/metrics/palette/amber/direction",
        rule="==",
    )
    assert violation.observed != violation.allowed
    assert violation.observed in {-1.0, 0.0, 1.0}
    assert violation.allowed in {-1.0, 0.0, 1.0}


def test_evaluate_catalog_names_sequential_y_order_regression(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Reject an interior full-LUT swap through the modeled-Y floor."""
    row = list(candidate_catalog.cmaps_256["amber"])
    row[100], row[150] = row[150], row[100]
    mutated = replace(
        candidate_catalog,
        cmaps_256=_with_row(candidate_catalog.cmaps_256, "amber", row),
    )

    report = _gates.evaluate_catalog(mutated, quality_baseline)

    violation = _require_violation(
        report,
        asset="amber",
        metric=("/metrics/cmaps_full_256/amber/oriented_delta_y/min"),
        rule=">=",
    )
    expected = _baseline_number(
        quality_baseline,
        "metrics",
        "cmaps_full_256",
        "amber",
        "oriented_delta_y",
        "min",
    )
    assert violation.allowed == expected
    assert violation.observed < violation.allowed


def test_full_lut_rejects_a_local_y_inversion_inside_global_v5_floor(
    quality_baseline: Mapping[str, object],
) -> None:
    """Reject a locally impossible inversion even when raw v5 minimum passes."""
    row = ["#ffffff", *(["#000000"] * 127), "#000200", *(["#000000"] * 127)]
    candidate = oracle.ordered_quality(row)
    quantization = _mapping(
        candidate["relative_y_quantization"],
        "candidate relative-Y quantization",
    )
    assert len(row) == 256
    assert quantization["worst_pair_index"] == 127
    assert _baseline_number(
        candidate, "oriented_delta_y", "min"
    ) == pytest.approx(-0.00043413593667503624, abs=1e-15)
    assert (
        _baseline_number(candidate, "relative_y_quantization", "margin") < 0.0
    )

    baseline_metrics = _mapping(quality_baseline["metrics"], "metrics")
    baseline_full = _mapping(
        baseline_metrics["cmaps_full_256"], "full-256 metrics"
    )
    baseline_tangerine = _mapping(
        baseline_full["tangerine"], "tangerine metrics"
    )
    raw_v5_floor = _baseline_number(
        baseline_tangerine, "oriented_delta_y", "min"
    )
    assert (
        _baseline_number(candidate, "oriented_delta_y", "min") >= raw_v5_floor
    )

    report = GateReport(
        violations=_gates.evaluate_quality_metrics(
            {"cmaps_full_256": {"synthetic": baseline_tangerine}},
            {"cmaps_full_256": {"synthetic": candidate}},
            {"synthetic": "sequential"},
        )
    )

    violation = _require_violation(
        report,
        asset="synthetic",
        metric=(
            "/metrics/cmaps_full_256/synthetic/relative_y_quantization/margin"
        ),
        rule=">=",
    )
    assert violation.observed == _baseline_number(
        candidate, "relative_y_quantization", "margin"
    )
    assert violation.allowed == 0.0
    assert "pair" in violation.message.lower()
    assert "127" in violation.message


def test_full_lut_keeps_asset_floor_when_absolute_y_margin_passes(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Keep the v5 asset floor as a second gate beyond cell quantization."""
    row = list(candidate_catalog.cmaps_256["afterglow"])
    row[1], row[2] = row[2], row[1]
    candidate = oracle.ordered_quality(row)
    assert (
        _baseline_number(candidate, "relative_y_quantization", "margin") >= 0.0
    )

    baseline_metrics = _mapping(quality_baseline["metrics"], "metrics")
    baseline_full = _mapping(
        baseline_metrics["cmaps_full_256"], "full-256 metrics"
    )
    baseline_afterglow = _mapping(
        baseline_full["afterglow"], "afterglow metrics"
    )
    report = GateReport(
        violations=_gates.evaluate_quality_metrics(
            {"cmaps_full_256": {"afterglow": baseline_afterglow}},
            {"cmaps_full_256": {"afterglow": candidate}},
            {"afterglow": "multi-hue"},
        )
    )

    quantization_path = (
        "/metrics/cmaps_full_256/afterglow/relative_y_quantization/margin"
    )
    assert all(
        violation.metric != quantization_path for violation in report.violations
    )
    violation = _require_violation(
        report,
        asset="afterglow",
        metric="/metrics/cmaps_full_256/afterglow/oriented_delta_y/min",
        rule=">=",
    )
    expected = _baseline_number(baseline_afterglow, "oriented_delta_y", "min")
    assert violation.allowed == expected
    assert violation.observed < violation.allowed


def test_full_lut_absolute_y_gate_does_not_apply_to_cvd_profiles(
    candidate_catalog: CatalogSnapshot,
) -> None:
    """Limit the local cell proof to normal sRGB rather than simulated CVD."""
    candidate = oracle.ordered_quality(candidate_catalog.cmaps_256["aurora"])
    assert (
        _baseline_number(candidate, "relative_y_quantization", "margin") > 0.0
    )
    assert _baseline_number(candidate, "protan_oriented_delta_y", "min") < 0.0
    metrics = {"cmaps_full_256": {"aurora": candidate}}

    violations = _gates.evaluate_quality_metrics(
        metrics, metrics, {"aurora": "multi-hue"}
    )

    assert violations == ()


def test_evaluate_catalog_names_diverging_mirror_regression(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Reject one endpoint change through mirrored modeled relative CIE Y."""
    row = list(candidate_catalog.cmaps_256["blue_red"])
    row[0] = "#000000"
    mutated = replace(
        candidate_catalog,
        cmaps_256=_with_row(candidate_catalog.cmaps_256, "blue_red", row),
    )

    report = _gates.evaluate_catalog(mutated, quality_baseline)

    violation = _require_violation(
        report,
        asset="blue_red",
        metric=("/metrics/topology/diverging/blue_red/mirror_delta_y/max"),
        rule="<=",
    )
    expected = _baseline_number(
        quality_baseline,
        "metrics",
        "topology",
        "diverging",
        "blue_red",
        "mirror_delta_y",
        "max",
    )
    assert violation.allowed == expected
    assert violation.observed > violation.allowed


def test_evaluate_catalog_names_diverging_arm_regression(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Reject symmetric interior swaps that reverse both diverging arms."""
    row = list(candidate_catalog.cmaps_256["blue_red"])
    for first, second in ((60, 100), (195, 155)):
        row[first], row[second] = row[second], row[first]
    mutated = replace(
        candidate_catalog,
        cmaps_256=_with_row(candidate_catalog.cmaps_256, "blue_red", row),
    )

    report = _gates.evaluate_catalog(mutated, quality_baseline)

    violation = _require_violation(
        report,
        asset="blue_red",
        metric=(
            "/metrics/topology/diverging/blue_red/left_arm_min_oriented_delta_y"
        ),
        rule=">=",
    )
    expected = _baseline_number(
        quality_baseline,
        "metrics",
        "topology",
        "diverging",
        "blue_red",
        "left_arm_min_oriented_delta_y",
    )
    assert violation.allowed == expected
    assert violation.observed < violation.allowed


def test_evaluate_catalog_names_cyclic_seam_regression(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Reject an enlarged cyclic seam using unrounded OKLab distance."""
    row = list(candidate_catalog.cmaps_256["hue"])
    row[0] = "#000000"
    mutated = replace(
        candidate_catalog,
        cmaps_256=_with_row(candidate_catalog.cmaps_256, "hue", row),
    )

    report = _gates.evaluate_catalog(mutated, quality_baseline)

    violation = _require_violation(
        report,
        asset="hue",
        metric="/metrics/topology/cyclic/hue/seam_delta_e_ok",
        rule="<=",
    )
    expected = _baseline_number(
        quality_baseline,
        "metrics",
        "topology",
        "cyclic",
        "hue",
        "seam_delta_e_ok",
    )
    assert violation.allowed == expected
    assert violation.observed > violation.allowed


@pytest.fixture(scope="module")
def duplicate_palette_report(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> GateReport:
    """Evaluate one fixed-count row with a new three-color duplicate run."""
    row = list(candidate_catalog.palette["amber"])
    row[3:6] = [row[3]] * 3
    mutated = replace(
        candidate_catalog,
        palette=_with_row(candidate_catalog.palette, "amber", row),
    )
    return _gates.evaluate_catalog(mutated, quality_baseline)


@pytest.mark.parametrize(
    ("field", "rule"),
    [
        pytest.param("unique_count", ">=", id="unique-count"),
        pytest.param(
            "adjacent_duplicate_count", "<=", id="adjacent-duplicates"
        ),
        pytest.param("max_run_length", "<=", id="maximum-run"),
    ],
)
def test_evaluate_catalog_names_duplicate_row_contract_regression(
    duplicate_palette_report: GateReport, field: str, rule: str
) -> None:
    """Gate each duplicate/run property against its asset-specific contract."""
    violation = _require_violation(
        duplicate_palette_report,
        asset="amber",
        metric=f"/row_contracts/palette/amber/{field}",
        rule=rule,
    )
    authority = load_color_v6_ssot()
    expected = _baseline_number(
        authority, "row_contracts", "palette", "amber", field
    )

    assert violation.allowed == expected
    if rule == ">=":
        assert violation.observed < violation.allowed
    else:
        assert violation.observed > violation.allowed


def test_evaluate_catalog_names_cycle_cvd_floor_regression(
    candidate_catalog: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> None:
    """Reject distinct colors that collapse under deutan simulation."""
    row = list(candidate_catalog.cycles["octave"])
    row[0:2] = ["#d62728", "#2ca02c"]
    mutated = replace(
        candidate_catalog,
        cycles=_with_row(candidate_catalog.cycles, "octave", row),
    )

    report = _gates.evaluate_catalog(mutated, quality_baseline)

    violation = _require_violation(
        report,
        asset="octave",
        metric="/metrics/cycles/octave/deutan_min_delta_e00",
        rule=">=",
    )
    expected = _baseline_number(
        quality_baseline, "metrics", "cycles", "octave", "deutan_min_delta_e00"
    )
    assert violation.allowed == expected
    assert violation.observed < violation.allowed
