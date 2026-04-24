"""Deprecation regression for :mod:`dartwork_mpl.asset_viz`.

The real implementations moved to :mod:`dartwork_mpl.diagnostics` in
the v0.3.x series (see issue #57). The legacy ``asset_viz`` import
path is retained as a thin shim that must:

1. keep exposing the same four names, and
2. emit a :class:`DeprecationWarning` on import.

The functional behaviour of the four helpers is covered by
``tests/test_diagnostics.py`` — we only pin the shim contract here.
"""

from __future__ import annotations

import importlib
import sys
import warnings

import matplotlib

matplotlib.use("Agg")


def _reimport_asset_viz():
    """Force a fresh import so ``__init__`` re-runs and re-warns."""
    sys.modules.pop("dartwork_mpl.asset_viz", None)
    return importlib.import_module("dartwork_mpl.asset_viz")


def test_legacy_path_still_works() -> None:
    """``from dartwork_mpl.asset_viz import ...`` continues to work."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        module = _reimport_asset_viz()

    assert hasattr(module, "classify_colormap")
    assert hasattr(module, "plot_colormaps")
    assert hasattr(module, "plot_colors")
    assert hasattr(module, "plot_fonts")


def test_legacy_path_emits_deprecation_warning() -> None:
    """Importing ``dartwork_mpl.asset_viz`` fires ``DeprecationWarning``."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _reimport_asset_viz()

    messages = [str(w.message) for w in caught]
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "asset_viz" in str(w.message)
        for w in caught
    ), f"Expected DeprecationWarning mentioning 'asset_viz', got {messages}"


def test_legacy_symbols_match_canonical() -> None:
    """Legacy re-exports must be the same object as the canonical ones."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        legacy = _reimport_asset_viz()

    from dartwork_mpl import diagnostics

    assert legacy.classify_colormap is diagnostics.classify_colormap
    assert legacy.plot_colormaps is diagnostics.plot_colormaps
    assert legacy.plot_colors is diagnostics.plot_colors
    assert legacy.plot_fonts is diagnostics.plot_fonts
