"""UI hardening (#236, domain F).

Covers the export robustness fix: ``_validate_export_format`` → 400 (not
an internal 500) for an unsupported ``fmt``. (The atomic preset-write tests
live with the legacy helpers in ui/tests/test_ui_legacy_presets.py.)
"""

from __future__ import annotations

import pytest

# The viewer lives behind the optional ``ui`` extra (fastapi/uvicorn).
pytest.importorskip("fastapi")

from fastapi import HTTPException

from dartwork_mpl.ui.render._figure import (
    _SUPPORTED_EXPORT_FORMATS,
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
