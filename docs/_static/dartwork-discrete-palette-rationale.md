# dartwork discrete (categorical) palette — design rationale

*The "why" before the "what". This is the criteria SSOT for dartwork-mpl's
discrete categorical palettes. Candidate palettes (see
`discrete_palette_pocs.html`) are derived from — and must satisfy — these
criteria. Color count is negotiable; the criteria are not.*

---

## 0. Why this exists (the gap)

dartwork-mpl ships a rich color ecosystem — 7 named libraries (`dc. oc. tw. md.
ad. cu. pr.`), 59 colormaps, and a `dc.` family of 9 hand-curated palettes. But
for **discrete categorical** use (the color *cycle* that distinguishes series in
a line/bar/scatter plot) there is one structural gap:

- **Every style preset hard-codes the same cycle** — `axes.prop_cycle =
  ['dc.0' … 'dc.5']` is identical across `scientific`, `report`, `presentation`,
  etc. A journal figure and a marketing dashboard get the *same six colors*.
- **No CVD verification.** None of the shipped categorical sets are documented as
  colorblind-safe, grayscale-safe, or print-safe.
- **No use-case mapping + no programmatic API** (`dm.get_palette('scientific')`).
  Users hardcode color lists.

So the redesign is not "prettier colors" — it is **a small set of deliberate,
context-matched, accessibility-verified categorical palettes**, each with a
documented rationale, that the presets and an API can point at.

---

## 1. The eight criteria (what makes a categorical palette *good*)

Every candidate palette is engineered and audited against these. They are
ordered by how often they silently fail.

| # | Criterion | Why it matters | How we check it |
|---|---|---|---|
| 1 | **Perceptual distinctness (OKLCH ΔE)** | RGB/HSV spacing is perceptually uneven — two "equidistant" RGB colors can look identical. Categories must be *seen* as different. | Even spacing + a minimum ΔE in OKLCH/CAM02-UCS between every pair. |
| 2 | **CVD safety** | ~8% of men have color-vision deficiency. Red–green pairs (deuter/protan) and blue–yellow (tritan) collapse. | Simulate all three (Brettel/Machado); pairs must stay separable. Okabe-Ito is the proven anchor. |
| 3 | **Grayscale / luminance separation** | Many figures print or photocopy in B&W. Hue-only palettes turn to mud. | Lightness (L) must vary, not just hue — target ≥10–15% ΔL between neighbors. |
| 4 | **Cognitive category limit (7±2 → 12)** | Beyond ~7 unordered categories, viewers lose track of which is which. | Keep report/scientific ≤6–8; allow infographic 8–12 only with ordering/grouping. |
| 5 | **Saturation & lightness consistency** | Mixed saturation makes one series falsely "shout" — visual hierarchy where none is meant. | Constrain chroma/lightness to a band per palette (except a deliberate accent). |
| 6 | **Print (CMYK) predictability** | Saturated sRGB falls outside CMYK gamut → shifts on press. | Keep within a safe sRGB sub-gamut for report/scientific. |
| 7 | **Hue semantics & reservation** | red≈bad, green≈good, blue≈trust. Misusing them adds cognitive load. | Don't spend semantic hues on arbitrary categories where sentiment is implied. |
| 8 | **Harmony vs distinctness (design intent)** | Max distinctness → garish; max harmony → indistinct. The tradeoff is the *design decision* that separates the three contexts. | Tune per context (§2): report leans harmony, infographic leans distinctness. |

**Multi-mode fidelity** is the cumulative test: a palette must survive
*color → CVD → grayscale → print* without two categories merging.

**References:** Okabe & Ito (2008, CUD); Brewer (ColorBrewer 2.0); Brettel/Viénot
(1997) & Machado (2009) CVD simulation; Tableau 10/20; IBM Design Language;
Stone, *A Field Guide to Digital Color*; Munzner, *Visualization Analysis &
Design* (ch. 6).

---

## 1b. How many colors — the count decision

**Container = 8 (hard ceiling). Recommended working count = 5–6.** The number is
not a style choice; **three independent constraints all top out at ~8**, so 8 is
the largest count the system can still *guarantee*:

| Constraint | Caps at | Why |
|---|---|---|
| **Cognitive** (Miller 7±2) | ~7–8 | Beyond ~8 unordered color categories, viewers can't match legend↔mark without effort. |
| **CVD safety** | 8 | The gold-standard accessible set (Okabe-Ito) deliberately stops at **8**; keeping every pair CVD-separable gets exponentially harder past it. |
| **B&W (even L\* ladder)** | ~8 | An even lightness ladder needs N distinct L\* rungs. 8 → ~7–8 ΔL\*/step (good); 10 → ~6 (marginal); 12 → ~5 (mud in grayscale). |

All three converge near 8 — so "every palette ships 8" is the *maximum the
engineering can back*, not arbitrary uniformity. (Our family proves it: 12 of 13
clear min ΔL\* ≥ 6.6 **and** CVD at 8 colors; at 9–10 those guarantees break.)

Why **5–6 is the recommended working count**: industry consensus (Few, Ware,
Brewer) puts *reliable* discrimination at ≤6–7, and most real report/scientific
figures carry **3–6 series**. 5–6 is the legibility + harmony + CVD-headroom
sweet spot.

**The mechanism (so 8 and 5–6 coexist):**
1. Ship every palette at **8** — the guaranteed container.
2. Order each palette so **first-N is the best-separated subset** → dropping the
   count slider to 6/5/4 auto-yields the optimal subset (no manual re-picking).
3. Docs **default the recommendation to 5–6**; 8 is the ceiling for when it's
   genuinely needed.
4. **Past 8 categories, don't add colors — change the encoding**: grouping,
   faceting / small multiples, direct labels, or (if ordered) switch to a
   sequential ramp.

> One-liner: **container 8, everyday 5–6, beyond 8 solve it with structure not color.**

---

## 2. The three contexts (where criterion #8 is decided)

The same eight criteria, weighted differently:

| | **Report** | **Scientific** | **Infographic** |
|---|---|---|---|
| Lean | harmony, restraint | safety, austerity | distinctness, energy |
| Saturation | muted (35–50% C) | conservative | high |
| Lightness spread | moderate | moderate, even | staggered hi/lo |
| Count | 4–6 | 5–8 | 8–12 |
| CVD | high | **mandatory** | aware |
| Tone | trustworthy, institutional | reproducible, neutral | lively, engaging |
| Anchor | dartwork teal `#12a594` | Okabe-Ito (or teal-anchored) | teal in the mix |
| Exemplars | Economist, FT, McKinsey | Nature/Cell, Okabe-Ito | Datawrapper, NYT graphics |

---

## 3. The palette system — 24 palettes, 11 families

Every palette is **8 colours, CIELAB-generated** (`_static/scripts/gen_palettes.py`),
**B&W + CVD verified** (`dm_palettes_gen.json`), and **interactively documented**
in `_static/palette_explorer.html` (live swatches, B&W, dark-canvas, 9 chart
types, per-palette intent/design/application). The system has **two organising
ideas**:

**(a) A categorical spine on one axis — spectral width** (narrow = harmony →
wide = distinctness). Pick by the *shape* of your data:

| Family | Members | Job |
|---|---|---|
| **Sequential** (3) | `teal_seq` `indigo_seq` `coral_seq` | ordered / rank — single-hue L* ramp |
| **Analogous** (2) | `teal_indigo` `forest` | a few related series, one mood |
| **Duo** (3) | `warm_cool` `blue_orange` `teal_coral` | two opposed groups (A/B) |
| **Balanced** (2) | `trustworthy` `corporate` | everyday 4–8 categories |
| **Spectrum** (2) | `spectrum` (even wheel) `bold` (curated punch) | many categories, max distinctness |

**(b) Intent families for specific jobs** (organised by purpose, not width):

| Family | Members | Job |
|---|---|---|
| **Neutral** (3) | `gray_seq` (true neutral) `warm_gray` `cool_gray` | hue-free ordered amount |
| **Emphasis** (2) | `focus` (teal accent) `focus_warm` (coral accent) | highlight one series, mute rest |
| **Muted** (2) | `muted` (pastel) `dusty` (deep/vintage) | soft editorial |
| **Diverging** (2) | `coolwarm` `teal_amber_div` | ordered ± data (change/correlation). **B&W-exempt** (ends share L by design) |
| **Tone** (2) | `earth` (warm/organic) `jewel` (deep/premium) | aesthetic verticals |
| **Accessible** (1) | `accessible` | mandatory CVD — **Okabe-Ito, fixed reference** (the one justified singleton) |

**Engineering invariants** (all families): 8 colours · even CIELAB L* ladder
(⇒ B&W + most CVD survive; *Diverging is the sole exception*) · CVD-verified
(colorspacious, not eyeballed) · subset-friendly (first-N ordering) ·
**house teal `#12a594` anchors every general-purpose palette** (slot 0 of
`teal_seq` `teal_indigo` `trustworthy` `corporate` `spectrum` `bold` `muted`
`focus` `jewel`; `teal_coral` `teal_amber_div` carry it too). Single-hue,
externally-defined (`accessible`), neutral, and warm-only (`earth`) palettes
legitimately don't carry teal.

> The set was pruned from 27 → 24 via an adversarial 3-lens redundancy audit
> (perceptual / intent / ruthless-editor): dropped `ocean` (≈ `teal_indigo`),
> the dual-accent focus (≈ single-accent), and `lively` (≈ `trustworthy`).
> Every family now has ≥2 members except the fixed Accessible reference.

---

## 4. How it lands in dartwork-mpl

**Done (design layer):**
1. `gen_palettes.py` generates all 24 in CIELAB; `dm_palettes_gen.json` is the
   verified colour SSOT; `palette_explorer.html` is the interactive doc.

**Pending (package layer — needs 2 calls):**
2. Add the 24 to `src/dartwork_mpl/asset/color/dc_palettes.json` as
   `dc.<name>0..7` (+ auto `dm.*` alias). **Decision A**: do the 24 *supersede*
   the old ad-hoc dc set (Vivid/Sunset/Ocean/Forest/Pop/Cyber/Autumn/Nordic) or
   *coexist* (only `forest` collides after pruning)?
3. Expose `dm.get_palette(name, n=None, subset=...)` + `dm.set_cycle(...)`
   (sister to `make_palette` in `helpers/colors.py`).
4. **Decision B**: per-preset `axes.prop_cycle` — keep one shared default,
   repoint the shared default, or differentiate per preset
   (scientific→accessible, report→trustworthy, …). Today all 14 presets share
   `dc.0–5`.
5. Swatch sheets via `docs/color_system/generate_assets.py`; a new
   `docs/color_system/categorical-palettes.md` page embedding the explorer.

*This file is the rationale SSOT; update it when palettes change.*
