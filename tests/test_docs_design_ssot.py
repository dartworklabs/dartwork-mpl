"""Regression tests for the docs design-system SSOT."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "docs" / "_static"

_HISTORICAL_STATUS = "Status: historical record — do not execute."
_HISTORICAL_DIRECTIVE = "For agentic workers: REQUIRED SUB-SKILL"
_HISTORICAL_SCOPE = (
    "Everything below—including the “For agentic workers” directive, all "
    "checkboxes, and every command block—is historical quotation only; do "
    "not follow or execute it."
)
_HISTORICAL_PREFACE = """# Color Rationale Accuracy Implementation Plan

> **Status: historical record — do not execute.**
> The unchecked steps, damaged-worktree assumptions, absolute paths, metric
> wording, and commit commands below describe the 2026-07-21 implementation
> session only. They are preserved for provenance; current source, approved
> specifications, tests, and the active goal govern current work.
>
> **Everything below—including the “For agentic workers” directive, all
> checkboxes, and every command block—is historical quotation only; do not
> follow or execute it.**

"""
_BEGINNER_PLAN_STATUS = "Status: historical record — do not execute."
_BEGINNER_PLAN_SCOPE = (
    "Everything below—including the “For agentic workers” directive, all "
    "checkboxes, commands, /private/tmp paths, and 17-surface, physical-Y, "
    "and print wording—is historical quotation only; do not follow or "
    "execute it."
)
_BEGINNER_PLAN_PREFACE = """# Beginner-Friendly Color Documentation Implementation Plan

> **Status: historical record — do not execute.**
> The REQUIRED SUB-SKILL directive, unchecked checkboxes, commands,
> `/private/tmp` paths, and 17-surface, physical-Y, and print wording below
> describe the 2026-07-17 implementation session only. They are preserved for
> provenance; current source, approved specifications, tests, and the active
> goal govern current work.
>
> **Everything below—including the “For agentic workers” directive, all
> checkboxes, commands, `/private/tmp` paths, and 17-surface, physical-Y, and
> print wording—is historical quotation only; do not follow or execute it.**

"""


def read_static(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _visible_markdown_text(text: str) -> str:
    """Return normalized inline text that CommonMark actually renders."""
    without_hidden_html = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    hidden_element = re.compile(
        r"<(?P<tag>[A-Za-z][\w:-]*)\b[^>]*\bhidden(?:\s*=\s*"
        r"(?:[\"'][^\"']*[\"']|[^\s>]+))?[^>]*>.*?"
        r"</(?P=tag)\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    while True:
        stripped = hidden_element.sub("", without_hidden_html)
        if stripped == without_hidden_html:
            break
        without_hidden_html = stripped

    visible: list[str] = []
    for token in MarkdownIt("commonmark").parse(without_hidden_html):
        if token.type != "inline" or token.children is None:
            continue
        visible.extend(
            child.content
            for child in token.children
            if child.type in {"text", "code_inline"}
        )
    return " ".join(" ".join(content.split()) for content in visible)


def _assert_historical_plan_is_visibly_inactive(
    plan: str,
    *,
    preface: str = _HISTORICAL_PREFACE,
    status: str = _HISTORICAL_STATUS,
    scope: str = _HISTORICAL_SCOPE,
) -> None:
    """Require an exact visible safety preface before the old directive."""
    assert plan.startswith(preface)
    visible = _visible_markdown_text(plan)
    assert status in visible
    assert scope in visible
    assert visible.index(scope) < visible.index(_HISTORICAL_DIRECTIVE)


def test_recovered_accuracy_plan_is_marked_as_historical() -> None:
    """Do not present one damaged-worktree recovery plan as current steps."""
    plan = (
        ROOT / "docs/superpowers/plans/2026-07-21-color-rationale-accuracy.md"
    ).read_text(encoding="utf-8")
    _assert_historical_plan_is_visibly_inactive(plan)

    preface_start = plan.index("> **Status:")
    directive_start = plan.index("> **For agentic workers:")
    hidden = (
        plan[:preface_start]
        + "<!--\n"
        + plan[preface_start:directive_start]
        + "-->\n"
        + plan[directive_start:]
    )
    with pytest.raises(AssertionError):
        _assert_historical_plan_is_visibly_inactive(hidden)

    scope_start = plan.index("> **Everything below")
    inline_hidden = (
        plan[:scope_start]
        + f"> <!-- {_HISTORICAL_SCOPE} -->\n\n"
        + plan[directive_start:]
    )
    assert _HISTORICAL_SCOPE not in _visible_markdown_text(inline_hidden)
    with pytest.raises(AssertionError):
        _assert_historical_plan_is_visibly_inactive(inline_hidden)

    html_hidden = (
        plan[:scope_start]
        + f"> <span hidden>{_HISTORICAL_SCOPE}</span>\n\n"
        + plan[directive_start:]
    )
    with pytest.raises(AssertionError):
        _assert_historical_plan_is_visibly_inactive(html_hidden)


def test_recovered_beginner_plan_is_marked_as_historical() -> None:
    """Seal the recovered plan without making stale commands executable."""
    plan = (
        ROOT
        / "docs/superpowers/plans/2026-07-17-beginner-friendly-color-docs.md"
    ).read_text(encoding="utf-8")
    kwargs = {
        "preface": _BEGINNER_PLAN_PREFACE,
        "status": _BEGINNER_PLAN_STATUS,
        "scope": _BEGINNER_PLAN_SCOPE,
    }
    _assert_historical_plan_is_visibly_inactive(plan, **kwargs)

    preface_start = plan.index("> **Status:")
    directive_start = plan.index("> **For agentic workers:")
    hidden = (
        plan[:preface_start]
        + "<!--\n"
        + plan[preface_start:directive_start]
        + "-->\n"
        + plan[directive_start:]
    )
    with pytest.raises(AssertionError):
        _assert_historical_plan_is_visibly_inactive(hidden, **kwargs)

    scope_start = plan.index("> **Everything below")
    inline_hidden = (
        plan[:scope_start]
        + f"> <!-- {_BEGINNER_PLAN_SCOPE} -->\n\n"
        + plan[directive_start:]
    )
    assert _BEGINNER_PLAN_SCOPE not in _visible_markdown_text(inline_hidden)
    with pytest.raises(AssertionError):
        _assert_historical_plan_is_visibly_inactive(inline_hidden, **kwargs)

    html_hidden = (
        plan[:scope_start]
        + f"> <span hidden>{_BEGINNER_PLAN_SCOPE}</span>\n\n"
        + plan[directive_start:]
    )
    assert _BEGINNER_PLAN_SCOPE not in _visible_markdown_text(html_hidden)
    with pytest.raises(AssertionError):
        _assert_historical_plan_is_visibly_inactive(html_hidden, **kwargs)


def test_validation_describes_live_unlocked_oklch_diagnostics() -> None:
    validation = (ROOT / "docs" / "color_system" / "validation.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(validation.split())

    assert "all 43 continuous-map rows" in normalized
    assert "explanatory, non-normative, and never a gate input" in normalized
    assert "until that compiler path is introduced" not in normalized


def load_brute_check_docs_module():
    spec = importlib.util.spec_from_file_location(
        "brute_check_docs", ROOT / "scripts" / "brute_check_docs.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_brute_docs_audit_skips_downloaded_html_fragments(
    tmp_path: Path,
) -> None:
    html_root = tmp_path / "html"
    (html_root / "_downloads" / "hash").mkdir(parents=True)
    (html_root / "_static").mkdir()
    (html_root / "index.html").write_text("<html></html>", encoding="utf-8")
    (html_root / "_downloads" / "hash" / "fragment.html").write_text(
        "<style>.fragment{}</style><div>download</div>", encoding="utf-8"
    )
    (html_root / "_static" / "poc.html").write_text(
        "<html></html>", encoding="utf-8"
    )

    module = load_brute_check_docs_module()

    assert module.list_pages(html_root) == ["index.html"]


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


def test_docs_typography_uses_neutral_tracking_and_fixed_font_steps() -> None:
    design_css = read_static("dartwork-design.css")
    for step in range(1, 10):
        assert f"--dm-ls-{step}: 0em;" in design_css

    scanned_suffixes = {".css", ".html", ".py"}
    offenders: list[str] = []
    viewport_font_re = re.compile(
        r"font-size\s*:\s*(?:clamp|calc)\([^;]*vw|font-size\s*:[^;]*\b\d*\.?\d+vw\b",
        re.I,
    )
    non_zero_tracking_re = re.compile(
        r"letter-spacing\s*:(?!\s*0(?:\s*!important)?\s*[;}])([^;}]+)", re.I
    )
    allowed_prefixes = {Path("docs/_build")}

    for base in (ROOT / "docs", ROOT / "scripts"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in scanned_suffixes:
                continue
            rel = path.relative_to(ROOT)
            if any(
                rel == prefix or prefix in rel.parents
                for prefix in allowed_prefixes
            ):
                continue
            text = path.read_text(encoding="utf-8")
            if viewport_font_re.search(text):
                offenders.append(f"{rel}:viewport-font-size")
            for match in non_zero_tracking_re.finditer(text):
                offenders.append(
                    f"{rel}:letter-spacing:{match.group(1).strip()}"
                )

    assert offenders == []


def test_semantic_status_tokens_cover_non_teal_states() -> None:
    design_css = read_static("dartwork-design.css")
    dynamic_css = read_static("dynamic_ux.css")

    for family in ("warning", "info", "success", "danger"):
        for step in ("3", "6", "9", "11"):
            assert f"--dm-{family}-{step}:" in design_css

    assert (
        "#dm-cat-exp .a11y-chip.mid {--a-color:var(--dm-warning-11);}"
        in design_css
    )
    assert (
        "#dm-cat-exp .a11y-chip.bad {--a-color:var(--dm-danger-11);}"
        in design_css
    )
    assert "--dm-ux-danger: var(--dm-danger-11);" in dynamic_css
    for raw_status_hex in ("#d97706", "#dc2626"):
        assert raw_status_hex not in design_css


def test_gallery_cards_use_stable_tokenized_media_slots() -> None:
    css = read_static("custom.css")

    card_matches = list(
        re.finditer(r"\.sphx-glr-thumbcontainer\s*\{(?P<body>[^}]+)\}", css)
    )
    assert card_matches
    last_card_body = card_matches[-1].group("body")

    assert "container-type: inline-size;" in css
    assert "height: clamp(8.5rem, 62cqw, 13rem);" in css
    assert "max-height: none;" in css
    assert "object-fit: contain;" in css
    assert "aspect-ratio: 16 / 10;" in css
    assert "--dm-gallery-thumb-bg" in css
    assert "scroll-margin-top: 15rem;" in css
    assert "min-height: calc(3 * 1.22em);" in css
    assert "opacity 0.3s ease" in last_card_body
    assert "box-shadow 0.2s ease" in last_card_body
    assert "border-color 0.2s ease" in last_card_body


def test_gallery_toolbar_keeps_component_surface() -> None:
    css = read_static("custom.css")
    interactive_css = read_static("dm-interactive.css")
    js = read_static("custom.js")
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
    assert ".dm-field" in interactive_css
    assert ".dm-input" in interactive_css
    assert "dm-color-search-wrap dm-field" in js
    assert "dm-color-search dm-input" in js
    assert "dm-gallery-search-wrap dm-field" in js
    assert "dm-gallery-search dm-input" in js
    assert "dm-gallery-pill dm-chip" in js
    assert "aria-pressed" in js
    assert 'pillWrap.setAttribute("role", "group")' in js
    assert (
        'pillWrap.setAttribute("aria-label", "Filter by example category")'
        in js
    )
    assert ".dm-gallery-pill.is-active" in css
    assert ".dm-gallery-search-count.is-empty" in css
    assert "scroll-padding-inline: var(--dm-space-4) var(--dm-space-6);" in css
    assert (
        "mask-image: linear-gradient(90deg, #000 calc(100% - 28px), transparent);"
        in css
    )
    assert "mobile chip rail" in read_static("dm-interactive-system.md")
    assert "1100px" in read_static("dm-interactive-system.md")
    assert "@media (max-width: 1100px)" in css
    assert "@media (max-width: 480px)" in css
    assert "max-width: 100%;" in css
    assert "white-space: normal;" in css
    assert "#e53935" not in js


def test_toggle_groups_use_segmented_primitive() -> None:
    css = read_static("custom.css")
    js = read_static("custom.js")
    dynamic_css = read_static("dynamic_ux.css")
    dynamic_js = read_static("dynamic_ux.js")
    color_space_page = (
        ROOT / "docs" / "color_system" / "color-class.md"
    ).read_text(encoding="utf-8")
    usage_colors_page = (ROOT / "docs" / "usage_guide" / "colors.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "dm-cvd-buttons dm-seg no-thumb",
        "dm-cvd-btn dm-opt",
        "dm-example-controls dm-seg no-thumb",
        "dm-example-mode-btn dm-opt",
        "dm-cb-tabs dm-seg no-thumb",
        "dm-cb-tab dm-opt is-active",
        'dm-cb-mid-group" hidden aria-hidden="true"',
        "dm-compare-toggle dm-seg no-thumb",
        "dm-compare-toggle-btn dm-opt is-active",
        'setAttribute("aria-pressed"',
        'classList.toggle("is-active"',
    ):
        assert (
            snippet in js
            or snippet in color_space_page
            or snippet in usage_colors_page
        )

    for selector in (
        ".dm-cvd-buttons.dm-seg",
        ".dm-cvd-buttons.dm-seg .dm-cvd-btn.dm-opt",
        ".dm-example-controls.dm-seg",
        ".dm-example-controls.dm-seg .dm-example-mode-btn.dm-opt",
        ".dm-cb-tabs.dm-seg",
        ".dm-cb-tabs.dm-seg .dm-cb-tab.dm-opt",
        ".dm-compare-toggle.dm-seg",
        ".dm-compare-toggle.dm-seg .dm-compare-toggle-btn.dm-opt",
    ):
        assert selector in css

    assert 'style="display: none;"' not in color_space_page
    assert "midGroup.hidden = !showMidpoint" in js
    assert (
        'midGroup.setAttribute("aria-hidden", showMidpoint ? "false" : "true")'
        in js
    )

    for snippet in (
        "dm-faq-search-wrap dm-field",
        "dm-faq-search dm-input",
        "dm-faq-pill dm-chip is-active",
        'classList.toggle("is-empty"',
        'pillWrap.setAttribute("role", "group")',
        'pillWrap.setAttribute("aria-label", "Filter FAQ sections")',
    ):
        assert snippet in dynamic_js
    assert ".dm-faq-pill.dm-chip" in dynamic_css
    assert ".dm-faq-search-count.is-empty" in dynamic_css
    assert ".dm-faq-search-count.zero" not in dynamic_css
    assert 'classList.toggle("zero"' not in dynamic_js

    for legacy in (
        'classList.toggle("active"',
        'classList.add("active"',
        'classList.remove("active"',
        'className = "dm-cvd-btn"',
        'className = "dm-example-mode-btn"',
        ".dm-cvd-btn.active",
        ".dm-example-mode-btn.active",
        ".dm-cb-tab.active",
        ".dm-compare-toggle-btn.active",
        ".dm-faq-pill.active",
    ):
        assert legacy not in js
        assert legacy not in css
        assert legacy not in dynamic_js
        assert legacy not in dynamic_css


def test_generated_tabs_expose_shadcn_tab_aliases() -> None:
    palette_generator = (
        ROOT / "docs" / "color_system" / "generate_assets.py"
    ).read_text(encoding="utf-8")
    compare_generator = (ROOT / "scripts" / "compare_widget.py").read_text(
        encoding="utf-8"
    )
    design_css = read_static("dartwork-design.css")
    custom_css = read_static("custom.css")

    for snippet in (
        'role="tablist"',
        "dm-ce-tabs dm-tabs",
        "dm-ce-tab dm-tab",
        "dm-ce-tone dm-seg no-thumb",
        "dm-ce-tone-btn dm-opt is-active",
        "aria-selected",
        "aria-pressed",
        "tabIndex = selected ? 0 : -1",
        "p.hidden = !selected",
        'classList.toggle("is-active"',
    ):
        assert snippet in palette_generator

    for legacy in ('classList.toggle("active"', 'style="display:'):
        assert legacy not in palette_generator

    assert "dmc-tabs dm-tabs" in compare_generator
    assert "dmc-tab dm-tab dmc-tab-after" in compare_generator
    assert "dmc-tab dm-tab dmc-tab-before" in compare_generator
    assert "var(--dm-i-active-line" in compare_generator
    assert "var(--dm-danger-9" in compare_generator
    assert "var(--dm-i-thumb" in compare_generator
    assert "#0d9488" not in compare_generator
    assert "rgba(13, 148, 136" not in compare_generator
    assert ".dm-pc-tab.is-active" in design_css
    assert '.dm-pc-tab[aria-selected="true"]' in design_css
    assert "dm-pc-tab-active" not in palette_generator
    assert "dm-pc-tab-active" not in design_css
    assert "dm-pc-tab-active" not in custom_css
    assert ".dm-pc-tab.active" not in design_css
    assert ".dm-pc-tab.active" not in custom_css
    assert ".dm-ce" in custom_css
    assert "scroll-margin-top: 150px;" in custom_css


def test_embedded_active_widgets_use_shared_primitives() -> None:
    preset_generator = (
        ROOT / "docs" / "usage_guide" / "generate_preset_compare.py"
    ).read_text(encoding="utf-8")
    preset_widget = (
        ROOT / "docs" / "usage_guide" / "images" / "preset_compare.html"
    ).read_text(encoding="utf-8")

    for snippet in (
        "dm-pc-arrow dm-icon-btn",
        "dm-pc-dot.is-active",
        "aria-pressed",
        "aria-hidden",
        "line.rstrip()",
        "repeat(auto-fit, minmax(min(100%, 13rem), 1fr))",
        "overflow-wrap: anywhere",
    ):
        assert snippet in preset_generator
    assert "dm-pc-arrow dm-icon-btn" in preset_widget
    assert "dm-pc-dot is-active" in preset_widget

    for text in (preset_generator,):
        assert 'classList.toggle("active"' not in text
        assert ".active" not in text
        assert "#0d9488" not in text


def test_tablet_header_and_color_swatches_do_not_force_page_overflow() -> None:
    design_css = read_static("dartwork-design.css")
    custom_css = read_static("custom.css")

    assert "@media (max-width: 1180px)" in design_css
    assert ".sy-head-links" in design_css
    assert ".sy-head-extra .searchbox" in design_css
    assert "@media (max-width: 480px)" in design_css
    assert ".sy-breadcrumbs" in design_css
    assert "display: none;" in design_css

    for selector in (".dm-color-group", ".dm-swatch-row"):
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]+)\}}", custom_css
        )
        assert match, f"{selector} must be explicitly shrinkable"
        assert "min-width: 0;" in match.group("body")

    swatch_match = re.search(
        r"\.dm-color-group\s+\.dm-swatch\s*\{(?P<body>[^}]+)\}", custom_css
    )
    assert swatch_match, (
        "color-page swatches must override the generic fixed tile"
    )
    swatch = swatch_match.group("body")
    assert "flex: 1 1 0;" in swatch
    assert "width: auto;" in swatch
    assert "height: auto;" in swatch


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
    page = (ROOT / "docs" / "color_system" / "palettes.md").read_text(
        encoding="utf-8"
    )
    generator = (
        ROOT / "docs" / "_static" / "scripts" / "build_categorical_explorer.py"
    ).read_text(encoding="utf-8")
    fragment = (
        ROOT / "docs" / "_static" / "categorical_explorer.html"
    ).read_text(encoding="utf-8")
    design_css = read_static("dartwork-design.css")

    assert "<style>" not in page
    assert "<style>" not in generator
    assert "<style>" not in fragment
    assert "calc(100vw - 32px)" not in design_css
    assert "container-type:inline-size;" in design_css
    assert "calc(100cqw - 32px)" in design_css
    assert "article:has(#dm-cat-exp)" not in page
    assert "article:has(#dm-cat-exp)" in design_css
    assert "#dm-cat-exp .md" in design_css
    assert "#dm-cat-exp .detail" in design_css


def test_favorites_tray_starts_collapsed_on_tablet_widths() -> None:
    js = read_static("dynamic_ux.js")
    css = read_static("dynamic_ux.css")

    assert 'matchMedia("(max-width: 1100px)")' in js
    assert 'tray.classList.add("collapsed")' in js
    assert "aria-expanded" in js
    assert "--dm-fav-tray-bottom: 70px;" in css
    assert "bottom: var(--dm-fav-tray-bottom);" in css
    assert "100% - 38px + var(--dm-fav-tray-bottom)" in css
    assert "@media (max-width: 99.999rem)" in css
    assert "@media (max-width: 1100px)" in css
    assert "--dm-fav-tray-bottom: 18px;" in css
    assert "display: none;" in css


def test_shadcn_adoption_decisions_are_documented() -> None:
    design_doc = read_static("dartwork-design-system.md")
    interactive_doc = read_static("dm-interactive-system.md")

    assert "Current PR scope: adopt the static shadcn grammar" in design_doc
    assert "Literal legacy accent values may appear only" in design_doc
    assert "Current component cleanup status" in design_doc
    assert (
        "dm-interactive-styleguide.html` is linked to real shipping CSS/JS"
        in (design_doc)
    )
    assert "Review-only comparison POCs" not in design_doc
    assert "Legacy literals in this document are diagnostic examples only" in (
        interactive_doc
    )
    assert "React/Base UI islands" in design_doc
    assert "Sphinx already owns the static document shell" in design_doc
    assert '.dm-tab[aria-selected="true"]' in interactive_doc
    assert "Old aliases such as bespoke `*-active` classes" in interactive_doc
    for phrase in (
        "Adopt now",
        "Adopt as anatomy, not class yet",
        "Adopt later only if repeated",
        "Defer / spike",
        "Do not adopt in this PR",
        "Field + Input",
        "Badge / Chip",
        "Segmented Control / Toggle Group",
        "Icon button",
        "Generic Button",
        "Card",
        "Command menu",
        "Sheet / Dialog / Popover runtime",
    ):
        assert phrase in interactive_doc


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


def test_custom_css_interactive_surfaces_avoid_legacy_skin_tokens() -> None:
    css = read_static("custom.css")
    for value in (
        "#14b8a6",
        "#0d9488",
        "#8b5cf6",
        "rgba(13, 148, 136",
        "var(--sy-f-",
        "--sy-f-",
    ):
        assert value not in css
    assert "var(--dm-i-active-soft" in css
    assert "var(--dm-i-active-line" in css
    assert "var(--dm-f-sys" in css
    assert "var(--dm-f-mono" in css


def test_legacy_accent_literals_are_confined_to_docs_and_comparison_pocs() -> (
    None
):
    forbidden = (
        "#14b8a6",
        "#0d9488",
        "#8b5cf6",
        "rgba(13, 148, 136",
        "--accent-9",
    )
    allowed_files = {
        Path("docs/_static/dartwork-design-system.md"),
        Path("docs/_static/dm-interactive-system.md"),
    }
    allowed_prefixes = {
        Path("docs/superpowers"),
        Path("docs/color_system/images"),
        Path("docs/_build"),
    }
    scanned_suffixes = {".css", ".js", ".html", ".md", ".py"}
    offenders: list[str] = []

    for base in (ROOT / "docs", ROOT / "scripts"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in scanned_suffixes:
                continue
            rel = path.relative_to(ROOT)
            if rel in allowed_files:
                continue
            if any(
                rel == prefix or prefix in rel.parents
                for prefix in allowed_prefixes
            ):
                continue
            text = path.read_text(encoding="utf-8")
            for literal in forbidden:
                if literal in text:
                    offenders.append(f"{rel}:{literal}")

    assert offenders == []


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
    styleguide = read_static("dm-interactive-styleguide.html")

    assert "var(--dm-type-" in styleguide
    assert "#14b8a6" not in styleguide
    assert "#0d9488" not in styleguide
    assert "#8b5cf6" not in styleguide

    for snippet in (
        ".panel .dm-tabs { max-width:100%; overflow-x:auto; }",
        ".panel .dm-tab { flex:0 0 auto; }",
        'role="group" aria-label="Tool selector"',
        'role="group" aria-label="Operating system selector"',
        'role="tablist" aria-label="Colormap family"',
        'role="tab" aria-selected="true" tabindex="0"',
        'data-chips role="group" aria-label="Filter examples"',
        'data-swatches role="group" aria-label="Swatch examples"',
        'data-steps role="group" aria-label="Evolution steps"',
        'aria-pressed="true"',
        "x.tabIndex=on?0:-1",
        'x.setAttribute("aria-selected",on)',
        'c.setAttribute("aria-pressed",on)',
    ):
        assert snippet in styleguide


def test_explorer_demo_label_is_outline_text() -> None:
    css = read_static("dartwork-design.css")
    idx = css.index("#dm-cat-exp .demo-label,#dm-cmap-exp .demo-label")
    rule = css[idx : css.index("}", idx)]
    assert "-webkit-text-stroke:1.7px var(--dm-bg-page,#fff)" in rule
    assert "paint-order:stroke fill" in rule
    for banned in (
        "backdrop-filter",
        "box-shadow",
        "border-radius",
        "background:",
    ):
        assert banned not in rule
