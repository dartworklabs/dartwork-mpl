# Gallery Layout Recipes (0.4)

Authoritative recipes for gallery examples in `docs/examples_source/`.
Every example **must** follow these patterns. Legacy 0.3 patterns
(`dm.SW/MW/TW/DW`, `dm.cm2in`, `dm.FS_*`, `figsize=` tuples,
`tight_layout`) are deprecated and emit warnings; the lint catalog
will block them.

---

## 0. The Three Things You Always Need

```python
import dartwork_mpl as dm

dm.style.use("scientific")                     # 1. pick a style
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))  # 2. width + aspect
ax.plot(...)
dm.simple_layout(fig)                             # 3. finalize layout
dm.save_formats(fig, "my_chart")                # (optional) save artifact
```

That's the entire surface for ~95% of plots. Everything below is just
variations on those three lines.

---

## 1. The Width and Aspect Contract

`plt.subplots(figsize=dm.figsize(...))` and `plt.figure(figsize=dm.figsize(...))` take **physical width** + **named
aspect ratio**, never raw figsize tuples.

### 1.1 Width

| Form                 | Example                | Notes                              |
| :------------------- | :--------------------- | :--------------------------------- |
| String with unit     | `width="13cm"`         | Preferred. Units: `cm`, `in`, `mm`, `pt` |
| Bare number          | `width=13`             | Rejected (`raw-width-number`); use a unit |
| `dm.cm()` helper     | `width=dm.cm(13)`      | Returns `Length`, type-safe        |
| `dm.col1` / `dm.col2`| `width=dm.col1`        | Academic single/double column      |

`dm.col1 = cm(9)` (single-column figure) and `dm.col2 = cm(17)`
(double-column figure) are sugar for the two widths that dominate
academic publishing.

### 1.2 Aspect Tokens

`aspect=` is height/width ratio. Named tokens cover ~all useful
shapes; raw floats are accepted when you need a non-standard ratio.

| Token        | Ratio (h/w) | Use case                              |
| :----------- | :---------- | :------------------------------------ |
| `square`     | 1.000       | Polar, scatter with equal axes        |
| `portrait`   | 1.250       | Tall plots, vertical bar charts       |
| `tall`       | 1.500       | Mobile reading, long vertical panels  |
| `standard`   | 0.750       | Default; most single panels           |
| `golden`     | 0.618       | Time series, line plots               |
| `wide`       | 0.667       | Side-by-side comparisons              |
| `a4`         | 0.707       | ISO paper ratios in landscape         |
| `slide`      | 0.562       | 16:9 slide decks                      |
| `cinema`     | 0.500       | Slide banners, very wide trends       |
| `panoramic`  | 0.333       | Long banners, sparklines              |

Raw floats also work: `aspect=0.4` or `aspect=1.1`. Use them only when
no named token fits; the tokens are the lingua franca and reviewers
read them faster than decimals.

---

## 2. Single-Panel Recipes

Pick a width based on where the figure will live, then choose an
aspect that matches the data shape.

### 2.1 Small / column-width single panel (9 cm)

```python
import numpy as np
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), color="dc.teal3", lw=dm.lw(1))
ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude")

dm.simple_layout(fig)
```

**Why 9 cm:** academic single-column or sidebar figures. Use
`width=dm.col1` if you prefer the named alias.

### 2.2 Medium single panel (13 cm)

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
```

**Why 13 cm:** most blog and slide use cases. Wide enough for a
single rich axis without dominating the page.

### 2.3 Large / double-column single panel (17 cm)

```python
fig, ax = plt.subplots(figsize=dm.figsize("17cm", "golden"))
```

**Why 17 cm + golden:** flagship single panel for journal articles
spanning the full page width, or hero charts in reports. The golden
ratio is a safe default for time series and scatter plots that read
left-to-right.

### 2.4 Square panel (polar, equal-axis scatter)

```python
fig, ax = plt.subplots(
    figsize=dm.figsize("9cm", "square"),
    subplot_kw={"projection": "polar"},
)
```

**Why square:** polar projections, correlation scatter with equal axis
limits, quantile-quantile plots. Anything where x and y carry the
same physical meaning.

### 2.5 Wide-format slide hero (17 cm × cinema)

```python
fig, ax = plt.subplots(figsize=dm.figsize("17cm", "cinema"))
ax.plot(years, gdp, color="tw.emerald600", lw=dm.lw(1))
```

**Why cinema:** 2:1 banner shape for slide deck title charts and
landing-page hero plots. More vertical compression than `wide`.

### 2.6 Custom aspect (raw float)

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", 0.4))
```

**When:** the plot has a constraint (e.g. matching a hand-drawn diagram
beside it) that no named token captures. The float is `height /
width`, so 0.4 = roughly 13 × 5.2 cm.

---

## 3. Multi-Panel Recipes

`plt.subplots(nrows, ncols, figsize=dm.figsize(...))` handles any uniform grid. Reach for
custom GridSpec only when row/column ratios diverge or you need
nested layouts.

### 3.1 Side-by-side, 1×2 (17 cm × wide)

```python
fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))

axes[0].plot(x, y1, color="dc.teal3", lw=dm.lw(1))
axes[0].set_title("Before")
axes[1].plot(x, y2, color="dc.orange3", lw=dm.lw(1))
axes[1].set_title("After")

dm.label_axes(axes)
dm.simple_layout(fig)
```

**Why 17 cm × wide:** two panels need horizontal room to breathe.
`wide` (2:3) gives each panel a near-square aperture.

### 3.2 Stacked rows, 2×1 (13 cm × portrait)

```python
fig, axes = plt.subplots(2, 1, figsize=dm.figsize("13cm", "portrait"), sharex=True)
axes[0].plot(t, signal, color="dc.teal3", lw=dm.lw(1))
axes[1].plot(t, residuals, color="dc.indigo3", lw=dm.lw(1))
axes[1].set_xlabel("Time (s)")

dm.label_axes(axes)
dm.simple_layout(fig)
```

**Why portrait:** stacking two panels needs extra vertical space.
`portrait` (5:4) prevents the rows from feeling cramped.

### 3.3 Uniform 2×2 grid (17 cm × standard)

```python
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"))

for ax, data, title in zip(axes.flat, datasets, titles, strict=True):
    ax.plot(data, color="dc.teal3", lw=dm.lw(1))
    ax.set_title(title, fontsize=dm.fs(0))

dm.label_axes(axes.flat)
dm.simple_layout(fig)
```

**Why 17 cm × standard:** four equal panels in a journal-friendly
shape. `aspect="standard"` keeps each panel close to landscape,
matching the figures readers expect in scientific publications.

### 3.4 Tall 3×2 dashboard (17 cm × portrait)

```python
fig, axes = plt.subplots(3, 2, figsize=dm.figsize("17cm", "portrait"))
dm.label_axes(axes.flat)
dm.simple_layout(fig)
```

**Why portrait:** six panels stacked 3×2 need the extra vertical room
that `portrait` (5:4) provides.

### 3.5 Asymmetric rows / columns (`width_ratios`, `height_ratios`)

When rows or columns have different widths, pass ratios directly to
`plt.subplots`:

```python
fig, axes = plt.subplots(
    1, 3,
    figsize=dm.figsize("17cm", "wide"),
    width_ratios=[2, 1, 1],
)
```

For non-rectangular layouts (a wide top panel above two narrow lower
panels), drop down to a custom GridSpec — see §4.

---

## 4. Custom GridSpec (Advanced)

Reach for `plt.figure(figsize=dm.figsize(...))` + `gridspec.GridSpec` only when:

- You span cells (top row spans all columns, etc.).
- You nest GridSpec inside GridSpec.
- You attach a colorbar with non-trivial placement.

For these advanced layouts, `dm.simple_layout(fig)` is the right
finalizer; the auto-layout retry loop assumes a uniform grid.

### 4.1 Asymmetric: 1 wide row + 2 narrow row

```python
import matplotlib.gridspec as gridspec
import dartwork_mpl as dm

dm.style.use("scientific")
fig = plt.figure(figsize=dm.figsize("17cm", "standard"))
gs = gridspec.GridSpec(
    2, 2,
    figure=fig,
    height_ratios=[1.4, 1],
    hspace=0.35,
    wspace=0.30,
)

ax_top = fig.add_subplot(gs[0, :])
ax_bl = fig.add_subplot(gs[1, 0])
ax_br = fig.add_subplot(gs[1, 1])

# ... plotting ...

dm.label_axes(fig.axes)
dm.simple_layout(fig)
```

**Why `simple_layout` here:** the top row spans columns, so per-cell
overflow measurement isn't well-defined. `simple_layout` solves the
GridSpec margins directly via L-BFGS-B and produces a deterministic
result.

### 4.2 Colorbar attached to a single panel

```python
fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
cf = axes[0].imshow(field, cmap="dc.aurora")
axes[1].plot(profile, color="dc.indigo6", lw=dm.lw(1))
fig.colorbar(cf, ax=axes[0], shrink=0.85, pad=0.02)

dm.label_axes(axes)
dm.simple_layout(fig)   # walks the colorbar's own axes too
```

---

## 5. Twinx (Dual Y-Axis)

dartwork-mpl 0.4 monkey-patches `Axes.twinx()` so the **right spine
is automatically visible** with the correct linewidth from the active
style. You no longer need to call `ax2.spines["right"].set_visible(True)`.

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
ax.bar(x, temperature, color="dc.teal2", width=0.55)
ax.set_ylabel("Temperature (°C)")

ax2 = ax.twinx()             # right spine visible by design
ax2.plot(x, change_pct, "o-", color="dc.orange3", lw=dm.lw(1))
ax2.set_ylabel("Change (%)", color="dc.orange3")
ax2.tick_params(axis="y", labelcolor="dc.orange3")

dm.simple_layout(fig)
```

**Why wide:** dual-axis plots crowd labels on both edges, so a wider
canvas keeps text legible.

---

## 6. Layout Finalizer — `simple_layout`

| Call                                          | When to use                                          |
| :-------------------------------------------- | :--------------------------------------------------- |
| `dm.simple_layout(fig)`                       | **Default.** Snaps content flush to figure edges.    |
| `dm.simple_layout(fig, margin="2%")`          | Uniform inset buffer (also `dm.mm(2)`, `dm.cm(0.5)`, `"5mm"`). |
| `dm.simple_layout(fig, ml=..., mt=..., ...)`  | Per-side asymmetric margins.                         |
| `dm.simple_layout(fig, gs=gs)`                | Target a specific GridSpec (multi-panel).            |
| ❌ `fig.tight_layout()`                       | Forbidden — collides with dartwork-mpl spines/legends. |
| ❌ `dm.auto_layout(fig)`                      | Removed in 0.5.4 — now raises `AttributeError`. Use `dm.simple_layout(fig, margin=...)`. |

`simple_layout` measures every visible artist on every axes
(texts, title, axis labels, view-limited tick labels, axis offset
text, legend) and arithmetically places the GridSpec so the
content union sits at the requested distance from each figure
edge. The result is deterministic — no scipy, no optimizer.

---

## 7. Saving the Figure

Always pair plots with `dm.save_formats(fig, "name")`. It writes both
PNG and PDF (and SVG if requested) to the rcParams output directory
and applies the active style's dpi.

```python
dm.save_formats(fig, "phase_diagram")
# or with explicit formats:
dm.save_formats(fig, "phase_diagram", formats=("png", "pdf", "svg"))
```

For interactive sessions, use `dm.save_and_show(fig, "name")` — it
saves first and then displays the figure inline.

---

## 8. Legacy ↔ 0.4 Cheat Sheet

A single line you can grep for when migrating old code.

| Legacy 0.3 pattern                              | 0.4 replacement                                       |
| :---------------------------------------------- | :---------------------------------------------------- |
| `figsize=(dm.SW, dm.SW * 0.7)`                  | `width="9cm", aspect="standard"`                      |
| `figsize=(dm.MW, dm.MW * 0.7)`                  | `width="12cm", aspect="standard"`                     |
| `figsize=(dm.TW, dm.TW * 0.55)`                 | `width="14.5cm", aspect="wide"` (or `width="13cm"`)   |
| `figsize=(dm.DW, dm.DW * 0.5)`                  | `width="17cm", aspect="cinema"`                       |
| `figsize=(dm.DW, dm.DW * 0.85)`                 | `width="17cm", aspect="standard"`                     |
| `figsize=(dm.SW * 1.4, dm.SW * 1.4)`            | `width="13cm", aspect="square"`                       |
| `figsize=(dm.cm2in(20), dm.cm2in(15))`          | `width="20cm", aspect=0.75`                           |
| `plt.subplots(figsize=(...))`                   | `plt.subplots(figsize=dm.figsize("...", "..."))`              |
| `plt.figure(figsize=(...))`                     | `plt.figure(figsize=dm.figsize("...", "..."))`                |
| `fig.tight_layout()`                            | `dm.simple_layout(fig)` (or `dm.simple_layout(fig)`)    |
| `plt.style.use("scientific")`                   | `dm.style.use("scientific")`                          |
| `dm.FS_SINGLE` / `dm.FS_DOUBLE`                 | `width="9cm"` / `width="17cm"` + explicit `aspect`    |

---

## 9. Style Selection

| Context                | Preset           | Notes                              |
| :--------------------- | :--------------- | :--------------------------------- |
| Default gallery        | `presentation`   | Slightly larger than `scientific`  |
| Academic / publication | `scientific`     | Smaller, denser labels             |
| Reports / dashboards   | `report`         | Business-facing styling            |
| Tufte / minimal        | `minimal`        | Spine-free, data-ink focused       |
| Slide presentations    | `presentation`   | Bold typography, thick lines       |
| Korean text            | `report-kr`      | Pretendard font, KR-aware          |
| Dark mode showcase     | `dark`           | Use sparingly, demo only           |

Stack styles when you need a layered tweak (e.g. add a Korean font on
top of a base preset):

```python
dm.style.use(["scientific", "lang-kr"])
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
```

---

## 10. Typography & Color (Quick Reference)

These haven't changed in 0.4 but are recapped for completeness.

### 10.1 Font Sizes

Use `dm.fs(level)` for relative scaling. Never hard-code `fontsize=N`.

| Element              | Size                         | Weight         |
| :------------------- | :--------------------------- | :------------- |
| `fig.suptitle`       | `dm.fs(2)`                   | `bold`         |
| `ax.set_title`       | `dm.fs(0)` to `dm.fs(1)`     | `bold`         |
| Axis label           | `dm.fs(0)`                   | normal         |
| Tick label           | `dm.fs(-0.5)`                | (set by style) |
| Legend               | `dm.fs(-1)`                  | normal         |
| Annotation / data    | `dm.fs(-1)` to `dm.fs(-0.5)` | normal or bold |

### 10.2 Line Weights

Use `dm.lw(level)` for relative scaling. Never hard-code `lw=2.5`.

```python
ax.plot(x, y, lw=dm.lw(1))            # primary trend
ax.axhline(0, lw=dm.lw(-1), color="dc.indigo2")  # reference
```

### 10.3 Colors

Use named palette strings (`oc.*`, `tw.*`, `dc.*`) or constructors
(`dm.oklch(...)`, `dm.cspace(...)`). Never raw hex or matplotlib
single-letter codes.

For fills/bands, prefer `dm.pseudo_alpha(...)` so the color stays
solid in vector exports:

```python
fill = dm.pseudo_alpha("dc.teal2", 0.15, background="white")
ax.fill_between(x, y_lo, y_hi, color=fill)
```

---

## 11. Lint Compliance

Every example is checked against
`dartwork_mpl.asset/prompt/02-anti-patterns.yaml`. The critical rules:

- `figsize=(...)` → forbidden. Use `plt.subplots(figsize=dm.figsize("...", "..."))`.
- `tight_layout()` → forbidden. Use `dm.simple_layout(fig)`.
- `plt.style.use(...)` → warning. Use `dm.style.use(...)`.
- `dm.subplots(...)` / `dm.figure(...)` → REMOVED. Use `plt.subplots(figsize=dm.figsize(...))`.
- `dm.SW/MW/TW/DW/FS_*/WIDTHS` → warning. Use `width="..cm", aspect="..."`.
- `dm.cm2in(...)` inside `figsize=` → warning. Migrate to `width="..cm"`.

Run the lint locally before opening a PR:

```python
from dartwork_mpl.lint import lint, format_report
print(format_report(lint(open("plot_my_example.py").read())))
```

A clean example reports `✅ No issues found.`
