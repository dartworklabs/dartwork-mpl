"""Contract tests for the immutable v5 color compatibility manifest."""

import hashlib
import json
import re
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)

BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
COMPAT_SHA256 = (
    "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
)
SCHEMA = "dartwork-mpl.color-compatibility/v1"
EXACT_SURFACES = (
    "palette",
    "cycles",
    "cmaps256",
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
LEGACY_EXACT_SURFACES = EXACT_SURFACES[:-1]
MAX_DISCRETE_N = {
    "sequential": 10,
    "multi-hue": 8,
    "diverging": 9,
    "cyclic": 24,
    "qualitative": 8,
}


def _object_map(value: object) -> dict[str, object]:
    """Narrow a decoded JSON object to its string-keyed mapping shape."""
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(dict[str, object], value)


def _object_list(value: object) -> list[object]:
    """Narrow a decoded JSON value to a list."""
    assert isinstance(value, list)
    return value


def _canonical_hash(value: object) -> str:
    """Return the manifest's canonical compact-JSON SHA-256 digest."""
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@pytest.fixture
def v5_compat() -> dict[str, object]:
    """Load the repository-local immutable v5 compatibility manifest."""
    if not COMPAT_PATH.is_file():
        return {}
    decoded = json.loads(COMPAT_PATH.read_text(encoding="utf-8"))
    return _object_map(decoded)


def assert_all_exact_surfaces_have_canonical_hashes(
    v5_compat: dict[str, object],
) -> None:
    """Assert that every exact surface has a matching canonical digest."""
    hashes = _object_map(v5_compat["canonical_hashes"])

    assert set(hashes) == set(EXACT_SURFACES)
    for surface in EXACT_SURFACES:
        digest = hashes[surface]
        assert isinstance(digest, str)
        assert digest == _canonical_hash(v5_compat[surface])


def assert_all_valid_discrete_forms_are_frozen(
    v5_compat: dict[str, object],
) -> None:
    """Assert that every valid family/n result and multi-hue index is frozen."""
    taxonomy = _object_map(v5_compat["taxonomy"])
    discrete_hex = _object_map(v5_compat["discrete_hex"])
    reverse_discrete_hex = _object_map(v5_compat["reverse_discrete_hex"])
    multi_hue_indices = _object_map(v5_compat["multi_hue_discrete_indices"])
    cmaps256 = _object_map(v5_compat["cmaps256"])

    assert set(discrete_hex) == set(taxonomy)
    assert set(reverse_discrete_hex) == set(taxonomy)
    expected_multi_hue = {
        name for name, kind in taxonomy.items() if kind == "multi-hue"
    }
    assert set(multi_hue_indices) == expected_multi_hue

    for name, kind_value in taxonomy.items():
        assert isinstance(kind_value, str)
        max_n = MAX_DISCRETE_N[kind_value]
        forms = _object_map(discrete_hex[name])
        reverse_forms = _object_map(reverse_discrete_hex[name])
        expected_n = {str(n) for n in range(1, max_n + 1)}
        assert set(forms) == expected_n
        assert set(reverse_forms) == expected_n
        for n_text, row_value in forms.items():
            row = _object_list(row_value)
            reverse_row = _object_list(reverse_forms[n_text])
            assert len(row) == int(n_text)
            assert all(isinstance(color, str) for color in row)
            assert reverse_row == list(reversed(row))

    for name in sorted(expected_multi_hue):
        index_forms = _object_map(multi_hue_indices[name])
        hex_forms = _object_map(discrete_hex[name])
        cmap = _object_list(cmaps256[name])
        assert set(index_forms) == {str(n) for n in range(1, 9)}
        for n_text, indices_value in index_forms.items():
            indices = _object_list(indices_value)
            assert len(indices) == int(n_text)
            assert all(
                isinstance(index, int) and 0 <= index < 256 for index in indices
            )
            expected_hex = [cmap[cast(int, index)] for index in indices]
            assert _object_list(hex_forms[n_text]) == expected_hex


def test_v5_manifest_is_complete(v5_compat: dict[str, object]) -> None:
    """Pin all public v5 color surfaces before the v6 compiler migration."""
    assert COMPAT_PATH.is_file(), f"missing compatibility asset: {COMPAT_PATH}"
    assert hashlib.sha256(COMPAT_PATH.read_bytes()).hexdigest() == COMPAT_SHA256
    assert v5_compat["schema"] == SCHEMA
    assert v5_compat["baseline_commit"] == BASELINE_COMMIT
    assert _object_map(v5_compat["source_hashes"]) == {
        "src/dartwork_mpl/_colors/_curated.py": (
            "ee570b840323015db427e1bb36f500eb4f12d67027aa3894f9b7ba02caa295f5"
        ),
        "src/dartwork_mpl/_colors/_generated.py": (
            "999950452b2f2d8e2d58449af7c7fa043d918c922719be68939f765f5f762d54"
        ),
        "docs/superpowers/specs/assets/2026-07-03-color-system-v5/"
        "color_v5_ssot.json": (
            "a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518"
        ),
        "src/dartwork_mpl/asset/color/ant_colors.json": (
            "9cad970d63064bfd35c122a03e9ee0d53d5e90754fea2e3dbaa911fa1f09fa7c"
        ),
        "src/dartwork_mpl/asset/color/chakra_colors.json": (
            "fd5c54c87c532a3448edab06c870407ec9616f93cb18eeacab933a34237af6f9"
        ),
        "src/dartwork_mpl/asset/color/material_colors.json": (
            "cce34cc9f41ed4562524ab03e26d1bbcb27f3f81e1e3c9ae22acb0d372817888"
        ),
        "src/dartwork_mpl/asset/color/opencolor.txt": (
            "8210fd90139d05ab38b34a2b62a5968adeabe9999f5f12607054c9c630728ad7"
        ),
        "src/dartwork_mpl/asset/color/primer_colors.json": (
            "91f269a580137ea58da44075b4cd732062aef3ea8b17a5cf20f3f339b78dab94"
        ),
        "src/dartwork_mpl/asset/color/tailwind_colors.json": (
            "281d2942d14d55d8dcabe389054757d2b898c9ab467ba1d752dbdef0f881436f"
        ),
    }

    inventory = _object_map(v5_compat["inventory"])
    assert inventory == {
        "palette_positions": 200,
        "cycle_positions": 16,
        "cmap_positions": 11008,
        "qualitative_families": 13,
        "families": 56,
        "registered_colormaps": 99,
        "dc_tokens": 380,
        "vendor_tokens": 892,
    }

    canonical_hashes = _object_map(v5_compat["canonical_hashes"])
    assert canonical_hashes["palette"] == (
        "4431b8d1accbeca9527e6097a62c048a51fd6fd699588998c202c359b98b458e"
    )
    assert canonical_hashes["cycles"] == (
        "cda50ebd800a44dbb3b8d58a4fe53924ecaf914f7dbadbc2ac196e77cf6595cd"
    )
    assert canonical_hashes["cmaps256"] == (
        "e026ce047dd8a186299b2857e3d8c81f2b2bc4b7249df37f35b7c0093c5240c1"
    )

    taxonomy = _object_map(v5_compat["taxonomy"])
    registrations = _object_list(v5_compat["registrations"])
    public_inventory = _object_list(v5_compat["public_inventory"])
    typing_literals = _object_map(v5_compat["typing_literals"])
    mcp_discovery = _object_map(v5_compat["mcp_discovery"])

    assert len(taxonomy) == 56
    assert len(registrations) == 99
    assert len(public_inventory) == 56
    assert len(_object_list(typing_literals["color_names"])) == 1272
    assert len(_object_list(typing_literals["colormap_names"])) == 99
    assert len(_object_list(mcp_discovery["tool_names"])) == 16
    assert len(_object_list(mcp_discovery["resource_uris"])) == 10
    assert len(_object_list(mcp_discovery["resource_template_uris"])) == 4
    assert len(_object_list(mcp_discovery["prompt_names"])) == 2

    vendor_colors = _object_map(v5_compat["vendor_colors"])
    vendor_names = {
        cast(str, name)
        for name in _object_list(typing_literals["color_names"])
        if isinstance(name, str) and not name.startswith("dc.")
    }
    assert len(vendor_colors) == 892
    assert set(vendor_colors) == vendor_names
    assert all(
        isinstance(value, str) and re.fullmatch(r"#[0-9a-f]{6}", value)
        for value in vendor_colors.values()
    )
    assert {
        "oc.gray0": vendor_colors["oc.gray0"],
        "tw.sky400": vendor_colors["tw.sky400"],
        "md.red500": vendor_colors["md.red500"],
    } == {"oc.gray0": "#f8f9fa", "tw.sky400": "#38bdf8", "md.red500": "#f44336"}

    assert_all_exact_surfaces_have_canonical_hashes(v5_compat)
    assert_all_valid_discrete_forms_are_frozen(v5_compat)


def test_additive_vendor_surface_preserves_v1_and_legacy_exact_payload(
    v5_compat: dict[str, object],
) -> None:
    """Add the 18th pre-release surface without changing the first 17."""
    legacy_projection = {
        surface: v5_compat[surface] for surface in LEGACY_EXACT_SURFACES
    }

    assert v5_compat["schema"] == "dartwork-mpl.color-compatibility/v1"
    assert _canonical_hash(legacy_projection) == (
        "4c56ca36a430ee02440e5639bf67780cbcf23ecc1272b985d0982636022d48fb"
    )
