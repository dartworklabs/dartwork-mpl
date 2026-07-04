"""§11 migration policy — freeze by default, opt-in remap, deprecation warning."""

from __future__ import annotations

import warnings

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated
from dartwork_mpl.colors._compat_v4 import set_palette_version


@pytest.fixture(autouse=True)
def _restore_version():
    yield
    set_palette_version(4)


def test_default_is_frozen_legacy():
    named = mcolors.get_named_colors_mapping()
    assert named["dc.teal5"] != _generated.PALETTE["teal"][5]


def test_opt_in_remap_and_back():
    named = mcolors.get_named_colors_mapping()
    legacy_teal5 = named["dc.teal5"]
    set_palette_version(5)
    assert named["dc.teal5"] == _generated.PALETTE["teal"][5]
    set_palette_version(4)
    assert named["dc.teal5"] == legacy_teal5


def test_legacy_token_warns_once():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        dm.color("dc.vivid3")
        dm.color("dc.vivid3")
    dep = [w for w in rec if issubclass(w.category, DeprecationWarning)]
    assert len(dep) == 1
    assert "vivid3" in str(dep[0].message)


def test_v5_token_does_not_warn():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        dm.color("dc.blue6")
    assert not [w for w in rec if issubclass(w.category, DeprecationWarning)]


def test_get_palette_length_policy_default_legacy_eight():
    """Default (v4) caps the colliding curated names at the legacy 8-step
    ramp — v5's non-colliding steps 8-9 would otherwise silently widen
    ``get_palette("teal")`` to a mixed-generator 10-step ramp (spec §11 /
    Task 11's reconciliation of Task 9's review)."""
    assert len(dm.get_palette("teal")) == 8
    assert len(dm.get_palette("indigo")) == 8
    assert len(dm.get_palette("gray")) == 8


def test_get_palette_length_policy_v5_opt_in_ten():
    """After ``set_palette_version(5)`` steps 0-7 become v5 too, so all 10
    steps share one (v5) generator and the full ramp is coherent again."""
    set_palette_version(5)
    assert len(dm.get_palette("teal")) == 10
    assert len(dm.get_palette("indigo")) == 10
    assert len(dm.get_palette("gray")) == 10
    set_palette_version(4)
    assert len(dm.get_palette("teal")) == 8
