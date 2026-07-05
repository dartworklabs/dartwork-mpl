# Palettes

Every named palette in dartwork-mpl, rendered as full-width sheets.
The `dc.*` ("dartwork color") family is the recommended starting point
for publication figures; six third-party design systems are bundled
for cross-team consistency.

:::{note}
**This page** is the static swatch reference — every color as a full-width
sheet for browsing and copy-paste. To *pick* a categorical `dc.*` palette
interactively (by intent, with B&W and color-blindness previews) and apply it
with `set_cycle` / `get_palette`, see **[Categorical palettes](categorical-palettes.md)**.
:::

## How to read the labels

- Format: `library.colorweight` (e.g. `tw.blue500`, `md.red700`, `oc.gray6`).
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

### dartwork Color — v5 families

The **16 single-hue families** are the perceptual backbone of the system.
Each is ten steps (`dc.blue0` … `dc.blue9`), generated deterministically on
CIELAB L\* + OKLCH and equalized so that *step-number difference = perceptual
difference* (`dc.blue3↔dc.blue5` covers the same distance as
`dc.blue6↔dc.blue8`). Reach any color as a plain string — `color="dc.blue6"`
— anywhere matplotlib accepts a color; the `dc.*` colormaps derive from these
same recipes. The full theory is on the
[Color system design](design.md) page.

```{raw} html
:file: images/colors_dc_families.html
```

### dartwork Color — curated categorical palettes

Alongside the continuous family sheets, the v5 families form a curated
**16-palette categorical system** (10 colors each, CIELAB/OKLCH-generated and
verified for black-&-white + color-blindness). The searched `dc.cycle` is the
everyday default for unrelated categories; family palettes are best when hue
should carry a specific tone:

- `dc.cycle` — the everyday 7-color screen/PDF cycle
- `dc.blue` / `dc.teal` / `dc.indigo` — cool analytical series
- `dc.green` / `dc.red` — positive/negative or status color families
- `dc.amber` / `dc.orange` — warm emphasis and threshold context
- `dc.gray` — reference, grid, and secondary marks

The interactive picker (intent, B&W, color-blindness, 9 chart shapes) lives on
the [Categorical palettes](categorical-palettes.md) page. Legacy v4 family
names were **removed** in the v5 clean break; see the
[migration guide](../migration.md) for the manual rename map.

```{raw} html
:file: images/colors_dc.html
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
