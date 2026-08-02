# dartwork categorical-family rationale

dartwork-mpl uses one OKLab-centered color system instead of a separate legacy
categorical catalog. The v6 compiler preserves the published v5 output exactly
while separating construction, modeled output coordinates, and validation.

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

## What Ships

- 20 `dc.*` families (19 chromatic plus gray): red, rose, coral, tangerine,
  orange, amber, yellow, lime, green, teal, cyan, sky, blue, cobalt, indigo,
  violet, purple, fuchsia, pink, gray.
- The 19 chromatic family ladders use ΔEOK arc-length equalization. The gray
  ladder directly samples ten evenly spaced neutral-tone positions; its
  resulting neighbor ΔEOK near-evenness is measured and protected by frozen
  non-regression gates, not produced by the chromatic equalizer. Every family
  still ships ten tokens, such as `dc.blue0` through `dc.blue9`.
- Two searched cycles: Octave (`dc.octave`) for screen/PDF and the hue-parallel
  Octave Print (`dc.octave_print`) with larger nominal CIELAB lightness gaps.
- 11 curated qualitative sets for general, muted, tonal, and emphasis use cases.
- Role tokens: `dc.pos`, `dc.neg`, `dc.ref`, and `dc.hl`.

## Design Rule

Use Octave for unrelated categories. Use a family palette when hue
has semantic value: `green` for positive states, `red` for negative states,
`coral`/`tangerine`/`amber`/`orange` for thresholds, `gray` for reference and
secondary context, and cool families (`blue`, `cobalt`, `teal`, `indigo`,
`cyan`) for analytical series.

Generated families use OKLab `L`, OKLCH `C`/`h`, and ΔEOK construction. Their
ordered output also preserves modeled `relative_y`; this is a compatibility
contract, not another perceptual-lightness coordinate. CIELAB, ΔE00, Machado
(2009) protan/deutan, and BVM (1997) tritan CVD are model-specific diagnostics.
WCAG contrast luminance remains a separate background-specific check.

The generated system compiles from 107 recipe input numbers in the packaged
`src/dartwork_mpl/asset/color/color_v6_ssot.json` authority, through
`src/dartwork_mpl/_colors/_recipe.py`, and is materialized in
`src/dartwork_mpl/_colors/_generated.py`. The preserved manual categorical
sets live in `src/dartwork_mpl/_colors/_curated.py`; they are not part of the
107-input recipe count. This file is documentation only.
