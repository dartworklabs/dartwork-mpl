#!/usr/bin/env python3
"""Build the interactive categorical-palette explorer fragment (v5).

Restores the left-rail + live-plot explorer, generated entirely from the v5
color SSOT — no hand-maintained JS data file:

- ``src/dartwork_mpl/colors/_generated.py``  ``PALETTE`` (20 families) + ``CYCLES``
- ``src/dartwork_mpl/colors/_curated.py``     ``CURATED`` (20 curated sets) + meta

Pick a cycle, a generative family, or a curated categorical set on the left;
the nine chart shapes on the right re-render live in that palette. Drag the
colour count, sort by lightness, shuffle or reverse, and preview in black &
white. Click a swatch to copy its hex, or copy the matching
``dm.get_palette(...)`` / ``dm.cycle(...)`` call.

The fragment is embedded by ``docs/color_system/categorical-palettes.md`` via
MyST ``{raw} html :file:``. Regenerate::

    python3 docs/_static/scripts/build_categorical_explorer.py
"""

from __future__ import annotations

import json
import runpy
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "categorical_explorer.html"
GENERATED = ROOT / "src" / "dartwork_mpl" / "colors" / "_generated.py"
CURATED_MOD = ROOT / "src" / "dartwork_mpl" / "colors" / "_curated.py"

# ── v5 generative families ────────────────────────────────────────────────
FAMILY_ORDER = [
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
FAMILY_INTENT = {
    "red": "Use red for ordered negative states: severity, loss, alerts, or "
    "risk intensity. It runs as a warm single-hue ramp, so the light to "
    "dark steps still carry rank when printed in black and white.",
    "rose": "Use rose for warm ordered annotations that should feel editorial "
    "rather than alarming. Its red-pink hue gives recency or intensity "
    "a softer voice while preserving the family ramp's lightness order.",
    "coral": "Use coral for human-scale ordered data such as intensity, recency, "
    "heat, or severity without going fully red. The orange-red hue "
    "feels warm and approachable, and its sequential ramp remains "
    "legible by lightness in grayscale.",
    "tangerine": "Use tangerine for ordered thresholds that need more attention "
    "than coral but less alarm than red. The bright orange-coral "
    "hue works for warnings and high-attention marks while the "
    "ramp keeps amount readable in black and white.",
    "orange": "Use orange for ordered warnings, warm emphasis, and operational "
    "thresholds. Its familiar caution hue reads quickly, and the "
    "single-hue ramp carries magnitude through lightness rather than "
    "hue changes.",
    "amber": "Use amber for ordered bands, caution zones, and contextual "
    "thresholds that should feel less urgent than orange. The golden "
    "hue is warm and stable, with lightness steps that hold up for "
    "sequential legends and print.",
    "yellow": "Use yellow for high-key ordered highlights, attention fields, "
    "and pale-to-rich emphasis where the page can support a bright "
    "hue. The ramp is intentionally luminous, so pair it with strong "
    "labels while relying on lightness for sequence.",
    "lime": "Use lime for ordered biological, ecological, or freshness scales "
    "where green alone feels too conventional. The yellow-green hue "
    "keeps the ramp lively, and the light-to-dark structure preserves "
    "rank under grayscale viewing.",
    "green": "Use green for ordered positive states: growth, health, progress, "
    "or success intensity. It is a clear natural hue with a sequential "
    "lightness ladder that still communicates amount in black and "
    "white.",
    "teal": "Use teal for the house analytical ramp and for ordered quantities "
    "that should feel calm, precise, and central to the system. Rank "
    "reads straight from lightness, making it the safest default "
    "single-hue ramp for grayscale and print.",
    "cyan": "Use cyan for ordered cool secondary data, dense marks, and related "
    "series that need distance from blue or teal. Its bright blue-green "
    "character stays technical and airy while the sequential ramp "
    "keeps magnitude readable.",
    "sky": "Use sky for ordered light-cool data, background quantities, or "
    "gentle secondary scales. The hue is the airy counterpart to blue, "
    "and its ramp is best when a calm lightness progression matters "
    "more than saturated color.",
    "blue": "Use blue for primary ordered analytical data and dependable "
    "amount scales. Sampled evenly it can carry a few related series, "
    "but as a full ramp it encodes magnitude through a robust lightness "
    "sequence.",
    "cobalt": "Use cobalt for ordered institutional emphasis when blue needs a "
    "deeper, more focused voice. It bridges blue and indigo, keeping "
    "a strong analytical character while preserving sequential "
    "lightness for grayscale reading.",
    "indigo": "Use indigo for ordered corporate or comparison data that should "
    "feel cooler and more formal than blue. The violet-blue hue adds "
    "depth, and the lightness ladder keeps the ramp usable for "
    "ranked values.",
    "violet": "Use violet for ordered premium, editorial, or exploratory data "
    "where a cooler accent is appropriate. Its purple-blue hue adds "
    "character without breaking the sequential light-to-dark read.",
    "purple": "Use purple for ordered accent groups, editorial quantities, and "
    "secondary ramps that need more warmth than violet. The hue is "
    "expressive, but the family still behaves as a lightness-ordered "
    "sequential scale.",
    "fuchsia": "Use fuchsia for ordered expressive accents between purple and "
    "pink, especially when a vivid editorial note is intentional. "
    "Its magenta hue is attention-getting, so the ramp relies on "
    "clear lightness steps to keep sequence legible.",
    "pink": "Use pink for ordered soft editorial accents, warmth, and "
    "approachable emphasis. The hue is gentle rather than urgent, and "
    "the light-to-dark ramp supports small sequential scales and "
    "grayscale fallback.",
    "gray": "Use gray when ordered amount should carry no separate hue meaning: "
    "reference values, grids, confidence, or neutral magnitude. It is "
    "the hue-free ramp, so black-and-white behavior is the design "
    "rather than a fallback.",
}

# ── v5 cycles ─────────────────────────────────────────────────────────────
CYCLE_ORDER = ["default", "print"]
CYCLE_LABEL = {"default": "Default", "print": "Print"}
CYCLE_INTENT = {
    "default": "The everyday categorical cycle — reach for this first for 4–8 "
    "unrelated series. Seven chromatic colours chosen by exhaustive "
    "search to stay distinct under color-vision-deficiency "
    "simulation; gray is reserved for grids, not spent as a series.",
    "print": "The print variant — an 8th dark-gray colour and a wider "
    "lightness spread so the series stay separable in black-and-white.",
}

# rail order for the explorer. FAMILY_ORDER remains the full family SSOT;
# only the rail taxonomy below separates chromatic sequential ramps from
# hue-free neutral ramps.
CHROMATIC_FAMILY_ORDER = [fam for fam in FAMILY_ORDER if fam != "gray"]
RAIL_GROUP_ORDER = [
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
GROUP_REMAP = {"Balanced": "Qualitative", "Spectrum": "Qualitative"}


def build_payload() -> dict:
    g = runpy.run_path(str(GENERATED))
    palette, cycles = g["PALETTE"], g["CYCLES"]
    c = runpy.run_path(str(CURATED_MOD))
    curated, meta, cur_order = (
        c["CURATED"],
        c["CURATED_META"],
        c["CURATED_ORDER"],
    )

    palettes: dict[str, dict] = {}
    groups_by_label: dict[str, list[str]] = {
        label: [] for label in RAIL_GROUP_ORDER
    }

    for name in CYCLE_ORDER:
        palettes[name] = {
            "name": CYCLE_LABEL[name],
            "kind": "cycle",
            "group": "Qualitative",
            "cols": list(cycles[name]),
            "intent": CYCLE_INTENT[name],
        }
        groups_by_label["Qualitative"].append(name)

    for fam in FAMILY_ORDER:
        group = "Neutral" if fam == "gray" else "Sequential"
        palettes[fam] = {
            "name": fam.capitalize(),
            "kind": "family",
            "group": group,
            "cols": list(palette[fam]),
            "intent": FAMILY_INTENT[fam],
        }
        if fam in CHROMATIC_FAMILY_ORDER:
            groups_by_label["Sequential"].append(fam)
        else:
            groups_by_label["Neutral"].append(fam)

    for key in cur_order:
        m = meta[key]
        group = GROUP_REMAP.get(m["family"], m["family"])
        palettes[key] = {
            "name": m["label"],
            "kind": "curated",
            "group": group,
            "cols": list(curated[key]),
            "intent": m["intent"],
            "design": m["design"],
            "application": m["application"],
            "bw": m["bw"],
            "cvd": m["cvd"],
        }
        groups_by_label[group].append(key)

    # Chromatic families are recipe-generated CIELAB/OKLCH 10-step ramps.
    # Gray, warm_gray, and cool_gray are hue-free ramps, so the rail presents
    # them together as Neutral.
    groups = [
        (label, groups_by_label[label])
        for label in RAIL_GROUP_ORDER
        if groups_by_label.get(label)
    ]
    order = [key for _, keys in groups for key in keys]

    return {
        "palettes": palettes,
        "order": order,
        "groups": groups,
        "counts": {
            "curated": len(cur_order),
            "families": len(FAMILY_ORDER),
            "family_colors": sum(len(palette[f]) for f in FAMILY_ORDER),
            "cycles": len(CYCLE_ORDER),
        },
    }


def main() -> None:
    payload = build_payload()
    html = TEMPLATE.replace("__PAYLOAD__", json.dumps(payload))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")


# ---------------------------------------------------------------------------
# The widget: CSS + skeleton + JS. Colours come only from __PAYLOAD__ (the v5
# SSOT). Renderers are self-contained SVG generators that take a hex array.
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!-- GENERATED FILE - do not edit by hand.
     Source: docs/_static/scripts/build_categorical_explorer.py
     Data:   src/dartwork_mpl/colors/_generated.py (PALETTE + CYCLES)
             src/dartwork_mpl/colors/_curated.py (CURATED categorical sets)
     Regenerate: python3 docs/_static/scripts/build_categorical_explorer.py -->
<div id="dm-cat-exp" class="yue">
<style>
#dm-cat-exp * {box-sizing:border-box;}
#dm-cat-exp {width:100%;margin:0;background:var(--dm-bg-page,#fff);color:var(--dm-gray-12,#1f2933);
  font-family:var(--dm-f-sys,"Inter",system-ui,sans-serif);letter-spacing:normal;}
#dm-cat-exp .poc-h {font-size:14.5px;color:var(--dm-text-muted,#667085);margin:0 0 6px;line-height:1.6;}
#dm-cat-exp .poc-h b {color:var(--dm-gray-12,#1f2933);font-weight:650;}
#dm-cat-exp .cx-count {font:600 12px var(--dm-f-mono,ui-monospace,monospace);color:var(--dm-text-muted,#667085);margin:0 0 16px;}
#dm-cat-exp .md {display:grid;grid-template-columns:198px 1fr;gap:28px;align-items:start;}
@media(max-width:760px){#dm-cat-exp .md{grid-template-columns:1fr;gap:18px;}#dm-cat-exp .detail{position:static!important;}}
#dm-cat-exp .rail {display:flex;flex-direction:column;gap:1px;position:sticky;top:96px;
  max-height:calc(100vh - 120px);overflow-y:auto;padding-right:8px;scrollbar-width:thin;}
#dm-cat-exp .rail::-webkit-scrollbar{width:9px;}
#dm-cat-exp .rail::-webkit-scrollbar-thumb{background:var(--dm-gray-a4,rgba(0,0,0,.13));border-radius:9px;border:2px solid transparent;background-clip:content-box;}
#dm-cat-exp .rail .fh {font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;
  color:var(--dm-gray-10,#7c8794);margin:16px 0 5px;}
#dm-cat-exp .rail .fh:first-child {margin-top:0;}
#dm-cat-exp .ri {display:flex;align-items:center;gap:10px;padding:4px 9px;border-radius:9px;cursor:pointer;min-width:0;}
#dm-cat-exp .ri:hover {background:var(--dm-gray-a2,rgba(0,0,0,.05));}
#dm-cat-exp .ri.on {background:var(--dm-accent-2,#e6f7f4);}
#dm-cat-exp .mini {display:inline-flex;height:13px;border-radius:3px;overflow:hidden;}
#dm-cat-exp .mini i {flex:1;min-width:3px;}
#dm-cat-exp .ri .mini {flex:0 0 36px;height:12px;border-radius:4px;}
#dm-cat-exp .ri .nm {font-size:12px;font-weight:400;color:var(--dm-gray-12,#1f2933);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;}
#dm-cat-exp .ri.on .nm {color:var(--dm-accent-11,#0c6b5e);font-weight:500;}
#dm-cat-exp .detail {position:static;top:auto;background:var(--dm-bg-subtle,#f7f9f9);border-radius:18px;padding:24px 26px;}
#dm-cat-exp .d-ey {font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--dm-accent-11,#0c6b5e);margin-bottom:7px;}
#dm-cat-exp .d-title {display:flex;align-items:baseline;gap:11px;flex-wrap:wrap;}
#dm-cat-exp .d-title h3 {margin:0;font-size:25px;font-weight:700;letter-spacing:-.02em;}
#dm-cat-exp .d-key {font-family:var(--dm-f-mono,monospace);font-size:13px;color:var(--dm-accent-11,#0c6b5e);
  background:var(--dm-accent-2,#e6f7f4);padding:2px 9px;border-radius:6px;font-weight:500;cursor:pointer;align-self:center;}
#dm-cat-exp .d-key:hover {background:var(--dm-accent-3,#d3f1ea);}
#dm-cat-exp .d-key.copied {background:var(--dm-accent-9,#12a594);color:#fff;}
#dm-cat-exp .d-key.copied::after {content:" \2713";}
#dm-cat-exp .d-use {font-size:15.5px;color:var(--dm-gray-11,#4a5560);line-height:1.62;margin:11px 0 8px;min-height:4.86em;}
#dm-cat-exp .ro {display:flex;flex-direction:column;gap:8px;margin:14px 0 12px;}
#dm-cat-exp .ro-i {display:flex;align-items:baseline;gap:9px;font-size:14.5px;flex-wrap:wrap;}
#dm-cat-exp .ro-ic {font-size:13px;line-height:1.2;color:var(--dm-gray-7,#adb5bd);font-weight:700;}
#dm-cat-exp .ro-ic.ok {color:var(--dm-accent-10,#0f9a89);}
#dm-cat-exp .ro-tx {color:var(--dm-text-muted,#667085);}
#dm-cat-exp .ro-tx b {color:var(--dm-gray-12,#1f2933);font-weight:600;}
#dm-cat-exp .ro-n {font-family:var(--dm-f-mono,monospace);font-size:11.5px;color:var(--dm-gray-8,#98a1ab);}
#dm-cat-exp .term {position:relative;display:inline-block;border-bottom:1px dotted var(--dm-gray-7,#adb5bd);cursor:help;outline:none;}
#dm-cat-exp .term:focus {border-bottom-color:var(--dm-accent-9,#12a594);}
#dm-cat-exp .term::after {content:attr(data-tip);position:absolute;left:0;top:calc(100% + 8px);width:max-content;max-width:250px;
  background:var(--dm-gray-12,#1f2933);color:var(--dm-bg-page,#fff);padding:9px 12px;border-radius:9px;
  font:400 11px/1.55 var(--dm-f-sys,"Inter",system-ui,sans-serif);letter-spacing:0;text-transform:none;
  opacity:0;visibility:hidden;transform:translateY(-3px);transition:opacity .14s ease,transform .14s ease;
  z-index:60;pointer-events:none;box-shadow:0 5px 16px rgba(0,0,0,.17);white-space:normal;}
#dm-cat-exp .term:hover::after,#dm-cat-exp .term:focus::after {opacity:1;visibility:visible;transform:translateY(0);}
#dm-cat-exp .term.r::after {left:auto;right:0;}
@media(prefers-reduced-motion:reduce){#dm-cat-exp .term::after{transition:none;}}
#dm-cat-exp .d-bar {display:flex;align-items:center;gap:13px;flex-wrap:nowrap;margin-bottom:16px;}
#dm-cat-exp .field {display:inline-flex;align-items:center;gap:8px;flex:0 0 auto;}
#dm-cat-exp .cl {font-size:13px;font-weight:500;color:var(--dm-gray-9,#8794a1);letter-spacing:normal;text-transform:none;white-space:nowrap;}
#dm-cat-exp .crng {accent-color:var(--dm-accent-9,#12a594);width:70px;}
#dm-cat-exp .cval {font-size:14px;font-weight:700;color:var(--dm-accent-11,#0c6b5e);min-width:1ch;}
#dm-cat-exp .tgl {appearance:none;border:0;background:transparent;padding:0;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font:inherit;flex:0 0 auto;white-space:nowrap;}
#dm-cat-exp .tgl .tgl-l {font-size:13px;font-weight:500;color:var(--dm-gray-9,#8794a1);transition:color .12s;}
#dm-cat-exp .tgl.on .tgl-l {color:var(--dm-gray-12,#1f2933);}
#dm-cat-exp .tgl-tr {width:32px;height:18px;border-radius:999px;background:var(--dm-gray-5,#c3c9d0);position:relative;transition:background .15s;flex:0 0 auto;}
#dm-cat-exp .tgl-kn {position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.28);transition:left .15s;}
#dm-cat-exp .tgl.on .tgl-tr {background:var(--dm-accent-9,#12a594);}
#dm-cat-exp .tgl.on .tgl-kn {left:16px;}
#dm-cat-exp .swhost {display:flex;gap:7px;margin-bottom:18px;}
#dm-cat-exp .strip {display:flex;gap:6px;margin:0 0 4px;}
#dm-cat-exp .sw {appearance:none;background:transparent;border:0;padding:0;font:inherit;flex:1;min-width:0;cursor:pointer;display:block;text-align:center;}
#dm-cat-exp .sw .chip {display:block;height:34px;border-radius:6px;transition:transform .1s,box-shadow .1s;}
#dm-cat-exp .swhost .sw {flex:1;}
#dm-cat-exp .swhost .chip {height:46px;border-radius:11px;}
#dm-cat-exp .sw:hover .chip {transform:translateY(-2px);box-shadow:0 2px 6px rgba(0,0,0,.12);}
#dm-cat-exp .sw .hx {font-family:var(--dm-f-mono,monospace);font-size:9px;color:var(--dm-text-muted,#667085);margin-top:4px;overflow:hidden;}
#dm-cat-exp .sw.copied .hx {color:var(--dm-accent-11,#0c6b5e);font-weight:700;}
#dm-cat-exp .sw.copied .hx::after {content:" \2713";}
#dm-cat-exp .plots {display:grid;grid-template-columns:repeat(3,1fr);gap:13px;}
#dm-cat-exp .pcell {background:var(--dm-bg-page,#fff);border-radius:13px;padding:10px 12px;}
#dm-cat-exp .pcell .pl {font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--dm-text-muted,#667085);margin-bottom:7px;}
#dm-cat-exp .plots.gs svg,#dm-cat-exp .strip.gs .chip {filter:grayscale(1);}
#dm-cat-exp svg {display:block;width:100%;height:auto;}
#dm-cat-exp .meta {font-size:14.5px;color:var(--dm-text-muted,#667085);line-height:1.72;display:grid;gap:4px;margin-top:4px;}
#dm-cat-exp .meta b {color:var(--dm-gray-12,#1f2933);font-weight:650;}
#dm-cat-exp .code {margin:16px 0 14px;background:var(--dm-i-code-surface,#f2f4f5);border-radius:8px;padding:11px 14px;
  font-family:var(--dm-f-mono,monospace);font-size:11.5px;color:var(--dm-gray-12,#1f2933);white-space:pre;overflow-x:auto;}
#dm-cat-exp .code pre {margin:0;padding:0;background:transparent;font:inherit;color:inherit;white-space:pre;}
#dm-cat-exp .dm-toast {position:fixed;bottom:26px;left:50%;transform:translateX(-50%);background:var(--dm-gray-12,#1f2933);color:#fff;padding:8px 16px;border-radius:999px;font-size:12.5px;opacity:0;transition:opacity .18s;pointer-events:none;z-index:99999;}
#dm-cat-exp .dm-toast.show {opacity:1;}
</style>
<div class="md"><div class="rail" id="cx-rail"></div><div class="detail" id="cx-detail"></div></div>
<script>(function(){
var D = __PAYLOAD__;
var PALETTES = D.palettes, GROUPS = D.groups;

var VB = '0 0 100 56';
// ── nine self-contained SVG chart renderers (take a hex array) ──
var P = {
  line: function(c){ var n=c.length, s='<svg viewBox="'+VB+'" preserveAspectRatio="none">';
    for(var i=0;i<n;i++){ var yc=n>1?9+i*(38/(n-1)):28, d='';
      for(var x=0;x<=100;x+=1.25){ var t=x/100, y=yc+Math.sin(t*4.6+i*0.9)*3.5-(t-0.5)*(i-n/2)*1.8; d+=(x===0?'M':'L')+x.toFixed(2)+' '+y.toFixed(2)+' '; }
      s+='<path d="'+d+'" fill="none" stroke="'+c[i]+'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'; }
    return s+'</svg>'; },
  scatter: function(c){ var n=c.length, s='<svg viewBox="'+VB+'">';
    for(var i=0;i<n;i++){ var cx=12+(i/(n-1||1))*76, cy=15+((i*37)%28);
      for(var k=0;k<11;k++){ var a=i*2.3+k*1.7; s+='<circle cx="'+(cx+Math.cos(a)*9+Math.sin(k*3.1)*2.6).toFixed(1)+'" cy="'+(cy+Math.sin(a)*9+Math.cos(k*2.2)*2.6).toFixed(1)+'" r="2" fill="'+c[i]+'" opacity="0.82"/>'; } }
    return s+'</svg>'; },
  area: function(c){ var n=c.length, S=48, acc=[], s='<svg viewBox="'+VB+'" preserveAspectRatio="none">';
    for(var q=0;q<=S;q++)acc.push(54);
    for(var i=0;i<n;i++){ var top='',bot='';
      for(var xi=0;xi<=S;xi++){ var x=xi*(100/S), v=(46/n)*(0.85+0.34*Math.sin(xi*0.22+i*0.95)), y0=acc[xi], y1=acc[xi]-v; acc[xi]=y1; top+=(xi===0?'M':'L')+x.toFixed(2)+' '+y1.toFixed(2)+' '; bot=x.toFixed(2)+' '+y0.toFixed(2)+' '+bot; }
      s+='<path d="'+top+'L'+bot+'Z" fill="'+c[i]+'" opacity="0.96"/>'; }
    return s+'</svg>'; },
  bar: function(c){ var n=c.length, g=2.2, bw=100/n, h=[40,28,48,34,44,30,38,46], s='<svg viewBox="'+VB+'" preserveAspectRatio="none">';
    for(var i=0;i<n;i++){ var x=i*bw+g/2, bh=h[i%8]; s+='<rect x="'+x.toFixed(1)+'" y="'+(52-bh).toFixed(1)+'" width="'+(bw-g).toFixed(1)+'" height="'+bh+'" rx="0.8" fill="'+c[i]+'"/>'; }
    return s+'</svg>'; },
  heatmap: function(c){ var n=c.length, cw=100/n, rows=5, rh=56/rows, s='<svg viewBox="'+VB+'">';
    for(var i=0;i<n;i++){ for(var r=0;r<rows;r++){ s+='<rect x="'+(i*cw).toFixed(1)+'" y="'+(r*rh).toFixed(1)+'" width="'+cw.toFixed(1)+'" height="'+rh.toFixed(1)+'" fill="'+c[i]+'" opacity="'+(0.4+r*0.14).toFixed(2)+'"/>'; } } return s+'</svg>'; },
  bubble: function(c){ var n=c.length, s='<svg viewBox="'+VB+'">';
    for(var i=0;i<n;i++){ var cx=12+(i/(n-1||1))*76, cy=16+((i*29)%26);
      for(var k=0;k<5;k++){ var a=i*1.7+k*2.2, rr=1.6+((i+k*3)%4)*1.4; s+='<circle cx="'+(cx+Math.cos(a)*8).toFixed(1)+'" cy="'+(cy+Math.sin(a)*8).toFixed(1)+'" r="'+rr.toFixed(1)+'" fill="'+c[i]+'" opacity="0.68"/>'; } }
    return s+'</svg>'; },
  lollipop: function(c){ var n=c.length, g=100/(n+1), s='<svg viewBox="'+VB+'">';
    for(var i=0;i<n;i++){ var x=g*(i+1), y=52-(14+Math.abs(Math.sin(i*1.5+0.4))*32); s+='<line x1="'+x.toFixed(1)+'" y1="52" x2="'+x.toFixed(1)+'" y2="'+y.toFixed(1)+'" stroke="'+c[i]+'" stroke-width="1.4"/><circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="3" fill="'+c[i]+'"/>'; }
    return s+'</svg>'; }
};
// squarified treemap — variable-size rects show every colour
P.treemap = function(c){ var W=100,H=56,vals=c.map(function(_,i){return 1+Math.abs(Math.sin(i*1.7+0.3))*1.7;});
  var tot=vals.reduce(function(a,b){return a+b;},0), items=c.map(function(col,i){return {col:col,area:vals[i]/tot*(W*H)};});
  var x=0,y=0,w=W,h=H,rects=[];
  function worst(row,len){var s=0,mn=Infinity,mx=0;row.forEach(function(r){s+=r.area;if(r.area<mn)mn=r.area;if(r.area>mx)mx=r.area;});return Math.max(len*len*mx/(s*s),s*s/(len*len*mn));}
  function lay(row,horiz){var sum=0;row.forEach(function(r){sum+=r.area;});
    if(horiz){var rh=sum/w,cx=x;row.forEach(function(r){var rw=r.area/rh;rects.push({x:cx,y:y,w:rw,h:rh,col:r.col});cx+=rw;});y+=rh;h-=rh;}
    else{var rw=sum/h,cy=y;row.forEach(function(r){var rh2=r.area/rw;rects.push({x:x,y:cy,w:rw,h:rh2,col:r.col});cy+=rh2;});x+=rw;w-=rw;}}
  var q=items.slice(),row=[];
  while(q.length){var horiz=(w<=h),len=horiz?w:h,nx=q[0];
    if(row.length===0||worst(row,len)>=worst(row.concat([nx]),len)){row.push(q.shift());}else{lay(row,horiz);row=[];}}
  if(row.length)lay(row,(w<=h));
  var s='<svg viewBox="'+VB+'">';rects.forEach(function(r){s+='<rect x="'+r.x.toFixed(2)+'" y="'+r.y.toFixed(2)+'" width="'+Math.max(0,r.w-0.5).toFixed(2)+'" height="'+Math.max(0,r.h-0.5).toFixed(2)+'" rx="1" fill="'+r.col+'"/>';});
  return s+'</svg>';};
// waffle — cumulative assignment fills every cell
P.waffle = function(c){ var n=c.length,cols=12,rows=5,cell=56/rows,cw=100/cols,total=cols*rows;
  var raw=c.map(function(_,i){return 0.6+Math.abs(Math.sin(i*1.7+0.2));}), t=raw.reduce(function(a,b){return a+b;},0),cum=0;
  var bounds=raw.map(function(v){cum+=v;return Math.round(cum/t*total);});
  var s='<svg viewBox="'+VB+'">',idx=0;
  for(var ci=0;ci<n;ci++){var end=(ci===n-1)?total:bounds[ci];
    for(;idx<end;idx++){var r=Math.floor(idx/cols),col=idx%cols;s+='<rect x="'+(col*cw+0.6).toFixed(2)+'" y="'+(r*cell+0.6).toFixed(2)+'" width="'+(cw-1.2).toFixed(2)+'" height="'+(cell-1.2).toFixed(2)+'" rx="1" fill="'+c[ci]+'"/>';}}
  return s+'</svg>';};
var PLABEL={line:"line",bar:"bar",scatter:"scatter",area:"stacked area",lollipop:"lollipop",bubble:"bubble",heatmap:"heatmap",waffle:"waffle",treemap:"treemap"};
var SHOWORDER=["line","bar","scatter","area","lollipop","bubble","heatmap","waffle","treemap"];

// ── colour math: L* and grayscale ──
function _hx(h){h=h.replace('#','');return [parseInt(h.substr(0,2),16),parseInt(h.substr(2,2),16),parseInt(h.substr(4,2),16)];}
function _hex(r,g,b){function c(v){v=Math.max(0,Math.min(255,Math.round(v)));var s=v.toString(16);return s.length<2?'0'+s:s;}return '#'+c(r)+c(g)+c(b);}
function _lin(v){v/=255;return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);}
function _slin(v){v=v<=0.0031308?v*12.92:1.055*Math.pow(v,1/2.4)-0.055;return v*255;}
function lstar(hex){var p=_hx(hex),Y=0.2126*_lin(p[0])+0.7152*_lin(p[1])+0.0722*_lin(p[2]);var f=Y>0.008856?Math.pow(Y,1/3):(7.787*Y+16/116);return 116*f-16;}
function simulate(hex,view){
  if(view==='color')return hex;
  var p=_hx(hex);
  if(view==='bw'){var Y=0.2126*_lin(p[0])+0.7152*_lin(p[1])+0.0722*_lin(p[2]),g=_slin(Y);return _hex(g,g,g);}
  return hex;
}
function minDL(cols){var m=Infinity;for(var i=0;i<cols.length;i++)for(var j=i+1;j<cols.length;j++){var d=Math.abs(lstar(cols[i])-lstar(cols[j]));if(d<m)m=d;}return cols.length<2?99:m;}
function shuffleSeeded(arr,seed){var s=(0x6d2b79f5^seed)>>>0;function rnd(){s=s+0x6d2b79f5>>>0;var t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;}
  for(var i=arr.length-1;i>0;i--){var j=Math.floor(rnd()*(i+1)),tmp=arr[i];arr[i]=arr[j];arr[j]=tmp;}return arr;}

// ── state ──
var state={key:D.order[0],n:PALETTES[D.order[0]].cols.length,gs:false,show:9,order:'default',rev:false,shuffleSeed:1};
function pal(){return PALETTES[state.key];}
function maxN(){return pal().cols.length;}
function active(){var p=pal(),sel=p.cols.slice(0,state.n);
  if(state.order==='lightness')sel=sel.slice().sort(function(a,b){return lstar(b)-lstar(a);});
  else if(state.order==='shuffle')sel=shuffleSeeded(sel.slice(),state.shuffleSeed);
  if(state.rev)sel=sel.slice().reverse();
  return sel;}
function simActive(){return active().map(function(c){return simulate(c,state.gs?'bw':'color');});}

// ── code snippet (v5-correct, runnable) ──
function pySnip(){var p=pal();
  if(p.kind==='cycle'){
    var expr;
    if(state.order==='default'){
      expr="dm.cycle('"+state.key+"')";
      if(state.n<p.cols.length)expr+="[:"+state.n+"]";
      if(state.rev)expr+="[::-1]";
    }else{
      expr="["+active().map(function(c){return "'"+c+"'";}).join(", ")+"]";
    }
    var note=[state.n+' colors'];
    if(state.order==='lightness')note.push('gradient');else if(state.order==='shuffle')note.push('shuffled');
    if(state.rev)note.push('reversed');
    return "import dartwork_mpl as dm\n# "+p.name+"  ("+note.join(', ')+")\ndm.set_cycle("+expr+")";}
  var parts=["'"+state.key+"'","n="+state.n];
  if(state.order==='lightness')parts.push("order='lightness'");
  else if(state.order==='shuffle'){parts.push("order='shuffle'");parts.push("seed="+state.shuffleSeed);}
  if(state.rev)parts.push("reverse=True");
  var note2=[state.n+' colors'];
  if(state.order==='lightness')note2.push('gradient');else if(state.order==='shuffle')note2.push('shuffled');
  if(state.rev)note2.push('reversed');
  return "import dartwork_mpl as dm\n# "+p.name+"  ("+note2.join(', ')+")\ndm.set_cycle(dm.get_palette("+parts.join(', ')+"))";}

// ── syntax highlight via the docs' own Pygments token classes ──
var PYKW={'import':'kn','from':'kn','as':'k','def':'k','return':'k','for':'k','in':'k','None':'kc','True':'kc','False':'kc'};
function _esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function pyHi(code){return code.split('\n').map(function(line){
  if(/^\s*#/.test(line))return '<span class="c1">'+_esc(line)+'</span>';
  var imp=/^\s*(import|from)\b/.test(line),nameCls=imp?'nn':'n',out='';
  var re=/(\s+)|('[^']*'|"[^"]*")|(\b\d+\b)|([A-Za-z_]\w*)|(.)/g,m;
  while((m=re.exec(line))){
    if(m[1])out+='<span class="w">'+m[1]+'</span>';
    else if(m[2])out+='<span class="'+(m[2][0]==="'"?'s1':'s2')+'">'+_esc(m[2])+'</span>';
    else if(m[3])out+='<span class="mi">'+m[3]+'</span>';
    else if(m[4]){var w=m[4];out+='<span class="'+(PYKW[w]||nameCls)+'">'+w+'</span>';}
    else{var ch=m[5],cc=(ch==='('||ch===')'||ch===',')?'p':((ch==='.'||ch==='=')?'o':'');out+=cc?'<span class="'+cc+'">'+_esc(ch)+'</span>':_esc(ch);}}
  return out;}).join('\n');}

// ── toast + swatch copy ──
function toast(msg){var el=document.getElementById('cx-toast');if(!el){el=document.createElement('div');el.id='cx-toast';el.className='dm-toast';document.body.appendChild(el);}el.textContent=msg;el.classList.add('show');clearTimeout(window._cxtt);window._cxtt=setTimeout(function(){el.classList.remove('show');},1100);}
function hexRgb(h){var m=h.replace('#','');return 'rgb('+parseInt(m.substr(0,2),16)+', '+parseInt(m.substr(2,2),16)+', '+parseInt(m.substr(4,2),16)+')';}
function swStrip(orig,sim){return orig.map(function(c,i){return '<button class="sw" data-hex="'+c+'" title="click: copy '+c+'   ·   shift-click: copy rgb"><span class="chip" style="background:'+sim[i]+'"></span><span class="hx">'+c+'</span></button>';}).join('');}
function wireSwatches(root){root.querySelectorAll('.sw[data-hex]').forEach(function(b){b.onclick=function(e){var hex=b.dataset.hex,txt=e.shiftKey?hexRgb(hex):hex;if(navigator.clipboard)navigator.clipboard.writeText(txt);toast(txt+' copied');b.classList.add('copied');setTimeout(function(){b.classList.remove('copied');},800);};});}
function plots(sim){return SHOWORDER.slice(0,state.show).map(function(pt){return '<div class="pcell"><div class="pl">'+PLABEL[pt]+'</div>'+P[pt](sim)+'</div>';}).join('');}

// ── controls ──
function _field(label,ctrl){return '<span class="field"><span class="cl">'+label+'</span>'+ctrl+'</span>';}
function _tgl(key,label,on){return '<button class="tgl'+(on?' on':'')+'" data-tgl="'+key+'"><span class="tgl-l">'+label+'</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>';}
function controlsHTML(){
  var colors=_field('Colors','<input type="range" min="2" max="'+maxN()+'" value="'+state.n+'" id="cnt" class="crng"><b id="cv" class="cval">'+state.n+'</b>');
  var idx={3:0,6:1,9:2}[state.show];
  var charts=_field('Charts','<input type="range" min="0" max="2" value="'+idx+'" id="shrng" class="crng"><b id="shv" class="cval">'+state.show+'</b>');
  return charts+colors+_tgl('light','Gradient',state.order==='lightness')+_tgl('rev','Reverse',state.rev)
    +_tgl('shuffle','Shuffle',state.order==='shuffle')+_tgl('bw','B&amp;W',state.gs);}
function wireControls(root,paint){
  var cnt=root.querySelector('#cnt');if(cnt)cnt.oninput=function(e){state.n=+e.target.value;var cv=root.querySelector('#cv');if(cv)cv.textContent=state.n;paint();};
  var sh=root.querySelector('#shrng');if(sh)sh.oninput=function(){state.show=[3,6,9][+sh.value];var v=root.querySelector('#shv');if(v)v.textContent=state.show;paint();};
  root.querySelectorAll('.tgl[data-tgl]').forEach(function(b){b.onclick=function(){var k=b.dataset.tgl;
    if(k==='bw')state.gs=!state.gs;
    else if(k==='rev')state.rev=!state.rev;
    else if(k==='light')state.order=(state.order==='lightness')?'default':'lightness';
    else if(k==='shuffle'){state.order=(state.order==='shuffle')?'default':'shuffle';if(state.order==='shuffle')state.shuffleSeed=Math.floor(Math.abs(lstar(pal().cols[0]))*997)%100000+1;}
    root.querySelectorAll('.tgl[data-tgl]').forEach(function(x){var kk=x.dataset.tgl,on=false;
      if(kk==='bw')on=state.gs;else if(kk==='rev')on=state.rev;
      else if(kk==='light')on=(state.order==='lightness');else if(kk==='shuffle')on=(state.order==='shuffle');
      x.classList.toggle('on',on);});
    paint();};});}

// ── live accessibility readout ──
var GLOSSARY={
  dl:"ΔL* — the smallest lightness gap between any two colors (CIE L*, a 0–100 brightness scale). Bigger means they stay distinct in grayscale or black-and-white print.",
  cvd:"Color-vision check — the smallest difference between colors as seen with simulated color-blindness. Bigger is safer.",
  d:"Deuteranopia — the most common red-green color-blindness (missing green cone), about 6% of men.",
  p:"Protanopia — red-green color-blindness (missing red cone).",
  t:"Tritanopia — blue-yellow color-blindness (rare)."
};
function term(txt,key,cls){return '<span class="term'+(cls?' '+cls:'')+'" tabindex="0" role="note" data-tip="'+GLOSSARY[key].replace(/"/g,'&quot;')+'">'+txt+'</span>';}
function bwNum(p){var m=(p.bw||'').match(/([\d.]+)/);return m?+m[1]:0;}
function cvdNums(p){var m=(p.cvd||'').match(/d([\d.]+).*?p([\d.]+).*?t([\d.]+)/);return m?{d:+m[1],p:+m[2],t:+m[3]}:{d:0,p:0,t:0};}
function bwVerdict(v){return v>=6?'Stays clear in black & white':(v>=4?'Mostly clear in black & white':'Some colors merge in black & white');}
function cvdVerdict(c){var m=Math.min(c.d,c.p,c.t);return m>=6?'Color-blind safe':(m>=4?'Mostly color-blind safe':'Take care for color-blind viewers');}
function readoutHTML(){var p=pal();
  if(p.kind==='curated'){
    var c=cvdNums(p),bw=bwNum(p),bwok=bw>=6,cvok=Math.min(c.d,c.p,c.t)>=6;
    return '<div class="ro">'
     +'<div class="ro-i"><span class="ro-ic'+(bwok?' ok':'')+'">'+(bwok?'✓':'◑')+'</span>'
       +'<span class="ro-tx">'+term('Black & white','dl')+' — <b>'+bwVerdict(bw)+'</b></span>'
       +'<span class="ro-n">ΔL* '+bw+'</span></div>'
     +'<div class="ro-i"><span class="ro-ic'+(cvok?' ok':'')+'">'+(cvok?'✓':'◔')+'</span>'
       +'<span class="ro-tx">'+term('Color-vision','cvd')+' — <b>'+cvdVerdict(c)+'</b></span>'
       +'<span class="ro-n">'+term('d','d')+' '+c.d+' · '+term('p','p')+' '+c.p+' · '+term('t','t','r')+' '+c.t+'</span></div>'
     +'</div>';
  }
  var dl=minDL(active()),ok=dl>=6;
  return '<div class="ro">'
   +'<div class="ro-i"><span class="ro-ic'+(ok?' ok':'')+'">'+(ok?'✓':'◑')+'</span>'
     +'<span class="ro-tx">'+term('Black & white','dl')+' — <b>'+bwVerdict(dl)+'</b></span>'
     +'<span class="ro-n">min ΔL* '+dl.toFixed(1)+'</span></div>'
   +'</div>';}
function metaBlock(){var p=pal(),h='<div class="meta">';
  if(p.kind==='curated'){h+='<div><b>How it’s built</b> '+p.design+'</div><div><b>Good for</b> '+p.application+'</div>'
    +'<div><b>Design targets</b> B&amp;W '+p.bw+' · CVD '+p.cvd+' (deuter / protan / tritan)</div>';}
  else if(p.kind==='cycle'){h+='<div><b>Good for</b> everyday multi-series charts — apply globally with <code>dm.set_cycle(dm.cycle(\''+state.key+'\'))</code>.</div>';}
  else {h+='<div><b>Good for</b> single-hue sequential ramps, or sample a few evenly-spaced steps for related series.</div>';}
  return h+'</div>';}

// ── rail ──
function mini(key){return '<span class="mini">'+PALETTES[key].cols.map(function(c){return '<i style="background:'+c+'"></i>';}).join('')+'</span>';}
function railHTML(){var h='';GROUPS.forEach(function(grp){h+='<div class="fh">'+grp[0]+'</div>';
  grp[1].forEach(function(k){h+='<div class="ri'+(k===state.key?' on':'')+'" data-k="'+k+'">'+mini(k)+'<span class="nm">'+PALETTES[k].name+'</span></div>';});});
  return h;}
function wireRail(){document.querySelectorAll('#dm-cat-exp .ri').forEach(function(e){e.onclick=function(){state.key=e.dataset.k;state.n=maxN();state.order='default';state.rev=false;document.getElementById('cx-rail').innerHTML=railHTML();wireRail();renderDetail();};});}

// ── detail ──
function paint(){var d=document.getElementById('cx-detail');var orig=active(),sim=simActive();
  d.querySelector('.ro-host').innerHTML=readoutHTML();
  var sh=d.querySelector('.swhost');sh.className='swhost strip'+(state.gs?' gs':'');sh.innerHTML=swStrip(orig,sim);wireSwatches(d);
  var pl=d.querySelector('.plots');pl.className='plots'+(state.gs?' gs':'');pl.innerHTML=plots(sim);
  d.querySelector('.meta-host').innerHTML=metaBlock();
  d.querySelector('.code').innerHTML='<pre>'+pyHi(pySnip())+'</pre>';}
function renderDetail(){var p=pal(),d=document.getElementById('cx-detail');
  var ey=p.group;
  d.innerHTML='<div class="d-ey">'+ey+'</div>'
    +'<div class="d-title"><h3>'+p.name+'</h3><code class="d-key" title="copy the palette name">'+state.key+'</code></div>'
    +'<p class="d-use">'+p.intent+'</p>'
    +'<div class="d-bar">'+controlsHTML()+'</div>'
    +'<div class="swhost"></div><div class="plots"></div>'
    +'<div class="code highlight"></div>'
    +'<div class="ro-host"></div>'
    +'<div class="meta-host"></div>';
  var dk=d.querySelector('.d-key');if(dk)dk.onclick=function(){if(navigator.clipboard)navigator.clipboard.writeText(state.key);toast(state.key+' copied');dk.classList.add('copied');setTimeout(function(){dk.classList.remove('copied');},900);};
  wireControls(d,paint);paint();}

document.getElementById('cx-rail').innerHTML=railHTML();wireRail();renderDetail();
})();</script>
</div>
"""


if __name__ == "__main__":
    main()
