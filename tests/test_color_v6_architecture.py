"""Architecture and provenance tests for the packaged color v6 SSOT."""

import ast
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "scripts/build_color_v6_ssot.py"
V6_SSOT_PATH = REPO_ROOT / "src/dartwork_mpl/asset/color/color_v6_ssot.json"
COMPATIBILITY_PATH = (
    REPO_ROOT
    / "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)
QUALITY_PATH = COMPATIBILITY_PATH.with_name("color_v5_quality.json")
BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
RECIPE_SHA256 = (
    "a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518"
)
COMPATIBILITY_SHA256 = (
    "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
)
QUALITY_SHA256 = (
    "326906a7ab05b48ec35f37d8e2a73931106fc03edde7db263e1e6735f3c95616"
)
ORACLE_SHA256 = (
    "52718f3bf19f2fc2e5c7b95ef3cfe6338335b684eea86cd4b55892ed03765548"
)
ROW_CONTRACT_COUNTS = {
    "palette": 20,
    "direct_32": 43,
    "full_256": 43,
    "cycles": 2,
    "curated_rows": 15,
    "dark_cycle": 1,
    "discrete_forward": 547,
}
EXPECTED_BASELINE_PATHS = {
    "recipe": (
        "docs/superpowers/specs/assets/2026-07-03-color-system-v5/"
        "color_v5_ssot.json"
    ),
    "compatibility": (
        "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
        "color-system/color_v5_compatibility.json"
    ),
    "quality": (
        "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
        "color-system/color_v5_quality.json"
    ),
    "oracle": "src/dartwork_mpl/_colors/_compatibility_metrics.py",
}


def _canonical_sha256(value: object) -> str:
    """Hash one JSON value with the v6 canonical section/row encoding."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _thaw(value: object) -> object:
    """Convert recursive read-only SSOT containers to JSON containers."""
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _mapping_keys(value: object) -> set[str]:
    """Collect recursive JSON object keys without inspecting prose values."""
    if isinstance(value, Mapping):
        keys: set[str] = {str(key) for key in value}
        for item in value.values():
            keys.update(_mapping_keys(item))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return set().union(*(_mapping_keys(item) for item in value))
    return set()


def _load_builder() -> ModuleType:
    """Import the offline generator without importing the package compiler."""
    spec = importlib.util.spec_from_file_location(
        "color_v6_builder", BUILDER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load color v6 SSOT builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_nested(
    container: object, path: tuple[object, ...], value: object
) -> None:
    """Set one nested decoded-JSON value for a corruption test."""
    target = container
    for key in path[:-1]:
        if isinstance(target, dict):
            target = target[key]
            continue
        if isinstance(target, list):
            if not isinstance(key, int):
                raise TypeError("list path components must be integers")
            target = target[key]
            continue
        raise TypeError(f"cannot descend through {type(target).__name__}")
    final = path[-1]
    if isinstance(target, dict):
        target[final] = value
        return
    if isinstance(target, list) and isinstance(final, int):
        target[final] = value
        return
    raise TypeError(f"cannot assign through {type(target).__name__}")


def _write_rehashed_section(
    tmp_path: Path, payload: dict[str, object], section: str
) -> Path:
    """Write a mutated payload whose enclosing section hash is valid."""
    hashes = cast(dict[str, str], payload["section_hashes"])
    hashes[section] = _canonical_sha256(payload[section])
    changed = tmp_path / f"malformed-{section}.json"
    changed.write_text(
        json.dumps(payload, allow_nan=False, sort_keys=True), encoding="utf-8"
    )
    return changed


@pytest.fixture(scope="module")
def v6_ssot() -> dict[str, object]:
    """Load the packaged operational v6 JSON as literal data."""
    decoded: object = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


@pytest.fixture(scope="module")
def compatibility() -> dict[str, object]:
    """Load the immutable v5 exact fixture for copied-section checks."""
    decoded: object = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


@pytest.fixture(scope="module")
def quality() -> dict[str, object]:
    """Load the immutable independent v5 quality fixture."""
    decoded: object = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


@pytest.mark.parametrize(
    ("legacy_lstar", "expected"),
    [
        (0.0, 0.0),
        (1.0, 0.10344827241379334),
        (8.0, 0.20689654482758668),
        (96.0, 0.9655172091954044),
    ],
)
def test_offline_migration_is_piecewise_at_the_cie_toe(
    legacy_lstar: float, expected: float
) -> None:
    """Invert the toe instead of extrapolating the affine upper branch."""
    builder = _load_builder()

    actual = builder._legacy_lstar_to_tone(legacy_lstar)

    assert actual == pytest.approx(expected, abs=1e-16, rel=0.0)


def test_offline_migration_is_continuous_around_the_cie_toe() -> None:
    """Keep the piecewise provenance continuous at L*=8."""
    builder = _load_builder()
    below = builder._legacy_lstar_to_tone(math.nextafter(8.0, 0.0))
    at = builder._legacy_lstar_to_tone(8.0)
    above = builder._legacy_lstar_to_tone(math.nextafter(8.0, math.inf))

    assert below <= at <= above
    assert above - below < 1e-15


def test_v6_ssot_has_all_authoritative_sections(
    v6_ssot: dict[str, object],
) -> None:
    """Package recipe, provenance, policies, baselines, and row contracts."""
    assert set(v6_ssot) == {
        "baseline_commit",
        "baselines",
        "coordinates",
        "migration",
        "multi_hue_discrete_indices",
        "policies",
        "recipe",
        "row_contracts",
        "schema",
        "section_hashes",
    }
    assert v6_ssot["schema"] == "dartwork-mpl.color-ssot/v6"
    assert v6_ssot["baseline_commit"] == BASELINE_COMMIT


def test_v6_section_hashes_cover_every_authoritative_section(
    v6_ssot: dict[str, object],
) -> None:
    """Make every top-level authority independently tamper-evident."""
    hashes = cast(dict[str, str], v6_ssot["section_hashes"])
    expected_sections = set(v6_ssot) - {"section_hashes"}

    assert set(hashes) == expected_sections
    assert hashes == {
        name: _canonical_sha256(v6_ssot[name])
        for name in sorted(expected_sections)
    }


def test_v6_baseline_provenance_pins_all_four_raw_sources(
    v6_ssot: dict[str, object],
) -> None:
    """Prevent coordinated baseline/compiler edits from redefining history."""
    baselines = cast(dict[str, object], v6_ssot["baselines"])
    assert cast(dict[str, object], baselines["recipe"])["raw_sha256"] == (
        RECIPE_SHA256
    )
    assert (
        cast(dict[str, object], baselines["compatibility"])["raw_sha256"]
        == COMPATIBILITY_SHA256
    )
    assert cast(dict[str, object], baselines["quality"])["raw_sha256"] == (
        QUALITY_SHA256
    )
    assert cast(dict[str, object], baselines["oracle"])["raw_sha256"] == (
        ORACLE_SHA256
    )


def test_v6_baseline_provenance_names_every_source_path(
    v6_ssot: dict[str, object],
) -> None:
    """Keep release-fixture and oracle paths explicit for later audits."""
    baselines = cast(dict[str, dict[str, object]], v6_ssot["baselines"])

    assert {
        name: record["path"] for name, record in baselines.items()
    } == EXPECTED_BASELINE_PATHS


def test_v6_coordinate_and_migration_provenance_is_explicit(
    v6_ssot: dict[str, object],
) -> None:
    """Separate OKLCH authoring from modeled relative-Y output history."""
    coordinates = cast(dict[str, object], v6_ssot["coordinates"])
    migration = cast(dict[str, object], v6_ssot["migration"])

    assert coordinates == {
        "authoring": "OKLab/OKLCH",
        "canonical": "OKLab",
        "neutral_tone": ("cbrt(modeled relative CIE Y from nominal D65 sRGB)"),
        "output": ("modeled relative CIE Y calculated from nominal D65 sRGB"),
        "relative_y_coefficients": [
            0.21267287873271212,
            0.7151521284847872,
            0.07217499278250072,
        ],
        "validation_only": ["CIELAB", "CIEDE2000", "Machado/BVM CVD"],
    }
    assert migration == {
        "denominator": 116.00000386666655,
        "legacy_coordinate": "CIELAB L* D65",
        "legacy_white_y": 1.0000001,
        "lower_formula": "cbrt((L* / (24389 / 27)) / S)",
        "scope": "offline v5 compatibility provenance only",
        "toe_lstar": 8.0,
        "toe_kappa": 903.2962962962963,
        "upper_formula": "(L* + 16) / D",
    }


def test_v6_named_policies_pin_construction_and_cvd_models(
    v6_ssot: dict[str, object], quality: dict[str, object]
) -> None:
    """Store all deterministic search values and deficiency model choices."""
    policies = cast(dict[str, dict[str, object]], v6_ssot["policies"])

    assert policies["gamut"] == {
        "iterations": 24,
        "max_chroma_upper": 0.4,
        "strategy": "preserve OKLCH L/h and reduce C",
        "tolerance": 1e-6,
    }
    assert policies["tone"] == {
        "catalog_chroma_fraction": 0.97,
        "luminance_search_iterations": 40,
        "max_chroma_search_iterations": 22,
        "max_chroma_tone_iterations": 30,
        "max_chroma_upper": 0.4,
        "probe_chroma": 0.04,
    }
    assert policies["cvd"] == {
        "gate_pipeline": cast(dict[str, object], quality["policy"])[
            "cvd_gate_pipeline"
        ],
        "models_by_deficiency": {
            "deutan": "Machado et al. 2009 severity 1.0",
            "protan": "Machado et al. 2009 severity 1.0",
            "tritan": "Brettel-Vienot-Mollon 1997 adapted linear-sRGB",
        },
        "role": "model-specific validation only",
    }


def test_manifest_numeric_policies_equal_runtime_policy_objects(
    v6_ssot: dict[str, object],
) -> None:
    """Keep packaged numeric authority synchronized with runtime searches."""
    from dartwork_mpl._colors._gamut import SRGB_GAMUT_POLICY
    from dartwork_mpl._colors._tone import SHIPPED_TONE_POLICY

    policies = cast(dict[str, dict[str, object]], v6_ssot["policies"])
    gamut = policies["gamut"]
    tone = policies["tone"]

    assert {
        "iterations": SRGB_GAMUT_POLICY.iterations,
        "max_chroma_upper": SRGB_GAMUT_POLICY.max_chroma_upper,
        "tolerance": SRGB_GAMUT_POLICY.tolerance,
    } == {
        key: gamut[key]
        for key in ("iterations", "max_chroma_upper", "tolerance")
    }
    assert {
        "catalog_chroma_fraction": (
            SHIPPED_TONE_POLICY.catalog_chroma_fraction
        ),
        "luminance_search_iterations": (
            SHIPPED_TONE_POLICY.luminance_search_iterations
        ),
        "max_chroma_search_iterations": (
            SHIPPED_TONE_POLICY.max_chroma_search_iterations
        ),
        "max_chroma_tone_iterations": (
            SHIPPED_TONE_POLICY.max_chroma_tone_iterations
        ),
        "max_chroma_upper": SHIPPED_TONE_POLICY.max_chroma_upper,
        "probe_chroma": SHIPPED_TONE_POLICY.probe_chroma,
    } == {key: tone[key] for key in tone if key != "strategy"}


def test_v6_copies_exact_and_quality_authority_without_candidate_metrics(
    v6_ssot: dict[str, object],
    compatibility: dict[str, object],
    quality: dict[str, object],
) -> None:
    """Copy frozen baseline values only, never a live candidate result."""
    baselines = cast(dict[str, object], v6_ssot["baselines"])
    exact = cast(dict[str, object], baselines["compatibility"])
    quality_baseline = cast(dict[str, object], baselines["quality"])

    assert exact["canonical_hashes"] == compatibility["canonical_hashes"]
    assert len(cast(dict[str, str], exact["canonical_hashes"])) == 18
    assert cast(dict[str, str], exact["canonical_hashes"])["vendor_colors"] == (
        "6dc6053c4f8c66adb9d7deb746c3e7eee0295c27cc107b37c872b46f83f79a72"
    )
    assert quality_baseline["metrics"] == quality["metrics"]
    assert quality_baseline["global_extrema"] == quality["global_extrema"]
    assert quality_baseline["policy"] == quality["policy"]
    forbidden_candidate_sections = {
        "candidate",
        "candidate_metrics",
        "candidate_global_extrema",
    }
    assert forbidden_candidate_sections.isdisjoint(_mapping_keys(baselines))


def test_v6_uses_the_frozen_multi_hue_indices(
    v6_ssot: dict[str, object], compatibility: dict[str, object]
) -> None:
    """Move shipped multi-hue selection authority out of the v5 accessor."""
    assert (
        v6_ssot["multi_hue_discrete_indices"]
        == compatibility["multi_hue_discrete_indices"]
    )


def test_v6_multi_hue_indices_cover_exactly_nine_families_and_sizes(
    v6_ssot: dict[str, object],
) -> None:
    """Require every shipped multi-hue form for each size one through eight."""
    expected_families = {
        "afterglow",
        "aurora",
        "blaze",
        "canopy",
        "glacier",
        "haze",
        "iris",
        "lagoon",
        "lava",
    }
    indices = cast(
        dict[str, dict[str, list[int]]], v6_ssot["multi_hue_discrete_indices"]
    )

    assert set(indices) == expected_families
    for family, forms in indices.items():
        assert set(forms) == {str(size) for size in range(1, 9)}, family
        for size_text, row in forms.items():
            assert len(row) == int(size_text), (family, size_text)
            assert all(
                isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < 256
                for index in row
            ), (family, size_text)


def test_v6_row_contract_cardinality_is_exact(
    v6_ssot: dict[str, object],
) -> None:
    """Pin all 671 frozen forward rows without a global uniqueness rule."""
    contracts = cast(dict[str, dict[str, object]], v6_ssot["row_contracts"])
    actual_counts = {name: len(rows) for name, rows in contracts.items()}

    assert actual_counts == ROW_CONTRACT_COUNTS
    assert sum(actual_counts.values()) == 671


def test_v6_row_contract_counts_and_duplicate_fields_are_consistent(
    v6_ssot: dict[str, object],
) -> None:
    """Validate per-category lengths and internally possible run topology."""
    contracts = cast(
        dict[str, dict[str, dict[str, object]]], v6_ssot["row_contracts"]
    )
    fixed_counts = {
        "palette": 10,
        "direct_32": 32,
        "full_256": 256,
        "cycles": 8,
        "curated_rows": 8,
        "dark_cycle": 7,
    }
    required_fields = {
        "adjacent_duplicate_count",
        "canonical_sha256",
        "count",
        "max_run_length",
        "unique_count",
    }

    for section, rows in contracts.items():
        for name, record in rows.items():
            assert set(record) == required_fields, (section, name)
            count = cast(int, record["count"])
            unique = cast(int, record["unique_count"])
            adjacent = cast(int, record["adjacent_duplicate_count"])
            max_run = cast(int, record["max_run_length"])
            expected_count = (
                int(name.rsplit("/", maxsplit=1)[1])
                if section == "discrete_forward"
                else fixed_counts[section]
            )
            assert count == expected_count, (section, name)
            assert 1 <= unique <= count, (section, name)
            assert 0 <= adjacent < count, (section, name)
            assert 1 <= max_run <= count, (section, name)
            assert unique <= count - adjacent, (section, name)
            assert max_run <= adjacent + 1, (section, name)
            if unique == count:
                assert (adjacent, max_run) == (0, 1), (section, name)
            if adjacent == 0:
                assert max_run == 1, (section, name)


def _iter_contract_rows(
    compatibility: Mapping[str, object],
) -> dict[str, dict[str, Sequence[str]]]:
    """Reconstruct all row-contract inputs from frozen v5 literals."""
    quality_payload = cast(
        Mapping[str, object],
        json.loads(QUALITY_PATH.read_text(encoding="utf-8")),
    )
    literal_inputs = cast(
        Mapping[str, object], quality_payload["literal_inputs"]
    )
    direct = cast(dict[str, Sequence[str]], literal_inputs["cmaps_preview_32"])
    discrete = cast(
        Mapping[str, Mapping[str, Sequence[str]]], compatibility["discrete_hex"]
    )
    discrete_flat = {
        f"{name}/{size}": row
        for name, forms in discrete.items()
        for size, row in forms.items()
    }
    return {
        "palette": cast(dict[str, Sequence[str]], compatibility["palette"]),
        "direct_32": direct,
        "full_256": cast(dict[str, Sequence[str]], compatibility["cmaps256"]),
        "cycles": cast(dict[str, Sequence[str]], compatibility["cycles"]),
        "curated_rows": cast(
            dict[str, Sequence[str]], compatibility["curated_rows"]
        ),
        "dark_cycle": {
            "dark_cycle": cast(Sequence[str], compatibility["dark_cycle"])
        },
        "discrete_forward": discrete_flat,
    }


def _max_run_length(row: Sequence[str]) -> int:
    """Return the longest adjacent equal-value run in one frozen row."""
    longest = 0
    current = 0
    previous: str | None = None
    for value in row:
        current = current + 1 if value == previous else 1
        longest = max(longest, current)
        previous = value
    return longest


def test_every_v6_row_contract_matches_frozen_literals(
    v6_ssot: dict[str, object], compatibility: dict[str, object]
) -> None:
    """Derive hashes and duplicate topology only from immutable v5 rows."""
    contracts = cast(
        dict[str, dict[str, dict[str, object]]], v6_ssot["row_contracts"]
    )
    rows = _iter_contract_rows(compatibility)
    expected = {
        section: {
            name: {
                "adjacent_duplicate_count": sum(
                    left == right for left, right in pairwise(row)
                ),
                "canonical_sha256": _canonical_sha256(list(row)),
                "count": len(row),
                "max_run_length": _max_run_length(row),
                "unique_count": len(set(row)),
            }
            for name, row in source_rows.items()
        }
        for section, source_rows in rows.items()
    }

    assert contracts == expected


def test_v6_ssot_generator_is_byte_reproducible(tmp_path: Path) -> None:
    """Emit the packaged authority identically on repeated pinned input."""
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = [
        sys.executable,
        str(BUILDER_PATH),
        "--baseline-commit",
        BASELINE_COMMIT,
    ]
    for output in (first, second):
        process = subprocess.run(
            [*command, "--output", str(output)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert process.returncode == 0, process.stderr

    assert (
        first.read_bytes() == second.read_bytes() == V6_SSOT_PATH.read_bytes()
    )


@pytest.mark.parametrize(
    "path_name",
    ["V5_RECIPE_PATH", "COMPATIBILITY_PATH", "QUALITY_PATH", "ORACLE_PATH"],
)
def test_v6_builder_rejects_raw_source_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path_name: str
) -> None:
    """Fail before decoding any historical input whose raw bytes changed."""
    builder = _load_builder()
    changed = tmp_path / f"changed-{path_name}"
    changed.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(builder, path_name, changed)

    with pytest.raises(RuntimeError, match="raw SHA-256"):
        builder._build_payload(BASELINE_COMMIT)


def test_v6_builder_has_no_candidate_compiler_import_boundary() -> None:
    """Generate baselines from pinned literals without importing live colors."""
    tree = ast.parse(BUILDER_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    forbidden = {
        "dartwork_mpl",
        "dartwork_mpl._colors._catalog",
        "dartwork_mpl._colors._cmaps",
        "dartwork_mpl._colors._generate",
        "dartwork_mpl._colors._recipe",
    }
    assert imported.isdisjoint(forbidden)


def test_validated_accessor_returns_deeply_immutable_data(
    v6_ssot: dict[str, object],
) -> None:
    """Expose one cached read-only authority to every production consumer."""
    from dartwork_mpl._colors._ssot import load_color_v6_ssot

    loaded = load_color_v6_ssot()
    recipe = cast(Mapping[str, object], loaded["recipe"])
    family_params = cast(Mapping[str, object], recipe["family_params"])
    red = cast(Mapping[str, object], family_params["red"])

    assert _thaw(loaded) == v6_ssot
    assert load_color_v6_ssot() is loaded
    with pytest.raises(TypeError):
        cast(dict[str, object], recipe)["changed"] = True
    with pytest.raises(TypeError):
        cast(dict[str, object], red)["tone_floor"] = 0.0


def test_validated_accessor_rejects_section_hash_drift(tmp_path: Path) -> None:
    """Reject decoded-but-tampered packaged data before construction uses it."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    payload["recipe"]["constants"]["TONE_TOP"] = 0.5
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="section hash"):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_invalid_schema(tmp_path: Path) -> None:
    """Reject a self-consistent payload from an unknown schema generation."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    payload["schema"] = "dartwork-mpl.color-ssot/v999"
    payload["section_hashes"]["schema"] = _canonical_sha256(payload["schema"])
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema"):
        _ssot._load_color_v6_ssot(changed)


@pytest.mark.parametrize(
    "path",
    [
        ("recipe", "family_params", "red", "tone_floor"),
        ("recipe", "constants", "TONE_TOP"),
        ("coordinates", "relative_y_coefficients", 0),
        ("migration", "denominator"),
        ("policies", "gamut", "tolerance"),
    ],
)
def test_validated_accessor_rejects_non_finite_authority(
    tmp_path: Path, path: tuple[object, ...]
) -> None:
    """Reject NaN before accepting or comparing a stale section hash."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    _set_nested(payload, path, math.nan)
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="finite"):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_out_of_range_tone(tmp_path: Path) -> None:
    """Reject a finite recipe tone outside the NeutralTone value domain."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    payload["recipe"]["family_params"]["red"]["tone_floor"] = 1.1
    payload["section_hashes"]["recipe"] = _canonical_sha256(payload["recipe"])
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="tone"):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_pinned_provenance_drift(
    tmp_path: Path,
) -> None:
    """Reject a recomputed section hash that rewrites the accepted fixture."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    payload["baselines"]["quality"]["raw_sha256"] = "0" * 64
    payload["section_hashes"]["baselines"] = _canonical_sha256(
        payload["baselines"]
    )
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="provenance"):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_row_contract_cardinality(
    tmp_path: Path,
) -> None:
    """Reject a self-consistent section that no longer covers all 671 rows."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    del payload["row_contracts"]["palette"]["amber"]
    payload["section_hashes"]["row_contracts"] = _canonical_sha256(
        payload["row_contracts"]
    )
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="row contract"):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_malformed_row_contract_hash(
    tmp_path: Path,
) -> None:
    """Reject a self-consistent section with a non-SHA row identifier."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    payload["row_contracts"]["palette"]["amber"]["canonical_sha256"] = (
        "not-a-sha"
    )
    payload["section_hashes"]["row_contracts"] = _canonical_sha256(
        payload["row_contracts"]
    )
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="row contract"):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_invalid_multi_hue_index(
    tmp_path: Path,
) -> None:
    """Reject an out-of-LUT shipped index even with a recomputed section hash."""
    from dartwork_mpl._colors import _ssot

    payload = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    payload["multi_hue_discrete_indices"]["aurora"]["8"][0] = 256
    payload["section_hashes"]["multi_hue_discrete_indices"] = _canonical_sha256(
        payload["multi_hue_discrete_indices"]
    )
    changed = tmp_path / "color_v6_ssot.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="multi-hue"):
        _ssot._load_color_v6_ssot(changed)


@pytest.mark.parametrize(
    ("section", "path", "value"),
    [
        (
            "coordinates",
            ("coordinates", "relative_y_coefficients"),
            [0.21267287873271212, 0.7151521284847872],
        ),
        ("coordinates", ("coordinates", "validation_only"), "CIELAB"),
        ("migration", ("migration", "denominator"), 0.0),
        ("migration", ("migration", "toe_lstar"), -1.0),
        ("policies", ("policies", "gamut", "iterations"), 0),
        ("policies", ("policies", "gamut", "tolerance"), -1e-6),
        ("policies", ("policies", "tone", "luminance_search_iterations"), 0),
        ("policies", ("policies", "tone", "catalog_chroma_fraction"), 1.1),
    ],
)
def test_validated_accessor_rejects_self_consistent_malformed_authority(
    tmp_path: Path, section: str, path: tuple[object, ...], value: object
) -> None:
    """Reject bad coordinate, migration, and policy shapes or domains."""
    from dartwork_mpl._colors import _ssot

    payload = cast(
        dict[str, object], json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    )
    _set_nested(payload, path, value)
    changed = _write_rehashed_section(tmp_path, payload, section)

    with pytest.raises(RuntimeError):
        _ssot._load_color_v6_ssot(changed)


@pytest.mark.parametrize(
    "path",
    [
        ("compatibility", "canonical_hashes"),
        ("quality", "metrics"),
        ("quality", "global_extrema"),
        ("quality", "policy"),
        ("oracle", "raw_sha256"),
    ],
)
def test_validated_accessor_rejects_missing_baseline_authority(
    tmp_path: Path, path: tuple[str, str]
) -> None:
    """Require all exact, metric, policy, extrema, and oracle baseline leaves."""
    from dartwork_mpl._colors import _ssot

    payload = cast(
        dict[str, object], json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    )
    baselines = cast(dict[str, dict[str, object]], payload["baselines"])
    del baselines[path[0]][path[1]]
    changed = _write_rehashed_section(tmp_path, payload, "baselines")

    with pytest.raises(RuntimeError):
        _ssot._load_color_v6_ssot(changed)


def test_validated_accessor_rejects_impossible_duplicate_contract(
    tmp_path: Path,
) -> None:
    """Reject a row claiming all-unique values and adjacent duplicates."""
    from dartwork_mpl._colors import _ssot

    payload = cast(
        dict[str, object], json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    )
    row_contracts = cast(
        dict[str, dict[str, dict[str, object]]], payload["row_contracts"]
    )
    row = row_contracts["palette"]["amber"]
    row["unique_count"] = row["count"]
    row["adjacent_duplicate_count"] = 1
    changed = _write_rehashed_section(tmp_path, payload, "row_contracts")

    with pytest.raises(RuntimeError):
        _ssot._load_color_v6_ssot(changed)


def _module_tree(name: str) -> ast.Module:
    """Parse one color construction module without importing it."""
    path = REPO_ROOT / f"src/dartwork_mpl/_colors/{name}.py"
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assigned_names(tree: ast.AST) -> set[str]:
    """Collect direct module-level assignment target names."""
    names: set[str] = set()
    for node in cast(ast.Module, tree).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _called_names(tree: ast.AST) -> set[str]:
    """Collect simple and attribute call names from one parsed module."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _function_tree(module: ast.Module, name: str) -> ast.FunctionDef:
    """Return one named synchronous top-level function."""
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_recipe_ast_has_only_neutral_tone_lightness_names() -> None:
    """Remove legacy construction names and embedded recipe literals."""
    tree = _module_tree("_recipe")
    names = _assigned_names(tree)
    source = ast.unparse(tree).lower()

    assert {"TONE_TOP", "GRAY_TONE_FLOOR", "TONE_DERIVATION_GRID"} <= names
    assert not {"L_TOP", "GRAY_FLOOR"} & names
    assert "floor_k3" not in source.replace("tone_floor_k3", "")
    assert "legacy_lstar" not in source
    assert "116" not in source
    embedded_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FamilyParams"
        and any(isinstance(argument, ast.Constant) for argument in node.args)
    ]
    assert embedded_calls == []


def test_build_and_catalog_use_the_validated_v6_accessor() -> None:
    """Prevent recipe/index copies and candidate borrowing from v5 fixtures."""
    recipe_tree = _module_tree("_recipe")
    build_tree = _module_tree("_build")
    catalog_tree = _module_tree("_catalog")
    candidate_tree = _function_tree(catalog_tree, "compile_candidate_snapshot")

    assert "load_color_v6_ssot" in _called_names(recipe_tree)
    assert "load_color_v6_ssot" in _called_names(build_tree)
    assert "load_color_v6_ssot" in _called_names(candidate_tree)
    assert "load_v5_snapshot" not in _called_names(candidate_tree)


def test_candidate_provenance_hashes_all_v6_construction_authorities() -> None:
    """Include tone, gamut, accessor, and packaged v6 bytes in reports."""
    import dartwork_mpl._colors._catalog as _catalog
    import dartwork_mpl._colors._gamut as _gamut
    import dartwork_mpl._colors._ssot as _ssot
    import dartwork_mpl._colors._tone as _tone

    source_hashes = _catalog._candidate_source_hashes()
    paths = {
        "src/dartwork_mpl/_colors/_gamut.py": Path(_gamut.__file__),
        "src/dartwork_mpl/_colors/_ssot.py": Path(_ssot.__file__),
        "src/dartwork_mpl/_colors/_tone.py": Path(_tone.__file__),
        "src/dartwork_mpl/asset/color/color_v6_ssot.json": V6_SSOT_PATH,
    }

    assert {name: source_hashes[name] for name in paths} == {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }


def test_v6_json_is_the_only_python_recipe_and_index_authority() -> None:
    """Keep full recipe and multi-hue index literals out of production Python."""
    recipe_tree = _module_tree("_recipe")
    catalog_tree = _module_tree("_catalog")
    recipe_dicts = [
        node
        for node in ast.walk(recipe_tree)
        if isinstance(node, ast.Dict) and len(node.keys) >= 7
    ]
    index_lists = [
        node
        for node in ast.walk(catalog_tree)
        if isinstance(node, (ast.List, ast.Tuple))
        and len(node.elts) >= 8
        and all(
            isinstance(item, ast.Constant) and isinstance(item.value, int)
            for item in node.elts
        )
    ]

    assert recipe_dicts == []
    assert index_lists == []


def _ast_identifiers(tree: ast.AST) -> set[str]:
    """Collect imported, declared, referenced, called, and argument names."""
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            identifiers.add(node.name)
        elif isinstance(node, ast.arg):
            identifiers.add(node.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            identifiers.update(
                alias.asname or alias.name for alias in node.names
            )
    return identifiers


NORMATIVE_CONSTRUCTION_MODULES = (
    "_recipe",
    "_generate",
    "_cmaps",
    "_tone",
    "_discrete",
)
VALIDATION_ONLY_MODULES = frozenset(
    {"_compatibility_metrics", "_gates", "_metrics"}
)


def _imported_module_names(tree: ast.AST) -> set[str]:
    """Collect terminal module and imported-object names from imports."""
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            candidates = [alias.name for alias in node.names]
            if node.module is not None:
                candidates.append(node.module)
        else:
            continue
        imported.update(name.rsplit(".", maxsplit=1)[-1] for name in candidates)
    return imported


def _construction_symbol_names(tree: ast.AST) -> set[str]:
    """Collect AST identifiers plus unaliased source names from imports."""
    symbols = _ast_identifiers(tree)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for alias in node.names:
            symbols.add(alias.name.rsplit(".", maxsplit=1)[-1])
            if alias.asname is not None:
                symbols.add(alias.asname)
    return {name.lower() for name in symbols}


def _is_validation_construction_symbol(name: str) -> bool:
    """Return whether one identifier names a CIELAB, CIEDE, or CVD tool."""
    normalized = name.lower().strip("_")
    compact = normalized.replace("_", "")
    tokens = normalized.split("_")
    return (
        "cielab" in compact
        or "ciede" in compact
        or "de2000" in compact
        or "de00" in compact
        or "deltae00" in compact
        or "cvd" in tokens
        or "lab" in tokens
    )


def _construction_boundary_violations(tree: ast.AST) -> set[str]:
    """Return validation-only imports and construction symbols in one AST."""
    imports = _imported_module_names(tree) & VALIDATION_ONLY_MODULES
    symbols = {
        name
        for name in _construction_symbol_names(tree)
        if _is_validation_construction_symbol(name)
    }
    violations = {f"import:{name}" for name in imports}
    violations.update(f"symbol:{name}" for name in symbols)
    return violations


def test_construction_boundary_detector_reads_ast_not_provenance_text() -> None:
    """Detect real imports/names while ignoring prose strings and comments."""
    tree = ast.parse(
        '''"""CIELAB, CIEDE2000, and CVD provenance only."""

# CVD and CIEDE2000 remain valid historical words in comments.
PROVENANCE = "CIELAB reference only"
from . import _metrics
from ._compatibility_metrics import de2000_hex as compatibility_distance
from ._gates import evaluate_catalog
from ._conversion import lab_from_rgb


def construct(cvd_rgb):
    return color.ciede2000(lab_from_rgb(cvd_rgb))
'''
    )

    assert _construction_boundary_violations(tree) == {
        "import:_compatibility_metrics",
        "import:_gates",
        "import:_metrics",
        "symbol:ciede2000",
        "symbol:cvd_rgb",
        "symbol:de2000_hex",
        "symbol:lab_from_rgb",
    }


@pytest.mark.parametrize("module_name", NORMATIVE_CONSTRUCTION_MODULES)
def test_normative_construction_boundary_excludes_validation_oracles(
    module_name: str,
) -> None:
    """Keep all five construction modules independent of validation oracles."""
    assert _construction_boundary_violations(_module_tree(module_name)) == set()


def test_palette_and_cmap_construction_ast_is_oklab_y_only() -> None:
    """Remove transitional L*/CIE/CVD solvers and legacy lightness names."""
    forbidden_exact = {
        "_compatibility_level",
        "ciede2000",
        "cvd_rgb",
        "gamut_max_chroma",
        "lab_from_rgb",
        "lab_l_hex",
        "lab_l_rgb",
        "solve_swatch_rgb",
    }
    forbidden_lightness = {
        "l_bot",
        "l_center",
        "l_end",
        "l_seam",
        "l_start",
        "l_t",
        "l_target",
        "l_top",
    }

    for module_name in ("_generate", "_cmaps"):
        tree = _module_tree(module_name)
        identifiers = {name.lower() for name in _ast_identifiers(tree)}
        cie_identifiers = {
            name
            for name in identifiers
            if "cielab" in name
            or "ciede" in name
            or name.startswith("cvd_")
            or name.startswith("lab_")
        }
        assert identifiers.isdisjoint(forbidden_exact), module_name
        assert identifiers.isdisjoint(forbidden_lightness), module_name
        assert cie_identifiers == set(), module_name

    generate_calls = _called_names(_module_tree("_generate"))
    cmap_calls = _called_names(_module_tree("_cmaps"))
    assert "render_oklch_at_tone" in generate_calls
    assert {"render_oklch_at_tone", "max_chroma_at_tone"} <= cmap_calls


def test_removed_legacy_solver_names_are_not_module_attributes() -> None:
    """Prevent private callers from keeping the transitional route alive."""
    from dartwork_mpl._colors import _cmaps, _generate

    forbidden = {"_compatibility_level", "gamut_max_chroma", "solve_swatch_rgb"}

    assert all(not hasattr(_generate, name) for name in forbidden)
    assert all(not hasattr(_cmaps, name) for name in forbidden)


def test_blue_red_shipped_mean_is_not_embedded_in_cmap_source() -> None:
    """Force blue_red tone to derive from the supplied locked palette."""
    constants = {
        node.value
        for node in ast.walk(_module_tree("_cmaps"))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    }

    assert 0.6635425400424864 not in constants


# Task 7: discrete construction consumes frozen v6 indices, never CIE gates.
def _large_integer_sequences(tree: ast.AST) -> list[ast.List | ast.Tuple]:
    """Find copied index-table rows large enough to hide a shipped form."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.List, ast.Tuple))
        and len(node.elts) >= 8
        and all(
            isinstance(item, ast.Constant)
            and isinstance(item.value, int)
            and not isinstance(item.value, bool)
            for item in node.elts
        )
    ]


def test_discrete_construction_ast_has_no_cie_or_legacy_optimizer() -> None:
    """Remove validation metrics, candidate search, and optimizer caches."""
    tree = _module_tree("_discrete")
    identifiers = {name.lower() for name in _ast_identifiers(tree)}
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden_modules = {"_compatibility_metrics", "_gates", "_metrics"}
    forbidden_identifiers = {
        "_candidate_data",
        "_candidatedata",
        "_compatible_masks",
        "_first_ordered_clique",
        "_multi_hue_tuple",
        "cache",
        "de2000_hex",
        "lab_from_rgb",
        "lab_l_hex",
        "multi_hue_min_de00_floors",
    }
    validation_identifiers = {
        name
        for name in identifiers
        if "cielab" in name
        or "ciede" in name
        or "de2000" in name
        or "de00" in name
        or "cvd" in name
        or name.startswith("lab_")
    }

    assert imported_modules.isdisjoint(forbidden_modules)
    assert identifiers.isdisjoint(forbidden_identifiers)
    assert validation_identifiers == set()


def test_discrete_multi_hue_reads_generated_indices_and_lut() -> None:
    """Make shipped multi-hue selection a lookup rather than an objective."""
    tree = _module_tree("_discrete")
    function = _function_tree(tree, "_multi_hue")
    identifiers = _ast_identifiers(function)

    assert {"MULTI_HUE_DISCRETE_INDICES", "CMAPS_256"} <= identifiers


def test_build_reads_v6_indices_from_the_validated_accessor() -> None:
    """Generate the frozen table from the packaged v6 authority."""
    build_tree = _module_tree("_build")
    build_source = ast.unparse(build_tree)

    assert "load_color_v6_ssot" in _called_names(build_tree)
    assert "multi_hue_discrete_indices" in build_source
    assert "MULTI_HUE_DISCRETE_INDICES" in build_source


def test_candidate_reads_v6_indices_without_borrowing_the_v5_baseline() -> None:
    """Make a broken candidate manifest visible to exact comparison."""
    catalog_tree = _module_tree("_catalog")
    candidate_tree = _function_tree(catalog_tree, "compile_candidate_snapshot")
    candidate_source = ast.unparse(candidate_tree)

    assert "load_color_v6_ssot" in _called_names(candidate_tree)
    assert "multi_hue_discrete_indices" in candidate_source
    assert "load_v5_snapshot" not in _called_names(candidate_tree)


def test_build_and_catalog_do_not_copy_large_index_rows() -> None:
    """Keep the packaged v6 JSON as the sole multi-hue index literal."""
    build_tree = _module_tree("_build")
    catalog_tree = _module_tree("_catalog")

    assert _large_integer_sequences(build_tree) == []
    assert _large_integer_sequences(catalog_tree) == []


@pytest.mark.parametrize(
    "corruption", ["family", "size", "length", "boolean", "order"]
)
def test_validated_accessor_rejects_malformed_multi_hue_manifest(
    tmp_path: Path, corruption: str
) -> None:
    """Reject family, size, length, integer, and ordering corruption."""
    from dartwork_mpl._colors import _ssot

    payload = cast(
        dict[str, object], json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    )
    manifest = cast(
        dict[str, dict[str, list[int]]], payload["multi_hue_discrete_indices"]
    )
    if corruption == "family":
        del manifest["lava"]
    elif corruption == "size":
        del manifest["aurora"]["8"]
    elif corruption == "length":
        manifest["aurora"]["8"].pop()
    elif corruption == "boolean":
        manifest["aurora"]["8"][0] = cast(int, True)
    else:
        manifest["aurora"]["8"][1] = manifest["aurora"]["8"][0]
    changed = _write_rehashed_section(
        tmp_path, payload, "multi_hue_discrete_indices"
    )

    with pytest.raises(RuntimeError, match="multi-hue"):
        _ssot._load_color_v6_ssot(changed)
