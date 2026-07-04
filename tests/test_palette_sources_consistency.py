"""Regression: the three categorical-palette sources must agree hex-for-hex.

The 24 curated palettes live in three places that can drift independently:

  · ``dm_palettes_gen.json``            — the CIELAB colour SSOT (generator out)
  · ``dc_palettes.json``                — the package registry (get_palette out)
  · ``categorical_explorer_data.js``    — the docs explorer widget's data

``build_dc_palettes.py``'s ``NAME`` map is the generator→public rename boundary.
If it drifts (e.g. reverts to the old PascalCase keys) or the widget data goes
stale (as ``teal_accent`` / ``coral_accent`` once did), users get one set of
colours from the API and see a different set in the docs. This test pins the
three sources together so that class of drift fails CI.
"""

from __future__ import annotations

import importlib.util
import json
import re
import runpy
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "docs" / "_static" / "scripts"
_PKG_JSON = (
    _REPO / "src" / "dartwork_mpl" / "asset" / "color" / "dc_palettes.json"
)


def _name_map() -> dict[str, str]:
    """The generator-key -> public-name map, imported from build_dc_palettes."""
    spec = importlib.util.spec_from_file_location(
        "_bdc_namemap", _SCRIPTS / "build_dc_palettes.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.NAME)


def _pkg_hex() -> dict[str, list[str]]:
    pkg = json.loads(_PKG_JSON.read_text(encoding="utf-8"))
    return {k: [h.upper() for _, h in v] for k, v in pkg.items()}


def _gen_hex(name_map: dict[str, str]) -> dict[str, list[str]]:
    gen = json.loads(
        (_SCRIPTS / "dm_palettes_gen.json").read_text(encoding="utf-8")
    )
    return {
        name_map[k]: [c.lstrip("#").upper() for c in gen[k]["colors"]]
        for k in name_map
    }


def _data_js_hex(names: list[str]) -> dict[str, list[str]]:
    js = (_SCRIPTS / "categorical_explorer_data.js").read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    for name in names:
        m = re.search(rf"\b{name}:\s*\{{", js)
        if not m:
            continue
        cm = re.search(r"cols:\[([^\]]*)\]", js[m.end() : m.end() + 1500])
        if cm:
            hexes = re.findall(r"#([0-9a-fA-F]{6})", cm.group(1))
            if len(hexes) == 8:
                out[name] = [h.upper() for h in hexes]
    return out


def test_palette_sources_agree_hex_for_hex() -> None:
    """gen SSOT, package registry, and widget data.js agree for all 24 palettes."""
    name_map = _name_map()
    curated = list(name_map.values())
    pkg, gen = _pkg_hex(), _gen_hex(name_map)
    data = _data_js_hex(curated)

    assert len(curated) == 24
    assert sorted(data) == sorted(curated), (
        "widget data.js missing curated palettes"
    )

    mismatches = {
        name: {
            "pkg": pkg.get(name),
            "gen": gen.get(name),
            "data": data.get(name),
        }
        for name in curated
        if not (pkg.get(name) == gen.get(name) == data.get(name))
    }
    assert not mismatches, f"palette source drift: {mismatches}"


def test_get_palette_resolves_every_curated_name() -> None:
    """Every curated public name resolves through the loader to dc.<name>0..7.

    Three names ("teal"/"indigo"/"gray") also collide with a v5 family:
    v5 registers their non-colliding steps 8-9 under the same bare name
    (spec §11), so the loader's dc.<name>N scan technically finds 10
    tokens for them. But Task 11's version-aware length cap
    (``helpers/colors.py::_palette_color_names``) keeps ``get_palette``
    at the legacy 8-step ramp by default — mixing legacy steps 0-7 with
    v5 steps 8-9 would be an incoherent ramp (two different generators)
    — and only widens to the full 10 once
    ``dartwork_mpl.set_palette_version(5)`` remaps 0-7 to v5 too, making
    all 10 steps share one generator."""
    import dartwork_mpl as dm
    from dartwork_mpl.colors._compat_v4 import set_palette_version

    v5_extended = {"teal", "indigo", "gray"}
    try:
        for name in _name_map().values():
            cols = dm.get_palette(name)
            assert len(cols) == 8, f"{name} did not resolve to 8 colors"
            assert cols[0] == f"dc.{name}0", (
                f"{name} slot 0 mismatch: {cols[0]}"
            )

        # Opt-in v5 remap widens exactly the three colliding names to 10.
        set_palette_version(5)
        for name in _name_map().values():
            cols = dm.get_palette(name)
            expected = 10 if name in v5_extended else 8
            assert len(cols) == expected, (
                f"{name} did not resolve to {expected} colors after "
                f"set_palette_version(5)"
            )
    finally:
        set_palette_version(4)


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(
        f"_widget_{name}", _SCRIPTS / f"{name}.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    ("builder", "artifact", "suffix"),
    [
        # Mirror each script's own writer exactly: the explorer writes
        # ``build()`` verbatim; the showcase appends one newline.
        ("build_categorical_explorer", "categorical_explorer.html", ""),
        ("build_showcase", "palette_showcase.html", "\n"),
    ],
)
def test_built_widgets_match_their_builders(
    builder: str, artifact: str, suffix: str
) -> None:
    """Committed widget HTML == rebuilding it from source, byte-for-byte.

    Replaces the old backward-looking ``_STALE_DC`` regex (which could
    only catch names renamed *before* it was written): a byte-compare
    catches hand edits, stale regens after a data.js/builder change,
    and the *next* rename wave alike. Both builders are deterministic
    (no timestamps/randomness) — verified byte-identical at the time
    this guard was added.
    """
    mod = _load_script(builder)
    built = mod.build() + suffix
    committed = (_REPO / "docs" / "_static" / artifact).read_text(
        encoding="utf-8"
    )
    assert built == committed, (
        f"{artifact} is stale — rerun docs/_static/scripts/{builder}.py"
    )


def test_widget_verification_stats_match_gen_json() -> None:
    """The ``bw:``/``cvd:`` readouts baked into the explorer data must
    equal the verification stats in ``dm_palettes_gen.json`` (the HTML
    byte-compare cannot see this — data.js is the input, so a stale
    stat there reproduces byte-identically)."""
    name_map = _name_map()
    gen = json.loads(
        (_SCRIPTS / "dm_palettes_gen.json").read_text(encoding="utf-8")
    )
    js = (_SCRIPTS / "categorical_explorer_data.js").read_text(encoding="utf-8")
    checked = 0
    for gen_key, public in name_map.items():
        verify = gen[gen_key].get("verify")
        if not verify:
            continue
        m = re.search(rf"\b{public}:\s*\{{", js)
        assert m, f"{public} missing from explorer data"
        block = js[m.end() : m.end() + 2000]
        bw = re.search(r'bw:"min ΔL\* ([0-9.]+)"', block)
        cvd = re.search(r'cvd:"d([0-9.]+) / p([0-9.]+) / t([0-9.]+)"', block)
        assert bw and cvd, f"{public}: bw/cvd readouts not found"
        assert float(bw.group(1)) == verify["bw_min_dLstar"], public
        assert (
            float(cvd.group(1)),
            float(cvd.group(2)),
            float(cvd.group(3)),
        ) == (verify["deuter"], verify["protan"], verify["tritan"]), public
        checked += 1
    assert checked >= 20, f"only {checked} palettes had stats — parser broken?"


def test_gen_palettes_reproduces_committed_ssot() -> None:
    """Running ``gen_palettes.py`` must reproduce the committed
    ``dm_palettes_gen.json`` — the CIELAB colour SSOT that
    ``build_dc_palettes.py`` consumes. Without this guard, editing a hue in
    ``gen_palettes.py`` and forgetting to copy the ``/tmp`` output onto the
    tracked file would silently leave the whole gen -> package -> widget chain
    on stale colours while every other test still passed."""
    pytest.importorskip("colorspacious")
    committed = json.loads(
        (_SCRIPTS / "dm_palettes_gen.json").read_text("utf-8")
    )
    # The generator computes its result into a module-level ``res`` dict (and
    # writes it to /tmp as a side effect). Exec it and compare that dict.
    ns = runpy.run_path(str(_SCRIPTS / "gen_palettes.py"))
    regenerated = json.loads(json.dumps(ns["res"]))
    assert regenerated == committed, (
        "gen_palettes.py output drifted from the committed dm_palettes_gen.json"
    )
