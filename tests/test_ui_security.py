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


class TestHostAllowlist:
    """DNS-rebinding defense: state-changing requests must carry an
    allowed Host, so a rebound ``evil.com -> 127.0.0.1`` page (which
    passes the same-origin check with matching Origin/Host) is rejected.
    """

    def test_loopback_hosts_allowed(self) -> None:
        from dartwork_mpl.ui.ui import _allowed_hostnames, _host_allowed

        allowed = _allowed_hostnames("127.0.0.1")
        assert _host_allowed("127.0.0.1:8501", allowed) is True
        assert _host_allowed("localhost:8501", allowed) is True
        assert _host_allowed("[::1]:8501", allowed) is True

    def test_rebound_attacker_host_blocked(self) -> None:
        from dartwork_mpl.ui.ui import _allowed_hostnames, _host_allowed

        allowed = _allowed_hostnames("127.0.0.1")
        assert _host_allowed("evil.com:8501", allowed) is False
        assert _host_allowed("evil.com", allowed) is False

    def test_missing_host_allowed(self) -> None:
        # Non-browser clients (curl) omit Host and aren't a rebinding vector.
        from dartwork_mpl.ui.ui import _allowed_hostnames, _host_allowed

        assert _host_allowed(None, _allowed_hostnames("127.0.0.1")) is True

    def test_public_bind_permits_any_host(self) -> None:
        # 0.0.0.0/:: can't pin valid external hostnames -> no allowlist.
        from dartwork_mpl.ui.ui import _allowed_hostnames, _host_allowed

        assert _allowed_hostnames("0.0.0.0") is None
        assert _host_allowed("anything.example", None) is True


class TestFigureNotLeaked:
    """render/export must not leak matplotlib figures when rendering fails."""

    def test_figure_closed_on_savefig_error(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from dartwork_mpl.ui.ui import _figure_to_bytes

        before = set(plt.get_fignums())

        def figure_fn(_model: object) -> plt.Figure:
            return plt.figure()

        # matplotlib raises ValueError for an unsupported savefig format.
        with pytest.raises(ValueError):
            _figure_to_bytes(figure_fn, None, "not-a-real-format")

        assert set(plt.get_fignums()) == before

    def test_figure_closed_on_success(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from dartwork_mpl.ui.ui import _figure_to_bytes

        before = set(plt.get_fignums())

        def figure_fn(_model: object) -> plt.Figure:
            fig = plt.figure()
            fig.add_subplot().plot([0, 1], [0, 1])
            return fig

        data = _figure_to_bytes(figure_fn, None, "png")
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert set(plt.get_fignums()) == before


class TestWidgetValueEscaping:
    """Color/range/number widgets must escape the stored value (`val`),
    which flows from user-saved config/preset JSON — otherwise a crafted
    value is stored XSS via attribute breakout.
    """

    def test_widget_values_are_escaped(self) -> None:
        from dartwork_mpl.ui import _scripts

        src = Path(_scripts.__file__).read_text(encoding="utf-8")
        assert 'value="${esc(val||"#000000")}"' in src  # color
        assert 'value="${esc(val)}"' in src  # range
        assert 'value="${esc(val||0)}"' in src  # number
        # No raw unescaped val interpolations remain in widget attributes.
        assert '"${val}"' not in src
        assert '"${val||0}"' not in src
        assert '"${val||"#000000"}"' not in src
