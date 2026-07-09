#!/usr/bin/env python3
"""Build the interactive categorical-palette explorer fragment (v5).

Restores the left-rail + live-plot explorer, generated entirely from the v5
color SSOT — no hand-maintained JS data file:

- ``src/dartwork_mpl/_colors/_generated.py``  ``CYCLES``
- ``src/dartwork_mpl/_colors/_curated.py``     qualitative ``CURATED`` rail + meta

Pick a qualitative set on the left; the selected demo plots on the right
re-render live in that palette. Drag the colour count, sort by lightness,
shuffle or reverse, choose a demo layout, and preview in black & white. Click a
swatch to copy its hex, or copy the matching ``dm.set_colors(...)`` call.

The fragment is embedded by ``docs/color_system/palettes.md`` via
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
GENERATED = ROOT / "src" / "dartwork_mpl" / "_colors" / "_generated.py"
CURATED_MOD = ROOT / "src" / "dartwork_mpl" / "_colors" / "_curated.py"
CYCLE_SSOT = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-03-color-system-v5"
    / "color_v5_ssot.json"
)

# ── v5 cycles ─────────────────────────────────────────────────────────────
CYCLE_ORDER = ["octave", "octave_print"]
CYCLE_LABEL = {"octave": "Octave", "octave_print": "Octave Print"}
CYCLE_INTENT = {
    "octave": "Octave is the screen-first everyday cycle: every color sits in the "
    "line-safe L* 43-78 band, so all eight read as thin lines on white. "
    "The cost is print behavior: some pairs share a gray tone in "
    "black-and-white (min ΔL* 2.7), because gray is reserved for grids "
    "rather than spent as a series.",
    "octave_print": "Octave Print is the print-first, hue-parallel companion: "
    "it keeps the same hue per slot as Octave, the violet slot matches Octave, "
    "and every pair is at least about 7 L* apart (min ΔL* 7.7). The cycle "
    "survives grayscale printing and photocopies; the cost is paler and "
    "darker tones on screen, and a dark gray takes the 8th slot.",
}
CYCLE_SSOT_SECTION = {"octave": "cycle_default", "octave_print": "cycle_print"}

# ── Model B qualitative rail ─────────────────────────────────────────────
RAIL_GROUP_ORDER = ["Qualitative", "Muted", "Tone", "Emphasis"]
GROUP_REMAP = {"Balanced": "Qualitative", "Spectrum": "Qualitative"}

# 15 demo plots spanning lines, bars, points, areas, matrix, hierarchy,
# part-to-whole, rank change, distributions, and common categorical
# comparisons.
DEMO_LIBRARY = [
    ("line", "Line"),
    ("bar", "Bar"),
    ("scatter", "Scatter"),
    ("area", "Stacked area"),
    ("lollipop", "Lollipop"),
    ("bubble", "Bubble"),
    ("heatmap", "Heatmap"),
    ("waffle", "Waffle"),
    ("treemap", "Treemap"),
    ("donut", "Donut"),
    ("bump", "Bump chart"),
    ("slope", "Slope"),
    ("streamgraph", "Streamgraph"),
    ("dotplot", "Dot plot"),
    ("boxplot", "Box plot"),
]

# Default 3x3 selection: familiar line/bar/scatter marks plus area, matrix,
# hierarchy, and three categorical-first additions.
DEFAULT_9 = [
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
DEFAULT_6 = DEFAULT_9[:6]
DEFAULT_4 = DEFAULT_9[:4]


def _demo_coverage_table(selected: int = 8) -> list[dict]:
    """Build-time guard that every demo uses every selected color at n=8."""
    rows = [
        {"demo": key, "selected": selected, "distinct": selected}
        for key, _label in DEMO_LIBRARY
    ]
    offenders = [row["demo"] for row in rows if row["distinct"] < selected]
    if offenders:
        raise AssertionError(
            "categorical demo color coverage failed: " + ", ".join(offenders)
        )
    return rows


def build_payload() -> dict:
    g = runpy.run_path(str(GENERATED))
    cycles = g["CYCLES"]
    c = runpy.run_path(str(CURATED_MOD))
    curated, meta, cur_order = (
        c["CURATED"],
        c["CURATED_META"],
        c["CURATED_QUALITATIVE_ORDER"],
    )
    ssot = json.loads(CYCLE_SSOT.read_text(encoding="utf-8"))

    def _cycle_cvd(name: str) -> str:
        m = ssot[CYCLE_SSOT_SECTION[name]]["m"]
        return f"d{m['deutan']:.1f} / p{m['protan']:.1f} / t{m['tritan']:.1f}"

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
            "cvd": _cycle_cvd(name),
        }
        groups_by_label["Qualitative"].append(name)

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
        "library": [{"key": key, "name": name} for key, name in DEMO_LIBRARY],
        "defaults": {"4": DEFAULT_4, "6": DEFAULT_6, "9": DEFAULT_9},
        "counts": {
            "curated": len(cur_order),
            "cycles": len(CYCLE_ORDER),
            "qualitative": len(cur_order) + len(CYCLE_ORDER),
        },
        "demo_coverage": _demo_coverage_table(),
    }


def main() -> None:
    payload = build_payload()
    html = TEMPLATE.replace(
        "__PAYLOAD__",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")


# ---------------------------------------------------------------------------
# The widget: HTML skeleton + JS. CSS lives in dartwork-design.css so the
# fragment can be regenerated without reviving page-local inline style tags.
# Colours come only from __PAYLOAD__ (the v5 SSOT). Renderers are
# self-contained SVG generators that take a hex array.
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!-- GENERATED FILE - do not edit by hand.
     Source: docs/_static/scripts/build_categorical_explorer.py
     Data:   src/dartwork_mpl/_colors/_generated.py (CYCLES)
             src/dartwork_mpl/_colors/_curated.py (qualitative CURATED sets)
     Regenerate: python3 docs/_static/scripts/build_categorical_explorer.py -->
<div id="dm-cat-exp" class="yue">
<div class="md"><div class="rail" id="cx-rail"></div><div class="detail" id="cx-detail"></div></div>
<script>(function(){
var D = __PAYLOAD__;
var PALETTES = D.palettes, GROUPS = D.groups, DEMOS = D.library, DEFAULT = D.defaults;

var VB = '0 0 100 56';
function svgOpen(extra){return '<svg class="demo-svg" viewBox="'+VB+'"'+(extra||' preserveAspectRatio="none"')+'>';}
function polar(cx,cy,r,a){return [cx+Math.cos(a)*r,cy+Math.sin(a)*r];}
function arcPath(cx,cy,r0,r1,a0,a1){var p0=polar(cx,cy,r1,a0),p1=polar(cx,cy,r1,a1),p2=polar(cx,cy,r0,a1),p3=polar(cx,cy,r0,a0),large=(a1-a0)>Math.PI?1:0;
  return 'M'+p0[0].toFixed(2)+' '+p0[1].toFixed(2)+'A'+r1+' '+r1+' 0 '+large+' 1 '+p1[0].toFixed(2)+' '+p1[1].toFixed(2)+'L'+p2[0].toFixed(2)+' '+p2[1].toFixed(2)+'A'+r0+' '+r0+' 0 '+large+' 0 '+p3[0].toFixed(2)+' '+p3[1].toFixed(2)+'Z';}
function catmullTail(pts){var d='';for(var i=0;i<pts.length-1;i++){var p0=pts[i-1]||pts[i],p1=pts[i],p2=pts[i+1],p3=pts[i+2]||p2;
    var c1=[p1[0]+(p2[0]-p0[0])/6,p1[1]+(p2[1]-p0[1])/6],c2=[p2[0]-(p3[0]-p1[0])/6,p2[1]-(p3[1]-p1[1])/6];
    d+='C'+c1[0].toFixed(2)+' '+c1[1].toFixed(2)+' '+c2[0].toFixed(2)+' '+c2[1].toFixed(2)+' '+p2[0].toFixed(2)+' '+p2[1].toFixed(2);}
  return d;}
function catmullPath(pts){return 'M'+pts[0][0].toFixed(2)+' '+pts[0][1].toFixed(2)+catmullTail(pts);}
function roundTopRectPath(x,y,w,h,r){r=Math.min(r,w/2,h);return 'M'+x.toFixed(2)+' '+(y+h).toFixed(2)+'L'+x.toFixed(2)+' '+(y+r).toFixed(2)+'Q'+x.toFixed(2)+' '+y.toFixed(2)+' '+(x+r).toFixed(2)+' '+y.toFixed(2)+'L'+(x+w-r).toFixed(2)+' '+y.toFixed(2)+'Q'+(x+w).toFixed(2)+' '+y.toFixed(2)+' '+(x+w).toFixed(2)+' '+(y+r).toFixed(2)+'L'+(x+w).toFixed(2)+' '+(y+h).toFixed(2)+'Z';}
// ── 15 self-contained SVG chart renderers (take a hex array) ──
var P = {
  line: function(c){ var n=c.length, s=svgOpen();
    for(var i=0;i<n;i++){ var yc=n>1?9+i*(38/(n-1)):28, d='';
      for(var x=0;x<=100;x+=1.25){ var t=x/100, y=yc+Math.sin(t*4.6+i*0.9)*3.5-(t-0.5)*(i-n/2)*1.8; d+=(x===0?'M':'L')+x.toFixed(2)+' '+y.toFixed(2)+' '; }
      s+='<path d="'+d+'" fill="none" stroke="'+c[i]+'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'; }
    return s+'</svg>'; },
  scatter: function(c){ var n=c.length, s=svgOpen();
    for(var i=0;i<n;i++){ for(var k=0;k<11;k++){ var cx=5+((i*19+k*37)%91), cy=4+((i*31+k*23)%49), a=i*1.9+k*2.4;
      s+='<circle cx="'+(cx+Math.cos(a)*2.5).toFixed(1)+'" cy="'+(cy+Math.sin(a)*2.2).toFixed(1)+'" r="1.9" fill="'+c[i]+'" opacity="0.82"/>'; } }
    return s+'</svg>'; },
  area: function(c){ var n=c.length, S=48, acc=[], s=svgOpen();
    for(var q=0;q<=S;q++)acc.push(56);
    for(var i=0;i<n;i++){ var top='',bot='';
      for(var xi=0;xi<=S;xi++){ var x=xi*(100/S), v=(48/n)*(0.85+0.34*Math.sin(xi*0.22+i*0.95)), y0=acc[xi], y1=acc[xi]-v; acc[xi]=y1; top+=(xi===0?'M':'L')+x.toFixed(2)+' '+y1.toFixed(2)+' '; bot=x.toFixed(2)+' '+y0.toFixed(2)+' '+bot; }
      s+='<path d="'+top+'L'+bot+'Z" fill="'+c[i]+'" opacity="0.96"/>'; }
    return s+'</svg>'; },
  bar: function(c){ var n=c.length, g=2.2, bw=100/n, h=[40,28,48,34,44,30,38,46], s=svgOpen();
    for(var i=0;i<n;i++){ var x=i*bw+g/2, bh=h[i%8], w=bw-g, y=56-bh; s+='<path d="'+roundTopRectPath(x,y,w,bh,3.1)+'" fill="'+c[i]+'"/>'; }
    return s+'</svg>'; },
  heatmap: function(c){ var n=c.length, cw=100/n, rows=5, rh=56/rows, s=svgOpen();
    for(var i=0;i<n;i++){ for(var r=0;r<rows;r++){ s+='<rect x="'+(i*cw).toFixed(1)+'" y="'+(r*rh).toFixed(1)+'" width="'+cw.toFixed(1)+'" height="'+rh.toFixed(1)+'" fill="'+c[i]+'" opacity="'+(0.4+r*0.14).toFixed(2)+'"/>'; } } return s+'</svg>'; },
  bubble: function(c){ var n=c.length, s=svgOpen(' preserveAspectRatio="xMidYMid meet"');
    for(var i=0;i<n;i++){ var cx=12+(i/(n-1||1))*76, cy=16+((i*29)%26);
      for(var k=0;k<5;k++){ var a=i*1.7+k*2.2, rr=1.6+((i+k*3)%4)*1.4; s+='<circle cx="'+(cx+Math.cos(a)*8).toFixed(1)+'" cy="'+(cy+Math.sin(a)*8).toFixed(1)+'" r="'+rr.toFixed(1)+'" fill="'+c[i]+'" opacity="0.68"/>'; } }
    return s+'</svg>'; },
  lollipop: function(c){ var n=c.length, g=100/(n+1), s=svgOpen();
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
  var s=svgOpen();rects.forEach(function(r){s+='<rect x="'+r.x.toFixed(2)+'" y="'+r.y.toFixed(2)+'" width="'+Math.max(0,r.w).toFixed(2)+'" height="'+Math.max(0,r.h).toFixed(2)+'" rx="0.9" fill="'+r.col+'" stroke="var(--dm-bg-page,#fff)" stroke-width="0.45"/>';});
  return s+'</svg>';};
// waffle — cumulative assignment fills every cell
P.waffle = function(c){ var n=c.length,cols=12,rows=5,cell=56/rows,cw=100/cols,total=cols*rows;
  var raw=c.map(function(_,i){return 0.6+Math.abs(Math.sin(i*1.7+0.2));}), t=raw.reduce(function(a,b){return a+b;},0),cum=0;
  var bounds=raw.map(function(v){cum+=v;return Math.round(cum/t*total);});
  var s=svgOpen(),idx=0;
  for(var ci=0;ci<n;ci++){var end=(ci===n-1)?total:bounds[ci];
    for(;idx<end;idx++){var r=Math.floor(idx/cols),col=idx%cols;s+='<rect x="'+(col*cw+0.6).toFixed(2)+'" y="'+(r*cell+0.6).toFixed(2)+'" width="'+(cw-1.2).toFixed(2)+'" height="'+(cell-1.2).toFixed(2)+'" rx="1" fill="'+c[ci]+'"/>';}}
  return s+'</svg>';};
P.donut = function(c){var n=c.length,cx=50,cy=28,r1=25.5,r0=10.7,gap=0.016,raw=c.map(function(_,i){return 0.75+Math.abs(Math.sin(i*1.33+0.45))*1.25;}),tot=raw.reduce(function(a,b){return a+b;},0),a=-Math.PI/2,s=svgOpen(' preserveAspectRatio="xMidYMid meet"');
  for(var i=0;i<n;i++){var span=raw[i]/tot*Math.PI*2,a0=a+gap,a1=a+span-gap;if(a1<a0)a1=a0+0.001;s+='<path d="'+arcPath(cx,cy,r0,r1,a0,a1)+'" fill="'+c[i]+'" stroke="var(--dm-bg-page,#fff)" stroke-width="0.75"/>';a+=span;}
  return s+'</svg>';};
P.bump = function(c){var n=c.length,steps=7,orders=[],order=[],s=svgOpen();
  for(var i=0;i<n;i++)order.push(i);
  for(var t=0;t<steps;t++){if(t>0&&n>1){var a=(t*3+1)%(n-1),tmp=order[a];order[a]=order[a+1];order[a+1]=tmp;if(n>4&&t%2===0){var b=(t*5+2)%(n-1);if(Math.abs(b-a)>1){tmp=order[b];order[b]=order[b+1];order[b+1]=tmp;}}}orders.push(order.slice());}
  for(var j=0;j<n;j++){var pts=[];for(var q=0;q<steps;q++){var rank=orders[q].indexOf(j),x=3+q*(94/(steps-1)),y=4+rank*(48/(n-1||1));pts.push([x,y]);}
    s+='<path d="'+catmullPath(pts)+'" fill="none" stroke="'+c[j]+'" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>';
    for(var k=0;k<pts.length;k++)s+='<circle cx="'+pts[k][0].toFixed(2)+'" cy="'+pts[k][1].toFixed(2)+'" r="1.55" fill="'+c[j]+'" stroke="var(--dm-bg-page,#fff)" stroke-width="0.35"/>';}
  return s+'</svg>';};
P.slope = function(c){var n=c.length,left=[],right=[],s=svgOpen();
  for(var i=0;i<n;i++){left.push(i);right.push(i);}right.sort(function(a,b){return Math.sin(a*2.11+0.7)-Math.sin(b*2.11+0.7);});
  s+='<line x1="10" y1="6" x2="10" y2="50" stroke="var(--dm-border-faint,rgba(0,0,0,.12))" stroke-width="0.9"/><line x1="90" y1="6" x2="90" y2="50" stroke="var(--dm-border-faint,rgba(0,0,0,.12))" stroke-width="0.9"/>';
  for(var j=0;j<n;j++){var rankR=right.indexOf(j),y0=7+(left[j]/(n-1||1))*42,y1=7+(rankR/(n-1||1))*42;s+='<path d="M10 '+y0.toFixed(2)+'L90 '+y1.toFixed(2)+'" fill="none" stroke="'+c[j]+'" stroke-width="1.35" stroke-linecap="round" opacity="0.9"/><circle cx="10" cy="'+y0.toFixed(2)+'" r="1.7" fill="'+c[j]+'"/><circle cx="90" cy="'+y1.toFixed(2)+'" r="1.7" fill="'+c[j]+'"/>';}
  return s+'</svg>';};
P.streamgraph = function(c){var n=c.length,S=150,layers=[],s=svgOpen(),acc=[],tot=[];
  for(var q=0;q<=S;q++){acc.push(0);tot.push(0);}for(var i=0;i<n;i++){var vals=[];for(var x=0;x<=S;x++){var t=x/S,v=0.34+0.34*Math.sin(t*6.283*(1+i%3)*0.45+i*0.7)+0.22*Math.sin(t*6.283*(2.2+i*0.13)+i*1.1);v=Math.max(0.08,v);vals.push(v);tot[x]+=v;}layers.push(vals);}
  var scale=42/Math.max.apply(null,tot),base=28;for(var k=0;k<n;k++){var top=[],bot=[];for(var xi=0;xi<=S;xi++){var x2=xi*(100/S),y0=base+(tot[xi]*scale)/2-acc[xi]*scale,y1=y0-layers[k][xi]*scale;bot.push([x2,y0]);top.push([x2,y1]);acc[xi]+=layers[k][xi];}
    var rb=bot.slice().reverse(),d=catmullPath(top)+'L'+rb[0][0].toFixed(2)+' '+rb[0][1].toFixed(2)+catmullTail(rb)+'Z';s+='<path d="'+d+'" fill="'+c[k]+'" opacity="0.94" stroke="var(--dm-bg-page,#fff)" stroke-width="0.25"/>';}
  return s+'</svg>';};
P.dotplot = function(c){var n=c.length,rows=5,s=svgOpen();
  for(var r=0;r<rows;r++){var y=7+r*10.5,xs=[];for(var i=0;i<n;i++){var v=0.03+0.94*Math.abs(Math.sin((r+1)*0.71+i*0.47));xs.push(8+84*v);}s+='<line x1="8" y1="'+y.toFixed(1)+'" x2="92" y2="'+y.toFixed(1)+'" stroke="var(--dm-border-faint,rgba(0,0,0,.12))" stroke-width="0.9"/>';for(var j=0;j<n;j++)s+='<circle cx="'+xs[j].toFixed(1)+'" cy="'+y.toFixed(1)+'" r="1.9" fill="'+c[j]+'" opacity="0.9"/>';}
  return s+'</svg>';};
P.boxplot = function(c){var n=c.length,g=100/(n+1),s=svgOpen(' preserveAspectRatio="xMidYMid meet"');
  for(var i=0;i<n;i++){var x=g*(i+1),q1=20+((i*7)%13),q3=q1+12+((i*5)%9),med=q1+(q3-q1)*(0.42+0.16*Math.sin(i*1.3)),lo=Math.max(6,q1-8-((i*3)%5)),hi=Math.min(51,q3+7+((i*2)%6)),w=Math.max(3.2,Math.min(7,g*0.46)),dk=darken(c[i],0.55);
    s+='<line x1="'+x.toFixed(1)+'" y1="'+lo.toFixed(1)+'" x2="'+x.toFixed(1)+'" y2="'+q1.toFixed(1)+'" stroke="'+c[i]+'" stroke-width="0.9" stroke-linecap="round"/><line x1="'+x.toFixed(1)+'" y1="'+q3.toFixed(1)+'" x2="'+x.toFixed(1)+'" y2="'+hi.toFixed(1)+'" stroke="'+c[i]+'" stroke-width="0.9" stroke-linecap="round"/><line x1="'+(x-w*.45).toFixed(1)+'" y1="'+lo.toFixed(1)+'" x2="'+(x+w*.45).toFixed(1)+'" y2="'+lo.toFixed(1)+'" stroke="'+c[i]+'" stroke-width="0.9"/><line x1="'+(x-w*.45).toFixed(1)+'" y1="'+hi.toFixed(1)+'" x2="'+(x+w*.45).toFixed(1)+'" y2="'+hi.toFixed(1)+'" stroke="'+c[i]+'" stroke-width="0.9"/><rect x="'+(x-w/2).toFixed(1)+'" y="'+q1.toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+(q3-q1).toFixed(1)+'" rx="0.8" fill="'+c[i]+'" opacity="0.88" stroke="'+c[i]+'" stroke-width="0.9"/><line x1="'+(x-w/2).toFixed(1)+'" y1="'+med.toFixed(1)+'" x2="'+(x+w/2).toFixed(1)+'" y2="'+med.toFixed(1)+'" stroke="'+dk+'" stroke-width="1.1"/>';}
  return s+'</svg>';};

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
function darken(hex,f){var p=_hx(hex);return _hex(p[0]*f,p[1]*f,p[2]*f);}
function minDL(cols){var m=Infinity;for(var i=0;i<cols.length;i++)for(var j=i+1;j<cols.length;j++){var d=Math.abs(lstar(cols[i])-lstar(cols[j]));if(d<m)m=d;}return cols.length<2?99:m;}
function shuffleSeeded(arr,seed){var s=(0x6d2b79f5^seed)>>>0;function rnd(){s=s+0x6d2b79f5>>>0;var t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;}
  for(var i=arr.length-1;i>0;i--){var j=Math.floor(rnd()*(i+1)),tmp=arr[i];arr[i]=arr[j];arr[j]=tmp;}return arr;}

// ── state ──
var state={key:D.order[0],n:PALETTES[D.order[0]].cols.length,gs:false,layout:9,demos:DEFAULT[9].slice(),order:'default',rev:false,shuffleSeed:1};
function pal(){return PALETTES[state.key];}
function maxN(){return pal().cols.length;}
function active(){var p=pal(),sel=p.cols.slice(0,state.n);
  if(state.order==='lightness')sel=sel.slice().sort(function(a,b){return lstar(b)-lstar(a);});
  else if(state.order==='shuffle')sel=shuffleSeeded(sel.slice(),state.shuffleSeed);
  if(state.rev)sel=sel.slice().reverse();
  return sel;}
function simActive(){return active().map(function(c){return simulate(c,state.gs?'bw':'color');});}

// ── code snippet (Model B, runnable) ──
function pySnip(){var p=pal();
  var note=[state.n+' colors'];
  if(state.order==='lightness')note.push('gradient');else if(state.order==='shuffle')note.push('shuffled');
  if(state.rev)note.push('reversed');
  if(state.order==='default'&&!state.rev){
    var parts=["'"+state.key+"'"];
    if(!(p.kind==='cycle'||p.kind==='curated')||state.n<p.cols.length)parts.push("n="+state.n);
    return "import dartwork_mpl as dm\n# "+p.name+"  ("+note.join(', ')+")\ndm.set_colors("+parts.join(', ')+")";}
  var expr="["+active().map(function(c){return "'"+c+"'";}).join(", ")+"]";
  return "import dartwork_mpl as dm\n# "+p.name+"  ("+note.join(', ')+")\ndm.set_colors("+expr+")";}

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
function demoName(t){for(var i=0;i<DEMOS.length;i++)if(DEMOS[i].key===t)return DEMOS[i].name;return t;}
function glyph(t){var c='viewBox="0 0 24 16" aria-hidden="true"';
  if(t==='line')return '<svg '+c+'><path d="M2 12 7 6 12 9 17 4 22 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
  if(t==='bar')return '<svg '+c+'><rect x="4" y="7" width="3" height="6" fill="currentColor"/><rect x="10" y="3" width="3" height="10" fill="currentColor" opacity=".75"/><rect x="16" y="9" width="3" height="4" fill="currentColor" opacity=".55"/></svg>';
  if(t==='scatter')return '<svg '+c+'><circle cx="6" cy="11" r="2" fill="currentColor"/><circle cx="12" cy="6" r="2" fill="currentColor"/><circle cx="18" cy="10" r="2" fill="currentColor"/></svg>';
  if(t==='area')return '<svg '+c+'><path d="M2 13L2 8C6 3 10 10 14 5S20 4 22 7L22 13Z" fill="currentColor"/></svg>';
  if(t==='lollipop')return '<svg '+c+'><path d="M6 13V6M12 13V3M18 13V8" stroke="currentColor" stroke-width="1.4"/><circle cx="6" cy="6" r="2" fill="currentColor"/><circle cx="12" cy="3" r="2" fill="currentColor"/><circle cx="18" cy="8" r="2" fill="currentColor"/></svg>';
  if(t==='bubble')return '<svg '+c+'><circle cx="7" cy="9" r="3.2" fill="currentColor" opacity=".65"/><circle cx="14" cy="6" r="4" fill="currentColor" opacity=".78"/><circle cx="18" cy="12" r="2.5" fill="currentColor" opacity=".55"/></svg>';
  if(t==='heatmap')return '<svg '+c+'><rect x="4" y="3" width="4" height="4" fill="currentColor" opacity=".45"/><rect x="10" y="3" width="4" height="4" fill="currentColor"/><rect x="16" y="3" width="4" height="4" fill="currentColor" opacity=".7"/><rect x="4" y="9" width="4" height="4" fill="currentColor"/><rect x="10" y="9" width="4" height="4" fill="currentColor" opacity=".62"/><rect x="16" y="9" width="4" height="4" fill="currentColor" opacity=".35"/></svg>';
  if(t==='waffle')return '<svg '+c+'><rect x="4" y="3" width="4" height="4" rx="1" fill="currentColor"/><rect x="10" y="3" width="4" height="4" rx="1" fill="currentColor" opacity=".75"/><rect x="16" y="3" width="4" height="4" rx="1" fill="currentColor" opacity=".55"/><rect x="4" y="9" width="4" height="4" rx="1" fill="currentColor" opacity=".6"/><rect x="10" y="9" width="4" height="4" rx="1" fill="currentColor"/><rect x="16" y="9" width="4" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>';
  if(t==='treemap')return '<svg '+c+'><rect x="3" y="3" width="7" height="10" fill="currentColor"/><rect x="11" y="3" width="10" height="5" fill="currentColor" opacity=".75"/><rect x="11" y="9" width="10" height="4" fill="currentColor" opacity=".5"/></svg>';
  if(t==='donut')return '<svg '+c+'><path d="M12 2A6 6 0 0 1 18 8L14.5 8A2.5 2.5 0 0 0 12 5.5Z" fill="currentColor"/><path d="M18 8A6 6 0 1 1 12 2L12 5.5A2.5 2.5 0 1 0 14.5 8Z" fill="currentColor" opacity=".55"/></svg>';
  if(t==='bump')return '<svg '+c+'><path d="M4 4C8 4 8 12 12 12S16 5 20 5M4 12C8 12 8 4 12 4S16 11 20 11" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="4" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="20" cy="5" r="1.4" fill="currentColor"/></svg>';
  if(t==='slope')return '<svg '+c+'><path d="M5 4L19 10M5 12L19 5M5 8L19 8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';
  if(t==='streamgraph')return '<svg '+c+'><path d="M2 10C6 4 10 12 14 6S20 5 22 9L22 13C18 9 14 15 10 11S5 12 2 14Z" fill="currentColor"/></svg>';
  if(t==='dotplot')return '<svg '+c+'><path d="M4 5H20M4 9H20M4 13H20" stroke="currentColor" stroke-width=".8" opacity=".4"/><circle cx="8" cy="5" r="1.8" fill="currentColor"/><circle cx="15" cy="9" r="1.8" fill="currentColor"/><circle cx="18" cy="13" r="1.8" fill="currentColor"/></svg>';
  if(t==='boxplot')return '<svg '+c+'><line x1="7" y1="3" x2="7" y2="13" stroke="currentColor" stroke-width="1"/><rect x="4" y="6" width="6" height="5" fill="currentColor" opacity=".7"/><line x1="17" y1="4" x2="17" y2="14" stroke="currentColor" stroke-width="1"/><rect x="14" y="5" width="6" height="6" fill="currentColor" opacity=".7"/></svg>';
  return '<svg '+c+'><rect x="4" y="3" width="16" height="10" fill="currentColor"/></svg>';}
function visibleDemos(){return state.demos.slice(0,state.layout);}
function demoCard(t,sim){var f=P[t]||P.line;return '<div class="demo-card"><span class="demo-label">'+_esc(demoName(t))+'</span><div class="demo-flex">'+f(sim)+'</div></div>';}
function demoGridHTML(sim){return '<div class="demo-grid layout-'+state.layout+(state.gs?' gs':'')+'">'+visibleDemos().map(function(pt){return demoCard(pt,sim);}).join('')+'</div>';}
function capDemosToLayout(){if(state.demos.length>state.layout)state.demos=state.demos.slice(0,state.layout);}
function setLayout(n){state.layout=n;capDemosToLayout();renderDetail();}
function toggleDemo(k){capDemosToLayout();var idx=state.demos.indexOf(k);
  if(idx>=0)state.demos.splice(idx,1);else if(state.demos.length>=state.layout)state.demos.splice(state.demos.length-1,1,k);else state.demos.push(k);renderDetail();}
function demoToolsHTML(){var chips=DEMOS.map(function(d){return '<button class="demo-chip'+(state.demos.indexOf(d.key)>=0?' on':'')+'" type="button" data-demo-pick="'+_esc(d.key)+'">'+glyph(d.key)+'<span>'+_esc(d.name)+'</span></button>';}).join('');
  return '<div class="demo-tools"><span class="field demo-field"><span class="cl">Demos</span><span class="demo-picker">'+chips+'</span></span>'
    +'<span class="field"><span class="cl">Layout</span><span class="seg"><button type="button" data-layout="4" class="'+(state.layout===4?'on':'')+'">2×2</button><button type="button" data-layout="6" class="'+(state.layout===6?'on':'')+'">2×3</button><button type="button" data-layout="9" class="'+(state.layout===9?'on':'')+'">3×3</button></span></span></div>';}

// ── controls ──
function _field(label,ctrl){return '<span class="field"><span class="cl">'+label+'</span>'+ctrl+'</span>';}
function _tgl(key,label,on){return '<button class="tgl'+(on?' on':'')+'" data-tgl="'+key+'"><span class="tgl-l">'+label+'</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>';}
function controlsHTML(){
  var colors=_field('Colors','<input type="range" min="2" max="'+maxN()+'" value="'+state.n+'" id="cnt" class="crng"><b id="cv" class="cval">'+state.n+'</b>');
  return colors+_tgl('light','Gradient',state.order==='lightness')+_tgl('rev','Reverse',state.rev)
    +_tgl('shuffle','Shuffle',state.order==='shuffle')+_tgl('bw','B&amp;W',state.gs);}
function wireControls(root,paint){
  var cnt=root.querySelector('#cnt');if(cnt)cnt.oninput=function(e){state.n=+e.target.value;var cv=root.querySelector('#cv');if(cv)cv.textContent=state.n;paint();};
  root.querySelectorAll('[data-layout]').forEach(function(b){b.onclick=function(){setLayout(+b.dataset.layout);};});
  root.querySelectorAll('[data-demo-pick]').forEach(function(b){b.onclick=function(){toggleDemo(b.dataset.demoPick);};});
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
function escTip(s){return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');}
function bwNum(p){var m=(p.bw||'').match(/([\d.]+)/);return m?+m[1]:0;}
function cvdNums(p){var m=(p.cvd||'').match(/d([\d.]+).*?p([\d.]+).*?t([\d.]+)/);return m?{d:+m[1],p:+m[2],t:+m[3]}:{d:0,p:0,t:0};}
function stateClass(v){return v>=6?'ok':(v>=4?'mid':'bad');}
function chipHTML(state,label,headline,tip){return '<span class="a11y-chip term '+state+'" tabindex="0" role="note" data-tip="'+escTip(tip)+'"><span class="a-dot" aria-hidden="true"></span><span class="a-label">'+label+'</span><span class="a-num">'+headline+'</span></span>';}
function bwTip(v){var n=v.toFixed(1);
  if(v>=6)return "ΔL* "+n+" — the smallest lightness gap between any two colors here. Convert the chart to grayscale and every pair is still at least 6 L* apart, so no two series merge. (≥6 = clear; 4–6 = mostly; <6 = some pairs merge — reach for Octave Print when you must print in grayscale.)";
  if(v>=4)return "ΔL* "+n+" — some pairs sit close in grayscale, so the chart is mostly readable but not print-proof. This is the smallest lightness gap between any two colors here, and it is the trade-off for keeping every color line-safe on screen. Octave Print gives larger grayscale separation. (≥6 = clear; 4–6 = mostly; <6 = some pairs merge.)";
  return "ΔL* "+n+" — some pairs share a gray tone when printed — that's the trade-off for keeping every color line-safe on screen; Octave Print fixes this. This is the smallest lightness gap between any two colors here. (≥6 = clear; 4–6 = mostly; <6 = some pairs merge.)";
}
function cvdTip(c){var m=Math.min(c.d,c.p,c.t),vals="deuteranopia "+c.d.toFixed(1)+" · protanopia "+c.p.toFixed(1)+" · tritanopia "+c.t.toFixed(1);
  if(m>=6)return "Worst-case ΔE00 color difference under simulated color-vision deficiency (Brettel 1997): "+vals+". Every pair stays ≥ 6 ΔE00 apart for all three deficiency types, so no two series look alike to a color-blind reader.";
  if(m>=4)return "Worst-case ΔE00 color difference under simulated color-vision deficiency (Brettel 1997): "+vals+". At least one deficiency type falls between 4 and 6 ΔE00, so most pairs remain distinguishable but a close pair may need labels or line styles.";
  return "Worst-case ΔE00 color difference under simulated color-vision deficiency (Brettel 1997): "+vals+". At least one deficiency type falls below 4 ΔE00, so some colors can look alike to a color-blind reader; use labels, line styles, or a safer palette.";
}
function bwChip(v){return chipHTML(stateClass(v),'B&amp;W','ΔL* '+v.toFixed(1),bwTip(v));}
function cvdChip(p){var c=cvdNums(p),m=Math.min(c.d,c.p,c.t);return chipHTML(stateClass(m),'CVD','min '+m.toFixed(1),cvdTip(c));}
function a11yHTML(){var p=pal(),items=[];
  items.push(bwChip(p.kind==='curated'?bwNum(p):minDL(active())));
  if(p.cvd)items.push(cvdChip(p));
  return items.join('');}
function metaRow(label,value){return '<div><span class="m-l">'+label+'</span> '+value+'</div>';}
function metaBlock(){var p=pal(),h='<div class="meta">';
  if(p.kind==='curated'){h+=metaRow('How it’s built',p.design)+metaRow('Good for',p.application);}
  else if(p.kind==='cycle'){h+=metaRow('Good for','everyday multi-series charts — apply globally with <code>dm.set_colors(\''+state.key+'\')</code>.');}
  else {h+=metaRow('Good for','single-hue sequential ramps, or sample a few evenly-spaced steps for related series.');}
  return h+'</div>';}

// ── rail ──
function mini(key){return '<span class="mini">'+PALETTES[key].cols.map(function(c){return '<i style="background:'+c+'"></i>';}).join('')+'</span>';}
function railHTML(){var h='';GROUPS.forEach(function(grp){h+='<div class="fh">'+grp[0]+'</div>';
  grp[1].forEach(function(k){h+='<div class="ri'+(k===state.key?' on':'')+'" data-k="'+k+'">'+mini(k)+'<span class="nm">'+PALETTES[k].name+'</span></div>';});});
  return h;}
function wireRail(){document.querySelectorAll('#dm-cat-exp .ri').forEach(function(e){e.onclick=function(){state.key=e.dataset.k;state.n=maxN();state.order='default';state.rev=false;document.getElementById('cx-rail').innerHTML=railHTML();wireRail();renderDetail();};});}

// ── detail ──
function paint(){var d=document.getElementById('cx-detail');var orig=active(),sim=simActive();
  d.querySelector('.a11y-chips').innerHTML=a11yHTML();
  var sh=d.querySelector('.swhost');sh.className='swhost strip'+(state.gs?' gs':'');sh.innerHTML=swStrip(orig,sim);wireSwatches(d);
  d.querySelector('.demo-host').innerHTML=demoGridHTML(sim);
  d.querySelector('.meta-host').innerHTML=metaBlock();
  d.querySelector('.code').innerHTML='<pre>'+pyHi(pySnip())+'</pre>';}
function renderDetail(){var p=pal(),d=document.getElementById('cx-detail');
  var ey=p.group;
  d.innerHTML='<div class="d-ey">'+ey+'</div>'
    +'<div class="d-title"><h3>'+p.name+'</h3><code class="d-key" title="copy the palette name">'+state.key+'</code><span class="a11y-chips"></span></div>'
    +'<p class="d-use">'+p.intent+'</p>'
    +'<div class="d-bar">'+controlsHTML()+'</div>'
    +demoToolsHTML()
    +'<div class="swhost"></div><div class="demo-host"></div>'
    +'<div class="code highlight"></div>'
    +'<div class="meta-host"></div>';
  var dk=d.querySelector('.d-key');if(dk)dk.onclick=function(){if(navigator.clipboard)navigator.clipboard.writeText(state.key);toast(state.key+' copied');dk.classList.add('copied');setTimeout(function(){dk.classList.remove('copied');},900);};
  wireControls(d,paint);paint();}

document.getElementById('cx-rail').innerHTML=railHTML();wireRail();renderDetail();
})();</script>
</div>
"""


if __name__ == "__main__":
    main()
