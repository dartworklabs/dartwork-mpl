"""UI hardening (#236, domain F).

Covers the export/build/preset-write robustness fixes:

- ``_validate_export_format`` → 400 (not an internal 500) for an
  unsupported ``fmt``,
- ``_build_model_checked`` → 422 for invalid params on the
  export/script/save-server endpoints (parity with /api/render),
- ``_atomic_write_text`` writes presets/config atomically.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# The viewer lives behind the optional ``ui`` extra (fastapi/uvicorn).
pytest.importorskip("fastapi")

from fastapi import HTTPException
from pydantic import BaseModel

from dartwork_mpl.ui._config import _atomic_write_text
from dartwork_mpl.ui.ui import (
    _SUPPORTED_EXPORT_FORMATS,
    _build_model_checked,
    _validate_export_format,
)


class TestValidateExportFormat:
    @pytest.mark.parametrize("fmt", ["png", "svg", "pdf"])
    def test_supported_formats_pass(self, fmt: str) -> None:
        # Should not raise.
        _validate_export_format(fmt)

    def test_supported_set_is_matplotlib_filetypes(self) -> None:
        assert {"png", "svg", "pdf"} <= _SUPPORTED_EXPORT_FORMATS

    @pytest.mark.parametrize("fmt", ["exe", "bogus", "../etc", ""])
    def test_unsupported_format_is_400(self, fmt: str) -> None:
        with pytest.raises(HTTPException) as ei:
            _validate_export_format(fmt)
        assert ei.value.status_code == 400

    def test_case_insensitive(self) -> None:
        # Upper-case extensions normalize before the membership test.
        _validate_export_format("PNG")


class _Model(BaseModel):
    x: int


class TestBuildModelChecked:
    def test_valid_params_build(self) -> None:
        model = _build_model_checked({"x": "5"}, _Model, [])
        assert model.x == 5

    def test_invalid_params_are_422_not_500(self) -> None:
        with pytest.raises(HTTPException) as ei:
            _build_model_checked({"x": "not-an-int"}, _Model, [])
        assert ei.value.status_code == 422


class TestAtomicWriteText:
    def test_writes_content(self, tmp_path: Path) -> None:
        target = tmp_path / "presets.json"
        _atomic_write_text(target, '[{"a": 1}]\n')
        assert target.read_text(encoding="utf-8") == '[{"a": 1}]\n'

    def test_overwrite_leaves_no_temp_files(self, tmp_path: Path) -> None:
        target = tmp_path / "presets.json"
        _atomic_write_text(target, "first")
        _atomic_write_text(target, "second")
        assert target.read_text(encoding="utf-8") == "second"
        # The temp file is renamed into place, never left behind.
        assert list(tmp_path.iterdir()) == [target]

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "dir" / "presets.json"
        _atomic_write_text(target, "ok")
        assert target.read_text(encoding="utf-8") == "ok"
