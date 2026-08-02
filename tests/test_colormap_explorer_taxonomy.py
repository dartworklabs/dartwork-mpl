"""Continuous-colormap explorer <-> color-SSOT parity + layout pins.

The interactive colormap explorer fragment is generated from the color SSOT
(``_generated.CMAPS_256``) by ``build_colormap_explorer.py``. These guards keep
the generated fragment and the builder pinned to the verified 43-map taxonomy
(20 sequential / 9 multi-hue / 11 diverging / 3 cyclic), the item-1 chroma
vivid-clip self-check, the 16-demo library, the design-token layout literals,
and zero-Hangul / no-raw-hex hygiene.
"""

from __future__ import annotations

import ast
import json
import math
import re
import runpy
import statistics
from itertools import pairwise
from pathlib import Path
from typing import TypedDict, cast
from unittest.mock import patch

import pytest

from dartwork_mpl._colors import _generated

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "docs" / "_static" / "scripts"
_EXPLORER = _REPO / "docs" / "_static" / "colormap_explorer.html"
_BUILDER = _SCRIPTS / "build_colormap_explorer.py"
_DESIGN_CSS = _REPO / "docs" / "_static" / "dartwork-design.css"
_V6_SSOT = _REPO / "src/dartwork_mpl/asset/color/color_v6_ssot.json"
_CVD_MODELS = {
    "deutan": "Machado et al. 2009 severity 1.0",
    "protan": "Machado et al. 2009 severity 1.0",
    "tritan": "Brettel-Vienot-Mollon 1997 adapted linear-sRGB",
}

_SEQUENTIAL = [
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
_MULTI_HUE = [
    "afterglow",
    "aurora",
    "blaze",
    "canopy",
    "glacier",
    "haze",
    "iris",
    "lagoon",
    "lava",
]
_DIVERGING = [
    "blue_red",
    "blue_orange",
    "cyan_red",
    "teal_amber",
    "teal_rose",
    "indigo_amber",
    "green_purple",
    "purple_orange",
    "violet_lime",
    "gray_blue",
    "gray_red",
]
_CYCLIC = ["hue", "halo", "corona"]
_DEMO_KEYS = [
    "heatmap",
    "contours",
    "isolines",
    "scatter",
    "signal",
    "streamlines",
    "hexbin",
    "terrain",
    "bars",
    "mosaic",
    "lines",
    "network",
    "ridgeline",
    "quiver",
    "polar_heat",
    "waffle",
]
_DEFAULT_9 = [
    "heatmap",
    "contours",
    "streamlines",
    "lines",
    "network",
    "ridgeline",
    "quiver",
    "polar_heat",
    "waffle",
]
_MULTI_HUE_VIVID_CUTOFFS = {
    "afterglow": 1,
    "aurora": 33,
    "blaze": 8,
    "canopy": 16,
    "glacier": 1,
    "haze": 37,
    "iris": 32,
    "lagoon": 29,
    "lava": 19,
}
_CANVAS_DEMOS = ["heatmap", "contours", "terrain", "signal", "polar_heat"]
_REPLACE_LAST_HANDLER = (
    "function capDemosToLayout(){if(state.demos.length>state.layout)"
    "state.demos=state.demos.slice(0,state.layout);}\n"
    "function setLayout(n){state.layout=n;capDemosToLayout();renderDetail();}\n"
    "function toggleDemo(k){capDemosToLayout();var idx=state.demos.indexOf(k);\n"
    "  if(idx>=0)state.demos.splice(idx,1);else if(state.demos.length>=state.layout)"
    "state.demos.splice(state.demos.length-1,1,k);else state.demos.push(k);"
    "renderDetail();}"
)


class _ExplorerVariant(TypedDict):
    """Subset of one generated variant used by parity assertions."""

    stops: list[str]
    demo: list[str]
    vivid_cutoff: int | None
    chips: list[dict[str, object]]
    oklab_l: list[float]
    relative_y: list[float]
    delta_e_ok: list[float]
    delta_e_00: list[float]
    cvd_model: dict[str, str]


class _ExplorerMap(TypedDict):
    """Subset of one generated map record used by parity assertions."""

    default_variant: str
    intent: str
    variants: dict[str, _ExplorerVariant]


class _ExplorerLibraryItem(TypedDict):
    """Subset of one generated demo-library item."""

    key: str


class _ExplorerPayload(TypedDict):
    """Typed subset of the embedded explorer JSON payload."""

    groups: list[tuple[str, list[str]]]
    counts: dict[str, int]
    order: list[str]
    maps: dict[str, _ExplorerMap]
    library: list[_ExplorerLibraryItem]
    defaults: dict[str, list[str]]


def _payload_from_html() -> _ExplorerPayload:
    """Parse the ``var D={...}`` JSON payload the builder injects."""
    html = _EXPLORER.read_text(encoding="utf-8")
    m = re.search(r"var D=(\{.*?\});\nvar MAPS", html, re.S)
    assert m, "explorer payload (var D={...}) not found"
    decoded: object = json.loads(m.group(1))
    if not isinstance(decoded, dict):
        raise TypeError("explorer payload must be a JSON object")
    return cast(_ExplorerPayload, decoded)


def _colormap_css() -> str:
    css = _DESIGN_CSS.read_text(encoding="utf-8")
    start = css.index("/* Explorer widget shared layer.")
    end = css.index("/* Categorical palette page polish.", start)
    return css[start:end]


# ── taxonomy partition ─────────────────────────────────────────────────────
def test_builder_taxonomy_partition_matches_cmaps_ssot() -> None:
    builder = runpy.run_path(str(_BUILDER))
    assert builder["SEQUENTIAL"] == _SEQUENTIAL
    assert builder["MULTI_HUE"] == _MULTI_HUE
    assert builder["DIVERGING"] == _DIVERGING
    assert builder["CYCLIC"] == _CYCLIC
    partition = (
        builder["SEQUENTIAL"]
        + builder["MULTI_HUE"]
        + builder["DIVERGING"]
        + builder["CYCLIC"]
    )
    assert len(partition) == len(set(partition)) == 43
    assert set(partition) == set(_generated.CMAPS_256)


def test_payload_group_counts_and_order() -> None:
    for payload in (
        runpy.run_path(str(_BUILDER))["build_payload"](),
        _payload_from_html(),
    ):
        assert [label for label, _ in payload["groups"]] == [
            "Sequential",
            "Multi-hue",
            "Diverging",
            "Cyclic",
        ]
        groups = dict(payload["groups"])
        assert groups["Sequential"] == _SEQUENTIAL
        assert groups["Multi-hue"] == _MULTI_HUE
        assert groups["Diverging"] == _DIVERGING
        assert groups["Cyclic"] == _CYCLIC
        assert payload["counts"] == {
            "sequential": 20,
            "multi_hue": 9,
            "diverging": 11,
            "cyclic": 3,
            "total": 43,
        }
        assert payload["order"] == (
            _SEQUENTIAL + _MULTI_HUE + _DIVERGING + _CYCLIC
        )


def test_explorer_map_stops_match_cmaps_ssot() -> None:
    """Every rendered ramp is a 64-stop subsample of the SSOT 256-LUT."""
    payload = _payload_from_html()
    for key, cmap in _generated.CMAPS_256.items():
        original = payload["maps"][key]["variants"]["original"]["stops"]
        idx = list(range(0, 256, 4))
        idx[-1] = 255
        assert original == [cmap[i] for i in idx], key


# ── item 1: chroma vivid-clip ──────────────────────────────────────────────
def test_vivid_cutoff_present_for_sequential_and_multihue_only() -> None:
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    for key, cmap in payload["maps"].items():
        if cmap["kind"] in ("family", "multi"):
            for variant_name, variant in cmap["variants"].items():
                label = f"{key}:{variant_name}"
                assert isinstance(variant["vivid_cutoff"], int), label
                # demo ramp is genuinely clipped shorter than the full ramp span
                assert variant["demo"] != variant["stops"], label
        else:
            variant = cmap["variants"][cmap["default_variant"]]
            assert variant["vivid_cutoff"] is None, key
            assert variant["demo"] == variant["stops"], key


def test_self_check_table_and_seq_multi_ratios_clear_055() -> None:
    """Item 1 step 6: darkest demo swatch >= 0.55 x own peak (seq+multi)."""
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    rows = payload["self_check"]
    assert len(rows) == 43
    seq_multi = [r for r in rows if r["group"] in ("family", "multi")]
    assert len(seq_multi) == 29
    offenders = [r for r in seq_multi if r["ratio"] < 0.55]
    assert not offenders, offenders
    assert min(r["ratio"] for r in seq_multi) >= 0.55
    # the four spot-check maps clear the bar with room to spare
    by_map = {r["map"]: r for r in rows}
    for key in ("teal", "blue", "purple", "tangerine"):
        assert by_map[key]["ratio"] >= 0.55, key


def test_unclipped_dark_ends_would_fail_the_guard() -> None:
    """Sanity: without the vivid clip the raw dark endpoints are near-black.

    Confirms the guard is load-bearing — several sequential maps' true dark
    endpoints fall well under 0.55 x peak chroma, which the demo clip fixes.
    """
    import math

    from dartwork_mpl._colors._metrics import lab_from_rgb, rgb_from_hex

    def chroma(hex_color: str) -> float:
        _l, a, b = lab_from_rgb(rgb_from_hex(hex_color))
        return math.hypot(a, b)

    for key in ("teal", "blue", "purple", "tangerine"):
        cmap = _generated.CMAPS_256[key]
        peak = max(chroma(h) for h in cmap)
        raw_dark_ratio = chroma(cmap[255]) / peak
        assert raw_dark_ratio < 0.2, (key, raw_dark_ratio)  # near-black


def test_builder_delegates_vivid_cutoff_to_library_helper() -> None:
    """The docs builder must not carry a local copy of the cutoff rule."""
    source = _BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    local_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "_vivid_cutoff" not in local_functions
    assert "_chroma" not in local_functions
    assert "0.6 * peak" not in source
    assert ">= 0.6 x peak" not in source


def test_v6_ssot_pins_shipped_multi_hue_vivid_cutoffs() -> None:
    """Keep compatibility presentation choices separate from color theory."""
    payload = json.loads(_V6_SSOT.read_text(encoding="utf-8"))

    assert (
        payload["policies"]["presentation"]["multi_hue_vivid_cutoffs"]
        == _MULTI_HUE_VIVID_CUTOFFS
    )


def test_explorer_uses_the_shipped_multi_hue_vivid_cutoffs() -> None:
    """Preserve all nine current demo cutoffs while the metric changes."""
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()

    assert {
        key: payload["maps"][key]["variants"]["original"]["vivid_cutoff"]
        for key in _MULTI_HUE
    } == _MULTI_HUE_VIVID_CUTOFFS


# ── removed Ends / L* profile payload ──────────────────────────────────────
def test_payload_ships_single_true_variant_without_profiles_or_refined_ends() -> (
    None
):
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()
    assert "FLAGGED_ENDS" not in builder
    assert "_refined_stops" not in builder
    for key, cmap in payload["maps"].items():
        assert cmap["default_variant"] == "original", key
        assert set(cmap["variants"]) == {"original"}, key
        variant = cmap["variants"]["original"]
        assert set(variant) == {
            "stops",
            "demo",
            "vivid_cutoff",
            "chips",
            "oklab_l",
            "relative_y",
            "delta_e_ok",
            "delta_e_00",
            "cvd_model",
        }, key


def test_metric_payload_uses_canonical_and_validation_keys_with_finite_values() -> (
    None
):
    """Explorer arrays expose OKLab/Y first and CIELAB/CVD as validation."""
    from dartwork_mpl._colors._compatibility_metrics import (
        ciede2000_rgb,
        delta_e_ok,
        hex_to_srgb,
        relative_y_srgb_d65,
        srgb_to_oklab,
    )

    builder_payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    for payload in (builder_payload, _payload_from_html()):
        for key in payload["order"]:
            variant = payload["maps"][key]["variants"]["original"]
            rgb = [hex_to_srgb(color) for color in variant["stops"]]
            expected = {
                "oklab_l": [srgb_to_oklab(color)[0] for color in rgb],
                "relative_y": [relative_y_srgb_d65(color) for color in rgb],
                "delta_e_ok": [
                    delta_e_ok(first, second) for first, second in pairwise(rgb)
                ],
                "delta_e_00": [
                    ciede2000_rgb(first, second)
                    for first, second in pairwise(rgb)
                ],
            }
            assert variant["cvd_model"] == _CVD_MODELS, key
            for metric, expected_values in expected.items():
                actual = variant[metric]
                expected_length = (
                    64 if metric in {"oklab_l", "relative_y"} else 63
                )
                assert len(actual) == expected_length, (key, metric)
                assert all(math.isfinite(value) for value in actual), (
                    key,
                    metric,
                )
                assert actual == pytest.approx(expected_values, abs=1e-6), (
                    key,
                    metric,
                )


def test_uniform_chip_means_delta_e_ok() -> None:
    """The primary uniformity badge is computed and named in ΔEOK."""
    for payload in (
        runpy.run_path(str(_BUILDER))["build_payload"](),
        _payload_from_html(),
    ):
        for key in _SEQUENTIAL + _MULTI_HUE:
            variant = payload["maps"][key]["variants"]["original"]
            chip = next(
                item for item in variant["chips"] if item["label"] == "Uniform"
            )
            text = f"{chip['num']} {chip['tip']}"
            assert "ΔEOK" in text, key
            assert "ΔE00" not in text and "Delta E00" not in text, key
            values = variant["delta_e_ok"]
            expected_cv = statistics.pstdev(values) / statistics.fmean(values)
            assert f"{expected_cv:.2f}" in text, key


def test_cvd_chip_reports_quantized_near_monotone_margin_without_strict_claim() -> (
    None
):
    """Expose tolerated CVD reversals instead of calling them ordered."""
    from dartwork_mpl._colors._compatibility_metrics import (
        hex_to_srgb,
        relative_y_srgb_d65,
        simulate_cvd_hex,
    )

    payloads = (
        runpy.run_path(str(_BUILDER))["build_payload"](),
        _payload_from_html(),
    )
    red = payloads[0]["maps"]["red"]["variants"]["original"]
    source_y = [
        relative_y_srgb_d65(hex_to_srgb(color)) for color in red["stops"]
    ]
    sign = 1.0 if source_y[-1] >= source_y[0] else -1.0
    simulated_y = [
        relative_y_srgb_d65(hex_to_srgb(simulate_cvd_hex(color, "protan")))
        for color in red["stops"]
    ]
    red_protan_steps = [
        sign * (second - first) for first, second in pairwise(simulated_y)
    ]

    assert min(red_protan_steps) < 0.0
    assert min(red_protan_steps) >= -0.004

    for payload in payloads:
        red_variant = payload["maps"]["red"]["variants"]["original"]
        chip = next(
            item for item in red_variant["chips"] if item["label"] == "CVD"
        )
        text = f"{chip['num']} {chip['tip']}"
        assert "remains ordered" not in text
        assert (
            "near-monotone within the explorer's 0.004 per-step tolerance"
            in text
        )
        assert f"{min(red_protan_steps):+.4f}" in text
        assert "Zero or above would be strict monotonicity" in text


def test_cyclic_topology_labels_only_hue_isoluminant() -> None:
    """Halo/corona are dark-center cycles; only hue is isoluminant."""
    for payload in (
        runpy.run_path(str(_BUILDER))["build_payload"](),
        _payload_from_html(),
    ):
        labels = {
            key: {
                chip["label"] for chip in cmap["variants"]["original"]["chips"]
            }
            for key, cmap in payload["maps"].items()
        }
        assert [
            key for key in payload["order"] if "Isoluminant" in labels[key]
        ] == ["hue"]
        for key in ("halo", "corona"):
            assert "Isoluminant" not in labels[key]
            assert "Dark center" in labels[key]
            variant = payload["maps"][key]["variants"]["original"]
            profile = variant["relative_y"]
            assert profile.index(min(profile)) in {31, 32}, key
            assert min(profile[0], profile[-1]) > min(profile), key


def test_hue_intent_names_near_flat_y_without_flat_lightness_claim() -> None:
    """Describe hue's measured Y profile without conflating lightness models."""
    for payload in (
        runpy.run_path(str(_BUILDER))["build_payload"](),
        _payload_from_html(),
    ):
        intent = payload["maps"]["hue"]["intent"]
        assert "modeled relative Y is nearly flat" in intent
        assert "not constant OKLab L or equal perceived brightness" in intent
        assert "one flat lightness" not in intent


def test_builder_check_is_byte_stable_and_never_writes(tmp_path: Path) -> None:
    """Fresh/stale/missing --check paths are all in-memory and read-only."""
    builder = runpy.run_path(str(_BUILDER))
    render_html = builder["render_html"]
    first = render_html()
    second = render_html()
    assert isinstance(first, str)
    assert first.encode("utf-8") == second.encode("utf-8")

    main = builder["main"]
    target = tmp_path / "colormap_explorer.html"
    main.__globals__["OUT"] = target
    target.write_bytes(first.encode("utf-8"))

    def checked() -> int:
        with (
            patch.object(
                Path, "write_text", side_effect=AssertionError("write")
            ),
            patch.object(
                Path, "write_bytes", side_effect=AssertionError("write")
            ),
            patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")),
        ):
            result = main(["--check"])
        assert isinstance(result, int)
        return result

    before = (
        target.read_bytes(),
        target.stat().st_mtime_ns,
        set(tmp_path.rglob("*")),
    )
    assert checked() == 0
    assert (
        target.read_bytes(),
        target.stat().st_mtime_ns,
        set(tmp_path.rglob("*")),
    ) == before

    target.write_bytes(b"stale")
    before = (
        target.read_bytes(),
        target.stat().st_mtime_ns,
        set(tmp_path.rglob("*")),
    )
    assert checked() != 0
    assert (
        target.read_bytes(),
        target.stat().st_mtime_ns,
        set(tmp_path.rglob("*")),
    ) == before

    target.unlink()
    target = tmp_path / "missing" / "colormap_explorer.html"
    main.__globals__["OUT"] = target
    before_entries = set(tmp_path.rglob("*"))
    assert checked() != 0
    assert not target.exists()
    assert set(tmp_path.rglob("*")) == before_entries


# ── demo library + defaults ────────────────────────────────────────────────
def test_demo_library_is_sixteen_without_radial_and_with_four_new_grammars() -> (
    None
):
    builder = runpy.run_path(str(_BUILDER))
    lib = [k for k, _ in builder["DEMO_LIBRARY"]]
    assert lib == _DEMO_KEYS
    assert len(lib) == 16
    assert "radial" not in lib
    for new in ("ridgeline", "quiver", "polar_heat", "waffle"):
        assert new in lib
    assert builder["DEFAULT_9"] == _DEFAULT_9
    assert len(builder["DEFAULT_9"]) == 9
    assert "radial" not in builder["DEFAULT_9"]
    payload = _payload_from_html()
    assert [d["key"] for d in payload["library"]] == _DEMO_KEYS
    assert payload["defaults"]["9"] == _DEFAULT_9
    html = _EXPLORER.read_text(encoding="utf-8")
    assert "Radial" not in html
    assert "radialSVG" not in html


def test_colormap_demo_picker_replaces_last_full_slot() -> None:
    """Demo selection is capped to the layout and swaps the newest slot."""
    html = _EXPLORER.read_text(encoding="utf-8")

    assert _REPLACE_LAST_HANDLER in html
    assert "var k=b.dataset.demoPick,idx=state.demos.indexOf(k)" not in html
    assert "if(wasDefault)" not in html

    demos = _DEFAULT_9[:4]
    new_key = "waffle"
    if new_key in demos:
        demos.remove(new_key)
    elif len(demos) >= 4:
        demos[-1] = new_key
    else:
        demos.append(new_key)
    assert demos == ["heatmap", "contours", "streamlines", "waffle"]

    demos.remove("contours")
    assert demos == ["heatmap", "streamlines", "waffle"]


# ── layout / style literals ────────────────────────────────────────────────
def test_root_wrapper_is_wide_yue_with_unique_id() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    assert '<div id="dm-cmap-exp" class="yue">' in html
    assert "<style" not in html
    # distinct id from the categorical explorer so both can coexist
    assert "dm-cat-exp" not in html


def test_layout_uses_design_tokens_and_bounded_grid() -> None:
    css = _colormap_css()
    assert "grid-template-columns:minmax(10rem,10.5rem) minmax(0,1fr)" in css
    assert (
        "#dm-cat-exp,#dm-cmap-exp {width:100%;max-width:100%;container-type:inline-size;"
        in css
    )
    assert "gap:var(--dm-space-4,16px)" in css
    assert "padding-right:4px" in css
    assert "flex-wrap:wrap;row-gap:8px;" in css
    assert "grid-template-columns:minmax(10.5rem,12rem)" not in css
    assert (
        "#dm-cat-exp .demo-tools .demo-field,#dm-cmap-exp .demo-tools .demo-field {flex:1 1 100%;min-width:0;align-items:flex-start;}"
        in css
    )
    assert (
        "#dm-cat-exp .demo-picker,#dm-cmap-exp .demo-picker {display:flex;align-items:center;gap:6px;flex-wrap:wrap;row-gap:6px;min-width:0;}"
        in css
    )
    for token in (
        "var(--dm-bg-page",
        "var(--dm-bg-panel",
        "var(--dm-border-faint",
        "var(--dm-accent-11",
        "var(--dm-radius-4",
        "var(--dm-f-sys",
        "var(--dm-f-mono",
        "var(--dm-space-5",
        "var(--dm-gray-12",
    ):
        assert token in css, token
    # POC-only bespoke tokens must be re-homed onto real --dm-* tokens
    assert "--dm-bg-subtle" not in css
    assert "var(--dm-line" not in css
    assert "calc(100cqw - 32px)" in css
    assert "calc(100vw - 32px)" not in css


def test_no_raw_hex_in_css_block_outside_fallbacks() -> None:
    css = _colormap_css()
    for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", css):
        prev = css[m.start() - 1 : m.start()]
        assert prev == ",", (
            f"raw hex {m.group(0)} not a var() fallback: "
            f"...{css[max(0, m.start() - 24) : m.start()]}"
        )


def test_removed_colorbars_frames_and_poc_chrome() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    css = _colormap_css()
    # item 3 / item 4: no demo-embedded colorbar strip, no inner frame rect
    assert "colorbar" not in html.lower()
    assert 'rx="5" fill="none"' not in html  # POC streamlines/isolines frame
    # dropped POC scaffolding
    for banned in (
        "pv-btn",
        "POC variants",
        "theme-btn",
        "featured-demo",
        "compare-wrap",
        "data-feature",
        "V1 &mdash; Grid",
    ):
        assert banned not in html, banned
    # centered demo content, not top-left anchored (item 2)
    assert "align-items:center;justify-content:center;" in css


def test_retina_gradient_backgrounds_are_non_repeating_images() -> None:
    """Retina guard: gradient shorthands must not reset repeat/size."""
    html = _EXPLORER.read_text(encoding="utf-8")
    css = _colormap_css()
    assert "#dm-cmap-exp .grad,#dm-cmap-exp .ri .mini" in css
    assert "background-repeat:no-repeat;background-size:100% 100%;" in css
    assert "g.style.backgroundImage=gradientCSS();" in html
    assert 'style="background-image:linear-gradient(90deg,' in html
    assert 'style="background:linear-gradient(90deg,' not in html


def test_rail_mini_strips_are_square_non_clipping_rectangles() -> None:
    css = _colormap_css()
    m = re.search(
        r"#dm-cat-exp \.ri \.mini,#dm-cmap-exp \.ri \.mini\{([^}]*)\}", css
    )
    assert m, "shared rail mini CSS rule missing"
    mini_rule = m.group(1)
    assert "flex:0 0 40px" in mini_rule
    assert "height:12px" in mini_rule
    assert "border-radius" not in mini_rule
    assert "overflow" not in mini_rule
    assert "border" not in mini_rule
    assert "box-shadow" not in mini_rule
    assert (
        "#dm-cmap-exp .grad {position:relative;height:44px;border-radius:"
        in css
    )


def test_field_demo_payload_ships_heatmap_and_contour_parameters_not_precomputed_grid() -> (
    None
):
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    field = payload["field"]
    assert set(field) == {"base", "bumps"}
    assert field["base"] == {"x": 0.32, "y": -0.2}
    assert field["bumps"] == [
        {"cx": 0.3, "cy": 0.34, "sx": 0.22, "sy": 0.26, "amp": 1.1},
        {"cx": 0.72, "cy": 0.68, "sx": 0.2, "sy": 0.24, "amp": 0.82},
    ]
    contour_field = payload["contour_field"]
    assert set(contour_field) == {"saddle", "ridge", "waves"}
    assert contour_field != field


def test_demo_geometry_uses_canvas_for_continuous_fields_and_svg_for_strokes() -> (
    None
):
    html = _EXPLORER.read_text(encoding="utf-8")
    css = _colormap_css()
    assert (
        'function openStroke(label){return \'<svg class="demo-svg" viewBox="0 0 '
        "'+VW+' '+VH+'\" preserveAspectRatio=\"xMidYMid meet\""
    ) in html
    assert "var VW=160,VH=100;" in html
    assert (
        "#dm-cmap-exp canvas.demo-canvas {display:block;width:100%;height:100%;"
        in css
    )
    assert "#dm-cmap-exp .demo-grid.gs canvas.demo-canvas" in css
    for demo in _CANVAS_DEMOS:
        assert (
            "data-canvas-demo=\"'+esc(t)+'\"" in html
            or f'data-canvas-demo="{demo}"' in html
        )
    assert "function renderCanvasDemo(cv,t)" in html
    assert "function canvasShell(t)" in html
    assert "function heatSVG()" not in html
    assert "function contoursSVG()" not in html
    assert "function terrainSVG()" not in html
    assert "function signalSVG()" not in html
    assert "SPAD" not in html
    assert "SIW" not in html
    assert "SIH" not in html
    for token in (
        "function fx(c){return c/(cols-1)*VW;}function fy(r){return r/(rows-1)*VH;}",
        "cx=\"'+(p[2]*VW).toFixed(2)+'\" cy=\"'+(p[3]*VH).toFixed(2)+'\"",
        "parts.map(function(p){return [p[0]*VW,(1-p[1])*VH];})",
        'function barsSVG(){var n=28,gap=1,colW=(VW-gap*(n-1))/n,s=openStroke("bars"),vals=[];',
        "function histValue(t)",
        "function cylinderFlowVec(x,y)",
        "function catmullRomPath(pts)",
        "function catmullRomSegmentPath(pts,i)",
        "function contourEdgeShade(vals,i,x,y,fw,fh,lo,span,bands)",
        "function polarHeat(cv,lut)",
        "function ridgelineSVG(){var rows=11,rowGap=8.6,peakH=rowGap*1.6",
        "function quiverSVG()",
        "function waffleSVG()",
        'function networkSVG(){var s=openStroke("network"),rows=5,cols=8',
    ):
        assert token in html, token
    assert 'preserveAspectRatio="none" aria-label="\'+esc(label)+\'">' in html
    assert (
        "var CANVAS_DEMOS={heatmap:1,contours:1,terrain:1,signal:1,polar_heat:1}"
        in html
    )


def test_canvas_backing_store_is_dpr_aware_and_pixel_capped() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    assert "MAX_CANVAS_PIXELS=1600000" in html
    assert "Math.min(Math.max(window.devicePixelRatio||1,1),2)" in html
    assert "Math.sqrt(MAX_CANVAS_PIXELS/(cw*ch))" in html
    assert "w=Math.max(1,Math.round(cw*scale))" in html
    assert "h=Math.max(1,Math.round(ch*scale))" in html
    assert "if(cv.width!==w)cv.width=w" in html
    assert "if(cv.height!==h)cv.height=h" in html
    assert "watchCanvasDpr()" in html


def test_polar_heat_uses_per_pixel_field_without_sector_bins() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    assert "function polarHeatFieldRange()" in html
    assert "polarValue(rr,th)" in html
    assert 'var cyclic=map().kind==="cyclic"' in html
    assert "if(cyclic)" in html
    assert "ti=scaledT(v,sc,p/4)" in html
    assert "rBins=9" not in html
    assert "aBins=36" not in html
    assert "Math.floor(rr*rBins)" not in html
    assert "Math.floor(th*aBins)" not in html


def test_svg_curve_demos_publish_cubic_path_stats() -> None:
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    stats = payload["svg_path_stats"]
    assert stats["isolines"]["c_segments"] > 0
    assert stats["isolines"]["l_segments"] == 0
    assert (
        stats["streamlines"]["c_segments"] >= stats["streamlines"]["paths"] * 30
    )
    assert stats["streamlines"]["l_segments"] == 0
    assert stats["lines"] == {"paths": 6, "c_segments": 1200, "l_segments": 0}
    assert stats["ridgeline"] == {
        "paths": 11,
        "c_segments": 1540,
        "l_segments": 22,
    }


def test_svg_curve_quality_sampling_and_turning_angle_gate() -> None:
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    quality = payload["svg_curve_quality"]

    assert quality["isolines"]["grid_cells"] == [220, 140]
    assert quality["isolines"]["simplify_epsilon"] == 0.15
    assert quality["isolines"]["angle_gate_degrees"] == 20.0
    assert quality["streamlines"]["arc_spacing"] <= 1.7
    assert quality["lines"]["samples_per_series"] >= 161
    assert quality["ridgeline"]["samples_per_profile"] >= 141

    for demo in ("isolines", "streamlines", "lines", "ridgeline"):
        angles = quality[demo]["turning_angle_degrees"]
        assert angles["max"] < quality[demo]["angle_gate_degrees"], demo


def test_red_demo_spectrum_coverage_self_check_hits_both_ends() -> None:
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    rows = payload["demo_coverage"]
    assert [r["demo"] for r in rows] == _DEMO_KEYS
    assert len(rows) == 16
    offenders = [r for r in rows if not (r["t0_hit"] and r["t1_hit"])]
    assert not offenders, offenders
    assert min(r["distinct"] for r in rows) >= 2
    assert [r["demo"] for r in rows if r["demo"] == "radial"] == []


def test_streamlines_use_cubic_smooth_paths_without_polyline_corners() -> None:
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    stats = payload["streamline_path_stats"]
    assert 26 <= stats["paths"] <= 30
    assert stats["c_segments"] >= stats["paths"] * 30
    assert stats["l_segments"] == 0
    html = _EXPLORER.read_text(encoding="utf-8")
    assert "CYL={cx:.35,cy:.5,r:.18,aspect:1.6}" in html
    assert "for(var r=0;r<28;r++)" in html
    assert "catmullRomPath(pts)" in html
    assert "catmullRomSegmentPath(L.pts,j)" in html
    assert "' C '" in html
    assert 'stroke-linecap="round"' in html
    assert 'd+=(it?"L":"M")' not in html
    assert 'stroke-linejoin="round"' in html


def test_quiver_geometry_stops_shaft_at_arrowhead_base() -> None:
    builder = runpy.run_path(str(_BUILDER))
    payload = builder["build_payload"]()
    stats = payload["quiver_geometry_stats"]
    assert stats == {
        "arrows": 70,
        "rows": 7,
        "cols": 10,
        "min_length": 7.2,
        "max_length": 13.8,
        "head_length": 4.6,
        "head_half_width": 1.77,
        "overshoots": 0,
    }
    assert builder["_quiver_geometry_stats"]()["overshoots"] == 0
    html = _EXPLORER.read_text(encoding="utf-8")
    assert "xBase=tipX-ux*headLen" in html
    assert 'stroke-linecap="round"' in html


def test_kept_controls_present_and_removed_controls_absent() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    for token in (
        'data-tgl="rev"',
        'data-tgl="bw"',
        'data-layout="4"',
        'data-layout="6"',
        'data-layout="9"',
        "copy the colormap name",
    ):
        assert token in html, token
    for banned in (
        'data-tgl="profile"',
        'data-ends="refined"',
        'data-ends="original"',
        'class="lstar"',
        "L* profile",
        "Refined",
        "Original",
        "profile-host",
        "lstarSVG",
    ):
        assert banned not in html, banned
    # Levels 5..50 + infinity, chip vocabulary
    assert '"5","10","15","20","25","30","35","40","45","50","∞"' in html


def test_chip_vocabulary_present() -> None:
    payload = runpy.run_path(str(_BUILDER))["build_payload"]()
    labels = set()
    for cmap in payload["maps"].values():
        for variant in cmap["variants"].values():
            for chip in variant["chips"]:
                labels.add(chip["label"])
    for expected in (
        "Uniform",
        "B&W",
        "CVD",
        "Balanced",
        "Center",
        "Seamless",
        "Isoluminant",
    ):
        assert expected in labels, expected
    assert "Ends" not in labels


def test_zero_hangul() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    assert not re.search(r"[가-힣]", html)


# ── colormaps.md graduation ────────────────────────────────────────────────
def test_colormaps_md_embeds_real_static_path() -> None:
    md = (_REPO / "docs" / "color_system" / "colormaps.md").read_text(
        encoding="utf-8"
    )
    assert ":file: ../_static/colormap_explorer.html" in md
    assert "images/colormap_explorer.html" not in md
    # verified taxonomy in the catalog table
    assert "20 |" in md and "9 |" in md and "11 |" in md and "3 |" in md
    assert "Topographic" not in md  # stale row removed
