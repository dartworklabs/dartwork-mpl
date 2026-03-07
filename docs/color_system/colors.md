# Colors

Wide, single-column sheets for every named palette in dartwork-mpl. Each preview
below is full-width so the swatch labels stay readable on both desktop and
mobile.

## How to read the labels

- Format: `library.base:weight` (`tw.blue500`, `md.red700`, `oc.gray6`).
- Works anywhere matplotlib accepts a color—no extra API layer required.
- `dm.style.use("scientific")` loads the dartwork style so these names look
  consistent across lines, fills, markers, and legends.

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

dm.style.use("scientific")
t = np.linspace(0, 2 * np.pi, 200)
plt.plot(t, np.sin(t), color="oc.indigo6", linewidth=2.4, label="Indigo 6")
plt.scatter(t[::12], np.cos(t[::12]), color="tw.rose500", edgecolor="none")
plt.legend()
plt.show()
```

## Palette sheets

**Dartwork.** 23 hand-curated categorical palettes for data visualization. Use
`dm.vivid0`–`dm.vivid5` for high-contrast presentations, `dm.pastel0`–`dm.pastel5`
for soft backgrounds, or `dm.acid0`–`dm.acid5` for bold fluorescent accents.

```{raw} html
:file: images/colors_dm.html
```

**OpenColor.** Balanced neutrals and calm hues for dashboards and UI frames. Even
weight steps make layered backgrounds straightforward.

```{raw} html
:file: images/colors_opencolor.html
```

**Tailwind.** The broadest weight range (50–950) for precise contrast tuning.
Perfect when you already think in Tailwind classes.

```{raw} html
:file: images/colors_tw.html
```

**Material Design.** Saturated primaries and secondaries that read clearly on
white backgrounds, with consistent 50–900 steps.

```{raw} html
:file: images/colors_md.html
```

**Ant Design.** Compact 1–10 weight system tuned for dense, data-heavy UIs with
both warm and cool tracks that stay legible in small marks.

```{raw} html
:file: images/colors_ant.html
```

**Chakra UI.** Soft, friendly ramps ideal for product illustrations, covers, and
muted backgrounds that do not overpower overlays.

```{raw} html
:file: images/colors_chakra.html
```

**Primer.** GitHub-inspired neutrals with subtle tints and shadows—great when
you need desaturated accents with strong contrast.

```{raw} html
:file: images/colors_primer.html
```

## Rendering guidance

- Use weights 400–600 for lines and markers; 50–200 for fills and backgrounds.
- Pair adjacent weights for related elements (e.g., line at 600, fill at 200).
- Keep a single library per figure unless you need deliberate contrast (Primer
  background with Tailwind accents, for example).
- Turn off `edgecolor` on dense scatters to keep swatches clean in exports.

## Refreshing the sheets

- HTML sheets and fallback PNGs live in `docs/color_system/images/`.
- A Sphinx build runs `color_system/generate_assets.py`; run it directly if you
  tweak palette data and want to update only the assets.
