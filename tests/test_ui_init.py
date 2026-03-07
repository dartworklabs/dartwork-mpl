"""Tests for ui/__init__.py lazy-loading behaviour."""

from __future__ import annotations

import pytest


class TestUiInit:
    """Tests for the ui package __init__ lazy imports."""

    def test_param_model_importable(self) -> None:
        """ParamModel is directly importable from dartwork_mpl.ui."""
        from dartwork_mpl.ui import ParamModel

        assert ParamModel is not None

    def test_unknown_attr_raises(self) -> None:
        """Accessing a non-existent attribute raises AttributeError."""
        import dartwork_mpl.ui as ui_mod

        with pytest.raises(AttributeError, match="no attribute"):
            _ = ui_mod.nonexistent_thing

    def test_all_exports(self) -> None:
        """__all__ contains expected public names."""
        import dartwork_mpl.ui as ui_mod

        assert "ParamModel" in ui_mod.__all__
        assert "run" in ui_mod.__all__
