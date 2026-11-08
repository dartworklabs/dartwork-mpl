"""Public ``findfont`` must follow font-table mutations that bundled loading makes.

Registering the bundled fonts changes two things that decide which file
``matplotlib.font_manager.findfont`` returns: the bundled entries are moved to
the front of ``fontManager.ttflist`` (so they win score ties against
same-named system fonts) and known-wrong bundled weights are replaced. A
resolution that was already cached before either change would keep pointing
at the old file unless the cache is invalidated.

``font/tests/test_font.py`` only observes the cache's size after the change.
These tests observe what a caller sees: the file the public ``findfont``
returns for a request that was already answered before the change.

Each request uses a font size no other test uses, so its cache key is fresh
and the test never has to reach into matplotlib's private cache.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from matplotlib import font_manager
from matplotlib.font_manager import FontEntry, FontProperties

from dartwork_mpl import font as font_module


def _resolve(prop: FontProperties) -> Path:
    return Path(
        font_manager.findfont(prop, fallback_to_default=False)
    ).resolve()


def test_bundled_first_order_replaces_a_primed_system_tie_winner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A tie won by an earlier non-bundled copy flips to the bundled file."""
    bundle_dir = font_module.get_font_dir()
    manager = font_manager.fontManager
    regular = next(
        entry
        for entry in manager.ttflist
        if Path(entry.fname).resolve() == bundle_dir / "Roboto-Regular.ttf"
    )
    # A stand-in for a system-installed copy: same family, style and weight,
    # so it ties the bundled entry on score, but it lives outside the bundle.
    system_copy = tmp_path / "Roboto-Regular.ttf"
    shutil.copy(regular.fname, system_copy)
    shadow = replace(regular, fname=str(system_copy))
    monkeypatch.setattr(manager, "ttflist", [shadow, *manager.ttflist])
    prop = FontProperties(family="Roboto", size=11.111)

    # Control: the earlier copy really wins the tie, and is now cached.
    assert _resolve(prop) == system_copy.resolve()

    font_module._promote_bundled_fonts()

    assert _resolve(prop) == bundle_dir / "Roboto-Regular.ttf"


def test_weight_correction_replaces_a_primed_tie_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Corrected Paperlogy weights change the file a primed light request gets."""
    manager = font_manager.fontManager
    thin_name, extra_light_name = (
        "Paperlogy-1Thin.ttf",
        "Paperlogy-2ExtraLight.ttf",
    )
    # Each file is registered under several names, so keep every entry and
    # only restore the wrong weight.
    wrong: dict[str, list[FontEntry]] = {thin_name: [], extra_light_name: []}
    rest: list[FontEntry] = []
    for entry in manager.ttflist:
        name = Path(entry.fname).name
        if name in wrong:
            wrong[name].append(replace(entry, weight=250))
        else:
            rest.append(entry)
    # Both files advertise weight 250; the earlier one wins a light request.
    # Thin first makes the stale answer differ from the corrected one.
    monkeypatch.setattr(
        manager, "ttflist", [*wrong[thin_name], *wrong[extra_light_name], *rest]
    )
    prop = FontProperties(family="Paperlogy", weight="light", size=11.222)

    # Control: the wrong tie really resolves to Thin, and is now cached.
    assert _resolve(prop).name == thin_name

    font_module._correct_bundled_weight_metadata()

    assert _resolve(prop).name == extra_light_name
