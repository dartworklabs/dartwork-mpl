"""Model B designed discrete color forms."""

from __future__ import annotations

from itertools import combinations, pairwise

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl  # noqa: F401  (registers color names)
from dartwork_mpl._colors import _curated, _generated
from dartwork_mpl._colors._discrete import (
    DIVERGING_CANONICALS,
    MULTI_HUE_MIN_DE00_FLOORS,
    discrete_colors,
)
from dartwork_mpl._colors._families import (
    CYCLIC,
    DIVERGING,
    FAMILIES,
    MULTI_HUE,
    QUALITATIVE,
    SEQUENTIAL,
)
from dartwork_mpl._colors._metrics import de2000_hex, lab_l_hex

GENERATED_DIVERGING = tuple(
    name for name in DIVERGING if name not in _curated.CURATED_DIVERGING_ORDER
)


def _min_pairwise_de00(colors: list[str]) -> float:
    return min(de2000_hex(a, b) for a, b in combinations(colors, 2))


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
    if n > 1:
        lstars = [lab_l_hex(c) for c in colors]
        assert all(a >= b for a, b in pairwise(lstars))


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


@pytest.mark.parametrize("name", MULTI_HUE)
@pytest.mark.parametrize("n", [3, 4, 6, 8])
def test_multi_hue_forms_are_deterministic_and_pinned(
    name: str, n: int
) -> None:
    colors = discrete_colors(name, n)
    assert colors == discrete_colors(name, n)
    assert len(colors) == n
    assert all(c in _generated.CMAPS_256[name] for c in colors)
    positions = [_generated.CMAPS_256[name].index(c) for c in colors]
    assert positions == sorted(positions)
    lstars = [lab_l_hex(c) for c in colors]
    assert min(lstars) >= 35.0
    assert max(lstars) <= 90.0
    if n == 8:
        assert (
            round(_min_pairwise_de00(colors), 1)
            == (MULTI_HUE_MIN_DE00_FLOORS[name])
        )


def test_multi_hue_min_de00_floors_are_measured_and_pinned() -> None:
    assert MULTI_HUE_MIN_DE00_FLOORS == {
        "afterglow": 6.7,
        "aurora": 7.4,
        "blaze": 12.0,
        "canopy": 7.4,
        "glacier": 7.5,
        "haze": 3.7,
        "iris": 8.0,
        "lagoon": 5.1,
        "lava": 6.8,
    }


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
        (QUALITATIVE[0], FAMILIES[QUALITATIVE[0]].discrete_size + 1),
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
