"""Model B family taxonomy and measured color invariants."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from functools import cache
from typing import cast

from dartwork_mpl._colors import _compatibility_metrics as oracle
from dartwork_mpl._colors import _curated, _generated
from dartwork_mpl._colors._families import FAMILIES
from dartwork_mpl._colors._gates import (
    evaluate_quality_metrics,
    load_quality_baseline,
)

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


def _mapping(value: object, label: str) -> Mapping[str, object]:
    """Narrow one string-keyed raw quality mapping."""
    assert isinstance(value, Mapping), label
    assert all(isinstance(key, str) for key in value), label
    return cast(Mapping[str, object], value)


@cache
def _baseline_metrics() -> Mapping[str, object]:
    """Load the hash-validated raw v5 quality baseline once."""
    baseline = load_quality_baseline()
    return _mapping(baseline["metrics"], "quality metrics")


def _evaluate_subset(
    section: str,
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> None:
    """Apply shared raw policy to one family-invariant metric section."""
    metrics = _baseline_metrics()
    dark = metrics["dark_cycle"]
    violations = evaluate_quality_metrics(
        {section: baseline, "dark_cycle": dark},
        {section: candidate, "dark_cycle": dark},
        {name: family.kind for name, family in FAMILIES.items()},
    )
    assert violations == ()


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


def test_sequential_and_multi_hue_lut_keep_raw_y_oklab_topology() -> None:
    """Gate ordered LUT direction, Y/L minima, span, CVD, and step CV."""
    names = EXPECTED["sequential"] | EXPECTED["multi-hue"]
    baseline_rows = _mapping(
        _baseline_metrics()["cmaps_full_256"], "full LUT baseline"
    )
    expected = {name: baseline_rows[name] for name in sorted(names)}
    measured = {
        name: oracle.ordered_quality(_generated.CMAPS_256[name])
        for name in sorted(names)
    }

    _evaluate_subset("cmaps_full_256", expected, measured)


def test_diverging_lut_keeps_raw_y_oklab_two_arm_topology() -> None:
    """Gate center, both arms, mirrors, and OKLab step balance raw."""
    topology = _mapping(_baseline_metrics()["topology"], "topology baseline")
    baseline_rows = _mapping(topology["diverging"], "diverging baseline")
    expected = {
        name: baseline_rows[name] for name in sorted(EXPECTED["diverging"])
    }
    measured = {
        name: oracle.diverging_topology(_generated.CMAPS_256[name])
        for name in sorted(EXPECTED["diverging"])
    }

    _evaluate_subset(
        "topology",
        {"diverging": expected, "cyclic": {}},
        {"diverging": measured, "cyclic": {}},
    )


def test_cyclic_lut_keeps_raw_oracle_seam_and_topology() -> None:
    """Gate unrounded seam distances, Y spread, and twilight arm topology."""
    topology = _mapping(_baseline_metrics()["topology"], "topology baseline")
    baseline_rows = _mapping(topology["cyclic"], "cyclic baseline")
    expected = {
        name: baseline_rows[name] for name in sorted(EXPECTED["cyclic"])
    }
    measured = {
        name: oracle.cyclic_topology(_generated.CMAPS_256[name])
        for name in sorted(EXPECTED["cyclic"])
    }

    _evaluate_subset(
        "topology",
        {"diverging": {}, "cyclic": expected},
        {"diverging": {}, "cyclic": measured},
    )


def test_qualitative_members_keep_raw_cvd_separation_floors() -> None:
    """Use independent CIEDE2000/CVD validation, not an L* authoring band."""
    metrics = _baseline_metrics()
    baseline_cycles = _mapping(metrics["cycles"], "cycle baseline")
    baseline_curated = _mapping(metrics["curated_rows"], "curated baseline")
    cycle_names = EXPECTED["qualitative"] & set(_generated.CYCLES)
    curated_names = EXPECTED["qualitative"] & set(_curated.CURATED)
    expected_cycles = {
        name: baseline_cycles[name] for name in sorted(cycle_names)
    }
    expected_curated = {
        name: baseline_curated[name] for name in sorted(curated_names)
    }
    measured_cycles = {
        name: oracle.categorical_quality(_generated.CYCLES[name])
        for name in sorted(cycle_names)
    }
    measured_curated = {
        name: oracle.categorical_quality(_curated.CURATED[name])
        for name in sorted(curated_names)
    }
    dark = metrics["dark_cycle"]

    violations = evaluate_quality_metrics(
        {
            "cycles": expected_cycles,
            "curated_rows": expected_curated,
            "dark_cycle": dark,
        },
        {
            "cycles": measured_cycles,
            "curated_rows": measured_curated,
            "dark_cycle": dark,
        },
        {},
    )
    assert violations == ()
