"""Model B designed discrete color forms.

The frozen v5 compatibility and quality inputs are read when a test that
needs them runs, not when this module is collected, so the tests that do not
read them still collect and run where those inputs are absent.
"""

from __future__ import annotations

import functools
import json
from itertools import pairwise
from pathlib import Path
from typing import cast

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl  # noqa: F401  (registers color names)
import dartwork_mpl._colors._compatibility_metrics as oracle
from dartwork_mpl._colors import _curated, _generated
from dartwork_mpl._colors.catalog._discrete import (
    DIVERGING_CANONICALS,
    discrete_colors,
)
from dartwork_mpl._colors.catalog._families import (
    CYCLIC,
    DIVERGING,
    FAMILIES,
    MULTI_HUE,
    QUALITATIVE,
    SEQUENTIAL,
)
from dartwork_mpl._colors.verify._comparison import matches_recorded_quality
from tests.support.approved_inputs import read_approved_text

REPO_ROOT = Path(__file__).resolve().parents[5]
COMPATIBILITY_INPUT = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_compatibility.json"
)
QUALITY_INPUT = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_quality.json"
)
V6_SSOT_PATH = REPO_ROOT / "src/dartwork_mpl/asset/color/color_v6_ssot.json"

# The frozen inventory sizes. The raw-SHA pin on the compatibility input fixes
# its bytes, so case ``i`` always names the same form: families sorted by
# name, then sizes in ascending order.
DISCRETE_FORM_COUNT = 547
MULTI_HUE_FORM_COUNT = 72

GENERATED_DIVERGING = tuple(
    name for name in DIVERGING if name not in _curated.CURATED_DIVERGING_ORDER
)

DiscreteCase = tuple[str, int, tuple[str, ...]]
MultiHueCase = tuple[str, int, tuple[int, ...], tuple[str, ...]]


def _json_object(text: str, label: object) -> dict[str, object]:
    """Decode one checked-in JSON contract as a string-keyed object."""
    decoded: object = json.loads(text)
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) for key in decoded
    ):
        raise TypeError(f"{label} must contain a JSON object")
    return cast(dict[str, object], decoded)


def _load_json(path: Path) -> dict[str, object]:
    """Load one checked-in JSON contract as a string-keyed object."""
    return _json_object(path.read_text(encoding="utf-8"), path)


@functools.cache
def _compatibility() -> dict[str, object]:
    """Load the pinned v5 compatibility input on first use."""
    return _json_object(
        read_approved_text(COMPATIBILITY_INPUT), COMPATIBILITY_INPUT
    )


@functools.cache
def _quality() -> dict[str, object]:
    """Load the pinned v5 quality input on first use."""
    return _json_object(read_approved_text(QUALITY_INPUT), QUALITY_INPUT)


V6_SSOT = _load_json(V6_SSOT_PATH)


@functools.cache
def _discrete_cases(field: str) -> tuple[DiscreteCase, ...]:
    """List every frozen discrete API form in a stable order."""
    families = cast(dict[str, dict[str, list[str]]], _compatibility()[field])
    return tuple(
        (name, int(size), tuple(colors))
        for name, forms in sorted(families.items())
        for size, colors in sorted(forms.items(), key=lambda item: int(item[0]))
    )


@functools.cache
def _multi_hue_cases() -> tuple[MultiHueCase, ...]:
    """List all 72 frozen multi-hue index and shipped-hex cases."""
    compatibility = _compatibility()
    indices = cast(
        dict[str, dict[str, list[int]]],
        compatibility["multi_hue_discrete_indices"],
    )
    colors = cast(
        dict[str, dict[str, list[str]]], compatibility["discrete_hex"]
    )
    return tuple(
        (name, int(size), tuple(row), tuple(colors[name][size]))
        for name, forms in sorted(indices.items())
        for size, row in sorted(forms.items(), key=lambda item: int(item[0]))
    )


def _case_id(index: int) -> str:
    """Name one inventory index; the test reports the family and size."""
    return f"case{index:03d}"


@pytest.mark.approved_input
def test_frozen_discrete_case_inventory_is_complete() -> None:
    """Cover 547 forward/reverse forms and all 72 multi-hue rows."""
    assert (
        len(_discrete_cases("discrete_hex")),
        len(_discrete_cases("reverse_discrete_hex")),
        len(_multi_hue_cases()),
    ) == (DISCRETE_FORM_COUNT, DISCRETE_FORM_COUNT, MULTI_HUE_FORM_COUNT)


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


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(MULTI_HUE_FORM_COUNT), ids=_case_id)
def test_v6_multi_hue_manifest_matches_every_frozen_index_row(
    index: int,
) -> None:
    name, n, expected_indices, _ = _multi_hue_cases()[index]
    manifest = cast(
        dict[str, dict[str, list[int]]], V6_SSOT["multi_hue_discrete_indices"]
    )

    assert tuple(manifest[name][str(n)]) == expected_indices, (name, n)


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(MULTI_HUE_FORM_COUNT), ids=_case_id)
def test_generated_module_exposes_every_frozen_multi_hue_index_row(
    index: int,
) -> None:
    name, n, expected_indices, _ = _multi_hue_cases()[index]
    manifest = getattr(_generated, "MULTI_HUE_DISCRETE_INDICES", None)

    assert manifest is not None
    assert tuple(manifest[name][n]) == expected_indices, (name, n)


def test_generated_module_exposes_multi_hue_discrete_manifest() -> None:
    """Require the generated artifact to publish the frozen index table."""
    assert hasattr(_generated, "MULTI_HUE_DISCRETE_INDICES")


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(MULTI_HUE_FORM_COUNT), ids=_case_id)
def test_multi_hue_indices_select_the_exact_shipped_hex(index: int) -> None:
    name, n, expected_indices, expected_hex = _multi_hue_cases()[index]
    selected = tuple(
        _generated.CMAPS_256[name][position] for position in expected_indices
    )

    assert selected == expected_hex, (name, n)


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(MULTI_HUE_FORM_COUNT), ids=_case_id)
def test_multi_hue_index_rows_increase_and_select_unique_hex(
    index: int,
) -> None:
    name, n, expected_indices, expected_hex = _multi_hue_cases()[index]

    assert len(expected_indices) == len(expected_hex) == n, (name, n)
    assert all(left < right for left, right in pairwise(expected_indices))
    assert len(set(expected_hex)) == n


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(MULTI_HUE_FORM_COUNT), ids=_case_id)
def test_multi_hue_raw_quality_matches_the_independent_frozen_oracle(
    index: int,
) -> None:
    name, n, _, expected_hex = _multi_hue_cases()[index]
    metrics = cast(dict[str, object], _quality()["metrics"])
    discrete = cast(
        dict[str, dict[str, dict[str, object]]], metrics["discrete"]
    )

    # Compared with the oracle's own tolerance rather than by ==: these are
    # doubles recomputed from the frozen hex, and the recorded baseline was
    # captured on a different machine than CI runs on. Structure, keys and
    # every non-numeric leaf are still matched exactly.
    assert matches_recorded_quality(
        oracle.categorical_quality(expected_hex), discrete[name][str(n)]
    ), (name, n)


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


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(DISCRETE_FORM_COUNT), ids=_case_id)
def test_every_forward_discrete_form_matches_the_frozen_public_contract(
    index: int,
) -> None:
    """Pin all 547 forward forms, including every family kind and maximum."""
    name, n, expected = _discrete_cases("discrete_hex")[index]
    assert tuple(discrete_colors(name, n)) == expected, (name, n)


@pytest.mark.approved_input
@pytest.mark.parametrize("index", range(DISCRETE_FORM_COUNT), ids=_case_id)
def test_every_reverse_discrete_form_matches_the_frozen_public_contract(
    index: int,
) -> None:
    """Pin all 547 reverse forms independently of implementation strategy."""
    name, n, expected = _discrete_cases("reverse_discrete_hex")[index]
    assert tuple(discrete_colors(name, n, reverse=True)) == expected, (name, n)


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
