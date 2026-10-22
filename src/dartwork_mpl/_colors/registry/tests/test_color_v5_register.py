"""v5 cmap registration (matplotlib-native access)."""

from __future__ import annotations

import subprocess
import sys
import textwrap

import matplotlib as mpl
import pytest

import dartwork_mpl  # noqa: F401 — registers dc.* cmaps on import
from dartwork_mpl._colors import _generated


def _registry_process(code: str) -> None:
    """Exercise the real native registry in an independent interpreter."""
    process = subprocess.run(
        [sys.executable, "-B", "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr


def test_reload_and_partial_retry_preserve_all_native_maps() -> None:
    """Reload and bounded missing-map retries keep all 99 exact maps intact."""
    _registry_process("""
        import importlib
        import random
        import matplotlib as mpl
        import dartwork_mpl
        reg = importlib.import_module('dartwork_mpl._colors.registry._register')
        expected = {n: mpl.colormaps[n] for n in mpl.colormaps if n.startswith('dc.')}
        assert len(expected) == 99
        rng = random.Random(501)
        for count in (0, 1, 7, 13):
            for name in rng.sample(list(expected), count):
                mpl.colormaps.unregister(name)
            importlib.reload(reg)
            assert reg.ensure_registered() is None
            assert reg.ensure_registered() is None
            assert {n for n in mpl.colormaps if n.startswith('dc.')} == set(expected)
            assert all(mpl.colormaps[n] == cm for n, cm in expected.items())
    """)


@pytest.mark.parametrize("position", [43, -1])
def test_static_external_collision_adds_nothing_and_removal_allows_retry(
    position: int,
) -> None:
    """A middle or last collision preserves the whole registry before retry."""
    names = [n for n in mpl.colormaps if n.startswith("dc.")]
    name = names[position]
    _registry_process(f"""
        import importlib
        import matplotlib as mpl
        from matplotlib.colors import ListedColormap
        name = {name!r}
        mpl.colormaps.register(ListedColormap(['red', 'blue'], name=name))
        mpl.colormaps.register(ListedColormap(['green'], name='core.unrelated'))
        before = {{n: mpl.colormaps[n] for n in mpl.colormaps}}
        try:
            importlib.import_module('dartwork_mpl')
        except ValueError as error:
            assert name in str(error)
        else:
            raise AssertionError('external collision was accepted')
        assert set(mpl.colormaps) == set(before), 'static collision added maps'
        assert all(mpl.colormaps[n] == cm for n, cm in before.items())
        mpl.colormaps.unregister(name)
        importlib.import_module('dartwork_mpl')
        assert len([n for n in mpl.colormaps if n.startswith('dc.')]) == 99
        assert mpl.colormaps['core.unrelated'] == before['core.unrelated']
    """)


@pytest.mark.parametrize(
    "change", ["untagged", "bad", "under", "over", "extend"]
)
def test_existing_equal_lut_requires_package_provenance_and_exact_metadata(
    change: str,
) -> None:
    """Equal visible colors cannot authorize external or metadata-altered maps."""
    _registry_process(f"""
        import importlib
        import matplotlib as mpl
        from matplotlib.colors import ListedColormap
        import dartwork_mpl
        reg = importlib.import_module('dartwork_mpl._colors.registry._register')
        name = 'dc.aurora'
        original = mpl.colormaps[name]
        changed = original.copy()
        change = {change!r}
        if change == 'untagged':
            changed = ListedColormap(original.colors, name=name)
        elif change == 'extend':
            changed.colorbar_extend = 'both'
        else:
            getattr(changed, 'set_' + change)('#a1b2c3')
        mpl.colormaps.unregister(name)
        mpl.colormaps.register(changed)
        # The loaded fast path remains intentionally unchanged.
        assert reg.ensure_registered() is None
        before = {{n: mpl.colormaps[n] for n in mpl.colormaps}}
        importlib.reload(reg)
        try:
            reg.ensure_registered()
        except ValueError as error:
            assert name in str(error)
        else:
            raise AssertionError('changed map was accepted')
        assert set(mpl.colormaps) == set(before)
        assert all(mpl.colormaps[n] == cm for n, cm in before.items())
        mpl.colormaps.unregister(name)
        mpl.colormaps.register(original)
        assert reg.ensure_registered() is None
    """)


def test_registry_names():
    for name in ("aurora", "blue", "blue_red", "halo"):
        assert f"dc.{name}" in mpl.colormaps
        assert f"dc.{name}_r" in mpl.colormaps
    assert "dc.octave" in mpl.colormaps and "dc.octave_print" in mpl.colormaps
    assert "dc.cycle" not in mpl.colormaps
    assert "dc.cycle_print" not in mpl.colormaps
    for name in ("coast", "blue_red_deep", "blue_red_soft"):
        assert f"dc.{name}" not in mpl.colormaps
        assert f"dc.{name}_r" not in mpl.colormaps


def test_registry_access_matplotlib_native():
    cm = mpl.colormaps["dc.aurora"]
    assert cm.N == 256
    assert [mpl.colors.to_hex(c) for c in cm.colors] == list(
        _generated.CMAPS_256["aurora"]
    )
    assert (
        mpl.colors.to_hex(mpl.colormaps["dc.aurora_r"].colors[0])
        == _generated.CMAPS_256["aurora"][-1]
    )
    with pytest.raises(KeyError):
        mpl.colormaps["dc.no_such_map"]


def test_v5_coral_colormap_comes_from_generated_catalog():
    """Promoted generated families own their ``dc.<family>`` colormap names."""
    cm = mpl.colormaps["dc.coral"]
    assert [mpl.colors.to_hex(c) for c in cm.colors] == list(
        _generated.CMAPS_256["coral"]
    )


def test_v5_cycle_cmap_tokens_stay_stable():
    """Cycle colormap tokens use the canonical octave names."""
    assert "dc.octave" in mpl.colormaps
    assert "dc.octave_print" in mpl.colormaps
    assert [
        mpl.colors.to_hex(c) for c in mpl.colormaps["dc.octave"].colors
    ] == list(_generated.CYCLES["octave"])
    assert [
        mpl.colors.to_hex(c) for c in mpl.colormaps["dc.octave_print"].colors
    ] == list(_generated.CYCLES["octave_print"])


def test_deleted_legacy_cmaps_are_absent():
    assert "dc.legacy_aurora" not in mpl.colormaps
    assert "dc.legacy_aurora_r" not in mpl.colormaps
    assert "dc.legacy_teal_rose" not in mpl.colormaps
    assert "dc.legacy_teal_rose_r" not in mpl.colormaps


def test_cmap_module_removed():
    import importlib

    import dartwork_mpl as dm

    assert not hasattr(dm, "cmap")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("dartwork_mpl" + ".cmap")
