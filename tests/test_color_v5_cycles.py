"""Tests for colors._cycles — frozen cycle specs (스펙 §8)."""

from __future__ import annotations

from itertools import combinations

from dartwork_mpl.colors._cycles import CYCLE_SPECS, cycle_hexes
from dartwork_mpl.colors._gates import gate_cycle
from dartwork_mpl.colors._metrics import lab_l_hex

_OCTAVE_PRINT_SPEC = [
    ["blue", 5],
    ["orange", 8],
    ["green", 1],
    ["pink", 2],
    ["amber", 5],
    ["violet", 9],
    ["cyan", 8],
    ["gray", 9],
]
_OCTAVE_PRINT_HEXES = [
    "#4aabfa",
    "#ef611a",
    "#cbf2cf",
    "#fdc0d6",
    "#ffa926",
    "#5a3ec3",
    "#128397",
    "#404245",
]


def test_specs_match_ssot(v5_ssot):
    assert [list(x) for x in CYCLE_SPECS["octave"]] == v5_ssot["cycle_default"][
        "spec"
    ]
    assert [list(x) for x in CYCLE_SPECS["octave_print"]] == v5_ssot[
        "cycle_print"
    ]["spec"]


def test_hexes_and_gate(v5_ssot):
    pal = v5_ssot["palette"]
    octave = cycle_hexes("octave", pal)
    octave_print = cycle_hexes("octave_print", pal)
    assert len(octave) == 8
    assert octave[0] == pal["blue"][6]
    assert octave[-1] == pal["rose"][8]
    assert [list(x) for x in CYCLE_SPECS["octave_print"]] == _OCTAVE_PRINT_SPEC
    assert octave_print == _OCTAVE_PRINT_HEXES
    # Common deficiencies (normal + protan + deutan) held to 10; the rare
    # tritan to a realistic 8 under the accurate Brettel-1997 model.
    for hexes in (octave, octave_print):
        g = gate_cycle(hexes)
        assert g["common_min"] >= 10.0
        assert g["tritan"] >= 8.0

    g_print = gate_cycle(octave_print)
    assert g_print["common_min"] == 10.4
    assert g_print["tritan"] == 9.8
    assert g_print["min00"] == 9.8
    lightness = [lab_l_hex(h) for h in octave_print]
    min_dl_all = min(abs(a - b) for a, b in combinations(lightness, 2))
    min_dl_first_four = min(
        abs(a - b) for a, b in combinations(lightness[:4], 2)
    )
    assert round(min_dl_first_four, 1) == 8.3
    assert round(min_dl_all, 1) == 7.7


def test_octave_print_is_hue_parallel_with_octave():
    assert [fam for fam, _ in CYCLE_SPECS["octave"][:7]] == [
        fam for fam, _ in CYCLE_SPECS["octave_print"][:7]
    ]
    assert CYCLE_SPECS["octave_print"][5][0] == "violet"
    assert CYCLE_SPECS["octave_print"][7][0] == "gray"
