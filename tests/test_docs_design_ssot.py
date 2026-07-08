"""Regression tests for the docs design-system SSOT."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "docs" / "_static"


def read_static(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_typography_role_tokens_exist() -> None:
    css = read_static("dartwork-design.css")
    required = [
        "--dm-type-display-size",
        "--dm-type-display-line",
        "--dm-type-display-weight",
        "--dm-type-display-spacing",
        "--dm-type-heading-size",
        "--dm-type-heading-line",
        "--dm-type-body-size",
        "--dm-type-body-line",
        "--dm-type-label-size",
        "--dm-type-caption-size",
        "--dm-type-mono-size",
        "--dm-type-mono-line",
    ]
    for token in required:
        assert token in css


def test_layout_width_contract_lives_in_design_ssot() -> None:
    design_css = read_static("dartwork-design.css")
    custom_css = read_static("custom.css")

    required = {
        "--dm-layout-shell-max": "96rem",
        "--dm-layout-article-max": "72rem",
        "--dm-layout-prose-max": "72ch",
        "--dm-layout-gutter": "28px",
    }
    for token, value in required.items():
        assert f"{token}: {value};" in design_css

    assert "--sy-c-content-width: var(--dm-layout-article-max);" in design_css
    assert "article section > p" not in custom_css
    assert ".sy-container" not in custom_css
    assert ".sy-main div:has(> article.yue)" not in custom_css


def test_wide_component_contract_avoids_viewport_breakouts() -> None:
    css = read_static("dartwork-design.css")
    match = re.search(r"\.dm-wide\s*\{(?P<body>[^}]+)\}", css)
    assert match, ".dm-wide must be a documented article-local width primitive"

    body = match.group("body")
    assert "max-width: 100%;" in body
    assert "width: 100%;" in body
    for forbidden in ("100vw", "calc(50%", "margin-left: -", "margin-right: -"):
        assert forbidden not in body


def test_gallery_cards_use_stable_tokenized_media_slots() -> None:
    css = read_static("custom.css")

    assert "container-type: inline-size;" in css
    assert "height: clamp(8.5rem, 62cqw, 13rem);" in css
    assert "max-height: none;" in css
    assert "object-fit: contain;" in css
    assert "aspect-ratio: 16 / 10;" in css
    assert "--dm-gallery-thumb-bg" in css
    assert "min-height: calc(3 * 1.22em);" in css


def test_gallery_toolbar_keeps_component_surface() -> None:
    css = read_static("custom.css")
    flush_match = re.search(
        r"T1 flush.*?\*/(?P<body>.*?)html\.dark :is", css, flags=re.S
    )
    assert flush_match, "T1 flush block should remain auditable"
    assert ".dm-gallery-toolbar" not in flush_match.group("body")

    toolbar_match = re.search(
        r"\.dm-gallery-toolbar\s*\{(?P<body>[^}]+)\}", css
    )
    assert toolbar_match
    toolbar = toolbar_match.group("body")
    assert "background: var(--dm-bg-panel);" in toolbar
    assert "border: 1px solid var(--dm-border-faint);" in toolbar
    assert "box-shadow: var(--dm-shadow-1);" in toolbar


def test_gallery_download_code_keeps_inline_code_surface() -> None:
    css = read_static("custom.css")
    match = re.search(
        r"\.sphx-glr-download code(?:\.xref)?\s*\{(?P<body>[^}]+)\}", css
    )
    assert match, "Sphinx-gallery download code needs explicit styling"
    body = match.group("body")
    assert "background-color: var(--dm-i-code-surface)" in body
    assert "border-radius: var(--dm-radius-2)" in body
    assert css.rfind(".sphx-glr-download a code.xref") > css.rfind(
        "article a code"
    )


def test_categorical_page_styles_are_global_not_inline() -> None:
    page = (
        ROOT / "docs" / "color_system" / "categorical-palettes.md"
    ).read_text(encoding="utf-8")
    design_css = read_static("dartwork-design.css")

    assert "<style>" not in page
    assert "article:has(#dm-cat-exp)" not in page
    assert "article:has(#dm-cat-exp)" in design_css


def test_docs_layout_regression_script_covers_width_contract() -> None:
    script = (ROOT / "scripts" / "check_docs_layout.py").read_text(
        encoding="utf-8"
    )

    for page in (
        "examples_gallery/index.html",
        "color_system/categorical-palettes.html",
    ):
        assert page in script

    for width in ("390", "1024", "1440", "1680"):
        assert f'"width": {width}' in script

    for selector in (
        ".sphx-glr-thumbcontainer",
        ".dm-wide",
        ".sy-rside",
        ".sy-right-toc",
        ".sy-offcanvas",
    ):
        assert selector in script


def test_font_specimens_use_design_tokens_instead_of_private_palette() -> None:
    css = read_static("font-specimens.css")
    assert "var(--dm-bg-panel)" in css
    assert "var(--dm-border-faint)" in css
    assert "var(--dm-type-heading-size)" in css
    assert "var(--dm-type-body-size)" in css
    assert "var(--dm-type-label-size)" in css
    assert "var(--dm-type-mono-size)" in css
    assert not re.search(r"#[0-9a-fA-F]{3,8}", css)


def test_dynamic_ux_css_uses_dm_tokens_not_legacy_skin() -> None:
    css = read_static("dynamic_ux.css")
    forbidden = ["#14b8a6", "#0d9488", "#8b5cf6", "var(--sy-", "--sy-"]
    for value in forbidden:
        assert value not in css
    assert "--dm-ux-accent: var(--dm-accent-9);" in css
    assert "--dm-ux-bg: var(--dm-bg-page);" in css
    assert "--dm-ux-text: var(--dm-text-strong);" in css


def test_validation_svg_reads_css_variables_instead_of_literal_skin() -> None:
    js = read_static("dynamic_ux.js")
    assert "function cssVar(" in js
    assert "cssVar(w," in js
    assert "getComputedStyle" in js
    forbidden_literals = [
        '"#ffffff"',
        '"#fcfcfd"',
        '"#cdced6"',
        '"#12a594"',
        '"#60646c"',
        '"#1c2024"',
        '"#0d9b8a"',
    ]
    for literal in forbidden_literals:
        assert literal not in js


def test_review_harnesses_use_type_roles_and_no_legacy_accent() -> None:
    for name in ["dm-interactive-styleguide.html", "_overhaul_review.html"]:
        html = read_static(name)
        assert "var(--dm-type-" in html
        assert "#14b8a6" not in html
        assert "#0d9488" not in html
        assert "#8b5cf6" not in html
