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
from pathlib import Path

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
    """Every curated public name resolves through the loader to dc.<name>0..7."""
    import dartwork_mpl as dm

    for name in _name_map().values():
        cols = dm.get_palette(name)
        assert len(cols) == 8, f"{name} did not resolve to 8 colors"
        assert cols[0] == f"dc.{name}0", f"{name} slot 0 mismatch: {cols[0]}"


_STALE_DC = re.compile(
    r"dc\.(?:focus|focuswarm|muted|tealseq|indigoseq|coralseq|tealindigo|"
    r"warmcool|blueorange|tealcoral|grayseq|warmgray|coolgray|tealamber)\d?"
)


def test_built_widgets_have_no_renamed_away_names() -> None:
    """Generated palette widgets must not reference the old (pre-rename) dc.* names.

    ``palette_showcase.html`` and ``categorical_explorer.html`` are committed,
    generator-produced artifacts. If their generator's name mapping drifts, they
    would label swatches ``dc.focus0`` / ``dc.muted0`` etc. — names the package
    no longer registers. This pins the generated output to the current names.
    """
    widgets = [
        _REPO / "docs" / "_static" / "palette_showcase.html",
        _REPO / "docs" / "_static" / "categorical_explorer.html",
    ]
    offenders = {}
    for widget in widgets:
        if not widget.exists():
            continue
        hits = sorted(
            {m.group(0) for m in _STALE_DC.finditer(widget.read_text())}
        )
        if hits:
            offenders[widget.name] = hits
    assert not offenders, f"stale palette names in built widgets: {offenders}"
