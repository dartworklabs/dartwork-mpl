"""v5 palette token registration."""

from __future__ import annotations

import matplotlib.colors as mcolors

import dartwork_mpl  # noqa: F401  (등록 트리거)
from dartwork_mpl.colors import _generated


def _named() -> dict:
    return mcolors.get_named_colors_mapping()


def test_v5_tokens_registered_for_noncolliding_families():
    named = _named()
    for fam in ("red", "blue", "violet", "amber"):
        for step in range(10):
            assert named[f"dc.{fam}{step}"] == _generated.PALETTE[fam][step]


def test_v5_tokens_default_to_generated_values():
    named = _named()
    assert named["dc.teal5"] == _generated.PALETTE["teal"][5]
    assert named["dc.teal8"] == _generated.PALETTE["teal"][8]


def test_dm_alias_removed():
    assert "dm.blue6" not in _named()
