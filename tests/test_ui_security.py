"""UI security hardening (#228).

Covers the local Host/source policy, typed output-name language, figure cleanup
and HTML escaping in the rendered template.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# The viewer lives behind the optional ``ui`` extra (fastapi/uvicorn).
pytest.importorskip("fastapi")

from dartwork_mpl.ui._boundary import (
    AccessDenied,
    InputFailure,
    LocalAccess,
    StartupRejected,
    authorize_request,
    normalize_bind,
    parse_output,
)
from dartwork_mpl.ui._template import get_html


class TestLocalRequestPolicy:
    """The single policy denies foreign/missing authorities and checks each source."""

    @pytest.mark.parametrize("source", ["origin", "referer"])
    def test_foreign_source_denied(self, source: str) -> None:
        """Each browser source is independently checked before an effect."""
        result = authorize_request(
            "POST",
            "/api/render",
            [
                (b"host", b"localhost:8501"),
                (source.encode(), b"http://evil.example"),
            ],
            "127.0.0.1",
        )
        assert isinstance(result, AccessDenied)

    def test_native_and_same_authority_allowed(self) -> None:
        """Native clients omit sources; local browser clients use the request authority."""
        for source in (
            [],
            [
                (b"origin", b"http://localhost:9999"),
                (b"referer", b"http://localhost:9999/page"),
            ],
        ):
            result = authorize_request(
                "POST",
                "/api/render",
                [(b"host", b"localhost:9999"), *source],
                "127.0.0.1",
            )
            assert isinstance(result, LocalAccess)

    @pytest.mark.parametrize(
        "host", [None, b"evil.example", b"localhost:invalid", b"user@localhost"]
    )
    def test_bad_host_denied(self, host: bytes | None) -> None:
        """All reads and effects require one complete valid local Host authority."""
        headers = [] if host is None else [(b"host", host)]
        assert isinstance(
            authorize_request("GET", "/api/health", headers, "127.0.0.1"),
            AccessDenied,
        )

    @pytest.mark.parametrize(
        "host", ["0.0.0.0", "::", "192.0.2.1", "example.test"]
    )
    def test_public_bind_rejected(self, host: str) -> None:
        """Unapproved bind addresses cannot issue a local-effect grant."""
        assert isinstance(normalize_bind(host), StartupRejected)


class TestOutputLanguage:
    """Only typed safe relative output paths reach the confined filesystem owner."""

    @pytest.mark.parametrize("name", ["figure.png", "sub/figure.png"])
    def test_safe_relative_name_allowed(self, name: str) -> None:
        """Relative files and safe subdirectories retain their accepted spelling."""
        result = parse_output(name)
        assert not isinstance(result, InputFailure)
        assert result.filename == name

    @pytest.mark.parametrize("name", ["../../etc/passwd", "/etc/passwd", "   "])
    def test_unsafe_name_rejected(self, name: str) -> None:
        """Absolute, parent traversal and blank names never become output capabilities."""
        assert isinstance(parse_output(name), InputFailure)


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
