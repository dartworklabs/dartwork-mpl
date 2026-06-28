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
