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
- A misspelt name raises `ValueError` when drawn and is a critical lint
  finding (`dm.lint_code`). Check a name with
  `"dc.teal3" in matplotlib.colors.get_named_colors_mapping()`.

## Series and palettes

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("report")
dm.set_colors("dc.octave")             # after style.use, before plotting
print(dm.colors("dc.teal", n=4))       # four ordered steps of one family
print(dm.colors("dc.vivid", n=3))      # first three of a qualitative set
print([c["name"] for c in dm.list_colors("qualitative")])
```

Unrelated categories: `dc.octave` or a qualitative set (`dc.vivid`,
`dc.pastel`, `dc.dusty`, `dc.earth`, `dc.jewel`, ...). Ordered groups: steps
of one family.

## One highlighted series

```python
x = np.arange(2015, 2025)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
for i, name in enumerate(["North", "South", "East", "West"]):
    y = 50 + 3 * i + np.cumsum(np.ones(len(x)) * (i - 1.5))
    focus = name == "East"
    ax.plot(x, y, color="dc.orange6" if focus else "dc.gray4",
            zorder=3 if focus else 2)
    ax.annotate(name, (x[-1], y[-1]), xytext=(4, 0),
                textcoords="offset points", va="center",
                color="dc.orange6" if focus else "dc.gray6")
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
- `dm.show_colors("sequential")` draws a swatch figure for choosing.

Construction and validation background lives in `dm.get_prompt("01-policy")`
(Color section) and the documentation's colour-system pages.
