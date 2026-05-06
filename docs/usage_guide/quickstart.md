# Quick Start

A minimal end-to-end workflow: apply a style, create a figure, and
export it. Skim this in five minutes — you'll already know enough to
ship a publication-grade plot.

:::{tip}
A **live ruler** below this section maps `dm.fs(n)` / `dm.fw(n)` / `dm.lw(n)`
to actual point sizes and stroke widths under each preset — drag the sliders
to read off the resolved values without leaving the docs.
:::

## At-a-glance ROI

| What used to hurt                   | dartwork-mpl                                    |
| ----------------------------------- | ----------------------------------------------- |
| Hand-tuning `figsize` and `dpi`     | `plt.subplots(figsize=dm.figsize("13cm", "standard"))`  |
| `tight_layout` clipping labels      | `dm.auto_layout(fig)` — real optimizer          |
| Reaching for hex codes              | `color="oc.blue5"` (Open Color), `"tw.*"`, `"md.*"`, `"ad.*"`, `"cu.*"`, `"pr.*"` |
| Saving in 3 formats                 | `dm.save_formats(fig, "out", formats=("png", "svg", "pdf"))` |
| Catching margin / overflow problems | `dm.validate_with_fixes(fig)`                   |

Here's a typical matplotlib figure, then the same figure with dartwork-mpl:

::::{tab-set}

:::{tab-item} ✨ With dartwork-mpl

```python
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")  # curated fonts, colors, line weights

# width = physical figure width, aspect = height/width ratio
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))

x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="oc.blue5", label="signal", lw=dm.lw(1.5))
ax.set_xticks(np.arange(0, 11, 2))
ax.set_xlabel("Time [s]")
ax.set_ylabel("Amplitude")
ax.legend()

dm.auto_layout(fig)             # auto-optimize margins
dm.save_and_show(fig, "first")  # save + inline preview
```

:::

:::{tab-item} 🔧 Vanilla matplotlib

```python
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(5.91, 3.94), dpi=300)

x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="#1c7ed6", label="signal", lw=1.5)
ax.set_xticks(np.arange(0, 11, 2))
ax.set_xlabel("Time [s]", fontsize=7.5)
ax.set_ylabel("Amplitude", fontsize=7.5)
ax.legend(fontsize=6.5)

fig.tight_layout()
fig.savefig("output.png", dpi=300, bbox_inches="tight")
plt.show()
```

:::

::::

:::{figure} images/quickstart_first_figure.svg
:alt: Scientific-style line chart created with dartwork-mpl
:width: 100%

The same chart rendered with `dm.style.use("scientific")` and
`plt.subplots(figsize=dm.figsize(…, …))` — professional typography,
optimized margins, and named colors.
:::

**Drag the slider to compare — same data, different styling:**

```{raw} html
:file: images/compare_slider.html
```

Same data, same plotting logic — the difference is one `dm.style.use()`
call, the `width` / `aspect` arguments on `dm.figsize`, named colors,
and `auto_layout`.

**What each dartwork-mpl call does:**

| Call                                          | Purpose                                                                            |
| --------------------------------------------- | ---------------------------------------------------------------------------------- |
| `dm.style.use("scientific")`                  | Sets palette, fonts, line weights — see [Styles](styles.md)                        |
| `dm.figsize("13cm", "standard")`              | Physical width plus an aspect token, returned as the inches tuple `figsize=` expects. |
| `dm.fs(0)`                                    | Returns the base font size of the active preset (`fs(2)` = base + 2 pt, and so on) |
| `dm.auto_layout(fig)`                         | Auto-optimizes margins (replaces `tight_layout`)                                   |
| `dm.save_and_show(fig, "first")`              | Saves multi-format and previews inline in the notebook                             |

### Static reference: `dm.fs(n)` resolved per preset

Plain-text fallback for the live ruler — useful when JavaScript is
disabled (AI agents, terminal browsers) or when copying numbers into a
spreadsheet. Each row is the **base font size** that ships with the
preset's `font-*.mplstyle`; `dm.fs(n)` returns ``base + n`` (in
points), `dm.fw(n)` and `dm.lw(n)` apply analogous offsets to font
weight and stroke width.

| Preset         | Base `font.size` (pt) | Typical `dm.fs(2)` (pt) |
| -------------- | --------------------: | ----------------------: |
| `scientific`   | 7.5                   | 9.5                     |
| `report`       | 8.0                   | 10.0                    |
| `web`          | 11.0                  | 13.0                    |
| `presentation` | 10.5                  | 12.5                    |
| `poster`       | 12.0                  | 14.0                    |
| `minimal`      | 7.5                   | 9.5                     |

Source of truth: `src/dartwork_mpl/asset/mplstyle/font-*.mplstyle`. If
those values change, regenerate this table.

## Creating Figures with `dm.figsize`

`dm.figsize(width, aspect)` is the sanctioned way to size a figure. It
returns the inch tuple matplotlib's `figsize=` argument expects, so you
keep the native `plt.subplots` / `plt.figure` constructors and never
hand-roll inches yourself.

```python
# Physical width plus an aspect token (default aspect="standard" = 3/4)
fig, ax = plt.subplots(figsize=dm.figsize("13cm"))
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
fig, ax = plt.subplots(figsize=dm.figsize(dm.cm(11.3), "square"))

# Apply a style preset separately
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))

# Stacked styles
dm.style.stack(["font-report", "theme-dark"])
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"))

# Academic-column shortcuts
fig, ax = plt.subplots(figsize=dm.figsize(dm.col1, "golden"))  # 9 cm
fig, ax = plt.subplots(figsize=dm.figsize(dm.col2, "cinema"))  # 17 cm
```

**Width** accepts:

- A unit-suffixed string: `"13cm"`, `"9.5cm"`, `"6.7in"`, `"170mm"`,
  `"24pt"`
- A `Length` value: `dm.cm(11.3)`, `dm.inch(4.6)`, `dm.mm(170)`,
  `dm.pt(24)`, or `dm.length("13cm")` (string parser)
- The sugar constants `dm.col1` (9 cm) and `dm.col2` (17 cm)

Bare `int` / `float` are rejected — the unit must always be explicit.

**Aspect** is one of `square` (1.0), `portrait` (5/4), `standard` (3/4),
`golden` (1/1.618), `wide` (2/3), `cinema` (1/2), or any positive float.

:::{note}
The 0.4-era constructors `dm.subplots` and `dm.figure` (and their
`figsize=` / `dpi=` arguments) were removed. Calls now raise
`AttributeError` / `TypeError` with a message naming the modern
`plt.subplots(figsize=dm.figsize(...))` form. See
[`asset/prompt/01-policy.md`](https://github.com/dartworklabs/dartwork-mpl/blob/main/src/dartwork_mpl/asset/prompt/01-policy.md)
for the full lint catalog.
:::

**Multi-panel figures:**

```python
fig, axes = plt.subplots(
    2, 2,
    figsize=dm.figsize("17cm", "standard"),
    width_ratios=[2, 1],
    height_ratios=[1, 2],
)

for ax in axes.flat:
    ax.plot(np.random.randn(100))

dm.auto_layout(fig)
```

## Adding color

dartwork-mpl registers named colors from several design systems. Use them
anywhere matplotlib accepts a color string:

```python
# Named color prefixes
ax.plot(x, y, color="oc.blue5")                    # OpenColor
ax.fill_between(x, y1, y2, color="tw.emerald200")  # Tailwind
ax.bar(categories, values, color="md.red500")      # Material Design
```

**Discover what's available without leaving Python:**

```python
import dartwork_mpl as dm

dm.list_palettes()[:5]   # → ['ad.blue', 'ad.cyan', 'ad.geekblue', ...]
dm.show_palette("oc.blue")  # renders the 9-shade swatch row in Jupyter
dm.plot_colors(ncols=4)     # full library overview, one figure per system
```

See [Colors and Colormaps](colors.md) for the full palette reference,
or open the [interactive palette explorer](../color_system/colors.md)
to click-and-copy color names from your browser.

## Multi-panel layout

```python
import dartwork_mpl as dm
import numpy as np

dm.style.use("presentation")

x = np.linspace(0, 10, 100)
fig = plt.figure(figsize=dm.figsize("15cm", "wide"))
gs = fig.add_gridspec(1, 2, wspace=0.3)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

ax1.plot(x, np.sin(x), color="oc.red5")
ax2.plot(x, np.cos(x), color="oc.blue5")

dm.label_axes([ax1, ax2])  # adds (a), (b) panel labels
dm.simple_layout(fig, gs=gs)
```

:::{figure} images/quickstart_multi_panel.svg
:alt: Two-panel layout with label_axes showing sin and cos
:width: 100%
:::

## Saving in multiple formats

```python
dm.save_formats(
    fig,
    "output/my_figure",
    formats=("png", "svg", "pdf"),
    dpi=300,
    validate=True,  # auto-check for overflow, overlap, etc.
)
```

## Catch problems before you export

`validate=True` above runs the same checks as the standalone
`validate_with_fixes` helper, which can also patch the easy issues
in-place:

```python
result = dm.validate_with_fixes(fig)
print(result.report())     # human-readable summary of warnings
# margin_asymmetry → auto-fixed via dm.auto_layout()
# pie_label_offset → auto-adjusted pctdistance
```

Use it in CI to fail a build when a figure breaks; use it locally to
get a one-line health check before you `save_formats`.

## Try the interactive UI

If you'd rather see the effect of every parameter before committing
it to code, dartwork-mpl ships a local web app that wires sliders to
your render function and exports the resulting Python script:

```bash
# 1. scaffold a starter viewer (first time only)
pip install "dartwork-mpl[ui]"
dartwork-ui init ./my-viewer --example simple

# 2. run it — opens http://127.0.0.1:8501
cd my-viewer && python viewer.py
```

→ [Interactive UI guide](interactive.md)

## Next steps

::::{grid} 1 1 2 3
:gutter: 2

:::{grid-item-card} 🎨 Styles and Presets
Choose the right preset for your use case — papers, reports, slides, posters.

→ [Browse presets](styles.md)
:::

:::{grid-item-card} 🌈 Colors and Colormaps
Explore 900+ named palettes and perceptual OKLCH interpolation.

→ [See palettes](colors.md)
:::

:::{grid-item-card} 📐 Layout and Typography
Panel labels, arrows, font scaling, and margin optimization.

→ [Learn layout](layout.md)
:::

:::{grid-item-card} 💾 Save and Validation
Multi-format export + automatic visual quality checks.

→ [Export guide](save_export.md)
:::

:::{grid-item-card} 🛠️ Interactive UI
Tune fonts, line weights, margins with sliders. Export the exact
script that reproduces what you see.

→ [Interactive UI](interactive.md)
:::

:::{grid-item-card} 🔬 Diagnostics & Templates
`dm.plot_colors()` / `plot_colormaps()` / `plot_fonts()` for asset
audit, plus ready-to-use plot templates like `plot_diverging_bar`.

→ [Extras guide](extras.md)
:::

::::
