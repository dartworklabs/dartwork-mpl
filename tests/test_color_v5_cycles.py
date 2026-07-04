"""Tests for colors._cycles — frozen cycle specs (스펙 §8)."""

from __future__ import annotations

from dartwork_mpl.colors._cycles import CYCLE_SPECS, cycle_hexes
from dartwork_mpl.colors._gates import gate_cycle


def test_specs_match_ssot(v5_ssot):
    assert [list(x) for x in CYCLE_SPECS["default"]] == v5_ssot[
        "cycle_default"
    ]["spec"]
    assert [list(x) for x in CYCLE_SPECS["print"]] == v5_ssot["cycle_print"][
        "spec"
    ]


def test_hexes_and_gate(v5_ssot):
    pal = v5_ssot["palette"]
    default = cycle_hexes("default", pal)
    assert len(default) == 7
    assert default[0] == pal["blue"][6]
    # Common deficiencies (normal + protan + deutan) held to 10; the rare
    # tritan to a realistic 8 under the accurate Brettel-1997 model.
    for hexes in (default, cycle_hexes("print", pal)):
        g = gate_cycle(hexes)
        assert g["common_min"] >= 10.0
        assert g["tritan"] >= 8.0
