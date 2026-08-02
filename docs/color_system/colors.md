# Colors

Use this page when you want to color one mark, line, area, label, or other plot
element.

A **color token** is one named color string, such as `"dc.blue6"`. A **family
step** is one swatch in a related ramp: `dc.blue6` is step 6 of the blue
family. For separate series or categories, use [Palettes](palettes.md).

```python
ax.plot(x, y, color="dc.blue6")
```

## How to read the labels

- A dartwork family step joins the `dc` prefix, a family name, and a number,
  such as `dc.blue6`.
- The general format is `library.colorweight` (for example, `tw.blue500`,
  `md.red700`, or `oc.gray6`).
- Works anywhere matplotlib accepts a color—no extra API layer required.
- `dm.style.use("scientific")` loads the dartwork style so these names look
  consistent across lines, fills, markers, and legends.

Every named color token in dartwork-mpl is rendered in the full-width sheets
below. The `dc.*` ("dartwork color") family is the recommended starting point
for publication figures; six third-party design systems are bundled for
cross-team consistency.

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

### dartwork Color — families

The **20 single-hue families** — 19 chromatic ramps plus gray — are the
perceptual backbone of the system. Each contains ten family steps
(`dc.blue0` … `dc.blue9`). Reach any step as a plain string —
`color="dc.blue6"` — anywhere matplotlib accepts a color.

:::{tip} In plain English
Adjacent numbers are designed to progress more consistently, and ordered ramps
also keep their accepted light-to-dark ordering under the catalog's nominal
sRGB model. These are design targets, not a promise that every observer sees
perfectly equal steps.
:::

See [Design rationale](design-rationale.md) for the exact construction and
output metrics, and [Validation](validation.md) for the model-specific release
checks.

```{raw} html
:file: images/colors_dc_families.html
```

## Semantic aliases

Role aliases keep meaning separate from hue choice. Use `dc.pos` and `dc.neg`
for signed data such as gains versus losses, anomalies above or below a
baseline, or pass / fail states; use `dc.ref` for reference lines; and use
`dc.hl` for the one series you want the eye to find first. The `pos` / `neg`
hues follow the active style's locale convention (`*-kr` styles swap to the
red-up / blue-down convention).

```python
ax.plot(gains, color="dc.pos")
ax.axhline(baseline, color="dc.ref")
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
