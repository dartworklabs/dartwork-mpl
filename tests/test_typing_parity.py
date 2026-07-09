"""Pin the generated typing Literals to the live registries (G5).

The pre-generation hand-maintained ``_typing.py`` drifted to ~98%
phantom/missing entries across two palette waves and the colormap
overhaul. These tests enforce exact equality in both directions; on
failure, rerun ``scripts/generate_typing.py``.
"""

from __future__ import annotations

from typing import get_args

import matplotlib as mpl
import matplotlib.colors as mcolors
import pytest

import dartwork_mpl  # noqa: F401 — registers color namespaces
from dartwork_mpl._colors._typing import DartworkColor, DartworkColormap

_REGEN = ".venv-local/bin/python scripts/generate_typing.py"

_COLOR_PREFIXES = ("ad.", "cu.", "dc.", "md.", "oc.", "pr.", "tw.")


def test_colormap_literal_matches_registry_exactly() -> None:
    registered = {n for n in mpl.colormaps if n.startswith("dc.")}
    literal = set(get_args(DartworkColormap))
    assert literal == registered, (
        f"DartworkColormap drift — phantom: {sorted(literal - registered)}, "
        f"missing: {sorted(registered - literal)}. Rerun: {_REGEN}"
    )


@pytest.mark.parametrize("prefix", _COLOR_PREFIXES)
def test_color_literal_matches_registry_per_prefix(prefix: str) -> None:
    mapping = mcolors.get_named_colors_mapping()
    registered = {k for k in mapping if k.startswith(prefix)}
    literal = {n for n in get_args(DartworkColor) if n.startswith(prefix)}
    assert literal == registered, (
        f"DartworkColor drift for {prefix!r} — "
        f"phantom: {sorted(literal - registered)[:5]}, "
        f"missing: {sorted(registered - literal)[:5]}. Rerun: {_REGEN}"
    )


def test_color_literal_has_no_foreign_prefixes() -> None:
    """The Literal must contain only the seven canonical prefixes (the
    dm.* alias namespace is deliberately excluded)."""
    foreign = {
        n for n in get_args(DartworkColor) if not n.startswith(_COLOR_PREFIXES)
    }
    assert not foreign, f"unexpected entries: {sorted(foreign)[:5]}"
