# Colours

The preset already sets a series colour cycle. Change colours when the user
asks or the figure needs it; explicit hex or matplotlib colours from the
user are used exactly.

## Named colours

- `dc.<family><step>`: 20 families (amber, blue, cobalt, coral, cyan,
  fuchsia, gray, green, indigo, lime, orange, pink, purple, red, rose, sky,
  tangerine, teal, violet, yellow), steps 0 (light) to 9 (dark): `dc.teal3`.
- Other libraries by name: `oc.blue5` (OpenColor), `tw.blue500` (Tailwind),
  `md.red500` (Material), `ad.blue6` (Ant), `cu.teal500` (Chakra),
  `pr.blue5` (Primer).
- `dc.pos` (gain) and `dc.neg` (loss) are green/red by default and red/blue under a `-kr` preset.
  Use a fixed name such as `dc.red5` to keep the same colour across presets.
- A misspelt name raises `ValueError` when drawn and is a critical lint
  finding (`dm.lint_code`). Check a name with
  `"dc.teal3" in matplotlib.colors.get_named_colors_mapping()`.

## Series and palettes

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("report")
print(dm.colors("dc.teal", n=4))       # four ordered steps of one family
print(dm.colors("dc.vivid", n=3))      # first three of a qualitative set
print([c["name"] for c in dm.list_colors("qualitative")])
```

Unrelated categories: `dc.octave` or a qualitative set (`dc.vivid`,
`dc.pastel`, `dc.dusty`, `dc.earth`, `dc.jewel`, ...). Ordered groups: steps
of one family.

More lines than the cycle has colours (eight; seven in `dark`): the cycle
starts again, so line nine has line one's colour. Keep the colours and draw
each line that repeats one dashed, `linestyle="--"`, so colour and dash
together name a line. Lines named at their ends (`dm.label_line_ends(ax)`)
keep that too.

## One highlighted series

The highlighted series keeps its own colour (in a new figure, the preset's
first colour); every other series or bar turns `dc.gray4`; widths, markers and
the legend stay.

```python
x = np.arange(2015, 2025)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
for i, name in enumerate(["North", "South", "East", "West"]):
    ax.plot(x, 50 + 3 * i + np.cumsum(np.ones(len(x)) * (i - 1.5)), label=name)
for line in ax.get_lines():
    if line.get_label() == "East":
        line.set_zorder(3)                    # keeps its colour
    else:
        line.set_color("dc.gray4")
dm.place_legend(ax)                           # after recolouring: fresh handles
dm.simple_layout(fig)
plt.close(fig)
```

## Colormaps

```python
z = np.outer(np.linspace(-1, 1, 30), np.linspace(-1, 1, 30))
fig, (a, b) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "7cm"))
a.imshow(np.abs(z), cmap="viridis")                    # ordered values
b.imshow(z, cmap="dc.blue_red", vmin=-1, vmax=1)       # signed, centred on 0
dm.simple_layout(fig)
plt.close(fig)
```

- Ordered values: `viridis`, `cividis`, `magma` or a family (`cmap="dc.blue"`,
  `cmap="dc.aurora"`). Signed values around a centre: a diverging map
  (`dm.list_colors("diverging")`) with symmetric limits.
- `jet`, `rainbow` and `hsv` get a lint warning; keep them when the user asks.

## A ramp between two colours

Ordered data of one hue: take a family (`dm.colors("dc.teal", n=6)`,
`cmap="dc.teal"`); its steps are already designed. Two given colours (two
brand colours, a hue pair no family has): interpolate in OKLab, not with
`LinearSegmentedColormap.from_list`, which mixes in sRGB and spaces the
lightness steps unevenly.

```python
from matplotlib.colors import LinearSegmentedColormap

lo = np.array(dm.color("oc.indigo8").to_oklab())
hi = np.array(dm.color("oc.teal4").to_oklab())
ramp = [dm.oklab(*(lo + (hi - lo) * t)).to_hex() for t in np.linspace(0, 1, 10)]
cmap = LinearSegmentedColormap.from_list("indigo_teal", ramp)   # continuous
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "7cm"))
ax.imshow(np.abs(z), cmap=cmap)
dm.simple_layout(fig)
plt.close(fig)
```

Use `ramp` as a list of discrete colours, `cmap` for an image. Two colours
of opposite hue (indigo and orange) meet in grey in any space; for values
around a centre take a diverging map. Do not interpolate in OKLCH: between
far hues it passes through others (indigo to orange runs through magenta),
and between near ones it asks for chroma sRGB cannot show and is cut.
