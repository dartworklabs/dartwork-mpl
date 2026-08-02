"""Reference and immutability tests for the v5 color-quality oracle."""

import ast
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from dartwork_mpl._colors import _compatibility_metrics as oracle

REPO_ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = REPO_ROOT / "src/dartwork_mpl/_colors/_compatibility_metrics.py"
QUALITY_PATH = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_quality.json"
)
COMPAT_PATH = QUALITY_PATH.with_name("color_v5_compatibility.json")
GENERATOR_PATH = REPO_ROOT / "scripts/freeze_color_v5_quality.py"

BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
COMPAT_SHA256 = (
    "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
)
ORACLE_SHA256 = (
    "52718f3bf19f2fc2e5c7b95ef3cfe6338335b684eea86cd4b55892ed03765548"
)
QUALITY_SHA256 = (
    "326906a7ab05b48ec35f37d8e2a73931106fc03edde7db263e1e6735f3c95616"
)


def _load_quality() -> dict[str, object]:
    """Load and narrow the repository-local quality fixture."""
    decoded = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    assert all(isinstance(key, str) for key in decoded)
    return cast(dict[str, object], decoded)


def _object_map(value: object) -> dict[str, object]:
    """Narrow a decoded JSON object to a string-keyed mapping."""
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(dict[str, object], value)


def _number(value: object) -> float:
    """Narrow one decoded JSON number to float."""
    assert not isinstance(value, bool)
    assert isinstance(value, int | float)
    return float(value)


def _assert_json_finite(value: object) -> None:
    """Recursively reject non-finite numbers in decoded JSON data."""
    if isinstance(value, dict):
        for item in value.values():
            _assert_json_finite(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_finite(item)
    elif isinstance(value, float):
        assert math.isfinite(value)


def test_oracle_has_a_standard_library_only_import_boundary() -> None:
    """Keep the compatibility oracle independent from candidate code."""
    tree = ast.parse(ORACLE_PATH.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module is not None
            imports.add(node.module.split(".")[0])

    assert imports <= {
        "collections",
        "dataclasses",
        "hashlib",
        "itertools",
        "json",
        "math",
        "pathlib",
        "statistics",
        "typing",
    }
    assert imports.isdisjoint(
        {"dartwork_mpl", "numpy", "matplotlib", "_catalog", "_conversion"}
    )


@pytest.mark.parametrize(
    ("encoded", "expected"),
    [
        (0.0, 0.0),
        (0.04045, 0.04045 / 12.92),
        (
            math.nextafter(0.04045, math.inf),
            ((math.nextafter(0.04045, math.inf) + 0.055) / 1.055) ** 2.4,
        ),
        (1.0, 1.0),
    ],
)
def test_srgb_gamma_decode_breakpoint(encoded: float, expected: float) -> None:
    """Pin the IEC sRGB decoding branch boundary."""
    assert oracle.srgb_channel_to_linear(encoded) == pytest.approx(
        expected, abs=1e-15
    )


@pytest.mark.parametrize(
    ("linear", "expected"),
    [
        (0.0, 0.0),
        (0.0031308, 12.92 * 0.0031308),
        (
            math.nextafter(0.0031308, math.inf),
            1.055 * math.nextafter(0.0031308, math.inf) ** (1.0 / 2.4) - 0.055,
        ),
        (1.0, 1.0),
    ],
)
def test_srgb_gamma_encode_breakpoint(linear: float, expected: float) -> None:
    """Pin the IEC sRGB encoding branch boundary."""
    assert oracle.linear_channel_to_srgb(linear) == pytest.approx(
        expected, abs=1e-15
    )


def test_hex_helpers_are_strict_and_use_round_to_even() -> None:
    """Reject malformed colors and match Python's round-to-even parity."""
    assert oracle.hex_to_srgb("#123456") == pytest.approx(
        (18 / 255, 52 / 255, 86 / 255)
    )
    assert oracle.srgb_to_hex((0.5 / 255, 1.5 / 255, 2.5 / 255)) == "#000202"
    for malformed in ("123456", "#fff", "#gg0000", "#1234567"):
        with pytest.raises(oracle.OracleValidationError):
            oracle.hex_to_srgb(malformed)
    for malformed_rgb in (
        (-0.1, 0.0, 0.0),
        (0.0, 1.1, 0.0),
        (math.nan, 0.0, 0.0),
    ):
        with pytest.raises(oracle.OracleValidationError):
            oracle.srgb_to_hex(malformed_rgb)


def test_modeled_relative_y_uses_normalized_d65_distinct_from_wcag() -> None:
    """Normalize legacy D65 white while keeping WCAG separately named."""
    assert oracle.relative_y_srgb_d65((1.0, 0.0, 0.0)) == pytest.approx(
        0.21267287873271212, abs=1e-15
    )
    assert oracle.relative_y_srgb_d65((0.0, 1.0, 0.0)) == pytest.approx(
        0.7151521284847872, abs=1e-15
    )
    assert oracle.relative_y_srgb_d65((0.0, 0.0, 1.0)) == pytest.approx(
        0.07217499278250072, abs=1e-15
    )
    assert oracle.relative_y_srgb_d65((1.0, 1.0, 1.0)) == 1.0
    assert oracle.wcag_relative_luminance((1.0, 0.0, 0.0)) == pytest.approx(
        0.2126, abs=1e-15
    )
    assert oracle.wcag_contrast_ratio((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)) == 21


def test_all_34_sharma_reference_pairs_are_verified() -> None:
    """Verify the published CIEDE2000 data before quality computation."""
    references = oracle.reference_payload()
    sharma = _object_map(references["sharma_ciede2000"])
    vectors = cast(list[object], sharma["vectors"])
    assert len(vectors) == 34
    assert sharma["source_sha256"] == (
        "44aebb39107128328add54fbef5ac8ee89909e50508f448a1580adea2058a4b8"
    )
    oracle.verify_reference_suite(references)

    mutated = json.loads(json.dumps(references))
    mutated_vectors = mutated["sharma_ciede2000"]["vectors"]
    mutated_vectors[0][2] += 0.001
    with pytest.raises(oracle.OracleValidationError):
        oracle.verify_reference_suite(mutated)


def test_machado_matrices_and_derived_vectors_are_pinned() -> None:
    """Pin severity-one transforms and derived float/hex examples."""
    references = oracle.reference_payload()
    machado = _object_map(references["machado_2009"])
    assert machado["provenance_sha256"] == (
        "379c549025f91ac05a611631114ff8202fa2d802bc29e15f79479c7985373346"
    )
    matrices = _object_map(machado["severity_1_matrices"])
    assert matrices["protan"] == [
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ]
    assert oracle.simulate_cvd_hex("#ff0000", "protan") == "#6d5f00"
    assert oracle.simulate_cvd_hex("#00ff00", "deutan") == "#efd63a"
    assert oracle.simulate_cvd("#123456", "protan") == pytest.approx(
        (0.14283413377226134, 0.21187566093436755, 0.3427561566870771)
    )


def test_bvm_tritan_model_covers_branches_neutral_and_clamp() -> None:
    """Exercise both BVM half-planes, projection continuity, and clamping."""
    references = oracle.reference_payload()
    bvm = _object_map(references["bvm_1997_tritan"])
    assert bvm["adaptation_commit"] == (
        "1a01fc1bf8d8dd419af8343b80b05e98ba50a75d"
    )
    assert bvm["adaptation_source_sha256"] == (
        "6503e903876280e66e3fbaae983c0f647da502d1c555ac200e32cb04e2905999"
    )
    high = cast(list[list[float]], bvm["high_matrix"])
    low = cast(list[list[float]], bvm["low_matrix"])
    separation = cast(list[float], bvm["separation_plane"])

    def project(
        matrix: list[list[float]], rgb: tuple[float, float, float]
    ) -> tuple[float, ...]:
        return tuple(
            sum(a * b for a, b in zip(row, rgb, strict=True)) for row in matrix
        )

    for matrix in (high, low):
        squared = [
            [
                sum(
                    matrix[row][inner] * matrix[inner][column]
                    for inner in range(3)
                )
                for column in range(3)
            ]
            for row in range(3)
        ]
        for actual_row, expected_row in zip(squared, matrix, strict=True):
            assert actual_row == pytest.approx(expected_row, abs=3e-5)

    for red, green in ((1.0, 1.0), (0.3, 0.2), (0.2, 0.25)):
        blue = -(separation[0] * red + separation[1] * green) / separation[2]
        plane_rgb = (red, green, blue)
        assert sum(
            a * b for a, b in zip(separation, plane_rgb, strict=True)
        ) == pytest.approx(0.0, abs=1e-15)
        assert project(high, plane_rgb) == pytest.approx(
            project(low, plane_rgb), abs=3e-5
        )

    assert oracle.tritan_branch((1.0, 0.0, 0.0)) == "high"
    assert oracle.tritan_branch((0.0, 1.0, 0.0)) == "low"
    neutral = (0.25, 0.25, 0.25)
    assert oracle.simulate_cvd_linear(neutral, "tritan") == pytest.approx(
        neutral, abs=3e-6
    )
    red_once = oracle.simulate_cvd_linear((1.0, 0.0, 0.0), "tritan")
    red_twice = oracle.simulate_cvd_linear(red_once, "tritan")
    assert red_twice == pytest.approx(red_once, abs=3e-6)
    assert oracle.simulate_cvd_hex("#ff0000", "tritan") == "#ff004e"
    assert oracle.simulate_cvd_hex("#00ff00", "tritan") == "#79e9ff"
    projected_red = oracle.simulate_cvd_linear((1.0, 0.0, 0.0), "tritan")
    assert projected_red[0] > 1.0
    assert projected_red[1] < 0.0
    assert oracle.simulate_cvd("#ff0000", "tritan")[:2] == pytest.approx(
        (1.0, 0.0)
    )
    assert all(
        0.0 <= channel <= 1.0
        for channel in oracle.simulate_cvd("#ff0000", "tritan")
    )
    with pytest.raises(oracle.OracleValidationError):
        oracle.simulate_cvd_hex("#123456", "achromatopsia")


def test_numeric_summary_uses_type_7_percentiles_and_null_for_empty() -> None:
    """Use deterministic Type-7 interpolation and reject empty summaries."""
    summary = oracle.summarize_numeric([0.0, 10.0, 20.0, 30.0, 40.0])
    assert summary.to_json_value() == {
        "min": 0.0,
        "p05": 2.0,
        "p50": 20.0,
        "p95": 38.0,
        "max": 40.0,
        "mean": 20.0,
    }
    singleton = oracle.summarize_numeric([4.0])
    assert singleton.to_json_value()["p05"] == 4.0
    with pytest.raises(oracle.OracleValidationError):
        oracle.summarize_numeric([])
    with pytest.raises(oracle.OracleValidationError):
        oracle.summarize_numeric([math.nan])
    with pytest.raises(oracle.OracleValidationError):
        oracle.canonical_json_bytes({"not_finite": math.inf})


def test_ordered_quality_marks_degenerate_steps_as_invalid() -> None:
    """Do not report an all-identical multi-stop row as perfect uniformity."""
    repeated = oracle.ordered_quality(["#000000", "#000000"])
    assert repeated["step_cv"] is None
    assert repeated["degenerate_neighbor_steps"] is True
    singleton = oracle.ordered_quality(["#000000"])
    assert singleton["step_cv"] is None
    assert singleton["degenerate_neighbor_steps"] is False


def test_ordered_quality_marks_one_zero_among_numeric_steps_degenerate() -> (
    None
):
    """Detect an isolated duplicate without discarding the row's numeric CV."""
    quality = oracle.ordered_quality(
        ["#000000", "#404040", "#404040", "#ffffff"]
    )

    assert quality["degenerate_neighbor_steps"] is True
    assert isinstance(quality["step_cv"], float)
    assert math.isfinite(quality["step_cv"])


def test_quality_validator_allows_numeric_cv_with_one_degenerate_step() -> None:
    """Represent one isolated zero step without conflating it with a zero row."""
    payload = _load_quality()
    metrics = _object_map(payload["metrics"])
    palette = _object_map(metrics["palette"])
    amber = _object_map(palette["amber"])
    neighbor_ok = _object_map(amber["neighbor_delta_e_ok"])
    neighbor_de00 = _object_map(amber["neighbor_delta_e00"])
    neighbor_ok["min"] = 0.0
    neighbor_de00["min"] = 0.0
    amber["degenerate_neighbor_steps"] = True
    assert isinstance(amber["step_cv"], float)

    validated = oracle.validate_quality_payload(
        payload, expected_oracle_sha256=ORACLE_SHA256
    )

    validated_metrics = _object_map(validated["metrics"])
    validated_palette = _object_map(validated_metrics["palette"])
    validated_amber = _object_map(validated_palette["amber"])
    assert validated_amber["degenerate_neighbor_steps"] is True
    assert isinstance(validated_amber["step_cv"], float)


def test_tangerine_records_local_round_to_even_y_quantization_margin() -> None:
    """Pin the worst full-LUT pair to its two local 8-bit sRGB cells."""
    compatibility = json.loads(COMPAT_PATH.read_text(encoding="utf-8"))
    tangerine = compatibility["cmaps256"]["tangerine"]

    quality = oracle.ordered_quality(tangerine)
    quantization = _object_map(quality["relative_y_quantization"])

    assert set(quantization) == {
        "worst_pair_index",
        "oriented_delta_y",
        "local_tolerance",
        "margin",
    }
    assert quantization == {
        "worst_pair_index": 248,
        "oriented_delta_y": pytest.approx(-0.0005861873267654708, abs=1e-15),
        "local_tolerance": pytest.approx(0.0014120957666379358, abs=1e-15),
        "margin": pytest.approx(0.000825908439872465, abs=1e-15),
    }


def test_diverging_and_cyclic_topology_preserve_full_baseline_contract() -> (
    None
):
    """Record arm monotonicity, mirrors, midpoint symmetry, and hue spread."""
    compatibility = json.loads(COMPAT_PATH.read_text(encoding="utf-8"))
    cmaps = compatibility["cmaps256"]
    diverging = oracle.diverging_topology(cmaps["gray_red"])
    assert diverging["center_is_global_max"] is True
    assert _number(diverging["left_arm_min_oriented_delta_y"]) > 0.0
    assert _number(diverging["right_arm_min_oriented_delta_y"]) > 0.0
    assert diverging["arm_arc_ratio"] == pytest.approx(1.074999551966007)
    assert (
        _number(_object_map(diverging["mirror_step_delta_e_ok"])["max"]) > 0.0
    )

    hue = oracle.cyclic_topology(cmaps["hue"])
    assert hue["topology_kind"] == "isoluminant"
    assert _number(hue["relative_y_spread"]) < 0.004
    assert hue["two_arm"] is None
    for name in ("halo", "corona"):
        twilight = oracle.cyclic_topology(cmaps[name])
        assert twilight["topology_kind"] == "twilight"
        arms = _object_map(twilight["two_arm"])
        assert arms["midpoint_contains_global_y_min"] is True
        assert _number(arms["left_min_oriented_delta_y"]) > 0.0
        assert _number(arms["right_min_oriented_delta_y"]) > 0.0
        assert _number(_object_map(arms["mirror_delta_y"])["max"]) > 0.0


def test_gate_decisions_use_raw_values_not_display_rounding() -> None:
    """A displayed 10.0 must not turn a raw sub-floor value into a pass."""
    assert round(9.999999, 1) == 10.0
    assert oracle.meets_minimum(9.999999, 10.0) is False


def test_quality_policy_distinguishes_step_cv_by_sampling_and_taxonomy() -> (
    None
):
    """Apply the 0.08 cap only to native ordered direct-preview rows."""
    quality = _load_quality()
    policy = _object_map(quality["policy"])
    gate_rules = _object_map(policy["gate_rules"])
    assert gate_rules["ordered_direct_32_step_cv"] == (
        "candidate <= min(asset_v5, 0.08)"
    )
    assert gate_rules["nonordered_direct_32_step_cv"] == (
        "candidate <= asset_v5"
    )
    assert gate_rules["full_256_step_cv"] == "candidate <= asset_v5"
    assert "direct_32_step_cv" not in gate_rules
    assert "ordered_step_cv" not in gate_rules


def test_quality_fixture_is_pinned_finite_and_validated() -> None:
    """Pin both immutable bytes and validate embedded source provenance."""
    assert hashlib.sha256(COMPAT_PATH.read_bytes()).hexdigest() == COMPAT_SHA256
    assert hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest() == ORACLE_SHA256
    assert (
        hashlib.sha256(QUALITY_PATH.read_bytes()).hexdigest() == QUALITY_SHA256
    )
    quality = _load_quality()
    assert _object_map(quality["compatibility"])["raw_sha256"] == COMPAT_SHA256
    _assert_json_finite(quality)
    validated = oracle.load_quality_payload(
        QUALITY_PATH,
        expected_raw_sha256=QUALITY_SHA256,
        expected_oracle_sha256=ORACLE_SHA256,
    )
    assert validated["schema"] == "dartwork-mpl.color-quality/v2"


def test_vendor_surface_provenance_does_not_change_quality_metric_values() -> (
    None
):
    """Keep all numeric quality authority independent of additive vendor data."""
    quality = _load_quality()
    metric_projection = {
        key: quality[key] for key in ("metrics", "global_extrema")
    }

    assert oracle.canonical_json_sha256(metric_projection) == (
        "62d0329f66bdd9052ba5fe60b9593b54329f5f12eb8325007c11c4f8dee98a82"
    )


def test_quality_v2_preserves_every_legacy_metric_outside_declared_changes() -> (
    None
):
    """Prove v2 only adds cell margins and fixes isolated-zero flags."""
    payload = _load_quality()
    legacy_projection = {
        key: json.loads(json.dumps(payload[key]))
        for key in ("metrics", "global_extrema")
    }

    def restore_v1_shape(value: object) -> None:
        if isinstance(value, dict):
            value.pop("relative_y_quantization", None)
            if "degenerate_neighbor_steps" in value:
                neighbor = _object_map(value["neighbor_delta_e_ok"])
                value["degenerate_neighbor_steps"] = neighbor["max"] == 0.0
            for item in value.values():
                restore_v1_shape(item)
        elif isinstance(value, list):
            for item in value:
                restore_v1_shape(item)

    restore_v1_shape(legacy_projection)
    assert oracle.canonical_json_sha256(legacy_projection) == (
        "7af19e8077925fb1f043bda2b696f1a7dcc7116119f37b4bb89c7badd92571e2"
    )


def test_quality_loader_rejects_source_and_payload_tampering(
    tmp_path: Path,
) -> None:
    """Reject raw-byte drift before trusting decoded quality values."""
    original = QUALITY_PATH.read_bytes()
    tampered = tmp_path / "quality.json"
    tampered.write_bytes(original + b"\n")
    with pytest.raises(oracle.OracleValidationError):
        oracle.load_quality_payload(
            tampered,
            expected_raw_sha256=QUALITY_SHA256,
            expected_oracle_sha256=ORACLE_SHA256,
        )

    decoded = _load_quality()
    oracle_info = _object_map(decoded["oracle"])
    oracle_info["source_sha256"] = "0" * 64
    payload = json.dumps(decoded, allow_nan=False).encode("utf-8")
    tampered.write_bytes(payload)
    with pytest.raises(oracle.OracleValidationError):
        oracle.load_quality_payload(
            tampered,
            expected_raw_sha256=hashlib.sha256(payload).hexdigest(),
            expected_oracle_sha256=ORACLE_SHA256,
        )

    for mutate in (
        lambda value: value.__setitem__("schema", "unknown"),
        lambda value: _object_map(value["compatibility"]).__setitem__(
            "raw_sha256", "0" * 64
        ),
    ):
        malformed = _load_quality()
        mutate(malformed)
        payload = json.dumps(malformed, allow_nan=False).encode("utf-8")
        tampered.write_bytes(payload)
        with pytest.raises(oracle.OracleValidationError):
            oracle.load_quality_payload(
                tampered,
                expected_raw_sha256=hashlib.sha256(payload).hexdigest(),
                expected_oracle_sha256=ORACLE_SHA256,
            )


@pytest.mark.parametrize(
    "mutation", ["empty_palette", "bad_summary", "bad_count", "empty_extrema"]
)
def test_quality_validator_rejects_malformed_metric_contracts(
    mutation: str,
) -> None:
    """Validate metric shapes before a later gate consumes the payload."""
    malformed = _load_quality()
    metrics = _object_map(malformed["metrics"])
    palette = _object_map(metrics["palette"])
    if mutation == "empty_palette":
        metrics["palette"] = {}
    elif mutation == "bad_summary":
        first = _object_map(palette[sorted(palette)[0]])
        first["relative_y"] = "bogus"
    elif mutation == "bad_count":
        first = _object_map(palette[sorted(palette)[0]])
        first["count"] = -1
    else:
        malformed["global_extrema"] = {}

    with pytest.raises(oracle.OracleValidationError):
        oracle.validate_quality_payload(
            malformed, expected_oracle_sha256=ORACLE_SHA256
        )


def test_quality_computation_rejects_singleton_ordered_luts_cleanly() -> None:
    """Reject empty ordered profiles with the oracle's domain exception."""
    compatibility = json.loads(COMPAT_PATH.read_text(encoding="utf-8"))
    quality = _load_quality()
    literal_inputs = _object_map(quality["literal_inputs"])
    previews = literal_inputs["cmaps_preview_32"]
    ordered_name = next(
        name
        for name, kind in sorted(compatibility["taxonomy"].items())
        if kind in {"sequential", "multi-hue"}
    )
    compatibility["cmaps256"][ordered_name] = ["#000000"]

    with pytest.raises(oracle.OracleValidationError, match="at least two"):
        oracle.compute_catalog_quality(compatibility, previews)


def test_quality_sanity_values_match_the_immutable_v5_baseline() -> None:
    """Pin representative raw extrema used by the migration gates."""
    quality = _load_quality()
    metrics = _object_map(quality["metrics"])
    palette = _object_map(metrics["palette"])
    preview = _object_map(metrics["cmaps_direct_32"])
    full = _object_map(metrics["cmaps_full_256"])
    cycles = _object_map(metrics["cycles"])
    dark = _object_map(metrics["dark_cycle"])
    topology = _object_map(metrics["topology"])
    global_extrema = _object_map(quality["global_extrema"])

    blue = _object_map(palette["blue"])
    lime = _object_map(palette["lime"])
    red32 = _object_map(preview["red"])
    haze32 = _object_map(preview["haze"])
    assert blue["step_cv"] == pytest.approx(0.010749185770891876)
    assert lime["step_cv"] == pytest.approx(0.02248589344129385)
    assert red32["step_cv"] == pytest.approx(0.030980990425383513)
    assert haze32["step_cv"] == pytest.approx(0.05392665608275016)

    worst_y = _object_map(global_extrema["worst_oriented_delta_y"])
    assert worst_y == {
        "asset": "tangerine",
        "index": 248,
        "value": pytest.approx(-0.0005861873267654708),
    }
    worst_cvd = _object_map(global_extrema["worst_cvd_oriented_delta_y"])
    assert worst_cvd == {
        "asset": "aurora",
        "index": 148,
        "mode": "protan",
        "value": pytest.approx(-0.004295185665984191),
    }
    assert _object_map(full["tangerine"])["direction"] == "decreasing"

    diverging = _object_map(topology["diverging"])
    gray_red = _object_map(diverging["gray_red"])
    assert gray_red["arm_arc_ratio"] == pytest.approx(1.074999551966007)
    cyclic = _object_map(topology["cyclic"])
    for name, expected in {
        "hue": 0.33879387805127936,
        "halo": 0.5570182443966718,
        "corona": 0.6196229210087726,
    }.items():
        assert _object_map(cyclic[name])["seam_delta_e_ok"] == pytest.approx(
            expected
        )

    for name, common, tritan in (
        ("octave", 10.312044280409367, 8.29118607511606),
        ("octave_print", 10.374644741458209, 9.76155586553625),
    ):
        metric = _object_map(cycles[name])
        assert metric["common_min_delta_e00"] == pytest.approx(common)
        assert metric["tritan_min_delta_e00"] == pytest.approx(tritan)
    assert dark["common_min_delta_e00"] == pytest.approx(11.513135454407905)
    assert dark["tritan_min_delta_e00"] == pytest.approx(11.010755633433755)


def test_every_discrete_form_has_quality_and_singletons_use_null() -> None:
    """Measure every frozen discrete row without serializing NaN."""
    quality = _load_quality()
    metrics = _object_map(quality["metrics"])
    discrete = _object_map(metrics["discrete"])
    compatibility = json.loads(COMPAT_PATH.read_text(encoding="utf-8"))
    assert set(discrete) == set(compatibility["discrete_hex"])
    for name, forms_value in discrete.items():
        forms = _object_map(forms_value)
        assert set(forms) == set(compatibility["discrete_hex"][name])
        singleton = _object_map(forms["1"])
        assert singleton["normal_delta_e00"] is None
        assert singleton["normal_delta_e_ok"] is None


def test_generator_is_byte_identical_and_uses_archived_baseline(
    tmp_path: Path,
) -> None:
    """Regenerate from pinned literals twice without touching candidate code."""
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = [
        sys.executable,
        str(GENERATOR_PATH),
        "--baseline-commit",
        BASELINE_COMMIT,
    ]
    import_trap = tmp_path / "import-trap" / "dartwork_mpl"
    import_trap.mkdir(parents=True)
    (import_trap / "__init__.py").write_text(
        "raise RuntimeError('candidate package import is forbidden')\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(import_trap.parent)
    subprocess.run(
        [*command, "--output", str(first)],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
    )
    subprocess.run(
        [*command, "--output", str(second)], cwd=REPO_ROOT, check=True
    )
    assert (
        first.read_bytes() == second.read_bytes() == QUALITY_PATH.read_bytes()
    )

    result = subprocess.run(
        [
            *command[:-1],
            f"{BASELINE_COMMIT}^",
            "--output",
            str(tmp_path / "bad.json"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "baseline commit" in result.stderr.lower()
