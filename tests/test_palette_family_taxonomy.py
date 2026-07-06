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
        "default",
        "print",
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

    assert palettes["default"]["name"] == "Default"
    assert palettes["print"]["name"] == "Print"
    assert palettes["coral"]["name"] == "Coral"
    assert palettes["cobalt"]["name"] == "Cobalt"
    assert palettes["warm_gray"]["name"] == "Warm Gray"
    assert set(palettes) >= {"default", "print", "coral", "warm_gray"}


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


def test_explorer_generated_payload_uses_new_presentation_taxonomy() -> None:
    """The checked-in generated explorer matches the builder taxonomy."""
    payload = _payload()
    groups = dict(payload["groups"])

    assert [label for label, _ in payload["groups"]] == _RAIL_GROUP_ORDER
    assert groups["Qualitative"] == [
        "default",
        "print",
        "trustworthy",
        "vivid",
        "neon",
    ]
    assert payload["palettes"]["coral"]["name"] == "Coral"
    assert payload["palettes"]["default"]["name"] == "Default"
    assert payload["palettes"]["print"]["name"] == "Print"
    assert not {"Cycles", "Balanced", "Spectrum"} & set(groups)


def test_explorer_detail_presentation_order_and_eyebrow_copy() -> None:
    """Actionable code appears before the readout and reference footer."""
    html = _EXPLORER.read_text(encoding="utf-8")

    assert "v5 cycle" not in html
    assert "v5 family" not in html
    assert " · curated" not in html
    assert "var ey=p.group;" in html

    ordered_fragments = [
        '<div class="d-ey">',
        '<div class="d-title">',
        '<p class="d-use">',
        '<div class="d-bar">',
        '<div class="swhost">',
        '<div class="plots">',
        '<div class="code highlight">',
        '<div class="ro-host">',
        '<div class="meta-host">',
    ]
    positions = [html.index(fragment) for fragment in ordered_fragments]
    assert positions == sorted(positions)


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
