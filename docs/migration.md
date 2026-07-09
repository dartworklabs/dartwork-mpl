---
orphan: true
---

# Migration Guide

This guide collects every rename / deprecation that has shipped on PyPI
(v0.4.0 onwards), **newest release first**. Every removed symbol now
raises `AttributeError` / `ModuleNotFoundError` / `TypeError` (or, for
palette tokens, the usual "not a valid color" error) with a message
naming its replacement.

> **New to dartwork-mpl?** You don't need this page. Head to the
> [Quick Start](usage_guide/quickstart.md) — it uses the current API
> end-to-end.

## At a glance

The moves you're most likely to hit, regardless of the version you're
coming from:

| Old surface                           | New surface                                          |
| ------------------------------------- | ---------------------------------------------------- |
| `dm.subplots(width=..., aspect=...)`  | `plt.subplots(figsize=dm.figsize(...))`              |
| `dm.figure(width=..., aspect=...)`    | `plt.figure(figsize=dm.figsize(...))`                |
| `plt.tight_layout()`                  | `dm.simple_layout(fig)`                              |
| `dm.auto_layout(fig)`                 | `dm.simple_layout(fig, margin=...)`                  |
| old named-color helper                | `dm.color("oc.red5")` (also accepts hex / `rgb(...)` / `oklch(...)` / `oklab(...)`) |
| `from dartwork_mpl.color import ...`  | `from dartwork_mpl._colors import ...` (submodule renamed) |
| `dartwork_mpl.asset_viz`              | `dartwork_mpl.diagnostics`                           |
| `dartwork_mpl.helpers.formatting`     | `dartwork_mpl.helpers.labels`                        |
| `dm.install_llm_txt()`                | `dm.get_agent_doc(name)` / `dm.agent_doc_path(name)` (or MCP `dartwork-mpl://guide/*`) |
| legacy `ocean*`, `spectrum*`, `focus*`, … families | see [dc.* palette migration](#dc-palette-migration-cumulative) |

The per-release sections below carry the full detail and runnable
snippets.

## v5 — generative color system (0.5.6 clean break)

A 107-number generative palette (20 families × 10 perceptually equalized
steps, `dc.{family}{step}`) replaced the hand-curated v4 catalog. v5 is a
**full clean break** (design spec:
`docs/superpowers/specs/2026-07-03-color-system-v5-design.md`):

1. **The throwaway v4 aliases were removed — but the curated categorical sets
   were kept.** The flat ad-hoc names (`sunset*`, `ocean*`, `nordic*`,
   `cyber*`, `spectrum*`, `bold*`, `corporate*`) and the numeric cycle aliases
   `0`–`7` no longer resolve. The scientifically curated categorical *sets* —
   `trustworthy`, `vivid`, `neon`, `jewel`, `blue_red`, `teal_amber`, `earth`,
   `forest`, `blue_orange`, and the rest — are **preserved** as first-class
   `dc.*` palettes: reach them through `dm.colors("trustworthy", n=6)` /
   `dm.set_colors("vivid")`, exactly like a generated family (see
   [Palettes](color_system/palettes.md)).
2. **There is no runtime palette-version switch.** The live registry is
   v5-only, so `teal`, `indigo`, and `gray` always mean the 10-step v5
   families.
3. **The old `dm.*` color aliases are gone.** Use `dc.*` named colors or
   `dm.color(...)` when you need a `Color` object.
4. **The palette-token codemod was deleted with the clean break.** The
   mapping table below is reference material for manual edits; there is no
   supported command to rewrite files automatically.
5. **Pre-v5 compatibility colormap files were removed.** Names such as
   `dc.aurora` and `dc.teal_rose` now refer to the v5 colormap catalog.
6. **Semantic tokens are v5-native.** Use `dc.pos`, `dc.neg`, `dc.ref`, and
   `dc.hl` for role-based color; use `dc.ref` rather than a gray shade for
   reference lines.
7. **The generated family set later gained `coral`, `tangerine`, `cobalt`, and
   `fuchsia`.** `coral` is now a recipe-generated 10-step family rather than
   a curated 8-step set.

## v0.5.5 — categorical palette overhaul

A judge-panel redesign reworked the then-current curated `dc.*` palette
catalog into a more coherent, better-covered set. Every palette in that
historical catalog was CIELAB-generated on an even-L\* ladder and CVD + B&W
verified — but several were renamed, merged, or dropped. The token mapping:

| Old token       | New token          | Change |
| --------------- | ------------------ | ------ |
| `spectrum*`  | `vivid*`        | rename |
| `coolwarm*`  | `dc.blue_red*`     | absorbed into the canonical blue-red diverging form |
| `bold*`      | `vivid*`        | merged into `vivid` |
| `corporate*` | `trustworthy*`  | merged into `trustworthy` |
| `dc.warm_cool*` | `dc.blue_orange*`  | removed (weakest under CVD) — use `blue_orange` |

`pastel` / `dusty` were also re-designed into an intentional high-key /
low-key pair (shared hue plan, different L\* band).

**New palettes** you can now reach for: `neon` (max-chroma electric),
`ember` (warm-vibrant), and `green_purple` (tritan-robust diverging).

## v0.5.4 — palette cleanup, module & MCP renames

### Legacy `dc.*` aliases removed

The 7 original back-compat aliases (`Vivid`, `Sunset`, `Ocean`, `Pop`,
`Cyber`, `Autumn`, `Nordic`) no longer resolve — `ocean2`, `nordic1`,
… now raise the usual "not a valid color" error. Their shade index is
preserved when you switch to the curated replacement:

| Old token     | New token (0.5.4)  |
| ------------- | ------------------ |
| `vivid*`   | `bold*`         |
| `sunset*`  | `earth*`        |
| `ocean*`   | `dc.teal*`         |
| `pop*`     | `spectrum*`     |
| `cyber*`   | `jewel*`        |
| `autumn*`  | `dusty*`        |
| `nordic*`  | `teal_indigo*`  |

> **Coming from 0.5.4 or earlier?** `bold` and `spectrum` were themselves
> renamed again in 0.5.5. The
> [dc.\* palette migration](#dc-palette-migration-cumulative) table folds
> both hops into one lookup.

### Curated palettes now use snake_case

| Old token          | New token         |
| ------------------ | ----------------- |
| `dc.teal_seq*`     | `dc.teal*`        |
| `dc.focus*`        | `dc.teal_accent*` |
| `dc.focus_warm*`   | `dc.coral_accent*`|
| `muted*`        | `pastel*`      |
| `dc.teal_amber_div*` | `dc.teal_amber*`|

### Module & entry-point removals

| Removed | Replacement |
| --- | --- |
| `dm.auto_layout(fig)` | `dm.simple_layout(fig, margin=...)` — the legacy `padding` inches arg maps to `margin`; `max_iter` / `tolerance` were obsolete. Now raises a migration-hint `AttributeError`. |
| `dartwork_mpl.helpers.formatting` | `dartwork_mpl.helpers.labels` (`ModuleNotFoundError`) |
| `dartwork_mpl.asset_viz` | `dartwork_mpl.diagnostics` (`ModuleNotFoundError`) |
| MCP `dartwork-mpl://guide/general-guide` | `dartwork-mpl://guide/agent-entry` |
| MCP `dartwork-mpl://guide/layout-guide` | `dartwork-mpl://guide/policy` |
| `ui._config.append_history` / `load_history` | `save_preset` / `load_presets` |

## v0.5.0 — installer removal & lighter core

**The `install_llm_txt` installer was removed.** It copied the bundled
prompt corpus into IDE-specific folders; the corpus is now read at runtime
instead, so there is nothing to install.

| Removed | Replacement |
|---|---|
| `dm.install_llm_txt(...)` | `dm.get_agent_doc(name)` / `dm.agent_doc_path(name)` — `name` ∈ `AGENTS`, `CLAUDE`, `llms`, `llms-full` — or the MCP `dartwork-mpl://guide/*` resources |
| `dm.uninstall_llm_txt(...)` | nothing — the corpus is read at runtime, so there is no install to undo |
| `dm.INSTALL_TARGETS` | nothing — install targets no longer exist |

**`ipython` is no longer a core dependency.** Only `dm.show()` (inline SVG
display in Jupyter) needs it, so it moved to the `notebook` optional
extra. `dm.show()` raises a clear `ImportError` naming the extra when
IPython is absent; every other entry point is unaffected.

| Old install | New install |
|---|---|
| `pip install dartwork-mpl` (pulled in ~30 MB of IPython deps) | `pip install "dartwork-mpl[notebook]"` if you use `dm.show()` |

## v0.4.1 — public API audit (wrapper removals)

The 0.4.1 audit retired the thin matplotlib wrappers whose only
contribution was default kwargs. Where the curated values were worth
keeping they now live as snippets in
[`usage_guide/recipes.md`](usage_guide/recipes.md).

### `dm.subplots` / `dm.figure` removal

The wrappers around the matplotlib figure constructors are gone. Use
`plt.subplots` / `plt.figure` directly and pass
`figsize=dm.figsize(width, aspect)`:

```python
# Before
fig, ax = dm.subplots(width="15cm", aspect="wide")

# Now
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
```

If you also passed `style=`, call `dm.style.use(...)` first:

```python
# Before
fig, ax = dm.subplots(width="15cm", aspect="wide", style="scientific")

# Now
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
```

`dm.figsize(width, aspect)` accepts a unit-string width (`"15cm"`,
`"5in"`, `"170mm"`, `"24pt"`) or a `Length` value (`dm.cm(15)`,
`dm.col1`, `dm.col2`), and four equivalent aspect forms — token
(`"wide"`), numeric ratio (`0.6`), unit-string height (`"12cm"`), or
`Length` height (`dm.cm(12)`). Bare `int` / `float` widths are rejected.

### `dm.style_spines` / `dm.add_grid` / `dm.minimal_axes` removal

All three were 1–3 line matplotlib calls; the curated kwargs now live in
[`usage_guide/recipes.md`](usage_guide/recipes.md):

| Removed | Inline replacement |
| --- | --- |
| `dm.style_spines(ax, color=c, linewidth=w, which=ws)` | `for s in ws: ax.spines[s].set_color(c); ax.spines[s].set_linewidth(w)` |
| `dm.add_grid(ax)` | `ax.grid(True, color="oc.gray3", alpha=0.3, linewidth=0.5); ax.set_axisbelow(True)` |
| `dm.minimal_axes(ax)` | see [Minimal axes recipe](usage_guide/recipes.md#minimal-axes-tufte-style) |

### `dm.auto_select_colors` → `dm.make_palette`

The rename cleaned up the argument names; the body is unchanged:

```python
# Before
colors = dm.auto_select_colors(n_series=5, color_type="sequential", highlight_index=2)

# Now
colors = dm.make_palette(5, kind="sequential", highlight=2)
```

### Formatter & spine wrappers → direct matplotlib

Five wrappers from audit round 3:

```python
# Before
dm.format_axis_percent(ax)
dm.format_axis_labels(ax, fmt="{:,.0f}")
dm.add_frame(fig)
dm.add_value_labels(ax, bars)
dm.set_xmargin(ax, 0.05); dm.set_ymargin(ax, 0.05)

# Now — direct matplotlib calls, sometimes one-liners
from matplotlib import ticker
ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
fig.patches.append(plt.Rectangle((0, 0), 1, 1, fill=False, transform=fig.transFigure))
for bar in bars: ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                          f"{bar.get_height():.0f}", ha="center", va="bottom")
ax.set_xmargin(0.05); ax.set_ymargin(0.05)
```

Eight more from audit round 2 — each is a single matplotlib call now:

```python
# Before / Now
dm.hide_spines(ax, ["top", "right"])            # → for s in ("top", "right"): ax.spines[s].set_visible(False)
dm.hide_all_spines(ax)                           # → for s in ax.spines: ax.spines[s].set_visible(False)
dm.show_only_spines(ax, ["left", "bottom"])      # → for s in ax.spines: ax.spines[s].set_visible(s in ("left", "bottom"))
dm.remove_grid(ax)                               # → ax.grid(False)
dm.format_axis_thousands(ax, axis="y")           # → see snippet below
dm.save_figure(fig, "out.png")                   # → fig.savefig("out.png")
dm.create_figure_with_style(width=..., style=...)  # → dm.style.use(style); plt.subplots(figsize=dm.figsize(...))
dm.templates.diverging_bar.get_source_code()     # → inspect.getsource(dm.templates.diverging_bar)
```

```python
# Thousand separator on y-axis:
from matplotlib import ticker
formatter = ticker.FuncFormatter(lambda x, p: f"{x:,.0f}")   # sep=","
# Non-comma separator:
# formatter = ticker.FuncFormatter(lambda x, p: f"{x:,.0f}".replace(",", sep))
ax.yaxis.set_major_formatter(formatter)   # or ax.xaxis for axis="x"
```

### `dm.Inches` → `dm.Length`

The in-flight `Inches(float)` marker was replaced by `dm.Length`, an
opaque wrapper with per-unit property views (`length.cm`, `length.mm`,
`length.inch`, `length.pt`). It is deliberately **not** a `float`
subclass — passing it to a pt-based (`fontsize=`) or px-based API would
silently misinterpret the value. `dm.Inches` is no longer importable.

## dc.* palette migration (cumulative)

If you have `dc.*` tokens from any release before 0.5.5, this table folds
every rename hop (0.5.4 legacy-alias removal, 0.5.4 snake_case, 0.5.5
overhaul) into a single lookup. Shade indices are preserved
(`ocean2` → `dc.teal2`).

| Legacy token (0.5.3 or earlier) | Current token |
| ------------------------------- | --------------------- |
| `Vivid*` / `vivid*` (alias) | `vivid*` |
| `Sunset*` / `sunset*`     | `earth*`           |
| `Ocean*` / `ocean*`       | `dc.teal*`            |
| `Pop*` / `pop*`           | `vivid*`           |
| `Cyber*` / `cyber*`       | `jewel*`           |
| `Autumn*` / `autumn*`     | `dusty*`           |
| `Nordic*` / `nordic*`     | `forest*`          |
| `spectrum*`                  | `vivid*`           |
| `bold*`                      | `vivid*`           |
| `coolwarm*`                  | `dc.blue_red*`        |
| `corporate*`                 | `trustworthy*`     |
| `dc.warm_cool*`                 | `dc.blue_orange*`     |
| `dc.teal_seq*`                  | `dc.teal*`            |
| `dc.focus*`                     | `dc.teal_accent*`     |
| `dc.focus_warm*`                | `dc.coral_accent*`    |
| `muted*`                     | `pastel*`          |
| `dc.teal_amber_div*`            | `dc.teal_amber*`      |

> These map each old token to its **closest current palette** — the
> colours themselves were re-generated in the overhaul, so a migrated
> token is a starting point, not a byte-identical swap. Browse the live
> set on the [Palettes](color_system/palettes.md)
> page.

## color parsing (old named-color helper → `dm.color`)

The old named-color helper is gone. The replacement is `dm.color`, a single string-parser
entry point that mirrors `dm.length`:

```python
# Before
red = legacy_named_color("oc.red5")

# Now
red = dm.color("oc.red5")               # palette token
red = dm.color("#ff0000")               # hex
red = dm.color("rgb(255, 0, 0)")        # rgb function string
red = dm.color("oklch(0.7 0.2 30)")     # oklch function string
red = dm.color("oklab(0.7 0.1 0.1)")    # oklab function string
```

The submodule was also renamed `color` → `colors`. Anywhere you used
`from dartwork_mpl.color import ...` swap to:

```python
# Before
from dartwork_mpl.color import Color

# Now
from dartwork_mpl._colors import Color
```
