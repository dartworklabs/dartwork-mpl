"""UI hardening (#236, domain F).

Covers the export robustness fix: ``parse_export_format`` refuses an
unsupported ``fmt`` with ``UnsupportedFormat`` (answered 400, not an internal
500). (The atomic preset-write tests live with the legacy helpers in
ui/tests/test_ui_legacy_presets.py.)
"""

from __future__ import annotations

import pytest

# The viewer lives behind the optional ``ui`` extra (fastapi/uvicorn).
pytest.importorskip("fastapi")

from dartwork_mpl.ui._refusals import refusal_response
from dartwork_mpl.ui.render._figure import (
    _SUPPORTED_EXPORT_FORMATS,
    ExportFormat,
    UnsupportedFormat,
    parse_export_format,
)


class TestValidateExportFormat:
    """Export format validation: matplotlib's formats pass, others are HTTP 400."""

    @pytest.mark.parametrize("fmt", ["png", "svg", "pdf"])
    def test_supported_formats_pass(self, fmt: str) -> None:
        assert parse_export_format(fmt) == ExportFormat(fmt)

    def test_supported_set_is_matplotlib_filetypes(self) -> None:
        assert {"png", "svg", "pdf"} <= _SUPPORTED_EXPORT_FORMATS

    @pytest.mark.parametrize("fmt", ["exe", "bogus", "../etc", ""])
    def test_unsupported_format_is_400(self, fmt: str) -> None:
        result = parse_export_format(fmt)
        assert isinstance(result, UnsupportedFormat)
        assert repr(fmt) in result.detail
        assert refusal_response(result).status_code == 400

    def test_case_insensitive(self) -> None:
        # Upper-case extensions normalize before the membership test.
        assert parse_export_format("PNG") == ExportFormat("png")

    @pytest.mark.parametrize("name", ["PNG", "bogus", ""])
    def test_export_format_rejects_unparsed_names(self, name: str) -> None:
        """Only lower-case supported names can be built, so no route sees another."""
        with pytest.raises(ValueError):
            ExportFormat(name)
