"""Model B family taxonomy and measured color invariants."""

from __future__ import annotations

from collections import Counter
from itertools import pairwise

from dartwork_mpl.colors import _curated, _generated
from dartwork_mpl.colors._families import FAMILIES
from dartwork_mpl.colors._metrics import de2000_hex, lab_l_hex

EXPECTED = {
    "sequential": {
        "red",
        "rose",
        "coral",
        "tangerine",
        "orange",
        "amber",
        "yellow",
        "lime",
        "green",
        "teal",
        "cyan",
        "sky",
        "blue",
        "cobalt",
        "indigo",
        "violet",
        "purple",
        "fuchsia",
        "pink",
        "gray",
    },
    "multi-hue": {
        "afterglow",
        "aurora",
        "blaze",
        "canopy",
        "glacier",
        "haze",
        "iris",
        "lagoon",
        "lava",
    },
    "diverging": {
        "blue_red",
        "blue_orange",
        "cyan_red",
        "teal_amber",
        "teal_rose",
        "indigo_amber",
        "green_purple",
        "purple_orange",
        "violet_lime",
        "gray_blue",
        "gray_red",
    },
    "cyclic": {"hue", "halo", "corona"},
    "qualitative": {
        "trustworthy",
        "vivid",
        "neon",
        "pastel",
        "dusty",
        "ember",
        "earth",
        "jewel",
        "forest",
        "teal_accent",
        "coral_accent",
        "octave",
        "octave_print",
    },
}


def _lstars(name: str) -> list[float]:
    return [lab_l_hex(h) for h in _generated.CMAPS_256[name]]


def _monotonic(
    values: list[float], *, increasing: bool, tol: float = 0.2
) -> bool:
    pairs = pairwise(values)
    if increasing:
        return all(b >= a - tol for a, b in pairs)
    return all(b <= a + tol for a, b in pairs)


def test_family_partition_matches_model_b_catalog() -> None:
    by_kind = {
        kind: {name for name, family in FAMILIES.items() if family.kind == kind}
        for kind in EXPECTED
    }
    assert by_kind == EXPECTED
    assert Counter(family.kind for family in FAMILIES.values()) == {
        "sequential": 20,
        "multi-hue": 9,
        "diverging": 11,
        "cyclic": 3,
        "qualitative": 13,
    }
    assert len(FAMILIES) == 56


def test_family_discrete_sizes_match_model_b_forms() -> None:
    for name in EXPECTED["sequential"]:
        assert FAMILIES[name].has_continuous
        assert FAMILIES[name].discrete_size == 10
    for name in EXPECTED["diverging"]:
        assert FAMILIES[name].has_continuous
        assert FAMILIES[name].discrete_size == 8
    for name in EXPECTED["multi-hue"] | EXPECTED["cyclic"]:
        assert FAMILIES[name].has_continuous
        assert FAMILIES[name].discrete_size is None
    for name in EXPECTED["qualitative"]:
        assert not FAMILIES[name].has_continuous
        assert FAMILIES[name].discrete_size == 8


def test_sequential_and_multi_hue_lut_lightness_is_monotonic() -> None:
    for name in EXPECTED["sequential"]:
        assert _monotonic(_lstars(name), increasing=False), name
    for name in EXPECTED["multi-hue"]:
        assert _monotonic(_lstars(name), increasing=True), name


def test_diverging_lut_arms_are_monotonic_and_lstar_mirrored() -> None:
    max_mirror_delta = 0.0
    for name in EXPECTED["diverging"]:
        lstars = _lstars(name)
        apex = max(range(len(lstars)), key=lstars.__getitem__)
        left = lstars[: apex + 1]
        right = lstars[apex:]
        assert _monotonic(left, increasing=True), name
        assert _monotonic(right, increasing=False), name
        pairs = min(len(left), len(right))
        mirror_delta = max(abs(left[-1 - i] - right[i]) for i in range(pairs))
        max_mirror_delta = max(max_mirror_delta, mirror_delta)
    assert max_mirror_delta <= 0.85


def test_cyclic_lut_seams_are_closed_in_delta_e00() -> None:
    measured = {
        name: de2000_hex(
            _generated.CMAPS_256[name][0], _generated.CMAPS_256[name][-1]
        )
        for name in EXPECTED["cyclic"]
    }
    assert {name: round(value, 1) for name, value in measured.items()} == {
        "hue": 0.7,
        "halo": 1.9,
        "corona": 2.0,
    }
    assert max(measured.values()) <= 2.01


def test_qualitative_members_stay_inside_pinned_lstar_band() -> None:
    colors: list[str] = []
    for name in EXPECTED["qualitative"]:
        if name in _generated.CYCLES:
            colors.extend(_generated.CYCLES[name])
        else:
            colors.extend(_curated.CURATED[name])
    band = [lab_l_hex(h) for h in colors]
    assert min(band) >= 26.0
    assert max(band) <= 94.0
