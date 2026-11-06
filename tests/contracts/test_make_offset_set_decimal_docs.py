"""make_offset and set_decimal are plain public helpers, described as they act.

D5: no "legacy / kept for compatibility" label, docstrings state the real
behaviour (point offsets through the Figure DPI transform; a dynamic
FuncFormatter that keeps the locator and view limits).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import dartwork_mpl as dm

_ROOT = Path(dm.__file__).parent


def test_root_does_not_label_helpers_legacy() -> None:
    source = (_ROOT / "__init__.py").read_text(encoding="utf-8")
    assert "legacy helpers" not in source
    assert "kept for compatibility" not in source


def test_make_offset_docstring_states_dpi_transform() -> None:
    doc = inspect.getdoc(dm.make_offset) or ""
    assert "point" in doc.lower()
    assert "dpi_scale_trans" in doc


def test_set_decimal_docstring_states_dynamic_formatter() -> None:
    doc = inspect.getdoc(dm.set_decimal) or ""
    assert "FuncFormatter" in doc
    assert "locator" in doc
    assert "fixed tick" not in doc.lower()
