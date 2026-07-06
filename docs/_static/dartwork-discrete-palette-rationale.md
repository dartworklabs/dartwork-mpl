# dartwork v5 categorical-family rationale

dartwork-mpl v5 uses one generated color system instead of a separate legacy
categorical catalog.

## What Ships

- 20 `dc.*` families: red, rose, coral, tangerine, orange, amber, yellow,
  lime, green, teal, cyan, sky, blue, cobalt, indigo, violet, purple,
  fuchsia, pink, gray.
- 10 perceptually equalized steps per family: `dc.blue0` through `dc.blue9`.
- Two searched cycles: `dc.cycle` for screen/PDF and `dc.cycle_print` for
  darker print-friendly output.
- Role tokens: `dc.pos`, `dc.neg`, `dc.ref`, and `dc.hl`.

## Design Rule

Use the searched cycle for unrelated categories. Use a family palette when hue
has semantic value: `green` for positive states, `red` for negative states,
`coral`/`tangerine`/`amber`/`orange` for thresholds, `gray` for reference and
secondary context, and cool families (`blue`, `cobalt`, `teal`, `indigo`,
`cyan`) for analytical series.

Every family is generated from the v5 recipe in
`src/dartwork_mpl/colors/_recipe.py` and materialized in
`src/dartwork_mpl/colors/_generated.py`. The old hand-curated palette asset
and its generator were removed; this file is documentation only.
