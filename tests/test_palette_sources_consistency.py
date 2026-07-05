"""v5 palette source and runtime registry must agree hex-for-hex."""

from __future__ import annotations

import matplotlib.colors as mcolors

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated
from dartwork_mpl.colors._loader import ensure_loaded


def test_generated_palette_registers_every_v5_token_hex_for_hex() -> None:
    """``_generated.PALETTE`` is the v5 source consumed by the loader."""
    ensure_loaded()
    mapping = mcolors.get_named_colors_mapping()
    for family, row in _generated.PALETTE.items():
        assert len(row) == 10
        for step, expected in enumerate(row):
            assert mapping[f"dc.{family}{step}"] == expected


def test_get_palette_resolves_every_v5_family_to_ten_steps() -> None:
    """Bare v5 family names resolve to the full 10-step ``dc.<family>`` row."""
    for family in _generated.PALETTE:
        cols = dm.get_palette(family)
        assert cols == [f"dc.{family}{i}" for i in range(10)]


def test_default_cycle_tokens_are_generated_v5_values() -> None:
    """The published default cycle is a selected subset of v5 palette tokens."""
    expected_tokens = (
        "dc.blue6",
        "dc.orange9",
        "dc.green5",
        "dc.pink3",
        "dc.amber7",
        "dc.violet8",
        "dc.cyan8",
    )
    expected_hexes = [dm.color(token).to_hex() for token in expected_tokens]
    assert list(_generated.CYCLES["default"]) == expected_hexes
