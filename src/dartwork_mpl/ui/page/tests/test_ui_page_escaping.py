"""The page escapes the configured title and every stored value it renders."""

from __future__ import annotations

from pathlib import Path

from dartwork_mpl.ui.page import get_html


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


class TestWidgetValueEscaping:
    """Color/range/number widgets must escape the stored value (`val`),
    which flows from user-saved config/preset JSON — otherwise a crafted
    value is stored XSS via attribute breakout.
    """

    def test_widget_values_are_escaped(self) -> None:
        from dartwork_mpl.ui.page import _scripts

        src = Path(_scripts.__file__).read_text(encoding="utf-8")
        assert 'value="${esc(val||"#000000")}"' in src  # color
        assert 'value="${esc(val)}"' in src  # range
        assert 'value="${esc(val||0)}"' in src  # number
        # No raw unescaped val interpolations remain in widget attributes.
        assert '"${val}"' not in src
        assert '"${val||0}"' not in src
        assert '"${val||"#000000"}"' not in src
