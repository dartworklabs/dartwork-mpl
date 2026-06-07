"""Tests for the UI HTML template assembly (``_template`` + ``_styles`` +
``_scripts``).

``_template.py`` was a single 1.5k-line ``get_html`` f-string with the CSS
and client-side JS inlined — every literal brace doubled (``{{ }}``) to
survive f-string parsing ("escape hell"). The stylesheet and script now
live in sibling modules as *plain* strings (real CSS ``{ }`` / JS
``${...}`` template literals), and ``get_html`` assembles them. These
tests lock that contract: the page is still assembled from the two blocks,
the only interpolation point is the (escaped) ``title``, and the extracted
blocks are genuinely brace-unescaped.
"""

from __future__ import annotations

from dartwork_mpl.ui._scripts import JS_BLOCK
from dartwork_mpl.ui._styles import CSS_BLOCK
from dartwork_mpl.ui._template import get_html


class TestTemplateSplit:
    def test_blocks_are_nonempty_strings(self) -> None:
        assert isinstance(CSS_BLOCK, str) and CSS_BLOCK.strip()
        assert isinstance(JS_BLOCK, str) and JS_BLOCK.strip()

    def test_get_html_embeds_both_blocks_verbatim(self) -> None:
        html = get_html("My Figure")
        assert CSS_BLOCK in html
        assert JS_BLOCK in html
        # Each block sits inside its own tag.
        assert f"<style>{CSS_BLOCK}</style>" in html
        assert f"<script>{JS_BLOCK}</script>" in html

    def test_css_block_has_real_unescaped_braces(self) -> None:
        # Plain string, not an f-string fragment: literal braces are single.
        assert "{{" not in CSS_BLOCK
        assert "}}" not in CSS_BLOCK
        assert "{" in CSS_BLOCK and "}" in CSS_BLOCK

    def test_js_block_keeps_real_template_literals(self) -> None:
        # The f-string source wrote ``${{esc(d.label)}}``; the extracted
        # plain string carries the real JS template literal ``${esc(...)}``.
        assert "${esc(d.label)}" in JS_BLOCK
        assert "${{" not in JS_BLOCK

    def test_title_is_the_only_interpolation_and_is_escaped(self) -> None:
        html = get_html('<x>&"q')
        # Reflected-XSS guard: the raw title must not appear unescaped.
        assert '<x>&"q' not in html
        assert "&lt;x&gt;" in html
        assert "<title>&lt;x&gt;" in html
