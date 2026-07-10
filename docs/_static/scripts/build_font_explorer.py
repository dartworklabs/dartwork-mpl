#!/usr/bin/env python3
"""Build the interactive two-panel font explorer fragment.

The fragment is embedded by ``docs/fonts/index.md`` via MyST
``{raw} html :file:``. It is generated from the bundled matplotlib font
registry and references real matplotlib SVG chart renders produced by
``build_font_realplots.py`` during the docs build.

Regenerate::

    python3 docs/_static/scripts/build_font_explorer.py
"""

from __future__ import annotations

import json
import re
import warnings
from collections import defaultdict
from pathlib import Path

from fontTools.ttLib import TTFont
from matplotlib import font_manager

from dartwork_mpl import font

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "font_explorer.html"
FONT_FACE_CSS = SCRIPT_DIR.parent / "font-face.css"

DEFAULT_FAMILY = "Roboto"
DEFAULT_WEIGHT = 400
BASE_WEIGHT = 300
HANGUL_SAMPLE = "한글 데이터 축 값"

_ROLE_GROUP = {"serif": "Serif", "mono": "Mono", "mono-kr": "Mono"}


def _group_for(family: str) -> str:
    return _ROLE_GROUP.get(font.FONTS[family].role, "Sans")


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


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _bundled_font_files() -> list[Path]:
    font_dir = font.get_font_dir()
    return sorted(
        path
        for path in font_dir.iterdir()
        if path.suffix.lower() in {".ttf", ".otf"}
    )


def _expected_font_face_files() -> dict[str, str]:
    return {
        font.css_font_face_name(path): path.name
        for path in _bundled_font_files()
    }


def _warn_if_local_css_disagrees() -> None:
    if not FONT_FACE_CSS.is_file():
        return

    css = FONT_FACE_CSS.read_text(encoding="utf-8")
    local = dict(
        re.findall(
            r"font-family: '([^']+)';\s*src: url\('fonts/([^']+)'\)",
            css,
            flags=re.S,
        )
    )
    expected = _expected_font_face_files()
    missing = sorted(set(expected) - set(local))
    extra = sorted(
        face for face in set(local) - set(expected) if face.startswith("dm-")
    )
    mismatched = sorted(
        face
        for face, filename in expected.items()
        if face in local and local[face] != filename
    )
    if not (missing or extra or mismatched):
        return

    details = []
    if missing:
        details.append(f"missing={missing[:8]}")
    if extra:
        details.append(f"extra={extra[:8]}")
    if mismatched:
        details.append(f"mismatched={mismatched[:8]}")
    warnings.warn(
        "local docs/_static/font-face.css disagrees with bundled font "
        f"naming SSOT ({'; '.join(details)}); rebuild docs assets",
        RuntimeWarning,
        stacklevel=2,
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
    suffix = suffix.removesuffix("It")
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
    role = font.FONTS[family].role
    if role in {"mono", "mono-kr"}:
        return "0O1l" if role == "mono" else "한글"
    if role == "kr-body":
        return "한글"
    return "Aa"


def _family_note(family: str, mono: bool, hangul: bool) -> str:
    if family == "Roboto":
        return "Default chart body face with a quiet, neutral voice."
    if family == "Inter Display":
        return "Display cut for large chart titles and poster-scale numbers."
    if family == "Source Serif 4":
        return "Serif body for journal- and book-matched figures (opt-in)."
    if family == "Noto Sans Math":
        return "Math and operator fallback for scientific notation."
    if family.startswith("Noto Sans Symbols"):
        return "Symbol fallback face for arrows, marks, and dingbats."
    if family == "D2Coding":
        return "Monospaced Hangul for code blocks and aligned Korean tables."
    if family in {"Inter", "Pretendard"}:
        return (
            "Browser tabular numerals are available, but real matplotlib uses "
            "proportional default digits for numeric axes."
        )
    if hangul:
        return "Bundled Hangul coverage for Korean and mixed-language figures."
    if mono:
        return "Fixed-width family for code, timestamps, and tabular labels."
    return "Bundled sans-serif family for publication chart typography."


def _numeric_label(record: font.FontFamily) -> str:
    if record.numeric_axes:
        return "numeric axes"
    if record.tnum_available:
        return "browser tnum"
    return "proportional digits"


def _fw_offset(weight: int) -> int | float:
    value = (weight - BASE_WEIGHT) / 100
    if float(value).is_integer():
        return int(value)
    return round(value, 2)


def _build_family_inventory() -> dict:
    _warn_if_local_css_disagrees()
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
            if family == "Noto Sans" and entry.stretch != "normal":
                continue
            path = Path(entry.fname)
            stem = path.stem
            label = _weight_label(stem)
            face = font.css_font_face_name(path)
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
            weights.append(
                {
                    "label": item["label"],
                    "weight": item["weight"],
                    "offset": _fw_offset(item["weight"]),
                    "face": item["face"],
                    "italic_face": italic["face"] if italic else None,
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
        group = _group_for(family)
        mono = group == "Mono"
        has_hangul = _has_hangul(hangul_path)
        record = font.FONTS[family]
        slug = _slug(family)
        families[family] = {
            "name": family,
            "slug": slug,
            "realplot": f"../_static/realplots/{slug}.svg",
            "group": group,
            "mono": mono,
            "hangul": has_hangul,
            "italic": any(entry.get("italic_face") for entry in weights),
            "numeric_axes": record.numeric_axes,
            "tnum_available": record.tnum_available,
            "numeric_label": _numeric_label(record),
            "default_weight": DEFAULT_WEIGHT,
            "regular_face": regular["face"],
            "rail_sample": _rail_sample(family),
            "note": _family_note(family, mono, has_hangul),
            "weights": weights,
        }

    return families


def _group_members(families: dict[str, dict], group: str) -> list[str]:
    return sorted(
        name for name, item in families.items() if item["group"] == group
    )


def _ordered_families(families: dict[str, dict]) -> list[str]:
    sans = _group_members(families, "Sans")
    if DEFAULT_FAMILY in sans:
        sans.remove(DEFAULT_FAMILY)
        sans.insert(0, DEFAULT_FAMILY)
    return (
        sans
        + _group_members(families, "Serif")
        + _group_members(families, "Mono")
    )


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
        [title, [name for name in order if families[name]["group"] == title]]
        for title in ("Sans", "Serif", "Mono")
    ]
    return {
        "families": families,
        "order": order,
        "groups": groups,
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
var FONTS=D.families,GROUPS=D.groups;
var state={family:D.order[0],weight:0,size:0,italic:false};
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function fam(){return FONTS[state.family];}
function weights(){return fam().weights;}
function defaultWeightIndex(f){for(var i=0;i<f.weights.length;i++)if(f.weights[i].weight===f.default_weight)return i;return 0;}
function wt(){var w=weights();if(state.weight>=w.length)state.weight=defaultWeightIndex(fam());return w[state.weight];}
function faceFor(w){return (state.italic&&w.italic_face)?w.italic_face:w.face;}
function signed(n){return n>0?"+"+n:String(n);}
function offsetExpr(v){return Number.isInteger(v)?String(v):String(v);}
function faceStyle(face){return "font-family:'"+face+"',var(--dm-f-sys,system-ui,sans-serif)";}
function fontStyle(w,extra){var size=12+state.size;return "--font-face:'"+faceFor(w)+"';--font-weight:"+w.weight+";--font-size:"+size+"px;"+(extra||"");}
function fixedFontStyle(face,weight,extra){return "--font-face:'"+face+"';--font-weight:"+weight+";"+(extra||"");}
function cardStyle(w){return ' style="'+fontStyle(w)+'"';}
function rcLine(){return 'plt.rcParams["font.family"] = ["'+state.family+'"]';}
function codeText(){var w=wt();return ['import matplotlib.pyplot as plt','import dartwork_mpl as dm','', 'dm.style.use("scientific")',rcLine(),'fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))','ax.set_title("Quarterly revenue", fontsize=dm.fs(0), fontweight=dm.fw('+offsetExpr(w.offset)+'))','dm.simple_layout(fig)'].join("\n");}
function copy(txt,el){if(navigator.clipboard)navigator.clipboard.writeText(txt);toast(txt+" copied");if(el){el.classList.add("copied");setTimeout(function(){el.classList.remove("copied");},900);}}
function toast(msg){var el=document.getElementById("fx-toast");if(!el){el=document.createElement("div");el.id="fx-toast";el.className="dm-toast";document.body.appendChild(el);}el.textContent=msg;el.classList.add("show");clearTimeout(window._fontToast);window._fontToast=setTimeout(function(){el.classList.remove("show");},1100);}
function weightsLadderHTML(){return '<div class="font-ladder">'+weights().map(function(w){return '<div class="font-ladder-row font-demo-text" style="'+fixedFontStyle(w.face,w.weight)+'"><span>'+esc(w.label)+'</span><b>Data labels '+w.weight+'</b></div>';}).join("")+'</div>';}
function koreanLineHTML(){if(fam().hangul)return '<div class="font-korean font-demo-text" data-hangul="1"><b>매출 추이</b><span>한글 축 레이블과 값 표시</span></div>';return '<div class="font-korean font-fallback-note" data-hangul="0"><b>No bundled Hangul in this face</b><span>Keep Pretendard, Paperlogy, or Noto Sans CJK KR in the fallback chain.</span></div>';}
function specimenHTML(){var w=wt();return '<div class="font-specimen-card"'+cardStyle(w)+'><div class="font-specimen-body"><div class="font-specimen-ladder">'+weightsLadderHTML()+'</div><p class="font-copy font-demo-text">A compact caption stays readable beside axes, legends, and numeric labels.</p><div class="font-bigrow font-demo-text">0O 1lI 3.1415 −×±</div>'+koreanLineHTML()+'</div><div class="font-foot">브라우저 렌더 (동일 TTF)</div></div>';}
function controlsHTML(){var f=fam(),ws=weights(),wchips=ws.map(function(w,i){return '<button type="button" data-weight="'+i+'" class="'+(i===state.weight?"on":"")+'">'+esc(w.label)+'<span>'+w.weight+'</span></button>';}).join("");
  var ital='<button class="tgl font-italic-toggle'+(state.italic?" on":"")+(f.italic?"":" font-disabled")+'" data-tgl="italic" type="button"'+(f.italic?"":' disabled')+'><span class="tgl-l">Italic</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>';
  var step='<span class="font-stepper"><button type="button" data-size-step="-1">−</button><b>dm.fs('+signed(state.size)+')</b><button type="button" data-size-step="1">+</button></span>';
  return '<span class="field font-weight-field"><span class="cl">Weight</span><span class="seg font-weight-seg">'+wchips+'</span></span><span class="field"><span class="cl">Size</span>'+step+'</span>'+ital;}
function codeHTML(){return '<button class="code font-code-chip" type="button" data-copy-code><pre>'+esc(codeText())+'</pre></button>';}
function badgesHTML(){var f=fam(),h='<div class="a11y-chips">';h+='<span class="a11y-chip '+(f.numeric_axes?"ok":"info")+'" data-tip="'+esc(f.numeric_label)+'"><span class="a-dot"></span><span class="a-label">NUM</span><span class="a-num">'+(f.numeric_axes?"yes":"-")+'</span></span>';if(f.tnum_available)h+='<span class="a11y-chip info" data-tip="Browser OpenType tabular numerals available"><span class="a-dot"></span><span class="a-label">tnum</span><span class="a-num">yes</span></span>';return h+'</div>';}
function realplotHTML(){var f=fam();return '<div class="font-panel font-realplot-card"><div class="font-panel-head"><h4>실제 플롯</h4><span>Panel A</span></div><img class="font-realplot-img" src="'+esc(f.realplot)+'" alt="'+esc(f.name)+' real matplotlib chart" loading="lazy"><p class="font-caption">실제 matplotlib 출력 · dm.style.use("scientific") 기본 상태 · Weight/Size 컨트롤 비적용</p></div>';}
function specimenPanelHTML(){return '<div class="font-panel"><div class="font-panel-head"><h4>타이포 스펙시멘</h4><span>Panel B</span></div><div class="d-bar">'+controlsHTML()+'</div>'+specimenHTML()+'</div>';}
function metaHTML(){var f=fam(),w=wt();return '<div class="meta"><div><span class="m-l">Inventory</span> '+f.weights.length+' upright weights'+(f.italic?", italic cuts available":", no italic cuts")+(f.hangul?", Hangul coverage detected":", Latin/symbol coverage only")+'</div><div><span class="m-l">Current specimen face</span> '+esc(faceFor(w))+' · fontweight '+w.weight+' · dm.fs('+signed(state.size)+')</div><div><span class="m-l">Numeric axes</span> '+esc(f.numeric_label)+'</div></div>';}
function detailHTML(){var f=fam();return '<div class="d-ey">Font explorer</div><div class="d-title"><h3 style="'+faceStyle(f.regular_face)+'">'+esc(f.name)+'</h3><button class="d-key" type="button" data-copy-family>font.family</button>'+badgesHTML()+'</div><p class="d-use">'+esc(f.note)+'</p><div class="font-panels">'+realplotHTML()+specimenPanelHTML()+'</div>'+codeHTML()+metaHTML();}
function railHTML(){var h="";GROUPS.forEach(function(g){h+='<div class="fh">'+esc(g[0])+'</div>';g[1].forEach(function(name){var f=FONTS[name],on=name===state.family,w=f.weights[defaultWeightIndex(f)],fs=faceStyle(w.face);h+='<button class="ri'+(on?" on":"")+'" type="button" data-family="'+esc(name)+'"><span class="font-rail-sample" style="'+fs+'">'+esc(f.rail_sample)+'</span><span class="nm" style="'+fs+'">'+esc(f.name)+'</span><span class="font-count">'+f.weights.length+'</span>'+(f.numeric_axes?'<span class="font-badge font-num-badge">NUM</span>':"")+(f.hangul?'<span class="font-badge">KR</span>':"")+'</button>';});});return h;}
function renderRail(){document.getElementById("fx-rail").innerHTML=railHTML();wireRail();}
function renderDetail(){document.getElementById("fx-detail").innerHTML=detailHTML();wireDetail();}
function wireRail(){document.querySelectorAll("#dm-font-exp .ri").forEach(function(e){e.onclick=function(){state.family=e.dataset.family;state.weight=defaultWeightIndex(fam());state.italic=false;renderRail();renderDetail();};});}
function wireDetail(){var root=document.getElementById("fx-detail");
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
