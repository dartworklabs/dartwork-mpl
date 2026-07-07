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

### dartwork Color — families

The **20 single-hue families** — 19 chromatic ramps plus gray — are the
perceptual backbone of the system. Each is ten steps (`dc.blue0` …
`dc.blue9`), generated deterministically on CIELAB L\* + OKLCH and equalized
so that *step-number difference = perceptual difference*
(`dc.blue3↔dc.blue5` covers the same distance as `dc.blue6↔dc.blue8`). Reach
any color as a plain string — `color="dc.blue6"` — anywhere matplotlib accepts
a color; the `dc.*` colormaps derive from these same recipes. The full theory
is on the
[Color system design](design.md) page.

```{raw} html
:file: images/colors_dc_families.html
```

### dartwork Color — curated categorical palettes

Beyond the 20 single-hue families, dartwork ships a curated
**20-palette categorical system** — hand-tuned qualitative, analogous, muted,
tonal, duo, diverging, neutral-cast, emphasis, and accessible *sets*
(CIELAB/OKLCH-anchored and verified for black-&-white + color-blindness) with
no generative equivalent. They resolve through the same API as any family, so
`dm.set_cycle("trustworthy")` and `dm.get_palette("cool_warm")` work exactly
like `dm.get_palette("blue")`.

Counts are intentional: sequential family ramps have 10 steps, curated
categorical sets have 8 colors, Octave has 8 chromatic colors, and Octave Print
has 7 chromatic colors plus dark gray. Octave Print is hue-parallel with
Octave, so the first seven slots keep the same hue identity while improving
print lightness separation. In the interactive explorer, Octave, Octave Print,
`trustworthy`, `vivid`, and `neon` form one **Qualitative** group ordered from
restrained to high chroma.

- `trustworthy` / `vivid` / `neon` — qualitative sets aligned with Octave and
  Octave Print for unrelated categories
- `pastel` / `dusty` — muted qualitative sets for soft editorial color
- `forest` / `teal_indigo` — analogous one-mood arcs
- `blue_orange` / `teal_coral` — two opposed groups
- `cool_warm` / `teal_amber` / `purple_green` — diverging ± scales
- `earth` / `jewel` / `ember` — tonal moods
- `warm_gray` / `cool_gray` — hue-free ramps with a cast
- `teal_accent` / `coral_accent` — highlight one series, mute the rest
- `accessible` — the Okabe-Ito CVD gold standard

The interactive picker (Qualitative palettes, Sequential families, intent
groups, B&W badges, CVD metrics, 9 chart shapes) lives on the
[Categorical palettes](categorical-palettes.md) page. The v5 clean break kept
these curated `dc.*` sets and trimmed only the throwaway ad-hoc aliases; see
the [migration guide](../migration.md) for the manual rename map.

```{raw} html
:file: images/colors_dc.html
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
