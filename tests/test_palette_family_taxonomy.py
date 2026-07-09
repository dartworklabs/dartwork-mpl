"""v5 categorical explorer ↔ color-SSOT parity (G13).

The interactive categorical explorer fragment is generated from the color SSOT
— ``_generated.CYCLES`` (cycles) + the qualitative rail subset of
``_curated.CURATED``. These guards keep the generated fragment and the builder's
intent lists pinned to that SSOT, and keep the removed v4 JS data file gone.
"""

from __future__ import annotations

import json
import re
import runpy
from pathlib import Path

from dartwork_mpl.colors import _curated, _generated

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "docs" / "_static" / "scripts"
_EXPLORER = _REPO / "docs" / "_static" / "categorical_explorer.html"
_DESIGN_CSS = _REPO / "docs" / "_static" / "dartwork-design.css"
_BUILDER = _SCRIPTS / "build_categorical_explorer.py"
_DEMO_KEYS = [
    "line",
    "bar",
    "scatter",
    "area",
    "lollipop",
    "bubble",
    "heatmap",
    "waffle",
    "treemap",
    "donut",
    "bump",
    "slope",
    "streamgraph",
    "dotplot",
    "boxplot",
]
_DEFAULT_9 = [
    "line",
    "bar",
    "scatter",
    "area",
    "heatmap",
    "treemap",
    "donut",
    "bump",
    "slope",
]
_NEW_DEMOS = ["donut", "bump", "slope", "streamgraph", "dotplot", "boxplot"]
_REPLACE_LAST_HANDLER = (
    "function capDemosToLayout(){if(state.demos.length>state.layout)"
    "state.demos=state.demos.slice(0,state.layout);}\n"
    "function setLayout(n){state.layout=n;capDemosToLayout();renderDetail();}\n"
    "function toggleDemo(k){capDemosToLayout();var idx=state.demos.indexOf(k);\n"
    "  if(idx>=0)state.demos.splice(idx,1);else if(state.demos.length>=state.layout)"
    "state.demos.splice(state.demos.length-1,1,k);else state.demos.push(k);"
    "renderDetail();}"
)
_RAIL_GROUP_ORDER = ["Qualitative", "Muted", "Tone", "Emphasis"]
_QUALITATIVE_ORDER = [
    "trustworthy",
    "vivid",
    "neon",
    "pastel",
    "dusty",
    "ember",
    "earth",
    "jewel",
    "forest",
    "teal_accent",
    "coral_accent",
]
_ABSORBED_DIVERGING = ["blue_red", "blue_orange", "teal_amber", "green_purple"]


def _payload() -> dict:
    """Parse the ``var D = {...}`` JSON payload the builder injects."""
    html = _EXPLORER.read_text(encoding="utf-8")
    m = re.search(r"var D = (\{.*?\});\s*\nvar PALETTES", html, re.S)
    assert m, "explorer payload (var D = {...}) not found"
    return json.loads(m.group(1))


def _builder_payload() -> dict:
    return runpy.run_path(str(_BUILDER))["build_payload"]()


def _by_kind(payload: dict, kind: str) -> dict[str, tuple[str, ...]]:
    return {
        key: tuple(p["cols"])
        for key, p in payload["palettes"].items()
        if p["kind"] == kind
    }


def test_no_legacy_js_data_file() -> None:
    """The v4 hand-maintained explorer data file stays gone (SSOT-generated)."""
    assert not (_SCRIPTS / "categorical_explorer_data.js").exists()


def test_builder_family_lists_match_palette_ssot() -> None:
    """The categorical explorer no longer carries sequential family ramps."""
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()

    assert "FAMILY_ORDER" not in builder
    assert "FAMILY_INTENT" not in builder
    assert _by_kind(payload, "family") == {}
    assert set(payload["order"]) == {
        "octave",
        "octave_print",
        *_QUALITATIVE_ORDER,
    }


def test_curated_ssot_splits_qualitative_rail_from_absorbed_diverging() -> None:
    """Absorbed diverging forms stay registered but leave the qualitative rail."""
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()

    assert list(_curated.CURATED_QUALITATIVE_ORDER) == _QUALITATIVE_ORDER
    assert list(_curated.CURATED_DIVERGING_ORDER) == _ABSORBED_DIVERGING
    assert set(_curated.CURATED) == set(_QUALITATIVE_ORDER) | set(
        _ABSORBED_DIVERGING
    )
    assert all(
        _curated.CURATED_META[k]["kind"] == "qualitative"
        for k in _QUALITATIVE_ORDER
    )
    assert all(
        _curated.CURATED_META[k]["kind"] == "diverging"
        for k in _ABSORBED_DIVERGING
    )
    assert not {
        "warm_gray",
        "cool_gray",
        "teal_coral",
        "teal_indigo",
        "accessible",
        "cool_warm",
        "purple_green",
    } & set(_curated.CURATED)
    assert _curated.CURATED["green_purple"][0] == "#09581b"
    assert _curated.CURATED["green_purple"][-1] == "#523f87"
    assert not set(_ABSORBED_DIVERGING) & set(payload["order"])


def test_builder_rail_groups_use_qualitative_taxonomy() -> None:
    """Cycle, trustworthy, vivid, and neon are one qualitative rail."""
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()
    groups = dict(payload["groups"])

    assert builder["RAIL_GROUP_ORDER"] == _RAIL_GROUP_ORDER
    assert [label for label, _ in payload["groups"]] == _RAIL_GROUP_ORDER
    assert groups["Qualitative"] == [
        "octave",
        "octave_print",
        "trustworthy",
        "vivid",
        "neon",
        "forest",
    ]
    assert groups["Muted"] == ["pastel", "dusty"]
    assert groups["Tone"] == ["ember", "earth", "jewel"]
    assert groups["Emphasis"] == ["teal_accent", "coral_accent"]
    assert not {
        "Cycles",
        "Balanced",
        "Spectrum",
        "Analogous",
        "Duo",
        "Diverging",
        "Neutral",
        "Accessible",
    } & set(groups)

    for key in groups["Qualitative"]:
        assert payload["palettes"][key]["group"] == "Qualitative"


def test_builder_presentation_names_are_title_case_without_code_key_drift() -> (
    None
):
    """Display names change casing; copyable palette keys stay lowercase."""
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()
    palettes = payload["palettes"]

    assert palettes["octave"]["name"] == "Octave"
    assert palettes["octave_print"]["name"] == "Octave Print"
    assert palettes["forest"]["name"] == "Forest"
    assert set(palettes) >= {"octave", "octave_print", "forest"}
    assert "coral" not in palettes
    assert "warm_gray" not in palettes


def test_builder_family_intents_are_substantive_layout_copy() -> None:
    """Qualitative copy fills the reserved detail-panel space with guidance."""
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()
    qualitative = {
        key: payload["palettes"][key]["intent"] for key in _QUALITATIVE_ORDER
    }

    terse = [
        key
        for key, text in qualitative.items()
        if text.count(".") + text.count("!") + text.count("?") < 2
    ]
    assert not terse


def test_builder_cycle_intents_explain_screen_print_tradeoff() -> None:
    """Octave and Octave Print lead with the screen-vs-print reason both exist."""
    builder = runpy.run_path(str(_BUILDER))
    cycle_intent = dict(builder["CYCLE_INTENT"])

    assert "screen-first" in cycle_intent["octave"]
    assert "line-safe L* 43-78 band" in cycle_intent["octave"]
    assert "thin lines on white" in cycle_intent["octave"]
    assert "some pairs share a gray tone" in cycle_intent["octave"]
    assert "min ΔL* 2.7" in cycle_intent["octave"]

    assert "print-first" in cycle_intent["octave_print"]
    assert "same hue per slot as Octave" in cycle_intent["octave_print"]
    assert "violet slot matches Octave" in cycle_intent["octave_print"]
    assert (
        "every pair is at least about 7 L* apart"
        in cycle_intent["octave_print"]
    )
    assert "min ΔL* 7.7" in cycle_intent["octave_print"]
    assert "grayscale printing and photocopies" in cycle_intent["octave_print"]
    assert "dark gray takes the 8th slot" in cycle_intent["octave_print"]


def test_explorer_generated_payload_uses_new_presentation_taxonomy() -> None:
    """The checked-in generated explorer matches the builder taxonomy."""
    payload = _payload()
    groups = dict(payload["groups"])

    assert [label for label, _ in payload["groups"]] == _RAIL_GROUP_ORDER
    assert groups["Qualitative"] == [
        "octave",
        "octave_print",
        "trustworthy",
        "vivid",
        "neon",
        "forest",
    ]
    assert payload["palettes"]["forest"]["name"] == "Forest"
    assert payload["palettes"]["octave"]["name"] == "Octave"
    assert payload["palettes"]["octave_print"]["name"] == "Octave Print"
    assert not {"Cycles", "Balanced", "Spectrum"} & set(groups)


def test_explorer_detail_presentation_order_and_eyebrow_copy() -> None:
    """A11y chips live in the title row; controls precede the slim footer."""
    html = _EXPLORER.read_text(encoding="utf-8")

    assert "v5 cycle" not in html
    assert "v5 family" not in html
    assert " · curated" not in html
    assert "var ey=p.group;" in html
    assert "Design targets" not in html
    assert (
        '\'<div class="d-title"><h3>\'+p.name+\'</h3><code class="d-key" '
        "title=\"copy the palette name\">'+state.key+'</code><span "
        'class="a11y-chips"></span></div>\''
    ) in html
    assert '<div class="a11y-host">' not in html

    ordered_fragments = [
        '<div class="d-ey">',
        '<div class="d-title">',
        '<p class="d-use">',
        '<div class="d-bar">',
        "+demoToolsHTML()",
        '<div class="swhost">',
        '<div class="demo-host">',
        '<div class="code highlight">',
        '<div class="meta-host">',
    ]
    detail_start = html.index("function renderDetail()")
    detail_end = html.index("document.getElementById('cx-rail')", detail_start)
    detail = html[detail_start:detail_end]
    positions = [detail.index(fragment) for fragment in ordered_fragments]
    assert positions == sorted(positions)


def test_categorical_demo_library_defaults_and_coverage_self_check() -> None:
    """The categorical explorer ships 15 selectable demos and a 3x3 default."""
    builder = runpy.run_path(str(_BUILDER))
    lib = [key for key, _label in builder["DEMO_LIBRARY"]]

    assert lib == _DEMO_KEYS
    assert len(lib) == 15
    for key in _NEW_DEMOS:
        assert key in lib
    assert builder["DEFAULT_9"] == _DEFAULT_9
    assert builder["DEFAULT_6"] == _DEFAULT_9[:6]
    assert builder["DEFAULT_4"] == _DEFAULT_9[:4]
    assert len(set(builder["DEFAULT_9"])) == 9

    payload = _builder_payload()
    assert [demo["key"] for demo in payload["library"]] == _DEMO_KEYS
    assert payload["defaults"] == {
        "4": builder["DEFAULT_4"],
        "6": builder["DEFAULT_6"],
        "9": builder["DEFAULT_9"],
    }
    rows = payload["demo_coverage"]
    assert [row["demo"] for row in rows] == _DEMO_KEYS
    assert all(row["selected"] == 8 for row in rows)
    assert min(row["distinct"] for row in rows) >= 8


def test_categorical_explorer_uses_shared_demo_and_layout_pickers() -> None:
    """Demo chips and 2x2/2x3/3x3 layout controls replace the Charts slider."""
    html = _EXPLORER.read_text(encoding="utf-8")
    payload = _payload()

    assert [demo["key"] for demo in payload["library"]] == _DEMO_KEYS
    assert payload["defaults"]["9"] == _DEFAULT_9
    assert "Charts" not in html
    assert 'id="shrng"' not in html
    assert "state.show" not in html
    assert "demoToolsHTML()" in html
    assert 'class="demo-picker"' in html
    assert "data-demo-pick" in html
    assert 'data-layout="4"' in html
    assert 'data-layout="6"' in html
    assert 'data-layout="9"' in html
    assert "'+state.layout" in html
    assert "visibleDemos()" in html
    for key in _NEW_DEMOS:
        assert f'"key":"{key}"' in html


def test_categorical_demo_picker_replaces_last_full_slot() -> None:
    """Demo selection is capped to the layout and swaps the newest slot."""
    html = _EXPLORER.read_text(encoding="utf-8")

    assert _REPLACE_LAST_HANDLER in html
    assert "var k=b.dataset.demoPick,idx=state.demos.indexOf(k)" not in html
    assert "if(wasDefault)" not in html
    assert "P.grouped" not in html
    assert '"key":"grouped"' not in html
    assert '{"key":"bump","name":"Bump chart"}' in html

    demos = _DEFAULT_9[:4]
    new_key = "streamgraph"
    if new_key in demos:
        demos.remove(new_key)
    elif len(demos) >= 4:
        demos[-1] = new_key
    else:
        demos.append(new_key)
    assert demos == ["line", "bar", "scatter", "streamgraph"]

    demos.remove("bar")
    assert demos == ["line", "scatter", "streamgraph"]


def test_explorer_layout_fits_article_column() -> None:
    """The explorer uses a bounded grid track and wrapping controls."""
    html = _EXPLORER.read_text(encoding="utf-8")
    css = _DESIGN_CSS.read_text(encoding="utf-8")

    assert '<div id="dm-cat-exp" class="yue">' in html
    assert "<style" not in html
    assert "grid-template-columns:minmax(10rem,10.5rem) minmax(0,1fr)" in css
    assert (
        "#dm-cat-exp,#dm-cmap-exp {width:100%;max-width:100%;container-type:inline-size;"
        in css
    )
    assert "#dm-cat-exp .detail,#dm-cmap-exp .detail {min-width:0;" in css
    assert "gap:var(--dm-space-4,16px)" in css
    assert "padding-right:4px" in css
    assert "flex-wrap:wrap;row-gap:8px;" in css
    assert "grid-template-columns:minmax(10.5rem,12rem)" not in css


def test_rail_mini_strips_share_square_non_clipping_rectangles() -> None:
    """Categorical and colormap rail minis use the same square-ended strip."""
    css = _DESIGN_CSS.read_text(encoding="utf-8")
    m = re.search(
        r"#dm-cat-exp \.ri \.mini,#dm-cmap-exp \.ri \.mini \{([^}]*)\}", css
    )
    assert m, "shared rail mini CSS rule missing"
    mini_rule = m.group(1)
    assert "flex:0 0 40px" in mini_rule
    assert "height:12px" in mini_rule
    assert "border-radius" not in mini_rule
    assert "overflow" not in mini_rule
    assert "border" not in mini_rule
    assert "box-shadow" not in mini_rule


def test_explorer_title_row_chips_replace_badge_readout() -> None:
    """Accessibility checks render as title-row outline chips with circle dots."""
    html = _EXPLORER.read_text(encoding="utf-8")
    css = _DESIGN_CSS.read_text(encoding="utf-8")
    readout_start = html.index("// ── live accessibility readout ──")
    readout_end = html.index("function metaRow", readout_start)
    readout = html[readout_start:readout_end]

    assert ".a11y-chips" in html
    assert ".a11y-chip" in html
    assert "a-dot" in html
    assert ".a-dot" in css
    assert "border-radius:var(--dm-radius-full,999px)" in css
    assert "margin-left:auto" in css
    assert "function chipHTML(" in html
    assert "d.querySelector('.a11y-chips').innerHTML=a11yHTML();" in html
    assert "function bwTip(v){" in html
    assert "function cvdTip(c){" in html
    assert "the smallest lightness gap between any two colors here" in html
    assert "some pairs share a gray tone when printed" in html
    assert "Octave Print fixes this" in html
    assert "Worst-case ΔE00 color difference" in html
    assert "all three deficiency types" in html
    assert ".a11y-badge" not in html
    assert ".a11y-badges" not in html
    assert "function badgeHTML(" not in html
    assert ".a11y-host" not in html
    assert "function stateIcon(" not in html
    assert "function readoutHTML(" not in html
    for glyph in ("✓", "×", "◑", "◔"):  # noqa: RUF001 — the banned glyphs themselves
        assert glyph not in readout


def test_cycle_payload_includes_cvd_metrics_from_ssot() -> None:
    """Octave and Octave Print carry CVD metrics for the badge parser."""
    builder = runpy.run_path(str(_BUILDER))
    for payload in (builder["build_payload"](), _payload()):
        for key in ("octave", "octave_print"):
            cvd = payload["palettes"][key]["cvd"]
            assert re.fullmatch(r"d\d+\.\d / p\d+\.\d / t\d+\.\d", cvd)


def test_docs_semantic_aliases_live_on_static_palette_page() -> None:
    cat = (
        _REPO / "docs" / "color_system" / "categorical-palettes.md"
    ).read_text(encoding="utf-8")
    colors = (_REPO / "docs" / "color_system" / "colors.md").read_text(
        encoding="utf-8"
    )

    assert "### Semantic tokens" not in cat
    assert "62ch" not in cat
    assert "## Semantic aliases" in colors
    assert 'ax.plot(gains, color="dc.pos")' in colors
    assert 'ax.axhline(baseline, color="dc.ref")' in colors


def test_docs_octave_reference_keeps_pinned_phrases_and_tradeoff() -> None:
    """The reference paragraph preserves fact pins and mirrors the trade-off."""
    cat = (
        _REPO / "docs" / "color_system" / "categorical-palettes.md"
    ).read_text(encoding="utf-8")
    cat_flat = re.sub(r"\s+", " ", cat)

    for phrase in (
        "min ΔE00 10.3",
        "Okabe-Ito benchmark's 11.5",
        "default cycle's 8.3 actually beats",
        "beats Okabe-Ito's 7.9",
        "13 qualitative choices",
    ):
        assert phrase in cat
    assert "line-safe L* 43-78 band" in cat_flat
    assert "same hue per slot as Octave" in cat_flat
    assert "violet slot matches Octave" in cat_flat
    assert (
        "Octave Print guarantees every pair is at least about 7 L* apart"
        in cat_flat
    )
    assert "min ΔL* 7.7" in cat_flat


def test_palette_metadata_fact_audit_claims_are_current() -> None:
    curated = (
        _REPO / "src" / "dartwork_mpl" / "colors" / "_curated.py"
    ).read_text(encoding="utf-8")
    ember_intent = _curated.CURATED_META["ember"]["intent"]
    rationale = (
        _REPO / "docs" / "_static" / "dartwork-discrete-palette-rationale.md"
    ).read_text(encoding="utf-8")

    assert "Up to 6 vivid categories" not in curated
    assert "Up to 8 vivid categories" in curated
    assert "brick, coral, orange, amber, gold, olive plus" not in curated
    assert (
        "brick, coral, ochre, gold, olive, pink, and clay plus" in ember_intent
    )
    assert "Up to 6 vivid categories" not in rationale
    assert "brick, coral, orange, amber, gold, olive plus" not in rationale
    assert "old hand-curated palette asset" not in rationale
    assert "11 curated qualitative sets" in rationale


def test_explorer_families_match_palette_ssot() -> None:
    """The categorical explorer rail is qualitative only."""
    fam = _by_kind(_payload(), "family")
    assert fam == {}


def test_explorer_curated_match_curated_ssot() -> None:
    cur = _by_kind(_payload(), "curated")
    expected = set(_curated.CURATED_QUALITATIVE_ORDER)
    assert set(cur) == expected, (
        f"curated drift: only-explorer={sorted(set(cur) - expected)}, "
        f"only-qualitative={sorted(expected - set(cur))}"
    )
    mismatched = {
        k: (cur[k], tuple(_curated.CURATED[k]))
        for k in expected
        if cur[k] != tuple(_curated.CURATED[k])
    }
    assert not mismatched, (
        f"curated color drift (explorer, CURATED): {mismatched}"
    )


def test_explorer_cycles_match_cycles_ssot() -> None:
    cyc = _by_kind(_payload(), "cycle")
    assert set(cyc) == set(_generated.CYCLES)
    for k in _generated.CYCLES:
        assert cyc[k] == tuple(_generated.CYCLES[k]), k


def test_explorer_counts_match_ssot() -> None:
    counts = _payload()["counts"]
    assert counts["qualitative"] == 13
    assert counts["curated"] == len(_curated.CURATED_QUALITATIVE_ORDER)
    assert counts["cycles"] == len(_generated.CYCLES)


def test_absorbed_diverging_palettes_are_registered_but_hidden() -> None:
    import matplotlib.colors as mcolors

    import dartwork_mpl as dm

    payload = _payload()
    names = mcolors.get_named_colors_mapping()
    for key in _ABSORBED_DIVERGING:
        assert dm.get_palette(key) == [f"dc.{key}{i}" for i in range(8)]
        assert all(f"dc.{key}{i}" in names for i in range(8))
        assert key not in payload["order"]
