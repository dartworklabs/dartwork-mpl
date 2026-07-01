#!/usr/bin/env python3
"""Build the interactive palette *specimen* showcase (``palette_showcase.html``).

Thesis: every dc palette is a *verified* even-L* ladder. The signature
element surfaces the science most galleries hide — per-palette B&W
separability (ΔL*) and color-vision distance (deuter/protan/tritan).

Colors, L*, and the verification stats are read from the generator SSOT
(``dm_palettes_gen.json``); only the editorial copy (name / family / band /
intent) lives here. The public ``dc.<name>`` swatch labels come from the rename
SSOT (``build_dc_palettes.NAME``) so they can never drift from what the package
actually registers. Run after ``gen_palettes.py``:

    python3 build_showcase.py
"""

from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GEN_JSON = SCRIPT_DIR / "dm_palettes_gen.json"
OUT = SCRIPT_DIR.parent / "palette_showcase.html"


def _public_names() -> dict[str, str]:
    """Generator key -> public ``dc.<name>``. The rename SSOT lives in
    ``build_dc_palettes.NAME``; import it so the showcase's ``dc.`` labels can
    never drift from what the package registers (``teal_seq`` -> ``dc.teal``,
    ``focus`` -> ``dc.teal_accent``, ``muted`` -> ``dc.pastel``, …)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_bdc_namemap", SCRIPT_DIR / "build_dc_palettes.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.NAME


PUBLIC = _public_names()

# editorial copy only — colors / L* / verify come from the generator SSOT
# (name, family, band, intent)
META = {
    "teal_seq": (
        "Teal Sequential",
        "Sequential",
        "single hue",
        "Categories with a natural ORDER — rank reads straight off the lightness.",
    ),
    "indigo_seq": (
        "Indigo Sequential",
        "Sequential",
        "single hue",
        "Ordered categories in a cooler, corporate register — tiers, periods, buckets.",
    ),
    "coral_seq": (
        "Coral Sequential",
        "Sequential",
        "single hue",
        "Ordered categories, warm & human — intensity, recency, heat / severity.",
    ),
    "teal_indigo": (
        "Teal → Indigo",
        "Analogous",
        "cool arc",
        "A few related series that feel like ONE mood, not a rainbow.",
    ),
    "forest": (
        "Forest",
        "Analogous",
        "green arc",
        "Related series in a natural register — ESG, agriculture, growth themes.",
    ),
    "blue_orange": (
        "Blue / Orange",
        "Duo",
        "180° split",
        "Two opposed groups on the most colorblind-robust opposition.",
    ),
    "teal_coral": (
        "Teal / Coral",
        "Duo",
        "180° split",
        "Two opposed groups in the house-teal brand voice.",
    ),
    "trustworthy": (
        "Trustworthy · default",
        "Balanced",
        "teal + neutrals",
        "The everyday DEFAULT — 4–8 unrelated categories, muted-but-distinct.",
    ),
    "muted": (
        "Muted Pastel",
        "Muted",
        "low chroma",
        "Soft editorial set for dense dashboards where vivid color would shout.",
    ),
    "dusty": (
        "Dusty",
        "Muted",
        "vintage muted",
        "A deeper, more vintage muted — moody editorial, dark-on-cream, retro.",
    ),
    "vivid": (
        "Vivid",
        "Vivid",
        "colourful default",
        "MANY unrelated categories — the intuitive colourful default (merges the old spectrum + bold).",
    ),
    "neon": (
        "Neon",
        "Vivid",
        "max chroma · electric",
        "Maximum-chroma electric set for dark UI, hero charts, few bold categories.",
    ),
    "ember": (
        "Ember",
        "Tone",
        "warm · vibrant",
        "The saturated WARM categorical — golden-hour energy without earth's muteness.",
    ),
    "accessible": (
        "Accessible · Okabe-Ito",
        "Accessible",
        "CVD gold standard",
        "When colorblind-safety is mandatory — the proven CUD 8-color set.",
    ),
    "gray_seq": (
        "Neutral",
        "Neutral",
        "hue-free ramp",
        "Ordered AMOUNT with no hue meaning — the most print- & CVD-proof ramp.",
    ),
    "warm_gray": (
        "Warm Gray",
        "Neutral",
        "warm taupe",
        "Hue-free ordered ramp with a warm cast — cream paper, editorial warmth.",
    ),
    "cool_gray": (
        "Cool Gray",
        "Neutral",
        "cool slate",
        "Hue-free ordered ramp with a cool cast — tech, clinical, cool brands.",
    ),
    "focus": (
        "Teal Accent",
        "Emphasis",
        "1 accent + 7 neutrals",
        "Highlight ONE series; everything else recedes to grey. 'Color the one thing.'",
    ),
    "focus_warm": (
        "Coral Accent",
        "Emphasis",
        "1 accent + 7 neutrals",
        "Highlight one series with a WARM accent instead of teal.",
    ),
    "coolwarm": (
        "Cool → Warm",
        "Diverging",
        "pale centre",
        "Ordered data with a meaningful MIDPOINT — change, correlation, z-scores.",
    ),
    "teal_amber_div": (
        "Teal → Amber",
        "Diverging",
        "pale centre",
        "The diverging intent in the house voice — teal ↔ amber through a pale centre.",
    ),
    "purple_green": (
        "Purple / Green",
        "Diverging",
        "tritan-robust",
        "Diverging purple to green — the tritan-robust axis blue-orange & teal-amber lack.",
    ),
    "earth": (
        "Earth / Natural",
        "Tone",
        "warm · earthy",
        "Categorical series in a warm, organic register — sustainability, geography.",
    ),
    "jewel": (
        "Jewel / Premium",
        "Tone",
        "deep · saturated",
        "Rich, deep, saturated variety for premium / luxury editorial.",
    ),
}
ORDER = [
    "teal_seq",
    "indigo_seq",
    "coral_seq",
    "teal_indigo",
    "forest",
    "blue_orange",
    "teal_coral",
    "trustworthy",
    "muted",
    "dusty",
    "vivid",
    "neon",
    "ember",
    "accessible",
    "gray_seq",
    "warm_gray",
    "cool_gray",
    "focus",
    "focus_warm",
    "coolwarm",
    "teal_amber_div",
    "purple_green",
    "earth",
    "jewel",
]
FAM_DESC = {
    "Balanced": "general-purpose categorical — reach for these first",
    "Vivid": "full-hue vibrant sets — many categories separated by color alone",
    "Sequential": "single-hue lightness ramps — encode a natural order",
    "Analogous": "one-mood hue arcs — cohesion over maximum distinctness",
    "Duo": "two opposed groups — the most colorblind-robust structure",
    "Diverging": "two-ended, pale centre — ordered ± data",
    "Emphasis": "one accent + graded neutrals — color the one thing",
    "Muted": "soft, editorial sets for dense or background work",
    "Tone": "aesthetic registers reached for by mood",
    "Neutral": "hue-free ramps — amount without category",
    "Accessible": "fixed CVD gold standard, shipped verbatim",
}
FAM_ORDER = [
    "Balanced",
    "Vivid",
    "Sequential",
    "Analogous",
    "Duo",
    "Diverging",
    "Emphasis",
    "Muted",
    "Tone",
    "Neutral",
    "Accessible",
]


def _hex(c: str) -> str:
    return c if c.startswith("#") else "#" + c


def build() -> str:
    gen = json.loads(GEN_JSON.read_text(encoding="utf-8"))

    def cvd_class(v: dict) -> str:
        m = min(v["deuter"], v["protan"], v["tritan"])
        return "strong" if m >= 8 else "ok" if m >= 6 else "soft"

    def swatches(key: str) -> str:
        e = gen[key]
        cols = [_hex(c if isinstance(c, str) else c[1]) for c in e["colors"]]
        ls = e.get("Lstar") or [0] * len(cols)
        out = []
        for i, (h, lv) in enumerate(zip(cols, ls, strict=False)):
            out.append(
                f'<button class="sw" style="--c:{h}" data-hex="{h.upper()}"'
                f' data-l="L* {lv:.0f}" aria-label="dc.{PUBLIC[key]}{i} {h.upper()}'
                f' L* {lv:.0f}"></button>'
            )
        return "\n".join(out)

    def specimen(key: str) -> str:
        name, fam, band, intent = META[key]
        v = gen[key]["verify"]
        bw = v["bw_min_dLstar"]
        bwtxt = f"B&amp;W ΔL* {bw:.1f}" if bw and bw >= 2 else "B&amp;W exempt"
        cvdtxt = f"CVD {v['deuter']:.1f}/{v['protan']:.1f}/{v['tritan']:.1f}"
        cc = cvd_class(v)
        return f"""    <article class="spec" data-fam="{fam}">
      <div class="spec-id">
        <code class="pid">dc.{PUBLIC[key]}</code>
        <span class="pname">{name}</span>
        <span class="pband">{band}</span>
        <p class="pintent">{intent}</p>
        <div class="verify">
          <span class="vchip">{bwtxt}</span>
          <span class="vchip v-{cc}">{cvdtxt}</span>
        </div>
      </div>
      <div class="ladder">
{swatches(key)}
      </div>
    </article>"""

    groups = []
    for fam in FAM_ORDER:
        keys = [k for k in ORDER if META[k][1] == fam]
        if not keys:
            continue
        specs = "\n".join(specimen(k) for k in keys)
        groups.append(f"""  <section class="fam">
    <header class="fam-h">
      <span class="fam-eyebrow">{fam}</span>
      <span class="fam-n">{len(keys)}</span>
      <p class="fam-desc">{FAM_DESC[fam]}</p>
    </header>
{specs}
  </section>""")
    return _SHELL.format(groups="\n".join(groups), n=len(ORDER))


_SHELL = """<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dartwork palettes — specimen</title>
<style>
:root {{
  --ink:#15161c; --ink-2:#4a4f5c; --muted:#8a90a0; --bg:#fdfdfc;
  --panel:#f7f6f3; --line:#ececea; --line-2:#e3e2df; --teal:#12a594;
  --teal-ink:#0c7d70; --soft:#c2410c; --ok:#b8860b; --strong:#1a8f6a;
  --mono:ui-monospace,"JetBrains Mono","SF Mono",Menlo,monospace;
  --sans:"Inter","Pretendard Variable",Pretendard,system-ui,sans-serif;
  --ease:cubic-bezier(.4,0,.2,1);
}}
html[data-theme="dark"] {{
  --ink:#eceef3; --ink-2:#b6bccb; --muted:#7e8696; --bg:#16171c;
  --panel:#1d1f26; --line:#2a2c34; --line-2:#33363f; --teal:#2dd4bf;
  --teal-ink:#5eead4; --soft:#fb923c; --ok:#fbbf24; --strong:#34d399;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans);
  -webkit-font-smoothing:antialiased; line-height:1.5; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:clamp(28px,5vw,60px) clamp(20px,4vw,48px) 88px; }}
.hero {{ display:flex; justify-content:space-between; align-items:flex-start; gap:24px;
  padding-bottom:30px; border-bottom:1px solid var(--line-2); }}
.eyebrow {{ font-family:var(--mono); font-size:11px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--teal-ink); margin:0 0 14px; }}
.htitle {{ font-size:clamp(28px,5vw,44px); line-height:1.05; font-weight:680;
  letter-spacing:-.02em; margin:0 0 14px; max-width:16ch; }}
.htitle em {{ font-style:normal; color:var(--teal); }}
.hsub {{ font-size:15px; color:var(--ink-2); margin:0; max-width:46ch; }}
.hsub code {{ font-family:var(--mono); font-size:.86em; color:var(--ink);
  background:var(--panel); padding:1px 6px; border-radius:5px; }}
.toggle {{ font-family:var(--mono); font-size:12px; color:var(--muted); background:none;
  border:1px solid var(--line-2); border-radius:999px; padding:7px 14px; cursor:pointer;
  white-space:nowrap; transition:.18s var(--ease); }}
.toggle:hover {{ color:var(--ink); border-color:var(--muted); }}
.rail {{ position:sticky; top:0; z-index:5; display:flex; flex-wrap:wrap; gap:7px;
  padding:16px 0; margin-bottom:6px;
  background:linear-gradient(var(--bg) 72%,transparent); backdrop-filter:blur(2px); }}
.fchip {{ font-family:var(--mono); font-size:11.5px; color:var(--ink-2); background:none;
  border:1px solid var(--line-2); border-radius:999px; padding:5px 12px; cursor:pointer;
  transition:.16s var(--ease); }}
.fchip:hover {{ border-color:var(--teal); color:var(--teal-ink); }}
.fchip.on {{ background:var(--teal); border-color:var(--teal); color:#fff; }}
html[data-theme="dark"] .fchip.on {{ color:#0b1110; }}
.fam {{ padding-top:32px; }}
.fam-h {{ display:grid; grid-template-columns:auto auto 1fr; align-items:baseline;
  gap:12px; padding-bottom:12px; }}
.fam-eyebrow {{ font-family:var(--mono); font-size:12.5px; font-weight:600;
  letter-spacing:.14em; text-transform:uppercase; color:var(--ink); }}
.fam-n {{ font-family:var(--mono); font-size:11px; color:var(--muted);
  border:1px solid var(--line-2); border-radius:999px; padding:1px 8px; }}
.fam-desc {{ font-size:13px; color:var(--muted); margin:0; justify-self:start; }}
.spec {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:28px; align-items:center;
  padding:18px 0; border-top:1px solid var(--line); }}
.pid {{ font-family:var(--mono); font-size:13.5px; font-weight:500; color:var(--teal-ink); }}
.pname {{ font-size:13.5px; color:var(--ink); margin-left:10px; font-weight:560; }}
.pband {{ font-family:var(--mono); font-size:11px; color:var(--muted); margin-left:10px; }}
.pintent {{ font-size:13px; color:var(--ink-2); margin:7px 0 9px; max-width:62ch; }}
.verify {{ display:flex; gap:7px; }}
.vchip {{ font-family:var(--mono); font-size:10.5px; padding:2px 8px; border-radius:5px;
  border:1px solid var(--line-2); color:var(--muted); }}
.v-strong {{ color:var(--strong); border-color:color-mix(in srgb,var(--strong) 35%,transparent); }}
.v-ok {{ color:var(--ok); border-color:color-mix(in srgb,var(--ok) 35%,transparent); }}
.v-soft {{ color:var(--soft); border-color:color-mix(in srgb,var(--soft) 35%,transparent); }}
.ladder {{ display:flex; gap:3px; }}
.sw {{ position:relative; width:34px; height:34px; border:none; border-radius:5px;
  background:var(--c); cursor:pointer; padding:0; outline:none;
  box-shadow:inset 0 0 0 1px rgba(127,127,127,.22); transition:transform .16s var(--ease); }}
.sw:hover, .sw:focus-visible {{ transform:translateY(-4px); z-index:3; }}
.sw:focus-visible {{ box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--teal); }}
.sw::after {{ content:attr(data-hex) " · " attr(data-l); position:absolute; left:50%;
  bottom:calc(100% + 7px); transform:translateX(-50%) translateY(3px); font-family:var(--mono);
  font-size:10.5px; white-space:nowrap; color:var(--bg); background:var(--ink); padding:3px 7px;
  border-radius:5px; opacity:0; pointer-events:none; transition:.16s var(--ease); }}
.sw:hover::after, .sw:focus-visible::after {{ opacity:1; transform:translateX(-50%) translateY(0); }}
.copied::after {{ content:"copied " attr(data-hex) " ✓"; }}
.foot {{ margin-top:56px; padding-top:22px; border-top:1px solid var(--line-2);
  font-size:12.5px; color:var(--muted); }}
.foot code {{ font-family:var(--mono); color:var(--ink-2); }}
@media (max-width:680px) {{
  .spec {{ grid-template-columns:1fr; gap:14px; }}
  .sw {{ width:30px; height:30px; }} .hero {{ flex-direction:column; }}
}}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none!important; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div>
      <p class="eyebrow">dartwork · categorical color</p>
      <h1 class="htitle">Every palette is a <em>verified</em> ladder.</h1>
      <p class="hsub">{n} categorical palettes, each built on an even-L*
      lightness ramp and checked for grayscale separability and color-vision
      safety. Hover a swatch for its hex and L*. Use as
      <code>dc.vivid0…7</code> or <code>dm.set_cycle("vivid")</code>.</p>
    </div>
    <button class="toggle" id="themeBtn" aria-label="Toggle theme">◐ theme</button>
  </header>
  <nav class="rail" id="rail" aria-label="Filter by family"></nav>
{groups}
  <footer class="foot">
    Verification per palette — <code>B&amp;W ΔL*</code> = min grayscale
    lightness gap; <code>CVD d/p/t</code> = min perceptual distance under
    deuter / protan / tritan vision (CAM02-UCS). Higher is safer. Diverging
    palettes are B&amp;W-exempt by design (symmetric tent).
  </footer>
</div>
<script>
(function(){{
  var root=document.documentElement, btn=document.getElementById("themeBtn");
  // inherit the host docs theme if embedded
  try {{ var t=document.referrer&&parent!==window?
    (parent.document.documentElement.classList.contains("dark")?"dark":"light"):null;
    if(t) root.dataset.theme=t; }} catch(e) {{}}
  btn.addEventListener("click",function(){{
    root.dataset.theme=root.dataset.theme==="dark"?"light":"dark"; }});
  var fams=[...new Set([...document.querySelectorAll(".spec")].map(s=>s.dataset.fam))];
  var rail=document.getElementById("rail");
  function chip(label){{ var b=document.createElement("button"); b.className="fchip";
    b.textContent=label; if(label==="All")b.classList.add("on");
    b.addEventListener("click",function(){{
      rail.querySelectorAll(".fchip").forEach(c=>c.classList.toggle("on",c.textContent===label));
      document.querySelectorAll(".spec").forEach(function(s){{
        s.style.display=(label==="All"||s.dataset.fam===label)?"":"none"; }});
      document.querySelectorAll(".fam").forEach(function(f){{
        f.style.display=[...f.querySelectorAll(".spec")].some(s=>s.style.display!=="none")?"":"none"; }});
    }}); return b; }}
  rail.appendChild(chip("All")); fams.forEach(f=>rail.appendChild(chip(f)));
  document.querySelectorAll(".sw").forEach(function(sw){{
    sw.addEventListener("click",function(){{
      var hex=sw.dataset.hex;
      (navigator.clipboard?navigator.clipboard.writeText(hex):Promise.resolve()).then(function(){{
        sw.classList.add("copied"); setTimeout(()=>sw.classList.remove("copied"),900); }})
        .catch(function(){{}}); }}); }});
}})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    OUT.write_text(build() + "\n", encoding="utf-8")
    print(f"wrote {OUT}  ({len(ORDER)} palettes)")
