# dartwork v5 categorical-family rationale

dartwork-mpl v5 uses one generated color system instead of a separate legacy
categorical catalog.

## What Ships

- 20 `dc.*` families: red, rose, coral, tangerine, orange, amber, yellow,
  lime, green, teal, cyan, sky, blue, cobalt, indigo, violet, purple,
  fuchsia, pink, gray.
- 10 perceptually equalized steps per family: `dc.blue0` through `dc.blue9`.
- Two searched cycles: Octave (`dc.cycle`) for screen/PDF and the hue-parallel
  Octave Print (`dc.cycle_print`) for print-friendly lightness separation.
- 20 curated categorical sets for qualitative, analogous, muted, tonal, duo,
  diverging, neutral-cast, emphasis, and accessible use cases.
- Role tokens: `dc.pos`, `dc.neg`, `dc.ref`, and `dc.hl`.

## Design Rule

Use Octave for unrelated categories. Use a family palette when hue
has semantic value: `green` for positive states, `red` for negative states,
`coral`/`tangerine`/`amber`/`orange` for thresholds, `gray` for reference and
secondary context, and cool families (`blue`, `cobalt`, `teal`, `indigo`,
`cyan`) for analytical series.

Every family is generated from the v5 recipe in
`src/dartwork_mpl/colors/_recipe.py` and materialized in
`src/dartwork_mpl/colors/_generated.py`. The preserved curated categorical
sets live in `src/dartwork_mpl/colors/_curated.py`; their legacy standalone
generator was removed, but the palette sets remain part of the `dc.*` system.
This file is documentation only.
