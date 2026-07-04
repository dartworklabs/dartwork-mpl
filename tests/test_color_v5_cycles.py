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
    assert gate_cycle(default)["min00"] >= 10.0
    assert gate_cycle(cycle_hexes("print", pal))["min00"] >= 10.0
