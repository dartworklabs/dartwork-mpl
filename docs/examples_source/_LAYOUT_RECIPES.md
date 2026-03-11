# Gallery Examples Quality Standard

Comprehensive quality criteria for `dartwork-mpl` example gallery plots.
Every example in `docs/examples_source/` **must** satisfy these standards.

---

## 1. Layout Architecture

### 1.1 GridSpec Mandate

Multi-panel figures **must** use explicit `gridspec.GridSpec(figure=fig)`.
Never use `plt.subplots()` for anything beyond a single panel.

```python
# ✅ Correct
fig = plt.figure(figsize=(dm.DW, dm.DW * 0.85))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.40)
ax = fig.add_subplot(gs[0, 0])

# ❌ Forbidden for multi-panel
fig, axes = plt.subplots(2, 2, figsize=(...))
```

### 1.2 Figure Dimensions

All dimensions derive from `dm.SW` (9 cm) and `dm.DW` (17 cm).
Raw pixel/inch values are forbidden.

| Layout         | figsize                       | Aspect  |
| :------------- | :---------------------------- | :------ |
| Single panel   | `(dm.SW, dm.SW * 0.7)`        | ~1.43:1 |
| Single wide    | `(dm.SW * 1.4, dm.SW * 0.9)`  | ~1.56:1 |
| 2×2 uniform    | `(dm.DW, dm.DW * 0.85)`       | ~1.18:1 |
| 3×2 poster     | `(dm.DW * 1.1, dm.DW * 0.95)` | ~1.16:1 |
| Polar / square | `(dm.SW * 1.4, dm.SW * 1.4)`  | 1:1     |

### 1.3 Spacing Parameters

Every `GridSpec` instance must set `hspace` and `wspace` explicitly.

| Param    | Min  | Default | Max  | When to increase                     |
| :------- | :--- | :------ | :--- | :----------------------------------- |
| `hspace` | 0.30 | 0.40    | 0.50 | Panels have xlabel + title both      |
| `wspace` | 0.25 | 0.35    | 0.45 | Panels have wide ylabel (e.g. units) |

### 1.4 Layout Finalization

| Condition                              | Finalizer               |
| :------------------------------------- | :---------------------- |
| No colorbar, no polar                  | `dm.simple_layout(fig)` |
| Colorbar present (`fig.colorbar(...)`) | `fig.tight_layout()`    |
| Polar subplot only (no colorbar)       | `dm.simple_layout(fig)` |

`dm.simple_layout()` uses L-BFGS-B optimization and produces tighter,
cleaner margins than `tight_layout`. Always prefer it when compatible.

### 1.5 Asymmetric Layouts

Use `height_ratios` or `width_ratios` for non-uniform grids:

```python
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.4, 1],
                       hspace=0.35, wspace=0.30)
ax_top = fig.add_subplot(gs[0, :])   # span full width
```

---

## 2. Typography Consistency

All text sizing **must** use `dm.fs()` relative scaling, never raw `fontsize=N`.
All line weights **must** use `dm.lw()`, never raw `lw=N` or `linewidth=N`.

### 2.1 Hierarchy

| Element        | Size                      | Weight          | Example                         |
| :------------- | :------------------------ | :-------------- | :------------------------------ |
| suptitle       | `dm.fs(2)`                | `weight='bold'` | Dashboard-level heading         |
| Panel title    | `dm.fs(0)`–`dm.fs(1)`     | `weight='bold'` | `ax.set_title(...)`             |
| Axis label     | `dm.fs(0)`                | normal          | `ax.set_xlabel(...)`            |
| Tick label     | `dm.fs(-0.5)`             | normal          | Set via style, or manually      |
| Legend entries | `dm.fs(-1)`               | normal          | `ax.legend(fontsize=dm.fs(-1))` |
| Annotations    | `dm.fs(-0.5)`–`dm.fs(-1)` | normal          | `ax.annotate(...)`, `ax.text()` |
| Data labels    | `dm.fs(-1)`               | normal or bold  | Values on bars, points          |

### 2.2 Forbidden Direct Values

```python
# ❌ Hard-coded sizes
ax.set_title("Title", fontsize=14)
ax.plot(x, y, lw=2.5)

# ✅ Relative scaling
ax.set_title("Title", fontsize=dm.fs(1))
ax.plot(x, y, lw=dm.lw(1))
```

### 2.3 Typographic Details

- **En-dash** (`\u2013`) for ranges: `"2020\u20132025"`, `"10\u201315%"`.
  Never a plain hyphen for numeric ranges.
- **Subscripts**: Prefer Unicode subscripts (`\u2081`, `\u2082`) over
  LaTeX `$X_1$` when in non-math context. Accept Roboto glyph warnings.
- **Title padding**: `pad=12`–`20` for `ax.set_title()`, `y=1.02`–`1.05`
  for `fig.suptitle()`.

---

## 3. dartwork-mpl Feature Utilization

Each example **must** demonstrate at least 2 distinct `dm.*` features beyond
basic `dm.style.use()` and `dm.simple_layout()`.

### 3.1 Required Feature Coverage

The gallery as a whole must cover every public API at least once:

| Feature              | API                            | Minimum examples  |
| :------------------- | :----------------------------- | :---------------- |
| Style presets        | `dm.style.use()`               | ≥2                |
| Style stacking       | `dm.style.stack()`             | ≥1                |
| Style context        | `dm.style.context()`           | ≥1                |
| OKLCH color creation | `dm.oklch()`, `dm.Color`       | ≥1                |
| Color interpolation  | `dm.cspace()`                  | ≥2                |
| Named color convert  | `dm.named()`                   | ≥2                |
| Pseudo-alpha         | `dm.pseudo_alpha()`            | ≥3                |
| Color mixing         | `dm.mix_colors()`              | ≥1                |
| Named palettes       | `oc.*`, `tw.*`, `dc.*` strings | ≥5                |
| Custom colormaps     | `cmap='dc.deep_sea'` etc.      | ≥2                |
| Font scaling         | `dm.fs()`                      | every example     |
| Line weight scaling  | `dm.lw()`                      | every example     |
| Layout optimizer     | `dm.simple_layout()`           | default           |
| Panel labels         | `dm.label_axes()`              | every multi-panel |
| Arrow axes           | `dm.arrow_axis()`              | ≥1                |
| Decimal formatting   | `dm.set_decimal()`             | ≥3                |
| Icon fonts           | `dm.icon_font()`               | ≥1                |
| Diverging bars       | `dm.plot_diverging_bar()`      | ≥1                |
| Width constants      | `dm.SW`, `dm.DW`               | every example     |

### 3.2 Color Usage

- **Never** use raw hex codes or matplotlib default colors (e.g. `'b'`,
  `'#ff0000'`, `'C0'`).
- **Always** use named palette strings (`oc.blue5`, `tw.emerald600`, `dc.3`)
  or `dm.oklch()`/`dm.cspace()` constructed colors.
- For fills/bands, prefer `dm.pseudo_alpha()` over raw `alpha=0.3`.
  This keeps SVG/PDF exports vector-clean.

```python
# ❌ Raw alpha — rasterizes in vector export
ax.fill_between(x, y1, y2, color='blue', alpha=0.2)

# ✅ Pseudo-alpha — solid color, vector-safe
fill = dm.pseudo_alpha('oc.blue5', 0.2, background='white')
ax.fill_between(x, y1, y2, color=fill)
```

### 3.3 Style Selection

| Context              | Preset         | Notes                        |
| :------------------- | :------------- | :--------------------------- |
| Default gallery      | `presentation` | 1pt larger than scientific   |
| Academic demo        | `scientific`   | Smaller, denser labels       |
| Dark mode demo       | `dark`         | Explicit showcase only       |
| Conceptual / minimal | `minimal`      | Spine-free, data-ink focused |
| Korean text demo     | `report-kr`    | Pretendard font              |

---

## 4. Aesthetic Standards

### 4.1 Data-Ink Ratio

Every visual element must earn its place.

- **Remove** top and right spines unless the data explicitly needs them
  (the default styles already handle this).
- **No** chartjunk: background images, 3D effects, gradient backgrounds.
- **Annotations** only where they add insight (critical points, milestones,
  threshold lines), not for decoration.

### 4.2 Color Harmony

- Use **at most 5–6 distinct hues** per panel. More than that becomes noisy.
- When using a sequential palette (e.g. OKLCH interpolation), ensure the
  lightest shade has sufficient contrast against white background
  (indices ≥2 for `dc.*` palettes are safe).
- Pair a **saturated accent** with **desaturated fills**:
  line in `oc.blue7`, fill in `dm.pseudo_alpha('oc.blue5', 0.15)`.

### 4.3 Legend Placement

| Entries | Layout                           | Position                      |
| :------ | :------------------------------- | :---------------------------- |
| 1–3     | Horizontal single row (`ncol=N`) | `loc='upper right'`           |
| 4+      | Vertical stacked                 | `bbox_to_anchor` outside plot |
| Polar   | Always external                  | `bbox_to_anchor=(1.3, 1.1)`   |

- Always `frameon=False` or at minimum semi-transparent frame.
- Expand `ylim` top margin by ~10–15% if legend overlaps data region.

### 4.4 Whitespace and Breathing Room

- Bar charts: `xlim` padded by ±0.5 beyond data range, or `margins(x=0.05)`.
- Scatter plots: `margins(0.08)` minimum so edge points aren't clipped.
- Between suptitle and top panels: `y=1.02` minimum for `fig.suptitle()`.
- Tick padding: `pad=3` to `pad=5` for clean separation from spines.

### 4.5 Consistency Across Gallery

- All examples in the same category should share similar visual weight —
  a user scrolling through thumbnails should see a uniform, curated gallery,
  not a random assortment.
- Maintain a consistent data narrative tone: scientific but accessible.
  Example titles should tell a story ("Damped Oscillation", "Phase Diagram"),
  not describe the chart type ("Line Plot Example").

---

## 5. GridSpec Recipe Reference

Validated configurations. Copy directly.

### Single panel

```python
fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.7))
dm.simple_layout(fig)
```

### 2×2 uniform

```python
fig = plt.figure(figsize=(dm.DW, dm.DW * 0.85))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.40)
dm.label_axes(fig.axes)
dm.simple_layout(fig)
```

### 2×2 with colorbar

```python
fig = plt.figure(figsize=(dm.DW, dm.DW * 0.85))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.35)
fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.02)
dm.label_axes(fig.axes[:4])  # exclude colorbar axes
fig.tight_layout()
```

### 1 + 2 asymmetric

```python
fig = plt.figure(figsize=(dm.DW, dm.DW * 0.85))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.4, 1], hspace=0.35, wspace=0.30)
ax_top = fig.add_subplot(gs[0, :])
ax_bl  = fig.add_subplot(gs[1, 0])
ax_br  = fig.add_subplot(gs[1, 1])
dm.simple_layout(fig)
```

### 3×2 poster

```python
fig = plt.figure(figsize=(dm.DW * 1.1, dm.DW * 0.95))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.40, wspace=0.35)
dm.label_axes(fig.axes)
dm.simple_layout(fig)
```
