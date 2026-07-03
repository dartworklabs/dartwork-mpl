"""v5 palette token registration + legacy collision policy (스펙 §11)."""

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


def test_colliding_tokens_default_to_frozen_legacy():
    # dc.teal5 는 레거시 dc_palettes.json 값 유지 (silent recolor 금지 — §11)
    named = _named()
    assert named["dc.teal5"] != _generated.PALETTE["teal"][5]
    # 레거시에 없는 스텝(8·9)은 v5 값으로 등록
    assert named["dc.teal8"] == _generated.PALETTE["teal"][8]


def test_dm_alias_exists():
    assert _named()["dm.blue6"] == _named()["dc.blue6"]
