"""Catalog-only tests for the v5/v6 color comparison boundary."""

import ast
import builtins
import dataclasses
import hashlib
import importlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import textwrap
from collections.abc import Iterator, Mapping, Sequence
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

import dartwork_mpl._colors._catalog as _catalog
import dartwork_mpl._colors._comparison as _comparison
import dartwork_mpl._colors._compatibility_metrics as oracle
from dartwork_mpl._colors import _cmaps, _generate

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
QUALITY_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_quality.json"
)
CLI_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "compare_color_systems.py"
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


@pytest.fixture(scope="module")
def candidate_catalog() -> "_catalog.CatalogSnapshot":
    """Compile the live candidate catalog once for catalog tests."""
    return _catalog.compile_candidate_snapshot()


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


def test_catalog_import_boundary_excludes_generated_candidate_surfaces() -> (
    None
):
    """Keep the complete candidate import closure outside circular modules."""
    assert _catalog.__file__ is not None
    colors_dir = Path(_catalog.__file__).parent
    pending = [Path(_catalog.__file__)]
    visited: set[Path] = set()
    imported: set[str] = set()
    while pending:
        source_path = pending.pop()
        if source_path in visited:
            continue
        visited.add(source_path)
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level != 1:
                continue
            module_names = (
                [node.module]
                if node.module is not None
                else [alias.name for alias in node.names]
            )
            for module_name in module_names:
                local_name = module_name.split(".", maxsplit=1)[0]
                target = colors_dir / f"{local_name}.py"
                if not target.is_file():
                    continue
                imported.add(local_name)
                pending.append(target)
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
    discovery = _catalog.scan_mcp_discovery()

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
    decoded = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
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


@pytest.mark.parametrize("name", ("blue_red", "hue"))
def test_degenerate_direct_preview_fails_report_and_cli_check(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
) -> None:
    """Gate diverging and cyclic direct-32 previews independently of topology."""
    previews = dict(candidate_catalog.cmaps_preview_32)
    previews[name] = ("#000000",) * 32
    mutated = dataclasses.replace(candidate_catalog, cmaps_preview_32=previews)

    report = _comparison.compare_catalog(baseline_catalog, mutated)
    cli = _load_cli()
    monkeypatch.setattr(cli, "load_v5_snapshot", lambda: baseline_catalog)
    monkeypatch.setattr(cli, "compile_candidate_snapshot", lambda: mutated)
    monkeypatch.setattr(
        cli, "compare_catalog", lambda baseline, candidate: report
    )
    output = tmp_path / name
    exit_code = cli.main(["--output", str(output), "--check"])

    assert report.total_exact_mismatches == 0
    assert report.passed is False
    assert exit_code == 1
    assert json.loads((output / "report.json").read_text())["passed"] is False
    violation_paths = {item.path for item in report.quality.violations}
    assert (
        f"/metrics/cmaps_direct_32/{name}/degenerate_neighbor_steps"
        in violation_paths
    )
    assert f"/metrics/cmaps_direct_32/{name}/step_cv" in violation_paths


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
    mismatch = _comparison.ExactMismatch(
        path="/probe",
        baseline_present=True,
        candidate_present=True,
        baseline=baseline,
        candidate=candidate,
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
    hostile = _comparison.Violation(
        code="injected",
        surface="<script>alert(1)</script>",
        asset='bad" name',
        path="/<unsafe>&",
        message="<b>unsafe</b>",
        baseline=None,
        candidate=None,
    )
    report = dataclasses.replace(
        comparison_report,
        passed=False,
        violations=tuple(sorted((*comparison_report.violations, hostile))),
    )

    rendered = _comparison.render_comparison_html(report)

    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in rendered


def test_html_exposes_violation_values_as_escaped_deterministic_json(
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Show the raw gate operands without permitting HTML injection."""
    violation = _comparison.Violation(
        code="exact_mismatch",
        surface="vendor_colors",
        asset="probe",
        path="/vendor_colors/probe",
        message="values differ",
        baseline={"z": True, "a": ["<old>", 1]},
        candidate='</code><script>alert("candidate")</script>',
    )
    report = dataclasses.replace(
        comparison_report, passed=False, violations=(violation,)
    )
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
    violation = _comparison.Violation(
        code="exact_mismatch",
        surface="vendor_colors",
        asset="probe",
        path="/vendor_colors/probe",
        message="values differ",
        baseline=baseline,
        candidate=candidate,
    )
    report = dataclasses.replace(
        comparison_report, passed=False, violations=(violation,)
    )
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


def _load_cli() -> ModuleType:
    """Load the repository validation CLI as a testable humble module."""
    spec = importlib.util.spec_from_file_location(
        "compare_color_systems", CLI_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _remove_audit_aliases(alias: str) -> None:
    """Remove private audit aliases created by one loader test."""
    for name in tuple(sys.modules):
        if name == alias or name.startswith(f"{alias}."):
            sys.modules.pop(name, None)


def _configure_forged_audit_module(module: ModuleType, source: Path) -> None:
    """Give a forged audit entry plausible metadata and false-PASS behavior."""
    module.__file__ = str(source)
    if module.__name__.endswith("._catalog"):
        module.__dict__["load_v5_snapshot"] = lambda: object()
        module.__dict__["compile_candidate_snapshot"] = lambda: object()
        return
    forged_report = SimpleNamespace(
        passed=True, to_json=lambda: '{"passed":true,"source":"forged"}\n'
    )
    module.__dict__["compare_catalog"] = lambda baseline, candidate: (
        forged_report
    )
    module.__dict__["render_comparison_html"] = lambda report: (
        "<html>forged pass</html>\n"
    )


def _assert_owned_audit_bootstrap(
    cli: ModuleType, catalog: ModuleType, comparison: ModuleType
) -> None:
    """Require exact source, loader, spec, and SHA ownership for all aliases."""
    alias = "_dartwork_mpl_color_audit"
    records = cast(Mapping[str, SimpleNamespace], cli._AUDIT_MODULE_CACHE)
    expected_names = {
        alias,
        f"{alias}._catalog",
        f"{alias}._cmaps",
        f"{alias}._comparison",
        f"{alias}._compatibility_metrics",
        f"{alias}._conversion",
        f"{alias}._curated",
        f"{alias}._cycles",
        f"{alias}._gamut",
        f"{alias}._gates",
        f"{alias}._generate",
        f"{alias}._recipe",
        f"{alias}._ssot",
        f"{alias}._tone",
    }

    assert set(records) == expected_names
    root_record = records[alias]
    assert root_record.module is sys.modules[alias]
    assert isinstance(root_record.loader, cli._AuditNamespaceLoader)
    assert root_record.module.__loader__ is root_record.loader
    assert root_record.module.__spec__ is root_record.specification
    assert root_record.source == cli._COLORS_DIR.resolve()
    assert root_record.source_sha256 is None
    for name in sorted(expected_names - {alias}):
        record = records[name]
        module = sys.modules[name]
        expected_source = (
            cli._COLORS_DIR / f"{name.rpartition('.')[2]}.py"
        ).resolve()
        assert record.module is module
        assert isinstance(record.loader, cli._AuditSourceLoader)
        assert module.__loader__ is record.loader
        assert module.__spec__ is record.specification
        assert module.__file__ is not None
        assert Path(module.__file__).resolve() == expected_source
        assert record.specification.origin is not None
        assert Path(record.specification.origin).resolve() == expected_source
        assert record.source == expected_source
        assert (
            record.source_sha256
            == hashlib.sha256(expected_source.read_bytes()).hexdigest()
        )
    assert catalog is sys.modules[f"{alias}._catalog"]
    assert comparison is sys.modules[f"{alias}._comparison"]


@pytest.fixture(autouse=True)
def _isolate_private_audit_namespace() -> Iterator[None]:
    """Prevent one dynamic CLI module instance leaking into another test."""
    alias = "_dartwork_mpl_color_audit"
    _remove_audit_aliases(alias)
    yield
    _remove_audit_aliases(alias)


def test_cli_check_writes_byte_stable_success_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Keep check mode writable and deterministic while returning zero."""
    cli = _load_cli()
    monkeypatch.setattr(cli, "load_v5_snapshot", lambda: baseline_catalog)
    monkeypatch.setattr(
        cli, "compile_candidate_snapshot", lambda: candidate_catalog
    )
    monkeypatch.setattr(
        cli, "compare_catalog", lambda baseline, candidate: comparison_report
    )
    output = tmp_path / "comparison"

    first_code = cli.main(["--output", str(output), "--check"])
    first = (
        (output / "index.html").read_bytes(),
        (output / "report.json").read_bytes(),
    )
    second_code = cli.main(["--output", str(output), "--check"])
    second = (
        (output / "index.html").read_bytes(),
        (output / "report.json").read_bytes(),
    )

    assert (first_code, second_code, first == second) == (0, 0, True)


def test_cli_writes_failure_artifacts_before_returning_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Preserve a trustworthy failing report for local and CI inspection."""
    cli = _load_cli()
    failing = dataclasses.replace(comparison_report, passed=False)
    monkeypatch.setattr(cli, "load_v5_snapshot", lambda: baseline_catalog)
    monkeypatch.setattr(
        cli, "compile_candidate_snapshot", lambda: candidate_catalog
    )
    monkeypatch.setattr(
        cli, "compare_catalog", lambda baseline, candidate: failing
    )
    output = tmp_path / "comparison"

    code = cli.main(["--output", str(output), "--check"])

    assert code == 1
    assert json.loads((output / "report.json").read_text())["passed"] is False
    assert (output / "index.html").is_file()


def test_cli_maps_oracle_and_io_failures_to_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reserve exit two for runs that cannot produce a trustworthy report."""
    cli = _load_cli()

    def reject_baseline() -> None:
        """Simulate a pinned oracle or fixture validation failure."""
        raise oracle.OracleValidationError("invalid reference")

    monkeypatch.setattr(cli, "load_v5_snapshot", reject_baseline)
    oracle_code = cli.main(["--output", str(tmp_path / "oracle")])
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(cli, "load_v5_snapshot", _catalog.load_v5_snapshot)
    io_code = cli.main(["--output", str(output_file)])

    assert (oracle_code, io_code) == (2, 2)
    assert "invalid reference" in capsys.readouterr().err


def test_cli_invalid_arguments_preserve_previous_report(tmp_path: Path) -> None:
    """Leave an older report untouched when parsing cannot select output."""
    cli = _load_cli()
    output = tmp_path / "comparison"
    output.mkdir()
    report = output / "report.json"
    previous = b'{"passed":true,"run":"previous"}\n'
    report.write_bytes(previous)

    exit_code = cli.main(["--output", str(output), "--unsupported-argument"])

    assert (exit_code, report.read_bytes()) == (2, previous)


@pytest.mark.parametrize(
    "failure_stage", ("mkdir", "oracle", "compiler", "render")
)
def test_cli_removes_stale_report_before_initial_failure(
    failure_stage: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalidate the prior report after successful argument parsing."""
    cli = _load_cli()
    output = tmp_path / failure_stage
    output.mkdir()
    stale_report = output / "report.json"
    stale_report.write_text('{"passed":true}\n', encoding="utf-8")
    stub_report = SimpleNamespace(
        passed=True, to_json=lambda: '{"passed":true}\n'
    )

    def fail() -> None:
        """Raise at the selected audit boundary."""
        raise RuntimeError(f"{failure_stage} failed")

    monkeypatch.setattr(cli, "load_v5_snapshot", lambda: object())
    monkeypatch.setattr(cli, "compile_candidate_snapshot", lambda: object())
    monkeypatch.setattr(
        cli, "compare_catalog", lambda baseline, candidate: stub_report
    )
    monkeypatch.setattr(
        cli, "render_comparison_html", lambda report: "<html></html>\n"
    )
    if failure_stage == "mkdir":
        real_mkdir = Path.mkdir

        def fail_output_mkdir(
            path: Path,
            mode: int = 0o777,
            parents: bool = False,
            exist_ok: bool = False,
        ) -> None:
            """Fail only the CLI output-directory preparation step."""
            if path == output:
                raise PermissionError("mkdir failed")
            real_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

        monkeypatch.setattr(cli.Path, "mkdir", fail_output_mkdir)
    elif failure_stage == "oracle":
        monkeypatch.setattr(cli, "load_v5_snapshot", fail)
    elif failure_stage == "compiler":
        monkeypatch.setattr(cli, "compile_candidate_snapshot", fail)
    else:
        monkeypatch.setattr(
            cli, "render_comparison_html", lambda report: fail()
        )

    exit_code = cli.main(["--output", str(output), "--check"])

    assert exit_code == 2
    assert not stale_report.exists()


@pytest.mark.parametrize(
    "error_type", (AttributeError, AssertionError, SyntaxError)
)
def test_cli_maps_every_ordinary_exception_to_two(
    error_type: type[Exception], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Map unexpected ordinary audit defects to an untrustworthy-run exit."""
    cli = _load_cli()

    def fail() -> None:
        """Raise one ordinary exception not covered by the former allowlist."""
        raise error_type("ordinary failure")

    monkeypatch.setattr(cli, "load_v5_snapshot", fail)

    exit_code = cli.main(["--output", str(tmp_path), "--check"])

    assert exit_code == 2


def test_cli_does_not_catch_base_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Allow interrupts and process-control exceptions to propagate."""
    cli = _load_cli()

    def interrupt() -> None:
        """Simulate an operator interrupt during reference loading."""
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "load_v5_snapshot", interrupt)

    with pytest.raises(KeyboardInterrupt):
        cli.main(["--output", str(tmp_path), "--check"])


def test_audit_bootstrap_cleans_created_namespace_after_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove a partial bootstrap and permit one clean retry."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    for name in tuple(sys.modules):
        if name == alias or name.startswith(alias + "."):
            monkeypatch.delitem(sys.modules, name)
    real_read_bytes = Path.read_bytes

    def fail_comparison(path: Path) -> bytes:
        """Fail while the owned loader reads the comparison source."""
        if path.resolve() == (cli._COLORS_DIR / "_comparison.py").resolve():
            raise ImportError("injected comparison import failure")
        return real_read_bytes(path)

    with monkeypatch.context() as context:
        context.setattr(cli.Path, "read_bytes", fail_comparison)

        with pytest.raises(
            ImportError, match="injected comparison import failure"
        ):
            cli._load_audit_modules()

    assert not any(
        name == alias or name.startswith(alias + ".") for name in sys.modules
    )
    try:
        catalog, comparison = cli._load_audit_modules()
        assert catalog.__name__ == f"{alias}._catalog"
        assert comparison.__name__ == f"{alias}._comparison"
    finally:
        _remove_audit_aliases(alias)


def test_audit_first_bootstrap_rejects_preexisting_valid_shaped_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse even an in-tree namespace not created by this CLI instance."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    _remove_audit_aliases(alias)
    package = cli._new_audit_namespace()
    monkeypatch.setitem(sys.modules, alias, package)

    with pytest.raises(RuntimeError, match="preexisting"):
        cli._load_audit_modules()

    assert {
        name
        for name in sys.modules
        if name == alias or name.startswith(alias + ".")
    } == {alias}


def test_audit_first_bootstrap_rejects_same_tree_forged_false_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Turn a same-tree forged PASS into an untrustworthy-run exit."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    _remove_audit_aliases(alias)
    package = cli._new_audit_namespace()
    catalog_name = f"{alias}._catalog"
    comparison_name = f"{alias}._comparison"
    forged_catalog = ModuleType(catalog_name)
    forged_comparison = ModuleType(comparison_name)
    _configure_forged_audit_module(
        forged_catalog, cli._COLORS_DIR / "_catalog.py"
    )
    _configure_forged_audit_module(
        forged_comparison, cli._COLORS_DIR / "_comparison.py"
    )
    monkeypatch.setitem(sys.modules, alias, package)
    monkeypatch.setitem(sys.modules, catalog_name, forged_catalog)
    monkeypatch.setitem(sys.modules, comparison_name, forged_comparison)
    output = tmp_path / "forged-pass"

    exit_code = cli.main(["--output", str(output), "--check"])

    assert exit_code == 2
    assert not (output / "report.json").exists()


def test_audit_cold_bootstrap_owns_source_despite_forged_import_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bypass false-PASS code returned by a substituted import dispatcher."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    dispatched: list[str] = []
    sources = {
        f"{alias}._catalog": cli._COLORS_DIR / "_catalog.py",
        f"{alias}._comparison": cli._COLORS_DIR / "_comparison.py",
    }

    def forged_import(name: str, package: str | None = None) -> ModuleType:
        """Return attacker code while presenting the expected source origin."""
        assert package is None
        dispatched.append(name)
        module = ModuleType(name)
        source = sources[name]
        module.__spec__ = ModuleSpec(
            name, loader=cast(Loader, SimpleNamespace()), origin=str(source)
        )
        _configure_forged_audit_module(module, source)
        sys.modules[name] = module
        return module

    monkeypatch.setattr(importlib, "import_module", forged_import)
    catalog, comparison = cli._load_audit_modules()

    assert dispatched == []
    _assert_owned_audit_bootstrap(cli, catalog, comparison)


def test_audit_cold_bootstrap_owns_source_despite_ambient_finder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep ambient meta-path providers outside private source loading."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    queried: list[str] = []
    executed: list[str] = []
    sources = {
        f"{alias}._catalog": cli._COLORS_DIR / "_catalog.py",
        f"{alias}._comparison": cli._COLORS_DIR / "_comparison.py",
    }

    class ForgedLoader(Loader):
        """Execute attacker code under an in-tree-looking module spec."""

        def create_module(self, spec: ModuleSpec) -> None:
            """Use the import system's ordinary module allocation."""
            del spec

        def exec_module(self, module: ModuleType) -> None:
            """Populate a false-PASS module with the claimed source path."""
            executed.append(module.__name__)
            _configure_forged_audit_module(module, sources[module.__name__])

    class ForgedFinder(MetaPathFinder):
        """Claim only the two audit entry modules during cold bootstrap."""

        def find_spec(
            self,
            fullname: str,
            path: Sequence[str] | None,
            target: ModuleType | None = None,
        ) -> ModuleSpec | None:
            """Present attacker loaders with the expected source origins."""
            del path, target
            queried.append(fullname)
            source = sources.get(fullname)
            if source is None:
                return None
            return ModuleSpec(fullname, ForgedLoader(), origin=str(source))

    monkeypatch.setattr(sys, "meta_path", [ForgedFinder(), *sys.meta_path])

    catalog, comparison = cli._load_audit_modules()

    assert (queried, executed) == ([], [])
    _assert_owned_audit_bootstrap(cli, catalog, comparison)


def test_audit_cold_bootstrap_excludes_post_load_ambient_import_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep private imports on the callback captured when the CLI loaded."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    standard_import = builtins.__import__
    observed_private_callers: list[str] = []

    def observing_import(
        name: str,
        global_values: Mapping[str, object] | None = None,
        local_values: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        """Record only calls made with private audit module globals."""
        caller = (
            None if global_values is None else global_values.get("__name__")
        )
        if isinstance(caller, str) and (
            caller == alias or caller.startswith(f"{alias}.")
        ):
            observed_private_callers.append(caller)
        return standard_import(
            name, global_values, local_values, fromlist, level
        )

    monkeypatch.setattr(builtins, "__import__", observing_import)

    catalog, comparison = cli._load_audit_modules()

    assert observed_private_callers == []
    _assert_owned_audit_bootstrap(cli, catalog, comparison)


def test_validate_file_module_requires_completed_source_execution() -> None:
    """Reject plausible metadata when this loader never executed the source."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    name = f"{alias}._catalog"
    source = (cli._COLORS_DIR / "_catalog.py").resolve()
    loader = cli._AuditSourceLoader.from_source(name, source)
    specification = ModuleSpec(name, loader, origin=str(source))
    specification.has_location = True
    module = importlib.util.module_from_spec(specification)
    module.__dict__["__builtins__"] = {
        **vars(builtins),
        "__import__": cli._STANDARD_IMPORT,
    }

    with pytest.raises(RuntimeError, match="source execution did not complete"):
        cli._validate_file_module(name, module, loader, specification)


def test_audit_bootstrap_reuses_only_its_cached_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reuse a legitimate bootstrap without asking import machinery again."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    _remove_audit_aliases(alias)
    try:
        first = cli._load_audit_modules()

        def reject_reimport(
            finder: object,
            fullname: str,
            path: Sequence[str] | None,
            target: ModuleType | None = None,
        ) -> ModuleSpec | None:
            """Make any second owned source lookup an observable failure."""
            raise AssertionError(
                f"unexpected re-import: {finder}, {fullname}, {path}, {target}"
            )

        monkeypatch.setattr(
            cli._AuditSourceFinder, "find_spec", reject_reimport
        )

        second = cli._load_audit_modules()

        assert second[0] is first[0]
        assert second[1] is first[1]
    finally:
        _remove_audit_aliases(alias)


def test_audit_bootstrap_rejects_cached_module_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed when an in-tree-looking cached entry is replaced."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    _remove_audit_aliases(alias)
    try:
        cli._load_audit_modules()
        catalog_name = f"{alias}._catalog"
        forged_catalog = ModuleType(catalog_name)
        forged_catalog.__file__ = str(cli._COLORS_DIR / "_catalog.py")
        sys.modules[catalog_name] = forged_catalog

        with pytest.raises(RuntimeError, match="replaced"):
            cli._load_audit_modules()
    finally:
        _remove_audit_aliases(alias)


def test_audit_bootstrap_rejects_module_injected_after_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed when a new same-tree alias appears after bootstrap."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    _remove_audit_aliases(alias)
    try:
        cli._load_audit_modules()
        injected_name = f"{alias}._forged"
        injected = ModuleType(injected_name)
        injected.__file__ = str(cli._COLORS_DIR / "_catalog.py")
        monkeypatch.setitem(sys.modules, injected_name, injected)

        with pytest.raises(RuntimeError, match="injected"):
            cli._load_audit_modules()
    finally:
        _remove_audit_aliases(alias)


def test_audit_bootstrap_rejects_existing_alias_with_another_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed instead of reusing an unrelated preloaded namespace."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    collision = ModuleType(alias)
    collision.__path__ = [str(tmp_path)]
    monkeypatch.setitem(sys.modules, alias, collision)

    with pytest.raises(RuntimeError, match="namespace collision"):
        cli._load_audit_modules()


def test_audit_first_bootstrap_rejects_orphaned_prefixed_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a prefixed module that exists without a trusted root package."""
    cli = _load_cli()
    alias = "_dartwork_mpl_color_audit"
    for name in tuple(sys.modules):
        if name == alias or name.startswith(alias + "."):
            monkeypatch.delitem(sys.modules, name)
    poison_name = f"{alias}._poisoned_dependency"
    poison = ModuleType(poison_name)
    poison.__file__ = str(tmp_path / "poison.py")
    monkeypatch.setitem(sys.modules, poison_name, poison)

    with pytest.raises(RuntimeError, match="preexisting"):
        cli._load_audit_modules()

    assert {
        name
        for name in sys.modules
        if name == alias or name.startswith(alias + ".")
    } == {poison_name}


def test_atomic_writer_cleans_unique_temp_after_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never leave fixed or unique sibling temp files after an I/O failure."""
    cli = _load_cli()
    target = tmp_path / "report.json"

    def reject_replace(source: str, destination: Path) -> None:
        """Simulate an atomic rename failure after the temp write."""
        raise OSError(f"cannot replace {source} -> {destination}")

    monkeypatch.setattr(cli.os, "replace", reject_replace)

    with pytest.raises(OSError):
        cli._atomic_write_text(target, "{}\n")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_cli_removes_stale_report_before_json_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    baseline_catalog: "_catalog.CatalogSnapshot",
    candidate_catalog: "_catalog.CatalogSnapshot",
    comparison_report: "_comparison.ComparisonReport",
) -> None:
    """Never pair new HTML with an old report completion marker."""
    cli = _load_cli()
    monkeypatch.setattr(cli, "load_v5_snapshot", lambda: baseline_catalog)
    monkeypatch.setattr(
        cli, "compile_candidate_snapshot", lambda: candidate_catalog
    )
    monkeypatch.setattr(
        cli, "compare_catalog", lambda baseline, candidate: comparison_report
    )
    output = tmp_path / "comparison"
    output.mkdir()
    stale_report = output / "report.json"
    stale_report.write_text('{"passed":true}\n', encoding="utf-8")
    real_writer = cli._atomic_write_text

    def fail_json(path: Path, text: str) -> None:
        """Publish HTML but fail the report completion marker."""
        if path.name == "report.json":
            raise OSError("simulated JSON failure")
        real_writer(path, text)

    monkeypatch.setattr(cli, "_atomic_write_text", fail_json)

    code = cli.main(["--output", str(output), "--check"])

    assert code == 2
    assert (output / "index.html").is_file()
    assert not stale_report.exists()


def test_comparison_import_closure_excludes_runtime_registries() -> None:
    """Keep report generation independent from generated/runtime registries."""
    assert _comparison.__file__ is not None
    colors_dir = Path(_comparison.__file__).parent
    pending = [Path(_comparison.__file__)]
    visited: set[Path] = set()
    imported: set[str] = set()
    external: set[str] = set()
    while pending:
        source_path = pending.pop()
        if source_path in visited:
            continue
        visited.add(source_path)
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
            module_names = (
                [node.module]
                if node.module is not None
                else [alias.name for alias in node.names]
            )
            for module_name in module_names:
                local_name = module_name.split(".", maxsplit=1)[0]
                target = colors_dir / f"{local_name}.py"
                if target.is_file():
                    imported.add(local_name)
                    pending.append(target)
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


def test_real_cli_subprocess_uses_isolated_source_audit_namespace(
    tmp_path: Path,
) -> None:
    """Run cold while blocking public/runtime imports and registry mutation."""
    repository = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository / "src")
    environment["MPLCONFIGDIR"] = str(tmp_path / "mplconfig")
    output = tmp_path / "subprocess-report"
    runner = tmp_path / "audit_runner.py"
    runner.write_text(
        textwrap.dedent(
            """
            import importlib.abc
            import json
            import runpy
            import sys
            from pathlib import Path

            import matplotlib
            from matplotlib.colors import get_named_colors_mapping

            FORBIDDEN_SUFFIXES = (
                "._generated",
                "._loader",
                "._register",
                "._semantic",
                "._families",
                "._discrete",
                "._typing",
            )
            ALIAS_ROOT = "_dartwork_mpl_color_audit"

            def is_forbidden(fullname):
                return (
                    fullname == "dartwork_mpl"
                    or fullname.startswith("dartwork_mpl.")
                    or (
                        fullname.startswith(ALIAS_ROOT + ".")
                        and fullname.endswith(FORBIDDEN_SUFFIXES)
                    )
                )

            class AuditImportBlocker(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if is_forbidden(fullname):
                        raise ImportError(f"forbidden audit import: {fullname}")
                    return None

            sys.meta_path.insert(0, AuditImportBlocker())
            before_cmaps = set(matplotlib.colormaps)
            before_named = set(get_named_colors_mapping())
            namespace = runpy.run_path(sys.argv[1], run_name="_color_audit_cli")
            exit_code = namespace["main"](
                ["--output", sys.argv[2], "--check"]
            )
            forbidden_loaded = sorted(
                name
                for name in sys.modules
                if is_forbidden(name)
            )
            colors_dir = Path(sys.argv[3]).resolve()
            alias_files = {
                name: str(Path(module.__file__).resolve())
                for name, module in sys.modules.items()
                if name.startswith(ALIAS_ROOT + ".")
                and getattr(module, "__file__", None) is not None
            }
            escaped_alias_files = sorted(
                path
                for path in alias_files.values()
                if not Path(path).is_relative_to(colors_dir)
            )
            print(
                json.dumps(
                    {
                        "alias_files": alias_files,
                        "cmap_registry_delta": sorted(
                            before_cmaps ^ set(matplotlib.colormaps)
                        ),
                        "exit_code": exit_code,
                        "escaped_alias_files": escaped_alias_files,
                        "forbidden_loaded": forbidden_loaded,
                        "named_registry_delta": sorted(
                            before_named ^ set(get_named_colors_mapping())
                        ),
                    },
                    sort_keys=True,
                )
            )
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            str(CLI_PATH),
            str(output),
            str(repository / "src" / "dartwork_mpl" / "_colors"),
        ],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    audit = json.loads(result.stdout)
    assert audit["exit_code"] == 0
    assert audit["forbidden_loaded"] == []
    assert audit["cmap_registry_delta"] == []
    assert audit["named_registry_delta"] == []
    assert audit["escaped_alias_files"] == []
    assert {
        "_dartwork_mpl_color_audit._catalog",
        "_dartwork_mpl_color_audit._comparison",
    } <= set(audit["alias_files"])
    assert (output / "index.html").is_file()
    assert json.loads((output / "report.json").read_text())["passed"] is True


def test_build_artifact_directory_is_exactly_ignored() -> None:
    """Keep local and CI report artifacts outside version control."""
    ignore = Path(__file__).resolve().parents[1] / ".gitignore"

    assert "/build/" in ignore.read_text(encoding="utf-8").splitlines()
