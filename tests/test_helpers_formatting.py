"""Smoke tests for the deprecated ``dartwork_mpl.helpers.formatting`` alias.

The module re-exports from :mod:`dartwork_mpl.helpers.labels` and emits a
``DeprecationWarning`` at import time. We validate the alias still
delivers the remaining names after round-3 API pruning.
"""

from __future__ import annotations

import importlib
import warnings


def test_import_emits_deprecation_warning() -> None:
    # Reload to guarantee the module-level warnings.warn fires under
    # this test even if another test already imported it.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        mod = importlib.reload(
            importlib.import_module("dartwork_mpl.helpers.formatting")
        )

    assert any(
        issubclass(w.category, DeprecationWarning)
        and "deprecated" in str(w.message).lower()
        for w in caught
    ), "DeprecationWarning was not emitted on import"

    # The remaining alias must still be present.
    assert hasattr(mod, "optimize_legend"), "Expected re-export optimize_legend"


def test_aliases_match_labels_module() -> None:
    from dartwork_mpl.helpers import formatting as alias_mod
    from dartwork_mpl.helpers import labels as labels_mod

    assert alias_mod.optimize_legend is labels_mod.optimize_legend


def test_alias_module_has_dunder_all() -> None:
    """The alias declares ``__all__`` for re-export discovery."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from dartwork_mpl.helpers import formatting as alias_mod

    assert hasattr(alias_mod, "__all__")
    assert set(alias_mod.__all__) == {"optimize_legend"}


def test_removed_names_no_longer_in_alias() -> None:
    """``format_axis_labels`` and ``add_value_labels`` were removed in
    round-3 of the API audit and must not be present on the alias."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from dartwork_mpl.helpers import formatting as alias_mod

    assert not hasattr(alias_mod, "format_axis_labels")
    assert not hasattr(alias_mod, "add_value_labels")
