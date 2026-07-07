"""v5 categorical explorer ↔ color-SSOT parity (G13).

The interactive categorical explorer fragment is generated from the color SSOT
— ``_generated.PALETTE`` (families) + ``_generated.CYCLES`` (cycles) +
``_curated.CURATED`` (curated sets). These guards keep the generated fragment
and the builder's family/intent lists pinned to that SSOT, and keep the removed
v4 JS data file gone.
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
_BUILDER = _SCRIPTS / "build_categorical_explorer.py"
_RAIL_GROUP_ORDER = [
    "Qualitative",
    "Sequential",
    "Analogous",
    "Muted",
    "Tone",
    "Duo",
    "Diverging",
    "Neutral",
    "Emphasis",
    "Accessible",
]


def _payload() -> dict:
    """Parse the ``var D = {...}`` JSON payload the builder injects."""
    html = _EXPLORER.read_text(encoding="utf-8")
    m = re.search(r"var D = (\{.*?\});\s*\nvar PALETTES", html, re.S)
    assert m, "explorer payload (var D = {...}) not found"
    return json.loads(m.group(1))


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
    """The builder's FAMILY_ORDER / FAMILY_INTENT cover exactly the v5
    families — no drift, no duplicates."""
    builder = runpy.run_path(str(_BUILDER))
    fam_order = list(builder["FAMILY_ORDER"])
    fam_intent = dict(builder["FAMILY_INTENT"])
    assert fam_order == [
        "red",
        "rose",
        "coral",
        "tangerine",
        "orange",
        "amber",
        "yellow",
        "lime",
        "green",
        "teal",
        "cyan",
        "sky",
        "blue",
        "cobalt",
        "indigo",
        "violet",
        "purple",
        "fuchsia",
        "pink",
        "gray",
    ]
    assert len(fam_order) == len(set(fam_order)), fam_order
    assert set(fam_order) == set(_generated.PALETTE), (
        f"FAMILY_ORDER drift: only-builder="
        f"{sorted(set(fam_order) - set(_generated.PALETTE))}, "
        f"only-PALETTE={sorted(set(_generated.PALETTE) - set(fam_order))}"
    )
    assert set(fam_intent) == set(_generated.PALETTE)


def test_builder_rail_groups_keep_chromatic_and_neutral_ramps_apart() -> None:
    """Sequential rail is the hue spectrum; neutral rail is gray ramps only."""
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()
    groups = dict(payload["groups"])

    assert groups["Sequential"] == [
        "red",
        "rose",
        "coral",
        "tangerine",
        "orange",
        "amber",
        "yellow",
        "lime",
        "green",
        "teal",
        "cyan",
        "sky",
        "blue",
        "cobalt",
        "indigo",
        "violet",
        "purple",
        "fuchsia",
        "pink",
    ]
    assert groups["Neutral"] == ["gray", "warm_gray", "cool_gray"]
    assert payload["palettes"]["coral"]["kind"] == "family"
    assert "coral" not in _curated.CURATED


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
    ]
    assert groups["Muted"] == ["pastel", "dusty"]
    assert groups["Tone"] == ["ember", "earth", "jewel"]
    assert groups["Duo"] == ["blue_orange", "teal_coral"]
    assert groups["Neutral"] == ["gray", "warm_gray", "cool_gray"]
    assert not {"Cycles", "Balanced", "Spectrum"} & set(groups)

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
    assert palettes["coral"]["name"] == "Coral"
    assert palettes["cobalt"]["name"] == "Cobalt"
    assert palettes["warm_gray"]["name"] == "Warm Gray"
    assert set(palettes) >= {"octave", "octave_print", "coral", "warm_gray"}


def test_builder_family_intents_are_substantive_layout_copy() -> None:
    """Family copy fills the reserved detail-panel space with real guidance."""
    builder = runpy.run_path(str(_BUILDER))
    fam_intent = dict(builder["FAMILY_INTENT"])

    terse = [
        fam
        for fam, text in fam_intent.items()
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
    ]
    assert payload["palettes"]["coral"]["name"] == "Coral"
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
        '<div class="swhost">',
        '<div class="plots">',
        '<div class="code highlight">',
        '<div class="meta-host">',
    ]
    positions = [html.index(fragment) for fragment in ordered_fragments]
    assert positions == sorted(positions)


def test_explorer_layout_fits_article_column() -> None:
    """The explorer uses a bounded grid track and wrapping controls."""
    html = _EXPLORER.read_text(encoding="utf-8")

    assert "grid-template-columns:168px minmax(0,1fr)" in html
    assert "#dm-cat-exp {width:100%;max-width:100%;overflow:clip;" in html
    assert "#dm-cat-exp .detail {min-width:0;" in html
    assert "flex-wrap:wrap;row-gap:8px;" in html


def test_explorer_title_row_chips_replace_badge_readout() -> None:
    """Accessibility checks render as title-row outline chips with circle dots."""
    html = _EXPLORER.read_text(encoding="utf-8")
    readout_start = html.index("// ── live accessibility readout ──")
    readout_end = html.index("function metaRow", readout_start)
    readout = html[readout_start:readout_end]

    assert ".a11y-chips" in html
    assert ".a11y-chip" in html
    assert ".a-dot" in html
    assert "border-radius:50%" in html
    assert "margin-left:auto" in html
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
        "curated 20-palette system",
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
    rationale = (
        _REPO / "docs" / "_static" / "dartwork-discrete-palette-rationale.md"
    ).read_text(encoding="utf-8")

    assert "Up to 6 vivid categories" not in curated
    assert "Up to 8 vivid categories" in curated
    assert "brick, coral, orange, amber, gold, olive plus" not in curated
    assert "brick, coral, ochre, gold, olive, pink, and clay plus" in curated
    assert "Up to 6 vivid categories" not in rationale
    assert "brick, coral, orange, amber, gold, olive plus" not in rationale
    assert "old hand-curated palette asset" not in rationale
    assert "20 curated categorical sets" in rationale


def test_explorer_families_match_palette_ssot() -> None:
    fam = _by_kind(_payload(), "family")
    assert set(fam) == set(_generated.PALETTE)
    mismatched = {
        k: (fam[k], tuple(_generated.PALETTE[k]))
        for k in _generated.PALETTE
        if fam[k] != tuple(_generated.PALETTE[k])
    }
    assert not mismatched, (
        f"family color drift (explorer, PALETTE): {mismatched}"
    )


def test_explorer_curated_match_curated_ssot() -> None:
    cur = _by_kind(_payload(), "curated")
    assert set(cur) == set(_curated.CURATED), (
        f"curated drift: only-explorer={sorted(set(cur) - set(_curated.CURATED))}, "
        f"only-CURATED={sorted(set(_curated.CURATED) - set(cur))}"
    )
    mismatched = {
        k: (cur[k], tuple(_curated.CURATED[k]))
        for k in _curated.CURATED
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
    assert counts["families"] == len(_generated.PALETTE)
    assert counts["curated"] == len(_curated.CURATED)
    assert counts["cycles"] == len(_generated.CYCLES)
    assert counts["family_colors"] == sum(
        len(row) for row in _generated.PALETTE.values()
    )
