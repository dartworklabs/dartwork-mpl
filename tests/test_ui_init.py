"""Tests for ui/__init__.py lazy-loading behaviour."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestUiInit:
    """Tests for the ui package __init__ lazy imports."""

    def test_param_model_importable(self) -> None:
        """ParamModel is directly importable from dartwork_mpl.ui."""
        from dartwork_mpl.ui import ParamModel

        assert ParamModel is not None

    def test_import_does_not_eagerly_load_pydantic(self) -> None:
        """Importing ``dartwork_mpl.ui`` must not pull in pydantic/_param.

        The ``dartwork-mpl-ui`` scaffold imports this package on a base
        install (no ``ui`` extra); an eager ``from ._param import
        ParamModel`` would crash there with ImportError. Run in a fresh
        interpreter so an earlier test that already imported pydantic
        cannot mask a regression (xc-deps-03).
        """
        code = (
            "import sys\n"
            "import dartwork_mpl.ui as ui\n"
            "assert 'pydantic' not in sys.modules, 'pydantic eagerly imported'\n"
            "assert 'dartwork_mpl.ui._param' not in sys.modules, "
            "'_param eagerly imported'\n"
            "assert ui.ParamModel is not None\n"
            "assert 'pydantic' in sys.modules, 'pydantic not loaded on access'\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

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
