# Design rationale

This is the design system's evidence page: why the colors — and eventually the
typography — are built and gated this way. The `dc.*` color system is not a
hand-picked table of hex codes. Every palette color, every colormap, and every
cycle is **generated deterministically from 107 numbers** by a small set of
perceptual axioms, and each output is checked against color-science gates
before it ships.

To use the color surfaces directly, see [Colors](colors.md),
[Palettes](palettes.md), [Colormaps](colormaps.md), and
[Color class](color-class.md). Every figure below is rendered live from the
shipped package by `docs/color_system/generate_theory_figures.py`, so the
pictures are the proof.

## Three principles

**1 · Perceptual-first.** Colors are designed on coordinates built for
human vision, not on RGB or HSV. Lightness lives on CIELAB L\*; hue and
chroma are manipulated in OKLCH. "Even in the numbers" and "even to the
eye" are made to agree.

**2 · Generative, not tabular.** Colors are not stored; they are *computed*.
Each family is defined by a handful of numbers, and a compiler turns those
numbers into a 10-step ladder. Consistency is enforced (every family passes
the same rules), extension is principled (a new hue axis is a point on a
curve, not a guess), and the design is verifiable (the per-family values lie
on smooth low-order curves — evidence that it is *one curve*, not fifteen
arbitrary choices).

**3 · Honest guarantees.** Color is a field of trade-offs: a palette that is
perfect under one metric necessarily compromises under another. v5 does not
hide this — it publishes **three metrics** and states, for each output, what
it guarantees and what it does not. A claim like "accessible" or
"perceptually uniform" is always qualified by *under which metric*.

## The perceptual foundation (axiom A1)

> **A1** — lightness is CIELAB L\* (D65); hue and chroma are OKLCH;
> out-of-gamut colors are mapped the CSS Color 4 way (hold L\* and hue,
> shrink chroma); every gate is judged in a ΔE metric.

:::{figure} theory_figures/theory_1_lightness_weber.svg
:alt: Even steps in physical luminance bunch up at the light end; even steps in CIELAB L* are perceptually uniform.
:width: 100%

Human lightness perception responds to physical luminance logarithmically
(Weber–Fechner). Even steps in luminance *Y* bunch up at the light end;
even steps in CIELAB L\* form a perceptually even staircase.
:::

**Why L\* for lightness — "log spacing" is already built in.** A common
instinct is to space color steps logarithmically rather than linearly. That
instinct is already satisfied: L\* *is* the log-compressed coordinate
(L\*50 ≈ 18% of white's luminance). Even spacing on L\* is therefore already
even to the eye — applying a second log on top would double-compress and
make the ramp *less* uniform.

**Why OKLCH for hue and chroma.** CIELAB is excellent for lightness but
distorts hue manipulation (brightening a blue drifts it toward purple).
OKLCH (Ottosson, 2020) holds hue constant while lightness and chroma move
independently, so a ladder keeps its color identity. The roles are split:
**CIELAB L\* measures lightness, OKLCH does the manipulation.**

**Gamut mapping.** When an OKLCH request falls outside sRGB, naive clipping
skews the hue. The CSS Color 4 method holds L\* and hue fixed and shrinks
chroma by bisection until the color is back in gamut.

## The generation axioms (A2–A8)

Each axiom is a testable rule, recorded together with its adoption evidence
(curve fit) and the alternative it beat.

### A2 · hue-specific lightness floor

> Every family starts at L\*96 and descends to a hue-specific floor. The
> floor is not the gamut wall — it is a perceptual design value defined by a
> Fourier curve `floor(h)`.

:::{figure} theory_figures/theory_2_floor.svg
:alt: Each hue family descends only as far as its hue survives — yellow stops at L*60, violet reaches L*37.
:width: 100%

Each hue goes only *as dark as the color survives*: yellow stops near L\*60
(darker turns to olive mud), violet reaches L\*37 and is still violet. This
is why the palette reads bright and crisp — dragging every family down to a
shared minimum would muddy the warm hues.
:::

The rejected alternative — "floor = the gamut wall where chroma has fallen
to λ× its peak" — was physically elegant but missed the design floors by
RMSE 15 L\*. The accepted model puts `floor(h)` on a Fourier (k=3) curve
that fits the family floors to **RMSE 0.77 L\***: the floor is a smooth
function of hue, and a new family's floor is read straight off the curve.

### A3 · chroma — hue fingerprint × shared shape

> Peak chroma `C_max(h)` is a smooth function of hue (Fourier k=3); the
> *shape* of the chroma ladder is one template shared by every family (rise
> → peak at `t_p` → fall), and only the peak position `t_p` differs.

:::{figure} theory_figures/theory_4_chroma.svg
:alt: Left, one Fourier curve fits every family's peak chroma; right, one shared rise-peak-fall shape with only t_p varying.
:width: 100%

Left: one curve explains the peak chroma of all fifteen chromatic families
(R²=0.945) — the cyan valley (sRGB is stingy with cyan) and violet peak fall
out automatically. Right: the rise-peak-fall *shape* is identical for every
family; only *when* the peak lands (`t_p`) changes — red peaks dark (0.85),
yellow peaks mid-ladder (0.45).
:::

### A4 · the drift power law

> Hue rotates as a function of lightness: `h(t) = h₀ + Δh · t^γ`. As colors
> darken, warm hues rotate a lot (toward flame-like orange/red), cool hues
> a little.

:::{figure} theory_figures/theory_3_drift.svg
:alt: Hue rotation curves — yellow rotates -46 degrees, blue only +15 degrees as they darken.
:width: 100%

Yellow rotates Δh −46° (bright lemon → dark amber); blue rotates only +15°.
`γ` controls *when* the rotation happens (γ>1 accelerates it in the dark
end). One power law captures every family's drift to wRMSE ≤ 1.7°. This
drift is what keeps dark colors vivid instead of muddy.
:::

### A5 · step placement is perceptual even-spacing

> The 10 steps are re-placed along the color path until neighbor ΔE is
> uniform. Spacing is generalized by a warp function `w(t)`; the default is
> linear (perceptually even), with `ease`/`exp`/`log` available as options.

:::{figure} theory_figures/theory_5_spacing.svg
:alt: Equalized spacing flattens the neighbor delta-E curve; naive linear-t sampling leaves it uneven.
:width: 100%

Equalized spacing flattens the neighbor ΔE so that *step-number difference =
perceptual difference* — index arithmetic becomes meaningful (`blue3↔blue5`
covers the same perceptual distance as `blue6↔blue8`). Naive linear-*t*
sampling leaves the spacing uneven.
:::

Even spacing is the default because it makes data visualization
predictable. It is not the only valid answer: UI and document design often
want more resolution at the ends (background pastels, emphasis darks), which
an S-curve (`ease`) provides — so the spacing is left open as a warp option
while the default stays linear.

### A6 · the achromatic exception (gray)

Gray alone uses an even L\* ladder (96→28) with a faint cool tint
(h250, C ≤ 0.011). Having no hue identity, it is exempt from the drift and
chroma-fingerprint rules; even L\* alone keeps its neighbor ΔE uniform. Gray
is reserved for grids, reference lines, benchmarks, and "other" categories —
it is deliberately **not** part of Octave (`dc.octave`); Octave Print adds a
dark gray as its 8th color for B&W lightness spread.

### A7 · the hard gates

Verified automatically at compile time; an output that fails cannot ship.

| Gate | Criterion | Metric |
|---|---|---|
| L\* monotonic | strictly light→dark within a family | CIELAB L\* |
| Equalization uniformity | neighbor-ΔE coefficient of variation cv ≤ 0.08 (palette ladders only — sequential-cmap cv is measured, not hard-gated) | OKLab ΔE |
| Categorical accessibility | common CVD (normal + protan + deutan) min ΔE ≥ 10; rare tritan ≥ 8 (accurate Brettel-1997 model) | CIEDE2000 |
| Sequential-cmap gray monotonic | monotonic even under luminance conversion | CIELAB L\* |

### A8 · colormaps do not inherit the palette floors

> Heatmap sequential colormaps are generated on a *wide* L\* range
> (96 → ~20), not on the family's hue-specific floor.

:::{figure} theory_figures/theory_7_dcseq.svg
:alt: aurora vs viridis — aurora holds a monotonic, near-linear L* over a wider range.
:width: 100%

A palette ladder stops at its hue floor, so different families span
different L\* ranges — fine for categorical swatches, wrong for a heatmap
where dynamic range and cross-panel comparability matter. Colormaps are
regenerated over a shared wide range instead. `aurora` holds monotonic,
near-linear L\* (ΔE cv 0.063, L\* range 81.9) against viridis (cv 0.086,
76.0) on the same 32-stop measurement of the shipped 256-LUT.
:::

## Anatomy of a family

The whole system regenerates from **107 numbers**: 19 chromatic families × 4 free
parameters (76) + 24 Fourier coefficients for the global hue curves + 7
constants. A family's four free numbers are `h₀` (hue anchor), `Δh` (total
drift), `γ` (drift timing), and `t_p` (chroma-peak position); the other four
(`C_max`, `floor`, `c₀`, `c_end`) are *derived* from the global curves.

:::{figure} theory_figures/theory_8_anatomy.svg
:alt: The eight numbers that define the yellow family and the L*, chroma, and hue trajectories they produce.
:width: 100%

The eight numbers behind `yellow`, and the trajectories they drive: L\*
descends to the floor, chroma rises to its peak at `t_p`, and the hue drifts
by `Δh` on the `γ` schedule.
:::

The confirmed parameters, rounded to a human-readable grid (rounding moves a
palette by mean ΔE 0.5–1.4, below the 8-bit hex quantization floor):

| family | h₀ | Δh | γ | t_p | C_max | floor | c₀ | c_end |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `red` | 16 | +11 | 1.10 | 0.85 | 0.210 | 42 | 0.10 | 0.90 |
| `rose` | 3 | +14 | 1.00 | 0.85 | 0.210 | 40 | 0.10 | 0.85 |
| `coral` | 27 | +2 | 1.15 | 0.85 | 0.205 | 44 | 0.10 | 0.90 |
| `tangerine` | 52 | −12 | 1.20 | 0.85 | 0.195 | 49 | 0.15 | 0.95 |
| `orange` | 77 | −41 | 1.30 | 0.85 | 0.190 | 54 | 0.15 | 1.00 |
| `amber` | 88 | −44 | 1.40 | 0.65 | 0.185 | 57 | 0.15 | 1.00 |
| `yellow` | 99 | −46 | 1.50 | 0.45 | 0.180 | 60 | 0.15 | 1.00 |
| `lime` | 122 | +11 | 0.60 | 0.45 | 0.190 | 56 | 0.15 | 0.85 |
| `green` | 149 | −3 | 0.60 | 0.50 | 0.185 | 51 | 0.15 | 0.75 |
| `teal` | 176 | −13 | 0.60 | 0.45 | 0.155 | 47 | 0.15 | 0.70 |
| `cyan` | 202 | +13 | 0.85 | 0.45 | 0.115 | 44 | 0.15 | 0.75 |
| `sky` | 220 | +14 | 0.85 | 0.60 | 0.130 | 43 | 0.15 | 0.80 |
| `blue` | 238 | +15 | 0.85 | 0.75 | 0.165 | 42 | 0.15 | 0.85 |
| `cobalt` | 256 | +5 | 1.25 | 0.80 | 0.190 | 40 | 0.15 | 0.85 |
| `indigo` | 273 | −5 | 1.65 | 0.85 | 0.210 | 39 | 0.10 | 0.85 |
| `violet` | 298 | −12 | 1.25 | 0.85 | 0.230 | 37 | 0.10 | 0.85 |
| `purple` | 319 | +0 | 1.00 | 0.75 | 0.220 | 37 | 0.05 | 0.85 |
| `fuchsia` | 335 | +9 | 0.95 | 0.80 | 0.210 | 37 | 0.05 | 0.85 |
| `pink` | 350 | +18 | 0.85 | 0.85 | 0.210 | 39 | 0.05 | 0.85 |

> `gray` follows the A6 rule (L\* 96→28, cool tint h250). A new family needs
> only its four free numbers — the rest is read off the global curves.

## The metric system — what the ruler is

A color system's credibility depends on **which ruler measures distance**.
v5 uses three, each for what it is best at:

| Purpose | Metric | Why |
|---|---|---|
| Equalization & design | OKLab ΔE | the space the recipe lives in; built for gradient uniformity |
| Accessibility gate | CIEDE2000 | the industry-standard discrimination metric, calibrated against the Okabe-Ito benchmark |
| Lightness & grayscale guarantee | CIELAB L\* | matches physical print and grayscale conversion |

:::{figure} theory_figures/theory_6_metric.svg
:alt: blue7 and violet7 are distinct in normal vision but collapse under deutan simulation; ΔE76 scores it a pass, CIEDE2000 correctly fails it.
:width: 100%

The single most important correction in v5. An earlier design measured
accessibility with ΔE76 (CIELAB Euclidean), which over-states the distance
between high-chroma colors. `blue7` and `violet7` are two clear colors in
normal vision but nearly merge under a deuteranopia simulation. ΔE76 scores
them well above the gate threshold — a false pass — while CIEDE2000 scores
them below it and correctly fails. An adversarial critique caught this; the
gate was switched to CIEDE2000 and the cycle re-searched from scratch.
:::

All three coefficients of variation are published on the palette diagnostic
card. **No step placement drives all three to zero simultaneously** — being
explicit about what is guaranteed is the honest design (principle 3).

The CVD simulation behind the accessibility gate is itself chosen for
accuracy per deficiency. The common red-green deficiencies (protanopia,
deuteranopia) use the Machado (2009) model; the rare S-cone deficiency
(tritanopia) uses the physiologically accurate Brettel-Viénot-Mollon (1997)
projection, because Machado's fitted tritan matrix over-states blue-yellow
separation. Under the accurate model a seven-hue cycle's tritan separation
tops out near 9 — so, rather than claim a number the colors cannot meet, the
gate is **tiered**: the common deficiencies are held to ≥ 10 and the rare
tritan to a realistic ≥ 8. `dc.octave` measures 10.3 (common) / 8.3 (tritan)
for Octave; `dc.octave_print`, 10.4 / 9.8 for Octave Print. Octave Print is
hue-parallel with Octave — same hue per slot, with the violet slot matching
and the dark gray anchor in slot eight — while keeping every pair at least
about 7 L\* apart (min ΔL\* 7.7) for grayscale. Publishing the real floors
instead of a flattering worst-case is the same honest-guarantees principle at
work.

## Colormaps, derived from the palette

The colormaps are made by the *same* generative system (perceptual
coordinates + recipe + ΔE equalization + gates): 43 continuous maps across
four families, plus the two palette cycles registered as qualitative maps. A
colormap is not a separate color vocabulary — it is *derived from the palette*,
and the naming grammar enforces that relationship.

:::{figure} theory_figures/theory_9_cmap_catalog.svg
:alt: The full 43-map v5 continuous colormap catalog rendered as gradients, grouped by family.
:width: 100%

The full catalog: 20 single-hue ramps, 9 multi-hue scenes, 11 diverging pairs,
three cyclic maps, and the two qualitative cycle registrations.
:::

**One naming grammar.** The name states color identity; the suffix states a
variant.

| Kind | Rule | Example |
|---|---|---|
| color token | `dc.{family}{step}` | `dc.blue6` |
| categorical cycle | `octave` · `octave_print` | `dm.set_colors()` |
| single-hue cmap | the family name itself | `cmap="dc.blue"` |
| multi-hue cmap | a natural-light scene name | `dc.aurora` |
| diverging cmap | a `low_high` pair name | `dc.blue_red` |
| cyclic cmap | a circular-light-phenomenon name | `dc.halo` |
| qualitative cmap | stable public cycle token | `dc.octave` |
| variant suffix | `_r` (reverse) | `dc.aurora_r` |

**Direction — an ink/light metaphor.** *Ink* maps (single-hue, diverging)
follow the "ink on white paper" metaphor: **high value = darker**. *Light*
maps (multi-hue, cyclic) follow the "light out of darkness" metaphor:
**high value = brighter** (the viridis convention). This replaces matplotlib's
unprincipled mix of directions (`Blues` runs light→dark, `viridis` runs
dark→light) with an explicit rule; reverse any map with `_r`.

**Anchor-graph coherence.** The 15 family anchors (`h₀`) are the system's
only hue vocabulary. A single-hue map renders one anchor; a diverging map
joins an anchor *pair*; a multi-hue map traces a *path* through anchors; a
cyclic map is a *closed loop* back to its start. Palette, cycle, and colormap
all live on one graph.

### The multi-hue scenes

Multi-hue maps traverse several hues to maximize perceptual resolution.
Because they cannot be named after one family, they take scene names — but
grounded in the dartwork theme "the natural-light scene where that color
path actually appears," with hue way-points chosen only at family anchors:

| Name | Scene | Anchor path | Analogous to |
|---|---|---|---|
| `aurora` (default) | polar light | violet→indigo→sky→teal→lime→yellow | viridis |
| `afterglow` | sunset afterglow | violet→purple→pink→red→orange | plasma |
| `blaze` | flame | violet→pink→red→orange→yellow | magma |
| `lava` | lava glow (no violet) | red→orange→amber→yellow | hot |
| `lagoon` | lagoon water | blue→cyan→teal→green→lime | — |
| `glacier` | glacier-crevasse light | indigo→blue→sky→cyan→teal | ice |
| `canopy` | forest-canopy light | teal→green→lime→yellow | algae |
| `haze` | misty dawn (low-chroma, CVD-optimal) | blue→sky→green→yellow | cividis |
| `iris` | wide-band spectrum | violet→blue→cyan→green→yellow→orange | Spectral |

`aurora` earns the default: against viridis it is ~1.3× as uniform (ΔE cv
0.063 vs 0.086) over a wider L\* range (81.9 vs 76.0), measured identically
at 32 stops on the shipped 256-LUT.

### The cyclic maps

:::{figure} theory_figures/theory_10_cyclic_demo.svg
:alt: A phase field drawn with an ordinary sequential map shows a false seam; cyclic maps join 0 and 1 smoothly.
:width: 100%

Angle and phase data (0° = 360° — CFD phase fields, FFT phase, wind
direction) drawn with an ordinary sequential map grow a *false*
discontinuity at the 0↔1 seam. A cyclic map starts where it ends, so the
seam vanishes. `halo` and `corona` are double-lobed lightness loops; `hue`
is an isoluminant hue wheel. The L\* monotonicity gate does not apply to
cyclic maps; a seam-continuity gate does instead.
:::

## What this system does not guarantee

Stated plainly, per principle 3:

- **Grayscale separation of diverging maps.** Both arms converge to the same
  lightness — the essence of a symmetric map. Grayscale print needs
  contours, hatching, or numbers alongside.
- **Body-text contrast of the yellow family.** 4.5:1 on white is
  structurally impossible for yellow (true of every color system); each
  family's "text-safe step" is marked on its diagnostic card.
- **Cross-family orthogonality of the warm dark steps.** `yellow9`,
  `amber9`, and `orange8` converge in a narrow hue corridor (a geometric
  consequence of the drift aesthetic); the family names' color identity is
  reliable through steps 0–7.
- **On-screen perceived brightness.** The L\* gate is a luminance (print)
  criterion; the Helmholtz–Kohlrausch effect makes saturated dark steps
  read brighter than an equal-L\* gray.
- **Dark backgrounds.** Every gate assumes a white background in v5; a dark
  variant is planned for v5.1.
- **turbo-style high-contrast rainbows.** Their apparent "detail" comes from
  a non-monotonic L\* — the very flaw that invents structure that is not in
  the data (an A7 violation). `iris` is the widest monotonic hue path
  possible.

## Reproducibility

The machine-readable SSOT (all 91 parameters, the palette, the cycles, and
the 43-map catalog) lives beside the design record:

- `docs/superpowers/specs/2026-07-03-color-system-v5-design-rationale.md` — the full
  design rationale.
- `docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json`
  — the parameter/palette/cmap SSOT.
- `docs/color_system/generate_theory_figures.py` — regenerates the figures
  above from the shipped package (run only when the SSOT changes).

## See also

- [Colors](colors.md) — the generated `dc.*` families as swatch sheets.
- [Palettes](palettes.md) — pick a cycle by intent.
- [Colormaps](colormaps.md) — the 43-map catalog, applied.
- [Color class](color-class.md) — the `Color` class and custom colormaps.

## Typography rationale

The font system now follows the same evidence pattern as color: families are
not bundled because they look plausible in a specimen sheet. Each family has
one chart job, every measured claim is derived from the shipped font files,
and the fallback chain is treated as product behavior rather than an accident
of matplotlib configuration.

**T1 · Jobs before taste.** Every registered matplotlib family has exactly one
documented role: body, display, Korean body, monospace, or fallback tail. A
new family must do a job that another bundled family does not already do
better.

**T2 · Measured gates.** OS/2 weights, tabular-numeral support, fixed-width
truth, chart-glyph coverage, Hangul coverage, and license class are read from
the bundled files in tests and docs. Known upstream metadata quirks are named
in the registry instead of being silently normalized.

**T3 · Roles in user space.** Presets and docs speak in roles, while users keep
native matplotlib `Figure` / `Axes` objects. Size and weight still flow through
`dm.fs()` and `dm.fw()`, so swapping presets does not strand literal point
sizes or arbitrary font weights.

**T4 · Fallback is pinned.** The base text chain is
`Roboto → Inter → Paperlogy → Noto Sans CJK KR → Pretendard → Noto Sans Math
→ Noto Sans Symbols → Noto Sans Symbols 2 → sans-serif`. Tests pin the first
family that resolves every guaranteed chart glyph, the digits, and `한`.

| Role | Default | Alternates | Job |
|---|---|---|---|
| body | Roboto | Inter · IBM Plex Sans · Source Sans 3 · Noto Sans | neutral Latin chart text and editorial alternates |
| display | Inter Display | - | large titles, headings, poster-scale numerals |
| kr-body | Paperlogy | Pretendard · Noto Sans CJK KR | Korean and CJK labels without system-font dependence |
| mono | JetBrains Mono | IBM Plex Mono · Roboto Mono · Source Code Pro | code, timestamps, aligned labels, tabular data |
| fallback-tail | Noto Sans Math | Noto Sans Symbols · Noto Sans Symbols 2 | math operators, arrows, signs, and dingbats |

```{raw} html
:file: ../_static/typography_matrix.html
```

### Anatomy of the fallback chain

Plain text in matplotlib resolves glyphs from `font.family`, so the chain must
name actual bundled families, not just the generic `sans-serif` alias. The
order starts with the body voice (`Roboto`, then `Inter`), moves through
Korean and CJK coverage (`Paperlogy`, `Noto Sans CJK KR`, `Pretendard`), then
lands on math and symbol faces. In the pinned resolver map, digits and most
operators resolve in Roboto, `→` first appears in Inter, and `한` first appears
in Paperlogy; nothing falls through to DejaVu.
