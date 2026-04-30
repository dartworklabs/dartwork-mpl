"""Smoke tests for the deprecated ``dartwork_mpl.helpers.formatting`` alias.

The module re-exports from :mod:`dartwork_mpl.helpers.labels` and emits a
``DeprecationWarning`` at import time. We only validate the alias still
delivers the expected names.
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

    # The aliases must still be present.
    for name in ("add_value_labels", "format_axis_labels", "optimize_legend"):
        assert hasattr(mod, name), f"Expected re-export {name} on alias"


def test_aliases_match_labels_module() -> None:
    from dartwork_mpl.helpers import formatting as alias_mod
    from dartwork_mpl.helpers import labels as labels_mod

    assert alias_mod.add_value_labels is labels_mod.add_value_labels
    assert alias_mod.format_axis_labels is labels_mod.format_axis_labels
    assert alias_mod.optimize_legend is labels_mod.optimize_legend
