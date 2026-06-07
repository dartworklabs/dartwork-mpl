"""UI security hardening (#228).

Covers the three defenses added to the interactive viewer:

- same-origin (CSRF) decision for state-changing requests
  (``_is_cross_origin``),
- path-traversal guard for client-supplied save filenames
  (``_safe_output_path``),
- HTML escaping in the rendered template (server-side ``title`` +
  client-side ``esc()`` wrapping of dynamic interpolations).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# The viewer lives behind the optional ``ui`` extra (fastapi/uvicorn).
pytest.importorskip("fastapi")

from dartwork_mpl.ui._template import get_html
from dartwork_mpl.ui.ui import _is_cross_origin, _safe_output_path

_HOST = "127.0.0.1:8501"


class TestCrossOriginGuard:
    def test_cross_site_post_is_blocked(self) -> None:
        assert _is_cross_origin("POST", "http://evil.com", None, _HOST) is True

    def test_same_origin_post_allowed(self) -> None:
        assert _is_cross_origin("POST", f"http://{_HOST}", None, _HOST) is False

    def test_referer_fallback_blocks_cross_site(self) -> None:
        assert (
            _is_cross_origin("POST", None, "http://evil.com/x", _HOST) is True
        )

    def test_no_origin_or_referer_allowed(self) -> None:
        # Non-browser client (curl) — not a CSRF vector.
        assert _is_cross_origin("POST", None, None, _HOST) is False

    def test_get_is_never_blocked(self) -> None:
        assert _is_cross_origin("GET", "http://evil.com", None, _HOST) is False

    def test_delete_cross_site_blocked(self) -> None:
        assert (
            _is_cross_origin("DELETE", "http://evil.com", None, _HOST) is True
        )


class TestSafeOutputPath:
    def test_plain_name_within_base(self, tmp_path: Path) -> None:
        assert (
            _safe_output_path(tmp_path, "figure.png")
            == (tmp_path / "figure.png").resolve()
        )

    def test_subdir_within_base_allowed(self, tmp_path: Path) -> None:
        assert (
            _safe_output_path(tmp_path, "sub/figure.png")
            == (tmp_path / "sub" / "figure.png").resolve()
        )

    def test_parent_traversal_rejected(self, tmp_path: Path) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _safe_output_path(tmp_path, "../../etc/passwd")
        assert exc.value.status_code == 400

    def test_absolute_path_rejected(self, tmp_path: Path) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _safe_output_path(tmp_path, "/etc/passwd")

    def test_blank_filename_rejected(self, tmp_path: Path) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _safe_output_path(tmp_path, "   ")


class TestTemplateEscaping:
    def test_title_is_escaped(self) -> None:
        doc = get_html(title="<script>alert(1)</script>")
        assert "<script>alert(1)</script>" not in doc
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in doc

    def test_esc_helper_present(self) -> None:
        assert "function esc(" in get_html()

    def test_dynamic_interpolations_wrapped(self) -> None:
        doc = get_html()
        assert "esc(d.label)" in doc
        assert "esc(p.label)" in doc
        assert "esc(groupName)" in doc
        assert "esc(c)" in doc
