---
orphan: true
---

# Landing-page hero — PoC gallery

> Internal preview. Pick the one (or two) "ugly → publication-ready"
> comparisons you want as the landing-page hero. Each card is a
> drag-to-wipe slider — left half is bare matplotlib defaults, right
> half is the **same plotting code** wrapped with
> `dm.style.use("scientific")`, the `dc.*` palette, and
> `dm.simple_layout(fig)`.

```{raw} html
:file: _static/landing_pocs_preview.html
```

## How the PoCs were generated

All eight pairs share a single deterministic dataset and are produced
by [`scripts/build_landing_pocs.py`](https://github.com/dartworklabs/dartwork-mpl/blob/main/scripts/build_landing_pocs.py).
Each one renders the *exact same data twice* — once via stock
`matplotlib.pyplot` (saved with `vanilla()` to clear any rcParam state),
once via:

```python
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
# ... plotting code identical to the vanilla version ...
dm.simple_layout(fig)
```

The colour palette across all eight after-figures stays inside `dc.*`
(ocean / forest / sunset / vivid / autumn / nordic), so the candidates
also doubles as a tour of the in-house palette.

## Complexity ladder

| ID | Title | What it stresses |
|---|---|---|
| **L1** | Quick line chart | rcParams diff alone (font, line weight, spine treatment) |
| **L2** | Grouped bar with labels | bar-label hierarchy + frameless legend |
| **L3** | Scatter + regression | scatter density + residual hint + frameless legend |
| **L4** | Dual-axis dashboard | twinx coordination + colour-coded right axis |
| **L5** | Small multiples (2×2) | grid spacing + panel labels + multi-hue series |
| **L6** | Stacked area composition | stack ordering + separator lines + curated palette |
| **L7** | Annotated heatmap | `dc.aurora` colormap + cell-aware text contrast |
| **L8** | Distribution comparison | violin + jittered raw points + inline median labels |

## Picking one (or two)

When you land on a favourite, mention its ID — e.g. *"go with **L3**
as the main hero and keep **L1** for the slider further down."* The
follow-up PR will:

1. Replace `docs/_static/before_default.svg` / `after_dartwork.svg`
   with the chosen pair.
2. Update the `compare_slider.html` "Exactly five rcParam shifts make
   the difference" explainer if the chosen PoC exercises rcParams
   that the current explainer doesn't list.
3. Optionally surface a second pair lower on the landing page (e.g.
   in the "Quick Example" section).
