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

    def test_add_value_labels_accessible(self) -> None:
        assert hasattr(helpers, "add_value_labels")

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

    def test_format_axis_labels_accessible(self) -> None:
        assert hasattr(helpers, "format_axis_labels")


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
            "add_value_labels",
            "auto_select_colors",
            "check_figure_quality",
            "format_axis_labels",
            "optimize_legend",
            "suggest_chart_type",
            "validate_data",
        ):
            assert name in helpers.__all__, f"{name} missing from __all__"
