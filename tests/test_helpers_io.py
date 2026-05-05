"""Tests for ``dartwork_mpl.helpers`` package.

The ``save_figure`` and ``create_figure_with_style`` helpers were removed in
0.5.0 (round 2 of the API audit, #141). This file verifies that:

1. The ``helpers`` package-level imports that *remain* are still accessible.
2. The deleted names are no longer present in ``helpers.__all__`` or as
   attributes of the ``helpers`` package.
"""

from __future__ import annotations

import importlib

import pytest

import dartwork_mpl as dm
from dartwork_mpl import helpers


class TestRemainingHelpersExported:
    """The remaining helpers must still be importable from ``dm.helpers``."""

    def test_auto_select_colors_accessible(self) -> None:
        assert hasattr(helpers, "auto_select_colors")

    def test_check_figure_quality_accessible(self) -> None:
        assert hasattr(helpers, "check_figure_quality")

    def test_validate_data_accessible(self) -> None:
        assert hasattr(helpers, "validate_data")

    def test_suggest_chart_type_accessible(self) -> None:
        assert hasattr(helpers, "suggest_chart_type")

    def test_optimize_legend_accessible(self) -> None:
        assert hasattr(helpers, "optimize_legend")


class TestRemovedHelpersGone:
    """Deleted names must not exist on ``helpers`` or in ``dm``."""

    def test_save_figure_not_in_helpers_all(self) -> None:
        assert "save_figure" not in helpers.__all__

    def test_create_figure_with_style_not_in_helpers_all(self) -> None:
        assert "create_figure_with_style" not in helpers.__all__

    def test_save_figure_not_on_dm(self) -> None:
        assert not hasattr(dm, "save_figure")

    def test_create_figure_with_style_not_on_dm(self) -> None:
        assert not hasattr(dm, "create_figure_with_style")

    def test_helpers_io_module_deleted(self) -> None:
        """``helpers.io`` must no longer be importable."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("dartwork_mpl.helpers.io")


class TestDunderAllComplete:
    """All public helpers appear in ``helpers.__all__``."""

    def test_remaining_names_in_all(self) -> None:
        for name in (
            "auto_select_colors",
            "check_figure_quality",
            "optimize_legend",
            "suggest_chart_type",
            "validate_data",
        ):
            assert name in helpers.__all__, f"{name} missing from __all__"

    def test_removed_names_not_in_all(self) -> None:
        """Round-3 removed names must not appear in helpers.__all__."""
        for name in ("add_value_labels", "format_axis_labels"):
            assert name not in helpers.__all__, (
                f"{name} should have been removed"
            )
