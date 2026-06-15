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

## 3. Candidate palettes (derived from §1–§2)

Rendered in use at **`discrete_palette_pocs.html`** (swatches + bar + line mocks
+ B&W preview). Recommended (★) per context:

### Report
- ★ **Report · Vivid** (6) — `#12a594 #1f3a5f #c85a3a #4a7c59 #9b6b3d #5a6b7f`.
  Teal-anchored; warm (coral/brown) vs cool (navy/green) balance; L 30–55 for
  on-screen + print. CVD high (deuter/protan).
- **Report · Neutral** (5) — `#12a594 #6b5b54 #2d5a6d #a85a4f #5a6f5f`. Most
  restrained; for printed board/policy material.

### Scientific
- ★ **Okabe-Ito Refined** (5) — `#E69F00 #0173B2 #029E73 #CC79A7 #56B4E9`. The
  gold-standard CVD-safe set; mandatory-grade for top journals.
- **Dartwork Scientific** (6) — `#12a594 #E67E22 #2E86AB #A23B72 #1B998B
  #6C757D`. Journal-rigor *plus* the house teal, for dartwork's own publications.

### Infographic
- ★ **Mosaic** (8) — `#C41E3A #FF6B35 #FDB833 #12A594 #0066CC #5B4B8A #6B7280
  #2D3E50`. 3 warm + 3 cool + 2 neutral; balanced, teal in the mix.
- **Spectrum** (8) — `#E63946 #F4D35E #52B788 #06D6A0 #118AB2 #D946EF #F97316
  #06B6D4`. Full hue wheel, bold and high-contrast.

---

## 4. How it lands in dartwork-mpl (proposed, after palette pick)

1. Add the chosen palettes to `dc_palettes.json` (or a new `categorical/`) with
   names: `report`, `scientific`, `infographic`.
2. Differentiate `axes.prop_cycle` **per preset** — `scientific.mplstyle` →
   Okabe-Ito; `report.mplstyle` → Report·Vivid; etc. (today they're identical).
3. Expose a programmatic API: `dm.get_palette(name, n)` / `dm.set_cycle(ax,
   name)` so users stop hardcoding color lists.
4. Document CVD/print verification per palette in `color_system/colors.md`.

*This file is the rationale SSOT; update it when palettes change.*
