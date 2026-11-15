"""Catalog-only tests for the v5/v6 color comparison boundary."""

import ast
import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

import dartwork_mpl._colors._compatibility_metrics as oracle
import dartwork_mpl._colors.construction._catalog as _catalog
import dartwork_mpl._colors.verify._comparison as _comparison
import dartwork_mpl._colors.verify._gates as _gates
from dartwork_mpl._colors.construction import _cmaps, _generate
from tests.support.repo_files import read_repo_text

EXACT_FIELDS = (
    "palette",
    "cycles",
    "cmaps_256",
    "curated_rows",
    "diverging_canonicals",
    "semantic_coordinates",
    "semantic_colors",
    "dark_cycle_coordinates",
    "dark_cycle",
    "taxonomy",
    "registrations",
    "typing_literals",
    "mcp_discovery",
    "public_inventory",
    "discrete_hex",
    "reverse_discrete_hex",
    "multi_hue_discrete_indices",
    "vendor_colors",
)
EXPECTED_HASHES = {
    "palette": (
        "4431b8d1accbeca9527e6097a62c048a51fd6fd699588998c202c359b98b458e"
    ),
    "cycles": (
        "cda50ebd800a44dbb3b8d58a4fe53924ecaf914f7dbadbc2ac196e77cf6595cd"
    ),
    "cmaps_256": (
        "e026ce047dd8a186299b2857e3d8c81f2b2bc4b7249df37f35b7c0093c5240c1"
    ),
    "vendor_colors": (
        "6dc6053c4f8c66adb9d7deb746c3e7eee0295c27cc107b37c872b46f83f79a72"
    ),
}
QUALITY_INPUT = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_quality.json"
)


def _canonical_hash(value: object) -> str:
    """Return a sorted compact-JSON SHA-256 digest."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@pytest.fixture(scope="module")
def baseline_catalog() -> "_catalog.CatalogSnapshot":
    """Load the immutable v5 catalog once for catalog tests."""
    return _catalog.load_v5_snapshot()


def test_current_catalog_matches_frozen_v5_exactly(
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Match every exact surface while keeping preview LUTs candidate-only."""
    mismatches = [
        field
        for field in EXACT_FIELDS
        if getattr(candidate_catalog, field) != getattr(baseline_catalog, field)
    ]

    assert (
        mismatches,
        dict(baseline_catalog.cmaps_preview_32),
        dict(baseline_catalog.cmaps_unlocked_preview_32),
        {len(row) for row in candidate_catalog.cmaps_preview_32.values()},
        {
            len(row)
            for row in candidate_catalog.cmaps_unlocked_preview_32.values()
        },
    ) == ([], {}, {}, {32}, {32})
    assert set(candidate_catalog.cmaps_unlocked_preview_32) == set(
        candidate_catalog.cmaps_preview_32
    )


def test_candidate_catalog_pins_canonical_compiler_digests(
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Keep generated rows and parsed vendor values byte-for-byte canonical."""
    payload = candidate_catalog.thaw()
    actual = {
        field: _canonical_hash(payload[field]) for field in EXPECTED_HASHES
    }

    assert actual == EXPECTED_HASHES


def test_candidate_catalog_has_complete_inventory(
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Derive all compatibility inventory counts from candidate surfaces."""
    color_names = candidate_catalog.typing_literals["color_names"]
    inventory = {
        "palette_positions": sum(
            len(row) for row in candidate_catalog.palette.values()
        ),
        "cycle_positions": sum(
            len(row) for row in candidate_catalog.cycles.values()
        ),
        "cmap_positions": sum(
            len(row) for row in candidate_catalog.cmaps_256.values()
        ),
        "qualitative_families": sum(
            kind == "qualitative"
            for kind in candidate_catalog.taxonomy.values()
        ),
        "families": len(candidate_catalog.taxonomy),
        "registered_colormaps": len(candidate_catalog.registrations),
        "dc_tokens": sum(name.startswith("dc.") for name in color_names),
        "vendor_tokens": sum(
            not name.startswith("dc.") for name in color_names
        ),
        "discrete_forms": sum(
            len(forms) for forms in candidate_catalog.discrete_hex.values()
        ),
    }

    assert inventory == {
        "palette_positions": 200,
        "cycle_positions": 16,
        "cmap_positions": 11008,
        "qualitative_families": 13,
        "families": 56,
        "registered_colormaps": 99,
        "dc_tokens": 380,
        "vendor_tokens": 892,
        "discrete_forms": 547,
    }


def test_snapshot_defensively_freezes_retained_inputs(
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Detach nested values from caller-owned mutable payload containers."""
    payload = baseline_catalog.thaw()
    palette = cast(dict[str, list[str]], payload["palette"])
    inventory = cast(list[dict[str, object]], payload["public_inventory"])
    nested = {"labels": ["original"]}
    inventory[0]["nested"] = nested
    snapshot = _catalog.CatalogSnapshot.from_payload(payload)
    original = snapshot.palette["amber"][0]

    palette["amber"][0] = "#000000"
    nested["labels"].append("mutated")

    thawed_inventory = cast(
        list[dict[str, object]], snapshot.thaw()["public_inventory"]
    )
    frozen_nested = cast(dict[str, list[str]], thawed_inventory[0]["nested"])
    assert (snapshot.palette["amber"][0], frozen_nested) == (
        original,
        {"labels": ["original"]},
    )
    with pytest.raises(TypeError):
        cast(dict[str, tuple[str, ...]], snapshot.palette)["new"] = ()


def test_snapshot_rejects_non_finite_nested_values_while_freezing(
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Fail at construction instead of creating a non-serializable snapshot."""
    payload = baseline_catalog.thaw()
    inventory = cast(list[dict[str, object]], payload["public_inventory"])
    inventory[0]["diagnostic"] = {"score": math.nan}

    with pytest.raises(ValueError, match="finite"):
        _catalog.CatalogSnapshot.from_payload(payload)


def test_snapshot_is_frozen_slotted_and_serializes_deterministically(
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Expose a stable JSON thaw without a mutable instance dictionary."""
    first = baseline_catalog.to_json()
    second = baseline_catalog.to_json()

    assert (
        dataclasses.is_dataclass(baseline_catalog),
        hasattr(baseline_catalog, "__dict__"),
        first == second,
        first.endswith("\n"),
        json.loads(first) == baseline_catalog.thaw(),
    ) == (True, False, True, True, True)


def test_v5_loader_rejects_manifest_whose_raw_sha_drifted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a coordinated manifest edit before decoding its surfaces."""
    tampered = tmp_path / "color_v5_compatibility.json"
    tampered.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(_catalog, "_V5_COMPAT_PATH", tampered)

    with pytest.raises(RuntimeError, match="SHA-256"):
        _catalog.load_v5_snapshot()


def test_candidate_mutations_reach_derived_consumers(
    monkeypatch: pytest.MonkeyPatch,
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Propagate live compiler changes into semantic, discrete, and typing data."""
    baseline = baseline_catalog.thaw()
    palette = cast(dict[str, list[str]], baseline["palette"])
    cmaps = cast(dict[str, list[str]], baseline["cmaps_256"])
    palette["green"][6] = "#010203"
    palette["candidate"] = list(palette["green"])
    cmaps["candidate"] = list(cmaps["green"])

    compiler_calls: list[tuple[int, bool]] = []

    def compile_palette(*, luminance_lock: bool = True) -> dict[str, list[str]]:
        """Return a deliberately changed compiler palette."""
        assert luminance_lock is True
        return palette

    def compile_cmaps(
        candidate_palette: dict[str, list[str]],
        n: int = 256,
        *,
        luminance_lock: bool = True,
    ) -> dict[str, list[str]]:
        """Return changed locked LUTs and candidate-only direct previews."""
        assert candidate_palette is palette
        compiler_calls.append((n, luminance_lock))
        if n == 256:
            assert luminance_lock is True
            return cmaps
        rows = {
            name: [row[round(index * 255 / 31)] for index in range(32)]
            for name, row in cmaps.items()
        }
        if not luminance_lock:
            rows["green"][0] = "#ffffff"
        return rows

    monkeypatch.setattr(_generate, "compile_palette", compile_palette)
    monkeypatch.setattr(_cmaps, "compile_cmaps", compile_cmaps)

    candidate = _catalog.compile_candidate_snapshot()

    assert (
        candidate.semantic_colors["default"]["dc.pos"],
        candidate.discrete_hex["green"]["10"][6],
        "dc.candidate0" in candidate.typing_literals["color_names"],
        "candidate" in candidate.discrete_hex,
        compiler_calls,
        candidate.cmaps_unlocked_preview_32["green"][0],
    ) == (
        "#010203",
        "#010203",
        True,
        True,
        [(32, True), (256, True), (32, False)],
        "#ffffff",
    )


@pytest.mark.color_pipeline
def test_candidate_snapshot_isolates_unlocked_compiler_failure(
    monkeypatch: pytest.MonkeyPatch,
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Keep a diagnostic-only compiler failure outside locked validation."""
    baseline = baseline_catalog.thaw()
    palette = cast(dict[str, list[str]], baseline["palette"])
    full = cast(dict[str, list[str]], baseline["cmaps_256"])
    literal_inputs = cast(
        dict[str, object], _quality_payload()["literal_inputs"]
    )
    direct = cast(dict[str, list[str]], literal_inputs["cmaps_preview_32"])

    def compile_palette(*, luminance_lock: bool = True) -> dict[str, list[str]]:
        assert luminance_lock is True
        return palette

    def compile_cmaps(
        candidate_palette: dict[str, list[str]],
        n: int = 256,
        *,
        luminance_lock: bool = True,
    ) -> dict[str, list[str]]:
        assert candidate_palette is palette
        if not luminance_lock:
            raise RuntimeError("unlocked diagnostic unavailable")
        if n == 256:
            return full
        return direct

    monkeypatch.setattr(_generate, "compile_palette", compile_palette)
    monkeypatch.setattr(_cmaps, "compile_cmaps", compile_cmaps)

    candidate = _catalog.compile_candidate_snapshot()
    exact = _comparison.compare_exact_surfaces(baseline_catalog, candidate)
    report = _comparison.compare_catalog(baseline_catalog, candidate)
    explanatory = cast(dict[str, object], report.to_payload()["explanatory"])
    unlocked = cast(dict[str, object], explanatory["direct_oklch_unlocked"])

    assert sum(row.mismatch_count for row in exact.values()) == 0
    assert candidate.cmaps_unlocked_preview_32 == {}
    assert candidate.cmaps_unlocked_preview_error == (
        "RuntimeError: unlocked diagnostic unavailable"
    )
    assert (report.passed, unlocked["available"], unlocked["gate_input"]) == (
        True,
        False,
        False,
    )
    assert unlocked["error"] == candidate.cmaps_unlocked_preview_error


_COLORS_SOURCE_DIR = Path(oracle.__file__).resolve().parent


def _color_import_closure(start: Path) -> tuple[set[str], set[str]]:
    """Follow relative imports from ``start`` through ``_colors/`` sources.

    Returns the stems of the reached ``_colors`` modules and packages, and the
    top-level names of every absolute import met on the way.
    """
    colors_dir = _COLORS_SOURCE_DIR
    pending = [start]
    visited: set[Path] = set()
    imported: set[str] = set()
    external: set[str] = set()
    while pending:
        source_path = pending.pop()
        if source_path in visited:
            continue
        visited.add(source_path)
        # A sub-package module runs its package initializer first. The
        # ``_colors`` root initializer is not followed: the build and the
        # isolated audit load these sources without it.
        package_init = source_path.parent / "__init__.py"
        if source_path.parent != colors_dir and package_init.is_file():
            pending.append(package_init)
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                external.update(
                    alias.name.split(".")[0] for alias in node.names
                )
                continue
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level == 0:
                if node.module is not None:
                    external.add(node.module.split(".")[0])
                continue
            base = source_path.parent
            for _ in range(node.level - 1):
                base = base.parent
            module_names = (
                [f"{node.module}.{alias.name}" for alias in node.names]
                if node.module is not None
                else [alias.name for alias in node.names]
            )
            for module_name in module_names:
                # Follow every prefix naming a module or package below
                # ``_colors/``: importing a sub-package module also runs its
                # package initializer.
                parts = module_name.split(".")
                for end in range(1, len(parts) + 1):
                    stem = base.joinpath(*parts[:end])
                    target = (
                        stem / "__init__.py"
                        if stem.is_dir()
                        else stem.with_suffix(".py")
                    )
                    if target.is_file() and target.is_relative_to(colors_dir):
                        imported.add(parts[end - 1])
                        pending.append(target)
    return imported, external


def test_catalog_import_boundary_excludes_generated_candidate_surfaces() -> (
    None
):
    """Keep the complete candidate import closure outside circular modules."""
    assert _catalog.__file__ is not None
    imported, _external = _color_import_closure(Path(_catalog.__file__))
    forbidden = {
        "_generated",
        "_semantic",
        "_families",
        "_discrete",
        "_register",
        "_loader",
        "_typing",
    }

    assert imported.isdisjoint(forbidden)


def test_comparison_module_never_imports_or_calls_live_compilers() -> None:
    """Keep diagnostics structural so catalog compilation remains one-way."""
    assert _comparison.__file__ is not None
    tree = ast.parse(Path(_comparison.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)

    assert not any(
        name.endswith(("._generate", "._cmaps")) for name in imported
    )
    assert {"compile_palette", "compile_cmaps"}.isdisjoint(called)


def test_comparison_source_has_real_unlocked_diagnostics_not_placeholder() -> (
    None
):
    """Require the Task 6 explanatory JSON and dedicated HTML panel."""
    assert _comparison.__file__ is not None
    source = Path(_comparison.__file__).read_text(encoding="utf-8")

    assert "not_available_before_task_6" not in source
    assert "explanatory-placeholder" not in source
    for marker in (
        "cmaps_unlocked_preview_32",
        'data-panel="luminance-lock-comparison"',
        'data-strip="locked-direct32"',
        'data-strip="unlocked-direct32"',
        'data-profile="lock-oklab-l"',
        'data-profile="lock-relative-y"',
        'data-profile="lock-neighbor-delta-e"',
    ):
        assert marker in source


def test_comparison_snapshot_protocol_declares_unlocked_preview_rows() -> None:
    """Type the diagnostic input without importing the concrete catalog."""
    assert "vendor_colors" in _comparison.CatalogSnapshot.__dict__
    assert "cmaps_unlocked_preview_32" in _comparison.CatalogSnapshot.__dict__
    assert (
        "cmaps_unlocked_preview_error" in _comparison.CatalogSnapshot.__dict__
    )


def test_vendor_and_mcp_loaders_match_frozen_discovery(
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Parse bundled vendor assets and MCP decorator source without registries."""
    vendor_colors = _catalog.load_vendor_colors()
    vendor_names = _catalog.load_vendor_color_names()
    discovery = _catalog.project_legacy_mcp_discovery(
        _catalog.scan_mcp_discovery()
    )

    assert (
        len(vendor_colors),
        len(vendor_names),
        vendor_names == tuple(vendor_colors),
        all(
            isinstance(value, str)
            and value == value.lower()
            and len(value) == 7
            and value.startswith("#")
            for value in vendor_colors.values()
        ),
        all(not name.startswith("dc.") for name in vendor_names),
        discovery,
    ) == (892, 892, True, True, True, baseline_catalog.mcp_discovery)
    assert vendor_colors == baseline_catalog.vendor_colors


def test_vendor_json_parser_rejects_normalized_name_collisions(
    tmp_path: Path,
) -> None:
    """Reject duplicate tokens even when distinct family labels normalize alike."""
    parser = getattr(_catalog, "_vendor_json_colors", None)
    assert callable(parser)
    source = tmp_path / "collision.json"
    source.write_text(
        json.dumps(
            {"Blue Gray": [["50", "abcdef"]], "BlueGray": [["50", "123456"]]}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate vendor color"):
        parser(source, "tw")


def test_vendor_json_parser_rejects_non_rgb_hex(tmp_path: Path) -> None:
    """Reject malformed vendor values before they enter an exact surface."""
    parser = getattr(_catalog, "_vendor_json_colors", None)
    assert callable(parser)
    source = tmp_path / "malformed.json"
    source.write_text(json.dumps({"Blue": [["50", "abc"]]}), encoding="utf-8")

    with pytest.raises(ValueError, match="six-digit RGB hex"):
        parser(source, "tw")


@pytest.mark.parametrize(
    ("decorator", "field", "arguments"),
    (
        ("tool", "tool_names", 'name="public_alias"'),
        ("tool", "tool_names", '"public_alias"'),
        ("prompt", "prompt_names", 'name="public_alias"'),
        ("prompt", "prompt_names", '"public_alias"'),
    ),
)
def test_mcp_source_scanner_uses_literal_public_name_override(
    decorator: str, field: str, arguments: str, tmp_path: Path
) -> None:
    """Freeze FastMCP's public alias rather than the Python implementation name."""
    source = tmp_path / "surface.py"
    source.write_text(
        f"@mcp.{decorator}({arguments})\ndef internal_name():\n    pass\n",
        encoding="utf-8",
    )

    visitor = _catalog._scan_mcp_source(source)

    assert getattr(visitor, field) == ["public_alias"]


def test_mcp_source_scanner_rejects_dynamic_public_name(tmp_path: Path) -> None:
    """Fail closed when offline discovery cannot know the runtime identity."""
    source = tmp_path / "surface.py"
    source.write_text(
        "@mcp.tool(name=PUBLIC_NAME)\ndef internal_name():\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="MCP tool name must be literal"):
        _catalog._scan_mcp_source(source)


def _quality_payload() -> dict[str, object]:
    """Load the immutable quality fixture for comparison assertions."""
    decoded = json.loads(read_repo_text(QUALITY_INPUT))
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


def _mutate_exact_field(
    snapshot: "_catalog.CatalogSnapshot", field: str
) -> "_catalog.CatalogSnapshot":
    """Return a snapshot with one leaf changed in the requested exact field."""
    payload = snapshot.thaw()
    if field in {
        "palette",
        "cycles",
        "cmaps_256",
        "curated_rows",
        "diverging_canonicals",
    }:
        hex_rows = cast(dict[str, list[str]], payload[field])
        name = sorted(hex_rows)[0]
        hex_rows[name][0] = "#010203"
    elif field == "semantic_coordinates":
        semantic_coordinates = cast(
            dict[str, dict[str, list[object]]], payload[field]
        )
        semantic_coordinates["default"]["dc.pos"][1] = 5
    elif field == "semantic_colors":
        semantic_colors = cast(dict[str, dict[str, str]], payload[field])
        semantic_colors["default"]["dc.pos"] = "#010203"
    elif field == "dark_cycle_coordinates":
        dark_coordinates = cast(list[list[object]], payload[field])
        dark_coordinates[0][1] = 4
    elif field == "dark_cycle":
        dark_colors = cast(list[str], payload[field])
        dark_colors[0] = "#010203"
    elif field == "taxonomy":
        taxonomy = cast(dict[str, str], payload[field])
        name = sorted(taxonomy)[0]
        taxonomy[name] = "cyclic"
    elif field == "registrations":
        registrations = cast(list[str], payload[field])
        registrations.append("dc.injected")
    elif field in {"typing_literals", "mcp_discovery"}:
        string_rows = cast(dict[str, list[str]], payload[field])
        name = sorted(string_rows)[0]
        string_rows[name].append("injected")
    elif field == "public_inventory":
        inventory = cast(list[dict[str, object]], payload[field])
        inventory[0]["name"] = "injected"
    elif field in {"discrete_hex", "reverse_discrete_hex"}:
        nested_hex_rows = cast(dict[str, dict[str, list[str]]], payload[field])
        name = sorted(nested_hex_rows)[0]
        size = sorted(nested_hex_rows[name], key=int)[0]
        nested_hex_rows[name][size][0] = "#010203"
    elif field == "multi_hue_discrete_indices":
        index_rows = cast(dict[str, dict[str, list[int]]], payload[field])
        name = sorted(index_rows)[0]
        index_rows[name]["1"][0] = (index_rows[name]["1"][0] + 1) % 256
    elif field == "vendor_colors":
        vendor_colors = cast(dict[str, str], payload[field])
        vendor_colors["oc.gray0"] = "#010203"
    else:
        raise AssertionError(f"unsupported exact field: {field}")
    return _catalog.CatalogSnapshot.from_payload(payload)


@pytest.fixture(scope="module")
def comparison_report(
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> "_comparison.ComparisonReport":
    """Build one complete real report for renderer and serialization tests."""
    return _comparison.compare_catalog(baseline_catalog, candidate_catalog)


def test_snapshot_exact_payload_declares_all_contract_fields_once(
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Expose one normalized exact view without provenance or preview data."""
    payload = baseline_catalog.exact_payload()

    assert tuple(payload) == EXACT_FIELDS
    assert "cmaps_unlocked_preview_32" not in payload


def test_pristine_comparison_passes_every_exact_and_quality_gate(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Accept the live compiler only when exact and raw quality both match."""
    assert (
        comparison_report.passed,
        comparison_report.total_exact_mismatches,
        comparison_report.total_hex_mismatches,
        comparison_report.quality.baseline_matches_fixture,
        comparison_report.quality.violations,
    ) == (True, 0, 0, True, ())


def test_comparator_reports_one_lut_mutation_with_raw_metrics(
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Locate a changed LUT index and retain nonzero independent metrics."""
    aurora = list(candidate_catalog.cmaps_256["aurora"])
    aurora[127] = "#000000"
    mutated = dataclasses.replace(
        candidate_catalog,
        cmaps_256={**candidate_catalog.cmaps_256, "aurora": tuple(aurora)},
    )

    report = _comparison.compare_catalog(baseline_catalog, mutated)
    row = report.cmaps_256["aurora"]

    assert report.passed is False
    assert row.mismatch_indices == (127,)
    assert row.mismatch_count == 1
    assert row.delta_e_ok is not None and row.delta_e_ok.max > 0.0
    assert row.absolute_delta_y is not None and row.absolute_delta_y.max > 0.0


@pytest.mark.parametrize("field", EXACT_FIELDS)
def test_exact_comparator_detects_one_leaf_in_every_surface(
    field: str, baseline_catalog: "_catalog.CatalogSnapshot"
) -> None:
    """Cover all 18 exact surfaces rather than only generated hex tables."""
    mutated = _mutate_exact_field(baseline_catalog, field)

    result = _comparison.compare_exact_surfaces(baseline_catalog, mutated)

    assert result[field].mismatch_count >= 1


def test_vendor_value_mutation_fails_with_json_pointer_leaf(
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Turn one shipped vendor-value drift into one exact failing violation."""
    payload = candidate_catalog.thaw()
    vendor_colors = cast(dict[str, str], payload["vendor_colors"])
    vendor_colors["oc.gray0"] = "#010203"
    mutated = _catalog.CatalogSnapshot.from_payload(payload)

    exact = _comparison.compare_exact_surfaces(baseline_catalog, mutated)
    report = _comparison.compare_catalog(baseline_catalog, mutated)

    assert len(exact) == 18
    assert [item.path for item in exact["vendor_colors"].mismatches] == [
        "/vendor_colors/oc.gray0"
    ]
    assert report.passed is False
    assert report.total_exact_mismatches == 1
    assert any(
        item.surface == "vendor_colors"
        and item.path == "/vendor_colors/oc.gray0"
        for item in report.violations
    )


def test_exact_comparator_reports_missing_extra_and_length_paths_sorted(
    baseline_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Represent shape drift as stable JSON pointers instead of crashing."""
    payload = baseline_catalog.thaw()
    palette = cast(dict[str, list[str]], payload["palette"])
    palette["amber"].pop()
    palette["injected"] = ["#010203"]
    mutated = _catalog.CatalogSnapshot.from_payload(payload)

    result = _comparison.compare_exact_surfaces(baseline_catalog, mutated)
    paths = tuple(item.path for item in result["palette"].mismatches)

    assert paths == tuple(sorted(paths))
    assert "/palette/amber/9" in paths
    assert "/palette/injected/0" in paths


def test_invalid_candidate_hex_is_a_failing_report_not_oracle_failure(
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Keep a representable malformed candidate leaf in the exit-one domain."""
    aurora = list(candidate_catalog.cmaps_256["aurora"])
    aurora[127] = "not-a-color"
    mutated = dataclasses.replace(
        candidate_catalog,
        cmaps_256={**candidate_catalog.cmaps_256, "aurora": tuple(aurora)},
    )

    report = _comparison.compare_catalog(baseline_catalog, mutated)

    assert report.passed is False
    assert report.cmaps_256["aurora"].mismatch_indices == (127,)
    assert any(
        item.code == "candidate_quality_invalid" for item in report.violations
    )


def test_quality_gate_uses_raw_values_below_display_precision(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Fail a tiny raw categorical regression that displays identically."""
    quality_payload = comparison_report.quality.to_payload()
    baseline = cast(dict[str, object], quality_payload["baseline_metrics"])
    candidate = json.loads(json.dumps(baseline))
    raw = candidate["cycles"]["octave"]["normal_min_delta_e00"]
    assert isinstance(raw, float)
    candidate["cycles"]["octave"]["normal_min_delta_e00"] = raw - 1e-9
    assert round(raw, 6) == round(raw - 1e-9, 6)

    violations = _comparison.compare_quality_metrics(
        baseline, cast(dict[str, object], candidate), comparison_report.taxonomy
    )

    assert any("normal_min_delta_e00" in item.path for item in violations)


@pytest.mark.parametrize(
    ("section", "name"),
    (("cmaps_direct_32", "blue_red"), ("cmaps_full_256", "hue")),
)
def test_cmap_generic_gate_compares_count_for_every_taxonomy(
    section: str, name: str, baseline_catalog: "_catalog.CatalogSnapshot"
) -> None:
    """Apply row-shape gates independently of taxonomy and topology."""
    quality_payload = _quality_payload()
    baseline = cast(dict[str, object], quality_payload["metrics"])
    candidate = json.loads(json.dumps(baseline))
    candidate[section][name]["count"] -= 1

    violations = _comparison.compare_quality_metrics(
        baseline, cast(dict[str, object], candidate), baseline_catalog.taxonomy
    )

    assert any(
        item.path == f"/metrics/{section}/{name}/count" for item in violations
    )


def test_report_json_is_strict_sorted_and_byte_deterministic(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Emit a stable machine-readable gate record with strict JSON."""
    first = comparison_report.to_json()
    second = comparison_report.to_json()

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["passed"] is True
    broken = dataclasses.replace(
        comparison_report, explanatory={"not_finite": math.nan}
    )
    with pytest.raises(ValueError):
        broken.to_json()


def test_report_uses_frozen_direct_32_previews(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Render archived v5 direct-32 literals rather than 256 downsampling."""
    quality = _quality_payload()
    literal_inputs = cast(dict[str, object], quality["literal_inputs"])
    previews = cast(dict[str, list[str]], literal_inputs["cmaps_preview_32"])

    assert comparison_report.cmaps_256["aurora"].baseline_preview_hex == tuple(
        previews["aurora"]
    )
    assert (
        len(comparison_report.cmaps_256["aurora"].candidate_preview_hex) == 32
    )


def test_explicit_empty_preview_is_not_relabelled_as_a_full_lut() -> None:
    """Distinguish missing direct-32 evidence from an omitted preview arg."""
    full = ("#000000", "#ffffff")

    comparison = _comparison._compare_hex_row(
        "probe",
        "sequential",
        full,
        full,
        baseline_preview=(),
        candidate_preview=(),
    )

    assert comparison.baseline_preview_hex == ()
    assert comparison.candidate_preview_hex == ()


def test_unlocked_previews_are_explanatory_not_exact_or_gate_inputs(
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
    comparison_report: "_comparison.ComparisonReport",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow diagnostic direct-OKLCH drift without changing PASS authority."""
    unlocked = dict(candidate_catalog.cmaps_unlocked_preview_32)
    unlocked["aurora"] = ("#000000",) * 32
    mutated = dataclasses.replace(
        candidate_catalog, cmaps_unlocked_preview_32=unlocked
    )
    baseline_previews = {
        name: row.baseline_preview_hex
        for name, row in comparison_report.cmaps_256.items()
    }
    original_rows = _comparison._row_comparisons

    def reuse_normative_rows(
        baseline_rows: Mapping[str, Sequence[str]],
        candidate_rows: Mapping[str, Sequence[str]],
        *,
        taxonomy: Mapping[str, str],
        default_kind: str,
        baseline_previews: Mapping[str, Sequence[str]] | None = None,
        candidate_previews: Mapping[str, Sequence[str]] | None = None,
    ) -> Mapping[str, "_comparison.HexRowComparison"]:
        """Reuse unchanged locked diagnostics while leaving direct rows live."""
        if baseline_rows is baseline_catalog.palette:
            return comparison_report.palette
        if baseline_rows is baseline_catalog.cycles:
            return comparison_report.cycles
        if baseline_rows is baseline_catalog.cmaps_256:
            return comparison_report.cmaps_256
        return original_rows(
            baseline_rows,
            candidate_rows,
            taxonomy=taxonomy,
            default_kind=default_kind,
            baseline_previews=baseline_previews,
            candidate_previews=candidate_previews,
        )

    monkeypatch.setattr(
        _comparison,
        "_quality_comparison",
        lambda baseline, candidate: (
            comparison_report.quality,
            baseline_previews,
        ),
    )
    monkeypatch.setattr(_comparison, "_row_comparisons", reuse_normative_rows)

    exact = _comparison.compare_exact_surfaces(baseline_catalog, mutated)
    report = _comparison.compare_catalog(baseline_catalog, mutated)

    assert sum(item.mismatch_count for item in exact.values()) == 0
    assert report.passed is True
    assert report.quality.violations == ()


def test_report_json_marks_unlocked_rows_non_normative_with_diagnostics(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Report direct OKLCH ΔE/Y/topology without promoting it to a gate."""
    payload = comparison_report.to_payload()
    explanatory = cast(dict[str, object], payload["explanatory"])
    unlocked = cast(dict[str, object], explanatory["direct_oklch_unlocked"])
    rows = cast(dict[str, dict[str, object]], unlocked["rows"])

    assert unlocked["normative"] is False
    assert unlocked["gate_input"] is False
    assert len(rows) == 43
    for name in ("blue", "aurora", "blue_red", "hue"):
        row = rows[name]
        assert {
            "absolute_delta_y",
            "delta_e_ok",
            "direct_hex",
            "direct_profile",
            "locked_hex",
            "locked_profile",
            "signed_delta_y",
            "topology",
        } <= set(row)
        assert len(cast(list[str], row["locked_hex"])) == 32
        assert len(cast(list[str], row["direct_hex"])) == 32
        for metric in ("delta_e_ok", "signed_delta_y", "absolute_delta_y"):
            summary = cast(dict[str, float], row[metric])
            assert {"min", "p05", "p50", "p95", "max", "mean"} <= set(summary)
        topology = cast(dict[str, object], row["topology"])
        assert {"kind", "locked", "direct"} <= set(topology)
        for profile_name in ("locked_profile", "direct_profile"):
            profile = cast(dict[str, list[object]], row[profile_name])
            assert {"neighbor_delta_e_ok", "oklab_l", "relative_y"} <= set(
                profile
            )


def test_unlocked_rows_record_taxonomy_specific_topology(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Record monotonic, mirror-arm, and twilight structure explicitly."""
    payload = comparison_report.to_payload()
    explanatory = cast(dict[str, object], payload["explanatory"])
    unlocked = cast(dict[str, object], explanatory["direct_oklch_unlocked"])
    rows = cast(dict[str, dict[str, object]], unlocked["rows"])

    for name in ("aurora", "blue_red", "hue", "halo"):
        topology = cast(dict[str, object], rows[name]["topology"])
        for side in ("locked", "direct"):
            metrics = cast(dict[str, object], topology[side])
            if name == "aurora":
                assert {
                    "direction",
                    "oriented_delta_l",
                    "oriented_delta_y",
                    "y_span",
                } <= set(metrics)
            elif name == "blue_red":
                assert {
                    "center_is_global_max",
                    "left_arm_min_oriented_delta_y",
                    "mirror_delta_y",
                    "right_arm_min_oriented_delta_y",
                } <= set(metrics)
            elif name == "hue":
                assert {
                    "seam_delta_e00",
                    "seam_delta_e_ok",
                    "topology_kind",
                } <= set(metrics)
            else:
                two_arm = cast(dict[str, object], metrics["two_arm"])
                assert {
                    "midpoint_contains_global_y_min",
                    "mirror_delta_oklab_l",
                    "mirror_delta_y",
                } <= set(two_arm)


def test_exported_exact_mismatch_defensively_freezes_nested_values() -> None:
    """Make the public frozen DTO immutable even outside factory paths."""
    baseline = {"nested": ["original"]}
    candidate = {"nested": ["candidate"]}
    mismatch = _comparison.ChangedLeaf(
        path="/probe", baseline=baseline, candidate=candidate
    )

    baseline["nested"].append("mutated")
    candidate["nested"].append("mutated")

    assert mismatch.to_payload() == {
        "baseline": {"nested": ["original"]},
        "baseline_present": True,
        "candidate": {"nested": ["candidate"]},
        "candidate_present": True,
        "path": "/probe",
    }


def test_standalone_html_is_deterministic_complete_and_offline(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Show all visual diagnostics without network or external assets."""
    first = _comparison.render_comparison_html(comparison_report)
    second = _comparison.render_comparison_html(comparison_report)

    assert first == second
    assert first.endswith("\n")
    assert first.count('class="cmap-panel"') == 43
    for marker in (
        'data-strip="v5-direct32"',
        'data-strip="v6-direct32"',
        'data-strip="grayscale-v5"',
        'data-strip="grayscale"',
        'data-strip="protan-v5"',
        'data-strip="protan"',
        'data-strip="deutan-v5"',
        'data-strip="deutan"',
        'data-strip="tritan-v5"',
        'data-strip="tritan"',
        'data-profile="oklab-l"',
        'data-profile="relative-y"',
        'data-profile="neighbor-delta-e"',
        'data-panel="diverging-mirror"',
        'data-panel="cyclic-seam"',
        'data-panel="luminance-lock-comparison"',
        'data-strip="locked-direct32"',
        'data-strip="unlocked-direct32"',
        'data-profile="lock-oklab-l"',
        'data-profile="lock-relative-y"',
        'data-profile="lock-neighbor-delta-e"',
    ):
        assert marker in first
    for marker in (
        "grayscale-v5",
        "grayscale",
        "protan-v5",
        "protan",
        "deutan-v5",
        "deutan",
        "tritan-v5",
        "tritan",
    ):
        assert first.count(f'data-strip="{marker}"') == 43
    assert first.count('data-panel="diverging-mirror"') == 11
    assert first.count('data-profile="mirror-y"') == 11
    assert first.count('data-panel="cyclic-seam"') == 3
    assert first.count('data-strip="cyclic-seam-v5"') == 3
    assert first.count('data-strip="cyclic-seam-v6"') == 3
    assert first.count('data-exact-surface="') == len(EXACT_FIELDS)
    assert first.count('data-panel="luminance-lock-comparison"') == 43
    assert first.count('data-strip="locked-direct32"') == 43
    assert first.count('data-strip="unlocked-direct32"') == 43
    assert first.count('data-profile="lock-oklab-l"') == 43
    assert first.count('data-profile="lock-relative-y"') == 43
    assert first.count('data-profile="lock-neighbor-delta-e"') == 43
    assert "explanatory-placeholder" not in first
    assert 'data-source="baseline"' in first
    assert 'data-source="candidate"' in first
    for chunk in first.split('data-panel="diverging-mirror"')[1:]:
        assert "<svg" in chunk.split("</section>", maxsplit=1)[0]
    for chunk in first.split('data-panel="cyclic-seam"')[1:]:
        panel = chunk.split("</section>", maxsplit=1)[0]
        assert panel.count('class="strip"') == 2
        assert panel.count('style="background:') == 16
    assert "http://" not in first and "https://" not in first
    assert "<script" not in first and "<link" not in first


def test_html_escapes_hostile_report_text(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Escape violations and paths before inserting them into standalone HTML."""
    hostile = _comparison.QualityMetricInvalid(
        surface="<script>alert(1)</script>",
        gate=_gates.InvalidMetric(
            asset='bad" name', metric="/<unsafe>&", message="<b>unsafe</b>"
        ),
    )
    report = dataclasses.replace(
        comparison_report,
        violations=tuple(
            sorted(
                (*comparison_report.violations, hostile),
                key=_comparison.violation_order,
            )
        ),
    )

    rendered = _comparison.render_comparison_html(report)

    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in rendered


def test_html_exposes_violation_values_as_escaped_deterministic_json(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Show the raw gate operands without permitting HTML injection."""
    violation = _comparison.ExactLeafMismatch(
        surface="vendor_colors",
        asset="probe",
        mismatch=_comparison.ChangedLeaf(
            path="/vendor_colors/probe",
            baseline={"z": True, "a": ["<old>", 1]},
            candidate='</code><script>alert("candidate")</script>',
        ),
    )
    report = dataclasses.replace(comparison_report, violations=(violation,))
    report_json = report.to_json()

    rendered = _comparison.render_comparison_html(report)

    assert (
        "<th>baseline / allowed</th><th>candidate / observed</th>" in rendered
    )
    assert (
        "{&quot;a&quot;:[&quot;&lt;old&gt;&quot;,1],&quot;z&quot;:true}"
        in rendered
    )
    assert (
        "&quot;&lt;/code&gt;&lt;script&gt;alert(\\&quot;candidate\\&quot;)"
        "&lt;/script&gt;&quot;" in rendered
    )
    assert "<script>alert" not in rendered
    assert report.to_json() == report_json


def test_violation_detaches_structured_values_from_caller_mutation(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Keep JSON and HTML stable after hostile retained inputs are mutated."""
    baseline = {"z": True, "a": ["<old>", {"nested": [1, 2]}]}
    candidate = {
        "payload": [
            '</code><script>alert("candidate")</script>',
            {"nested": [False, None]},
        ]
    }
    violation = _comparison.ExactLeafMismatch(
        surface="vendor_colors",
        asset="probe",
        mismatch=_comparison.ChangedLeaf(
            path="/vendor_colors/probe", baseline=baseline, candidate=candidate
        ),
    )
    report = dataclasses.replace(comparison_report, violations=(violation,))
    report_json = report.to_json().encode("utf-8")
    report_html = _comparison.render_comparison_html(report).encode("utf-8")

    cast(list[object], baseline["a"]).append("mutated")
    cast(dict[str, list[object]], candidate["payload"][1])["nested"].append(
        "mutated"
    )
    candidate["injected"] = ["new"]

    assert report.to_json().encode("utf-8") == report_json
    assert _comparison.render_comparison_html(report).encode("utf-8") == (
        report_html
    )
    payload = json.loads(report_json)
    assert payload["violations"][0]["baseline"] == {
        "a": ["<old>", {"nested": [1, 2]}],
        "z": True,
    }
    assert payload["violations"][0]["candidate"] == {
        "payload": [
            '</code><script>alert("candidate")</script>',
            {"nested": [False, None]},
        ]
    }


def test_comparison_import_closure_excludes_runtime_registries() -> None:
    """Keep report generation independent from generated/runtime registries."""
    assert _comparison.__file__ is not None
    imported, external = _color_import_closure(Path(_comparison.__file__))
    forbidden = {
        "_generated",
        "_semantic",
        "_families",
        "_discrete",
        "_register",
        "_loader",
        "_typing",
    }

    assert imported.isdisjoint(forbidden)
    assert external.isdisjoint({"dartwork_mpl", "matplotlib"})
