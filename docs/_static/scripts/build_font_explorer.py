#!/usr/bin/env python3
"""Build the interactive font explorer fragment.

The fragment is embedded by ``docs/fonts/index.md`` via MyST
``{raw} html :file:``. It is generated from the bundled matplotlib font
registry, and validates every emitted webfont face against
``docs/_static/font-face.css``.

Regenerate::

    python3 docs/_static/scripts/build_font_explorer.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from fontTools.ttLib import TTFont
from matplotlib import font_manager

from dartwork_mpl import font

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "font_explorer.html"
FONT_FACE_CSS = SCRIPT_DIR.parent / "font-face.css"
STATIC_FONT_DIR = SCRIPT_DIR.parent / "fonts"

MONO_FAMILIES = [
    "IBM Plex Mono",
    "JetBrains Mono",
    "Roboto Mono",
    "Source Code Pro",
]
DEFAULT_FAMILY = "Roboto"
DEFAULT_WEIGHT = 400
BASE_WEIGHT = 300
HANGUL_SAMPLE = "한글 데이터 축 값"

WEIGHT_ORDER = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}

DEMO_LIBRARY = [
    ("title_axes", "Title & axes"),
    ("tick_numerals", "Tick numerals"),
    ("value_labels", "Value labels"),
    ("legend", "Legend"),
    ("annotation", "Annotation"),
    ("weights_ladder", "Weights ladder"),
    ("size_ladder", "Size ladder"),
    ("paragraph", "Paragraph"),
    ("numerals_confusables", "Numerals & confusables"),
    ("korean", "Korean"),
    ("code_mono", "Code / mono"),
    ("caps_tracking", "Caps & tracking"),
]
DEFAULT_9 = [
    "title_axes",
    "tick_numerals",
    "value_labels",
    "legend",
    "annotation",
    "weights_ladder",
    "size_ladder",
    "paragraph",
    "numerals_confusables",
]
DEFAULT_6 = DEFAULT_9[:6]
DEFAULT_4 = DEFAULT_9[:4]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _declared_faces() -> set[str]:
    css = FONT_FACE_CSS.read_text(encoding="utf-8")
    return set(re.findall(r"font-family: '([^']+)'", css))


def _font_files_by_face() -> dict[str, str]:
    css = FONT_FACE_CSS.read_text(encoding="utf-8")
    return dict(
        re.findall(
            r"font-family: '([^']+)';\s*src: url\('fonts/([^']+)'\)",
            css,
            flags=re.S,
        )
    )


def _entry_records() -> list[font_manager.FontEntry]:
    font.ensure_loaded()
    bundle_dir = font.get_font_dir().resolve()
    records = []
    for entry in font_manager.fontManager.ttflist:
        try:
            path = Path(entry.fname).resolve()
            if not path.is_relative_to(bundle_dir):
                continue
        except (OSError, ValueError):
            continue
        records.append(entry)
    return records


def _weight_label(stem: str) -> str:
    suffix = stem.split("-", 1)[1] if "-" in stem else "Regular"
    suffix = suffix.removesuffix("Italic")
    suffix = re.sub(r"^\d+", "", suffix)
    if suffix in {"", "Italic"}:
        return "Regular"
    return suffix


def _weight_sort_key(entry: dict) -> tuple[int, int, str]:
    label_rank = WEIGHT_ORDER.get(entry["label"], int(entry["weight"]))
    return (label_rank, int(entry["weight"]), entry["face"])


def _closest_regular(entries: list[dict]) -> dict:
    regular = [entry for entry in entries if entry["weight"] == DEFAULT_WEIGHT]
    if regular:
        return sorted(regular, key=_weight_sort_key)[0]
    return min(entries, key=lambda item: abs(item["weight"] - DEFAULT_WEIGHT))


def _cmap_codepoints(path: Path) -> set[int]:
    ttfont = TTFont(str(path), lazy=True)
    codepoints: set[int] = set()
    try:
        for table in ttfont["cmap"].tables:
            if table.isUnicode():
                codepoints.update(table.cmap.keys())
    finally:
        ttfont.close()
    return codepoints


def _has_hangul(path: Path) -> bool:
    codepoints = _cmap_codepoints(path)
    return all(ord(char) in codepoints for char in HANGUL_SAMPLE if char != " ")


def _rail_sample(family: str) -> str:
    if family == "Noto Sans Math":
        return "∑π"
    if family == "Noto Sans Symbols":
        return "→±"
    if family == "Noto Sans Symbols 2":
        return "⚠★"
    if family in MONO_FAMILIES:
        return "0O1l"
    if family in {"Paperlogy", "Pretendard", "Noto Sans CJK KR"}:
        return "한글"
    return "Aa"


def _family_note(family: str, mono: bool, hangul: bool) -> str:
    if family == "Roboto":
        return "Default chart body face with a quiet, neutral voice."
    if family == "Inter Display":
        return "Display cut for large chart titles and poster-scale numbers."
    if family == "Noto Sans Math":
        return "Math and operator fallback for scientific notation."
    if family.startswith("Noto Sans Symbols"):
        return "Symbol fallback face for arrows, marks, and dingbats."
    if hangul:
        return "Bundled Hangul coverage for Korean and mixed-language figures."
    if mono:
        return "Fixed-width family for code, timestamps, and tabular labels."
    return "Bundled sans-serif family for publication chart typography."


def _fw_offset(weight: int) -> int | float:
    value = (weight - BASE_WEIGHT) / 100
    if float(value).is_integer():
        return int(value)
    return round(value, 2)


def _build_family_inventory() -> dict:
    declared_faces = _declared_faces()
    face_files = _font_files_by_face()
    entries_by_family: dict[str, list[font_manager.FontEntry]] = defaultdict(
        list
    )
    for entry in _entry_records():
        entries_by_family[entry.name].append(entry)

    registered = font.list_registered()
    if set(entries_by_family) != set(registered):
        missing = set(registered) - set(entries_by_family)
        extra = set(entries_by_family) - set(registered)
        raise AssertionError(
            f"registered font inventory mismatch; missing={missing}, extra={extra}"
        )

    families: dict[str, dict] = {}
    for family in registered:
        usable: dict[tuple[str, int, str], dict] = {}
        for entry in entries_by_family[family]:
            # Noto Sans registers Condensed/SemiCondensed files as the same
            # matplotlib family. The explorer is one chip per family name, so
            # the normal-width face is the representative for that family.
            if family == "Noto Sans" and entry.stretch != "normal":
                continue
            path = Path(entry.fname)
            stem = path.stem
            label = _weight_label(stem)
            face = f"dm-{stem}"
            style = str(entry.style)
            key = (label, int(entry.weight), style)
            usable[key] = {
                "label": label,
                "weight": int(entry.weight),
                "style": style,
                "face": face,
                "file": path.name,
            }

        normal_by_weight: dict[tuple[str, int], dict] = {}
        italic_by_weight: dict[tuple[str, int], dict] = {}
        for (label, weight, style), item in usable.items():
            target = italic_by_weight if style == "italic" else normal_by_weight
            target[(label, weight)] = item

        weights: list[dict] = []
        for key, item in normal_by_weight.items():
            italic = italic_by_weight.get(key)
            face = item["face"]
            if face not in declared_faces:
                raise AssertionError(f"missing @font-face for {family}: {face}")
            if (
                face_files.get(face)
                and not (STATIC_FONT_DIR / face_files[face]).exists()
            ):
                raise AssertionError(f"@font-face file missing for {face}")
            italic_face = italic["face"] if italic else None
            if italic_face and italic_face not in declared_faces:
                raise AssertionError(
                    f"missing italic @font-face for {family}: {italic_face}"
                )
            weights.append(
                {
                    "label": item["label"],
                    "weight": item["weight"],
                    "offset": _fw_offset(item["weight"]),
                    "face": face,
                    "italic_face": italic_face,
                    "file": item["file"],
                }
            )

        weights = sorted(weights, key=_weight_sort_key)
        if not weights:
            raise AssertionError(
                f"no upright normal-width weights for {family}"
            )

        regular = _closest_regular(weights)
        hangul_path = font.get_font_dir() / regular["file"]
        mono = family in MONO_FAMILIES
        families[family] = {
            "name": family,
            "slug": _slug(family),
            "group": "Mono" if mono else "Sans",
            "mono": mono,
            "hangul": _has_hangul(hangul_path),
            "italic": any(entry.get("italic_face") for entry in weights),
            "default_weight": DEFAULT_WEIGHT,
            "regular_face": regular["face"],
            "rail_sample": _rail_sample(family),
            "note": _family_note(family, mono, _has_hangul(hangul_path)),
            "weights": weights,
        }

    return families


def _ordered_families(families: dict[str, dict]) -> list[str]:
    sans = sorted(
        name for name, item in families.items() if item["group"] == "Sans"
    )
    mono = [name for name in MONO_FAMILIES if name in families]
    if DEFAULT_FAMILY in sans:
        sans.remove(DEFAULT_FAMILY)
        sans.insert(0, DEFAULT_FAMILY)
    return sans + mono


def _font_counts() -> dict[str, int]:
    font_dir = font.get_font_dir()
    font_files = [
        path
        for path in font_dir.iterdir()
        if path.suffix.lower() in {".ttf", ".otf"}
    ]
    return {
        "files": len(font_files),
        "file_groups": len({path.stem.split("-")[0] for path in font_files}),
        "families": len(font.list_registered()),
    }


def build_payload() -> dict:
    families = _build_family_inventory()
    order = _ordered_families(families)
    groups = [
        ["Sans", [name for name in order if families[name]["group"] == "Sans"]],
        ["Mono", [name for name in order if families[name]["group"] == "Mono"]],
    ]
    return {
        "families": families,
        "order": order,
        "groups": groups,
        "library": [{"key": key, "name": name} for key, name in DEMO_LIBRARY],
        "defaults": {"4": DEFAULT_4, "6": DEFAULT_6, "9": DEFAULT_9},
        "counts": _font_counts(),
    }


def build_fragment() -> str:
    payload = build_payload()
    return TEMPLATE.replace(
        "__PAYLOAD__",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def main() -> None:
    html = build_fragment()
    OUT.write_text(html, encoding="utf-8")
    payload = build_payload()
    print(f"wrote {OUT}")
    print(f"fragment bytes: {OUT.stat().st_size}")
    print(
        "font counts: "
        f"{payload['counts']['files']} files, "
        f"{payload['counts']['file_groups']} groups, "
        f"{payload['counts']['families']} families"
    )


TEMPLATE = r"""<!-- GENERATED FILE - do not edit by hand.
     Source: docs/_static/scripts/build_font_explorer.py
     Data:   dartwork_mpl.font.list_registered() + matplotlib font_manager
     Regenerate: python3 docs/_static/scripts/build_font_explorer.py -->
<div id="dm-font-exp" class="yue">
<div class="md"><div class="rail" id="fx-rail"></div><div class="detail" id="fx-detail"></div></div>
<script>(function(){
var D=__PAYLOAD__;
var FONTS=D.families,GROUPS=D.groups,DEMOS=D.library,DEFAULT={4:D.defaults["4"],6:D.defaults["6"],9:D.defaults["9"]};
var state={family:D.order[0],weight:0,size:0,italic:false,layout:9,demos:DEFAULT[9].slice()};
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function fam(){return FONTS[state.family];}
function weights(){return fam().weights;}
function defaultWeightIndex(f){for(var i=0;i<f.weights.length;i++)if(f.weights[i].weight===f.default_weight)return i;return 0;}
function wt(){var w=weights();if(state.weight>=w.length)state.weight=defaultWeightIndex(fam());return w[state.weight];}
function faceFor(w){return (state.italic&&w.italic_face)?w.italic_face:w.face;}
function fontStyle(w,extra){var size=12+state.size;return "--font-face:'"+faceFor(w)+"';--font-weight:"+w.weight+";--font-size:"+size+"px;"+(extra||"");}
function faceStyle(face){return "font-family:'"+face+"',var(--dm-f-sys,system-ui,sans-serif)";}
function fixedFontStyle(face,weight,extra){return "--font-face:'"+face+"';--font-weight:"+weight+";"+(extra||"");}
function cardStyle(w){return ' style="'+fontStyle(w)+'"';}
function signed(n){return n>0?"+"+n:String(n);}
function offsetExpr(v){return Number.isInteger(v)?String(v):String(v);}
function demoName(t){for(var i=0;i<DEMOS.length;i++)if(DEMOS[i].key===t)return DEMOS[i].name;return t;}
function rcLine(){return 'plt.rcParams["font.family"] = "'+state.family+'"';}
function codeText(){var w=wt();return ['import matplotlib.pyplot as plt','import dartwork_mpl as dm','', 'dm.style.use("scientific")',rcLine(),'ax.set_title("Quarterly revenue", fontsize=dm.fs('+state.size+'), fontweight=dm.fw('+offsetExpr(w.offset)+'))'].join("\n");}
function copy(txt,el){if(navigator.clipboard)navigator.clipboard.writeText(txt);toast(txt+" copied");if(el){el.classList.add("copied");setTimeout(function(){el.classList.remove("copied");},900);}}
function toast(msg){var el=document.getElementById("fx-toast");if(!el){el=document.createElement("div");el.id="fx-toast";el.className="dm-toast";document.body.appendChild(el);}el.textContent=msg;el.classList.add("show");clearTimeout(window._fontToast);window._fontToast=setTimeout(function(){el.classList.remove("show");},1100);}
function glyph(t){var c='viewBox="0 0 24 16" aria-hidden="true"';
  if(t==="title_axes")return '<svg '+c+'><path d="M4 13H21M4 13V3" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M7 9H18" stroke="currentColor" stroke-width="1.8"/><path d="M7 5H14" stroke="currentColor" stroke-width="1.4" opacity=".6"/></svg>';
  if(t==="tick_numerals")return '<svg '+c+'><path d="M3 12H21" stroke="currentColor"/><path d="M5 12V9M10 12V7M15 12V9M20 12V6" stroke="currentColor"/><text x="4" y="6" font-size="5" fill="currentColor">123</text></svg>';
  if(t==="value_labels")return '<svg '+c+'><rect x="5" y="7" width="3" height="6" fill="currentColor"/><rect x="11" y="4" width="3" height="9" fill="currentColor" opacity=".7"/><rect x="17" y="9" width="3" height="4" fill="currentColor" opacity=".55"/></svg>';
  if(t==="legend")return '<svg '+c+'><path d="M4 10 9 7 14 9 20 4" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="5" y="3" width="10" height="3" fill="currentColor" opacity=".25"/></svg>';
  if(t==="annotation")return '<svg '+c+'><path d="M3 12C8 4 15 14 21 5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M14 5 18 2" stroke="currentColor"/><circle cx="14" cy="5" r="1.6" fill="currentColor"/></svg>';
  if(t==="weights_ladder")return '<svg '+c+'><path d="M4 4H20M4 8H20M4 12H20" stroke="currentColor" stroke-width="1.8"/></svg>';
  if(t==="size_ladder")return '<svg '+c+'><text x="4" y="6" font-size="5" fill="currentColor">Aa</text><text x="10" y="11" font-size="10" fill="currentColor">Aa</text></svg>';
  if(t==="paragraph")return '<svg '+c+'><path d="M4 4H20M4 8H18M4 12H16" stroke="currentColor" stroke-width="1.4"/></svg>';
  if(t==="numerals_confusables")return '<svg '+c+'><text x="3" y="11" font-size="9" fill="currentColor">0O1l</text></svg>';
  if(t==="korean")return '<svg '+c+'><text x="3" y="11" font-size="8" fill="currentColor">한글</text></svg>';
  if(t==="code_mono")return '<svg '+c+'><path d="M7 4 4 8 7 12M17 4 20 8 17 12M10 12 14 4" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>';
  return '<svg '+c+'><text x="4" y="11" font-size="8" fill="currentColor">ABC</text></svg>';}
function visibleDemos(){return state.demos.slice(0,state.layout);}
function svgOpen(){return '<svg class="demo-svg font-svg" viewBox="0 0 160 100" preserveAspectRatio="none">';}
function axisFrame(){return '<path class="font-axis" d="M28 76H148M28 76V18"/><path class="font-gridline" d="M28 56H148M28 36H148"/>';}
var R={
  title_axes:function(){return svgOpen()+axisFrame()+'<text class="font-demo-text font-title" x="28" y="14">Quarterly revenue</text><text class="font-demo-text font-axis-label" x="88" y="94">Period</text><text class="font-demo-text font-axis-label" transform="translate(12 52) rotate(-90)">Revenue</text><text class="font-demo-text font-tick" x="28" y="88">Q1</text><text class="font-demo-text font-tick" x="67" y="88">Q2</text><text class="font-demo-text font-tick" x="106" y="88">Q3</text><text class="font-demo-text font-tick" x="140" y="88">Q4</text><path class="font-accent-stroke" d="M32 61 67 49 106 34 142 27"/></svg>';},
  tick_numerals:function(){var s=svgOpen()+axisFrame();for(var i=0;i<9;i++){var x=30+i*14;s+='<path class="font-tickmark" d="M'+x+' 76V80"/><text class="font-demo-text font-tick" x="'+(x-6)+'" y="91">'+(1000+i*125)+'</text>';}return s+'<text class="font-demo-text font-title" x="30" y="18">Dense numeric ticks</text></svg>';},
  value_labels:function(){var vals=[42,68,55,91,74],s=svgOpen()+axisFrame();for(var i=0;i<vals.length;i++){var h=vals[i]*.54,x=38+i*22,y=76-h;s+='<rect class="font-bar" x="'+x+'" y="'+y.toFixed(1)+'" width="13" height="'+h.toFixed(1)+'" rx="2"/><text class="font-demo-text font-value" x="'+(x+6.5)+'" y="'+(y-5).toFixed(1)+'">'+vals[i]+'</text>';}return s+'</svg>';},
  legend:function(){return svgOpen()+axisFrame()+'<path class="font-series-a" d="M32 62C58 42 74 58 98 35S126 43 144 24"/><path class="font-series-b" d="M32 70C58 66 78 38 102 54S130 55 144 38"/><rect class="font-legend-box" x="94" y="18" width="48" height="27" rx="3"/><path class="font-series-a" d="M100 27H115"/><path class="font-series-b" d="M100 37H115"/><text class="font-demo-text font-legend" x="119" y="30">Plan</text><text class="font-demo-text font-legend" x="119" y="40">Actual</text></svg>';},
  annotation:function(){return svgOpen()+axisFrame()+'<path class="font-series-a" d="M32 65C52 36 68 66 88 44S124 22 144 36"/><circle class="font-point" cx="106" cy="29" r="3"/><path class="font-callout-line" d="M106 29 121 16"/><text class="font-demo-text font-callout" x="84" y="15">Peak +18%</text></svg>';},
  paragraph:function(){return '<div class="font-copy font-demo-text">A caption has to stay readable beside data, labels, and legends. This specimen uses chart-length prose instead of a poster headline.</div>';},
  numerals_confusables:function(){return '<div class="font-bigrow font-demo-text">0O 1lI 3.1415 −+ ×</div>';},
  code_mono:function(){return '<pre class="font-codeblock font-demo-text">fig, ax = plt.subplots()\\nax.plot(x, y, lw=dm.lw(0))\\ndm.simple_layout(fig)</pre>';},
  caps_tracking:function(){return '<div class="font-caps-wrap font-demo-text"><span>OPERATING MARGIN</span><b>Q4 2026</b></div>';},
  korean:function(){if(fam().hangul)return '<div class="font-korean font-demo-text" data-hangul="1"><b>매출 추이</b><span>한글 축 레이블과 값 표시</span></div>';return '<div class="font-korean font-fallback-note" data-hangul="0"><b>No bundled Hangul in this face</b><span>Keep Pretendard, Paperlogy, or Noto Sans CJK KR in the fallback chain.</span></div>';},
  weights_ladder:function(){return '<div class="font-ladder">'+weights().map(function(w){return '<div class="font-ladder-row font-demo-text" style="'+fixedFontStyle(w.face,w.weight)+'"><span>'+esc(w.label)+'</span><b>Data labels '+w.weight+'</b></div>';}).join("")+'</div>';},
  size_ladder:function(){var rows=[];for(var i=-2;i<=4;i++){rows.push('<div class="font-size-row font-demo-text" style="'+fontStyle(wt(),'--font-size:'+(12+i)+'px')+'"><span>fs('+signed(i)+')</span><b>Small multiple label</b></div>');}return '<div class="font-size-ladder">'+rows.join("")+'</div>';}
};
function demoCard(t){var body=(R[t]||R.title_axes)();return '<div class="demo-card font-card" data-demo="'+esc(t)+'"><span class="demo-label">'+esc(demoName(t))+'</span><div class="demo-flex"'+cardStyle(wt())+'>'+body+'</div></div>';}
function demoGridHTML(){return '<div class="demo-grid layout-'+state.layout+'">'+visibleDemos().map(demoCard).join("")+'</div>';}
function capDemosToLayout(){if(state.demos.length>state.layout)state.demos=state.demos.slice(0,state.layout);}
function setLayout(n){state.layout=n;capDemosToLayout();renderDetail();}
function toggleDemo(k){capDemosToLayout();var idx=state.demos.indexOf(k);
  if(idx>=0)state.demos.splice(idx,1);else if(state.demos.length>=state.layout)state.demos.splice(state.demos.length-1,1,k);else state.demos.push(k);renderDetail();}
function demoToolsHTML(){var chips=DEMOS.map(function(d){return '<button class="demo-chip'+(state.demos.indexOf(d.key)>=0?" on":"")+'" type="button" data-demo-pick="'+esc(d.key)+'">'+glyph(d.key)+'<span>'+esc(d.name)+'</span></button>';}).join("");
  return '<div class="demo-tools"><span class="field demo-field"><span class="cl">Demos</span><span class="demo-picker">'+chips+'</span></span>'
    +'<span class="field"><span class="cl">Layout</span><span class="seg"><button type="button" data-layout="4" class="'+(state.layout===4?"on":"")+'">2×2</button><button type="button" data-layout="6" class="'+(state.layout===6?"on":"")+'">2×3</button><button type="button" data-layout="9" class="'+(state.layout===9?"on":"")+'">3×3</button></span></span></div>';}
function controlsHTML(){var f=fam(),ws=weights(),wchips=ws.map(function(w,i){return '<button type="button" data-weight="'+i+'" class="'+(i===state.weight?"on":"")+'">'+esc(w.label)+'<span>'+w.weight+'</span></button>';}).join("");
  var ital='<button class="tgl font-italic-toggle'+(state.italic?" on":"")+(f.italic?"":" font-disabled")+'" data-tgl="italic" type="button"'+(f.italic?"":' disabled')+'><span class="tgl-l">Italic</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>';
  var step='<span class="font-stepper"><button type="button" data-size-step="-1">−</button><b>dm.fs('+signed(state.size)+')</b><button type="button" data-size-step="1">+</button></span>';
  return '<span class="field font-weight-field"><span class="cl">Weight</span><span class="seg font-weight-seg">'+wchips+'</span></span><span class="field"><span class="cl">Size</span>'+step+'</span>'+ital;}
function codeHTML(){return '<button class="code font-code-chip" type="button" data-copy-code><pre>'+esc(codeText())+'</pre></button>';}
function metaHTML(){var f=fam(),w=wt();return '<div class="meta"><div><span class="m-l">Inventory</span> '+f.weights.length+' upright weights'+(f.italic?", italic cuts available":", no italic cuts")+(f.hangul?", Hangul coverage detected":", Latin/symbol coverage only")+'</div><div><span class="m-l">Current face</span> '+esc(faceFor(w))+' · fontweight '+w.weight+' · dm.fs('+signed(state.size)+')</div></div>';}
function detailHTML(){var f=fam();return '<div class="d-ey">Font explorer</div><div class="d-title"><h3 style="'+faceStyle(f.regular_face)+'">'+esc(f.name)+'</h3><button class="d-key" type="button" data-copy-family>font.family</button></div><p class="d-use">'+esc(f.note)+'</p><div class="d-bar">'+controlsHTML()+'</div>'+demoToolsHTML()+demoGridHTML()+codeHTML()+metaHTML();}
function railHTML(){var h="";GROUPS.forEach(function(g){h+='<div class="fh">'+esc(g[0])+'</div>';g[1].forEach(function(name){var f=FONTS[name],on=name===state.family,w=f.weights[defaultWeightIndex(f)],fs=faceStyle(w.face);h+='<button class="ri'+(on?" on":"")+'" type="button" data-family="'+esc(name)+'"><span class="font-rail-sample" style="'+fs+'">'+esc(f.rail_sample)+'</span><span class="nm" style="'+fs+'">'+esc(f.name)+'</span><span class="font-count">'+f.weights.length+'</span>'+(f.hangul?'<span class="font-badge">KR</span>':"")+'</button>';});});return h;}
function renderRail(){document.getElementById("fx-rail").innerHTML=railHTML();wireRail();}
function renderDetail(){document.getElementById("fx-detail").innerHTML=detailHTML();wireDetail();}
function wireRail(){document.querySelectorAll("#dm-font-exp .ri").forEach(function(e){e.onclick=function(){state.family=e.dataset.family;state.weight=defaultWeightIndex(fam());state.italic=false;renderRail();renderDetail();};});}
function wireDetail(){var root=document.getElementById("fx-detail");
  root.querySelectorAll("[data-layout]").forEach(function(b){b.onclick=function(){setLayout(+b.dataset.layout);};});
  root.querySelectorAll("[data-demo-pick]").forEach(function(b){b.onclick=function(){toggleDemo(b.dataset.demoPick);};});
  root.querySelectorAll("[data-weight]").forEach(function(b){b.onclick=function(){state.weight=+b.dataset.weight;renderDetail();};});
  root.querySelectorAll("[data-size-step]").forEach(function(b){b.onclick=function(){state.size=Math.max(-2,Math.min(4,state.size+(+b.dataset.sizeStep)));renderDetail();};});
  var it=root.querySelector('[data-tgl="italic"]');if(it)it.onclick=function(){if(fam().italic){state.italic=!state.italic;renderDetail();}};
  var cf=root.querySelector("[data-copy-family]");if(cf)cf.onclick=function(){copy(rcLine(),cf);};
  var cc=root.querySelector("[data-copy-code]");if(cc)cc.onclick=function(){copy(codeText(),cc);};
}
renderRail();renderDetail();
})();</script>
</div>
"""


if __name__ == "__main__":
    main()
