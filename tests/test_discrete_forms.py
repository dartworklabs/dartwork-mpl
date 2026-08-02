"""Model B designed discrete color forms."""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path
from typing import cast

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl  # noqa: F401  (registers color names)
import dartwork_mpl._colors._compatibility_metrics as oracle
from dartwork_mpl._colors import _curated, _generated
from dartwork_mpl._colors._discrete import DIVERGING_CANONICALS, discrete_colors
from dartwork_mpl._colors._families import (
    CYCLIC,
    DIVERGING,
    FAMILIES,
    MULTI_HUE,
    QUALITATIVE,
    SEQUENTIAL,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY_PATH = (
    REPO_ROOT
    / "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)
QUALITY_PATH = COMPATIBILITY_PATH.with_name("color_v5_quality.json")
V6_SSOT_PATH = REPO_ROOT / "src/dartwork_mpl/asset/color/color_v6_ssot.json"

GENERATED_DIVERGING = tuple(
    name for name in DIVERGING if name not in _curated.CURATED_DIVERGING_ORDER
)


def _load_json(path: Path) -> dict[str, object]:
    """Load one checked-in JSON contract as a string-keyed object."""
    decoded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) for key in decoded
    ):
        raise TypeError(f"{path} must contain a JSON object")
    return cast(dict[str, object], decoded)


COMPATIBILITY = _load_json(COMPATIBILITY_PATH)
QUALITY = _load_json(QUALITY_PATH)
V6_SSOT = _load_json(V6_SSOT_PATH)


def _discrete_cases(field: str) -> tuple[object, ...]:
    """Build stable pytest cases for every frozen discrete API form."""
    families = cast(dict[str, dict[str, list[str]]], COMPATIBILITY[field])
    return tuple(
        pytest.param(name, int(size), tuple(colors), id=f"{name}-{size}")
        for name, forms in sorted(families.items())
        for size, colors in sorted(forms.items(), key=lambda item: int(item[0]))
    )


def _multi_hue_cases() -> tuple[object, ...]:
    """Build all 72 frozen multi-hue index and shipped-hex cases."""
    indices = cast(
        dict[str, dict[str, list[int]]],
        COMPATIBILITY["multi_hue_discrete_indices"],
    )
    colors = cast(
        dict[str, dict[str, list[str]]], COMPATIBILITY["discrete_hex"]
    )
    return tuple(
        pytest.param(
            name,
            int(size),
            tuple(row),
            tuple(colors[name][size]),
            id=f"{name}-{size}",
        )
        for name, forms in sorted(indices.items())
        for size, row in sorted(forms.items(), key=lambda item: int(item[0]))
    )


FORWARD_DISCRETE_CASES = _discrete_cases("discrete_hex")
REVERSE_DISCRETE_CASES = _discrete_cases("reverse_discrete_hex")
MULTI_HUE_CASES = _multi_hue_cases()


def test_frozen_discrete_case_inventory_is_complete() -> None:
    """Cover 547 forward/reverse forms and all 72 multi-hue rows."""
    assert (
        len(FORWARD_DISCRETE_CASES),
        len(REVERSE_DISCRETE_CASES),
        len(MULTI_HUE_CASES),
    ) == (547, 547, 72)


@pytest.mark.parametrize("name", SEQUENTIAL)
@pytest.mark.parametrize("n", [1, 2, 5, 8, 9, 10])
def test_sequential_forms_are_deterministic_ladder_windows(
    name: str, n: int
) -> None:
    colors = discrete_colors(name, n)
    assert colors == discrete_colors(name, n)
    assert len(colors) == n
    assert all(c in _generated.PALETTE[name] for c in colors)
    if n <= 8:
        assert all(c in _generated.PALETTE[name][1:9] for c in colors)
    elif n == 9:
        assert colors == list(_generated.PALETTE[name][:9])
    else:
        assert colors == list(_generated.PALETTE[name])


@pytest.mark.parametrize("name", DIVERGING)
def test_diverging_canonical_forms_and_outer_pair_subsets(name: str) -> None:
    canonical = list(DIVERGING_CANONICALS[name])
    assert discrete_colors(name, 8) == canonical
    assert discrete_colors(name, 8) == discrete_colors(name, 8)
    assert discrete_colors(name, 2) == [canonical[0], canonical[-1]]
    assert discrete_colors(name, 4) == [
        canonical[0],
        canonical[1],
        canonical[-2],
        canonical[-1],
    ]
    five = discrete_colors(name, 5)
    assert five[:2] == canonical[:2]
    assert five[-2:] == canonical[-2:]
    assert five[2] == _generated.CMAPS_256[name][128]


@pytest.mark.parametrize("name", GENERATED_DIVERGING)
def test_generated_diverging_tokens_are_registered_in_low_high_order(
    name: str,
) -> None:
    named = mcolors.get_named_colors_mapping()
    low, high = name.split("_", maxsplit=1)
    expected = tuple(_generated.PALETTE[low][i] for i in (7, 5, 3, 1)) + tuple(
        _generated.PALETTE[high][i] for i in (1, 3, 5, 7)
    )
    assert DIVERGING_CANONICALS[name] == expected
    for i, hex_value in enumerate(expected):
        assert named[f"dc.{name}{i}"] == hex_value


@pytest.mark.parametrize(
    ("name", "n", "expected_indices", "expected_hex"), MULTI_HUE_CASES
)
def test_v6_multi_hue_manifest_matches_every_frozen_index_row(
    name: str,
    n: int,
    expected_indices: tuple[int, ...],
    expected_hex: tuple[str, ...],
) -> None:
    del expected_hex
    manifest = cast(
        dict[str, dict[str, list[int]]], V6_SSOT["multi_hue_discrete_indices"]
    )

    assert tuple(manifest[name][str(n)]) == expected_indices


@pytest.mark.parametrize(
    ("name", "n", "expected_indices", "expected_hex"), MULTI_HUE_CASES
)
@pytest.mark.skipif(
    not hasattr(_generated, "MULTI_HUE_DISCRETE_INDICES"),
    reason="generated multi-hue manifest is the Task 7 RED contract",
)
def test_generated_module_exposes_every_frozen_multi_hue_index_row(
    name: str,
    n: int,
    expected_indices: tuple[int, ...],
    expected_hex: tuple[str, ...],
) -> None:
    del expected_hex
    manifest = getattr(_generated, "MULTI_HUE_DISCRETE_INDICES", None)

    assert manifest is not None
    assert tuple(manifest[name][n]) == expected_indices


def test_generated_module_exposes_multi_hue_discrete_manifest() -> None:
    """Require the generated artifact to publish the frozen index table."""
    assert hasattr(_generated, "MULTI_HUE_DISCRETE_INDICES")


@pytest.mark.parametrize(
    ("name", "n", "expected_indices", "expected_hex"), MULTI_HUE_CASES
)
def test_multi_hue_indices_select_the_exact_shipped_hex(
    name: str,
    n: int,
    expected_indices: tuple[int, ...],
    expected_hex: tuple[str, ...],
) -> None:
    del n
    selected = tuple(
        _generated.CMAPS_256[name][index] for index in expected_indices
    )

    assert selected == expected_hex


@pytest.mark.parametrize(
    ("name", "n", "expected_indices", "expected_hex"), MULTI_HUE_CASES
)
def test_multi_hue_index_rows_increase_and_select_unique_hex(
    name: str,
    n: int,
    expected_indices: tuple[int, ...],
    expected_hex: tuple[str, ...],
) -> None:
    del name

    assert len(expected_indices) == len(expected_hex) == n
    assert all(left < right for left, right in pairwise(expected_indices))
    assert len(set(expected_hex)) == n


@pytest.mark.parametrize(
    ("name", "n", "expected_indices", "expected_hex"), MULTI_HUE_CASES
)
def test_multi_hue_raw_quality_matches_the_independent_frozen_oracle(
    name: str,
    n: int,
    expected_indices: tuple[int, ...],
    expected_hex: tuple[str, ...],
) -> None:
    del expected_indices
    metrics = cast(dict[str, object], QUALITY["metrics"])
    discrete = cast(
        dict[str, dict[str, dict[str, object]]], metrics["discrete"]
    )

    assert oracle.categorical_quality(expected_hex) == discrete[name][str(n)]


@pytest.mark.parametrize("name", CYCLIC)
@pytest.mark.parametrize("n", [1, 3, 12, 24])
def test_cyclic_forms_use_equal_phase_samples(name: str, n: int) -> None:
    colors = discrete_colors(name, n)
    assert colors == discrete_colors(name, n)
    assert len(colors) == n
    expected = [
        _generated.CMAPS_256[name][min(int(i * 256 / n), 255)] for i in range(n)
    ]
    assert colors == expected


@pytest.mark.parametrize("name", QUALITATIVE)
def test_qualitative_forms_are_prefixes(name: str) -> None:
    source = (
        _generated.CYCLES[name]
        if name in _generated.CYCLES
        else _curated.CURATED[name]
    )
    for n in (1, 3, len(source)):
        colors = discrete_colors(name, n)
        assert colors == list(source[:n])
        assert colors == discrete_colors(name, n)


@pytest.mark.parametrize(
    ("name", "n"),
    [
        (SEQUENTIAL[0], 11),
        (DIVERGING[0], 10),
        (MULTI_HUE[0], 9),
        (CYCLIC[0], 25),
        (QUALITATIVE[0], cast(int, FAMILIES[QUALITATIVE[0]].discrete_size) + 1),
    ],
)
def test_discrete_form_value_errors_state_kind_and_max(
    name: str, n: int
) -> None:
    family = FAMILIES[name]
    with pytest.raises(ValueError) as excinfo:
        discrete_colors(name, n)
    msg = str(excinfo.value)
    assert name in msg
    assert family.kind in msg
    assert f"max n={n - 1}" in msg


def test_reverse_returns_reversed_copy() -> None:
    assert discrete_colors("blue", 5, reverse=True) == list(
        reversed(discrete_colors("blue", 5))
    )


@pytest.mark.parametrize(("name", "n", "expected"), FORWARD_DISCRETE_CASES)
def test_every_forward_discrete_form_matches_the_frozen_public_contract(
    name: str, n: int, expected: tuple[str, ...]
) -> None:
    """Pin all 547 forward forms, including every family kind and maximum."""
    assert tuple(discrete_colors(name, n)) == expected


@pytest.mark.parametrize(("name", "n", "expected"), REVERSE_DISCRETE_CASES)
def test_every_reverse_discrete_form_matches_the_frozen_public_contract(
    name: str, n: int, expected: tuple[str, ...]
) -> None:
    """Pin all 547 reverse forms independently of implementation strategy."""
    assert tuple(discrete_colors(name, n, reverse=True)) == expected


@pytest.mark.parametrize(
    ("name", "n"),
    [
        (SEQUENTIAL[0], 10),
        (DIVERGING[0], 9),
        (MULTI_HUE[0], 8),
        (CYCLIC[0], 24),
        (QUALITATIVE[0], 8),
    ],
)
def test_dc_prefix_preserves_each_family_kind_at_maximum_n(
    name: str, n: int
) -> None:
    """Keep the public ``dc.`` spelling equivalent for all five kinds."""
    assert discrete_colors(f"dc.{name}", n) == discrete_colors(name, n)
