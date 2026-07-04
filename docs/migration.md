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
| `dm.named("oc.red5")`                 | `dm.color("oc.red5")` (also accepts hex / `rgb(...)` / `oklch(...)` / `oklab(...)`) |
| `from dartwork_mpl.color import ...`  | `from dartwork_mpl.colors import ...` (submodule renamed) |
| `dartwork_mpl.asset_viz`              | `dartwork_mpl.diagnostics`                           |
| `dartwork_mpl.helpers.formatting`     | `dartwork_mpl.helpers.labels`                        |
| `dm.install_llm_txt()`                | `dm.get_agent_doc(name)` / `dm.agent_doc_path(name)` (or MCP `dartwork-mpl://guide/*`) |
| `dc.ocean*`, `dc.spectrum*`, `dc.focus*`, … | see [dc.* palette migration](#dc-palette-migration-cumulative) |

The per-release sections below carry the full detail and runnable
snippets.

## v5 — generative color system (Unreleased)

A 91-parameter generative palette (16 families × 10 perceptually-equalized
steps, `dc.{family}{step}`) replaces the hand-curated v4 catalog as the
default. Design spec:
`docs/superpowers/specs/2026-07-03-color-system-v5-design.md`.

1. **v4 `dc.*` tokens are frozen, not removed.** Every legacy-only token
   (`dc.vivid*`, `dc.pastel*`, `dc.0`–`dc.7`, …) keeps resolving to its
   pre-v5 hex value — existing scripts render unchanged. Accessing one
   emits a one-time `DeprecationWarning` per token; removal is planned
   no sooner than two minor releases out.
2. **Opt in to the v5 remap for the three colliding families** with
   `dm.set_palette_version(5)`. `dc.teal*`, `dc.indigo*`, and `dc.gray*`
   (steps 0–7) are the only names that exist in both catalogs; calling
   this remaps those specific tokens (and their `dm.*` alias) to their
   v5 hex in place. The default (`dm.set_palette_version(4)`, implicit)
   keeps them frozen at the legacy value.
3. **Colormaps are matplotlib-native — no bespoke accessor.** Use
   `cmap="dc.aurora"` in any plotting call, or `plt.colormaps["dc.aurora"]`
   / `mpl.colormaps["dc.aurora"]` to fetch the `Colormap` object directly.
4. **BREAKING: `dc.aurora` / `dc.teal_rose` renamed to
   `dc.legacy_aurora` / `dc.legacy_teal_rose`.** Both names are ceded to
   the new v5 colormap catalog, which ships a differently-tuned
   `dc.aurora`. A script that passes `cmap="dc.aurora"` will silently
   start rendering the v5 colormap after upgrading — swap to
   `cmap="dc.legacy_aurora"` (or `dc.legacy_teal_rose`) to keep the
   pre-v5 rendering.
5. **`get_palette("teal" | "indigo" | "gray")` length depends on the
   active palette version.** These three curated names collide with a
   v5 family, so under the default version (4) they stay capped at the
   legacy 8-step ramp; call `dm.set_palette_version(5)` first to get the
   full, coherent 10-step v5 ramp. Every other family always returns 10
   steps regardless of version.
6. **The `DeprecationWarning` only fires through `dm.color()` /
   `Color()`.** Native matplotlib color resolution — e.g.
   `plt.plot(color="dc.vivid3")` — reads the named-color mapping
   directly and does not go through dartwork-mpl's warning hook, so it
   will not warn even though the token is frozen-legacy.
7. **`dc.ref` is a new token, not an alias for `dc.gray6`.** The
   locale-aware semantic tokens (`dc.pos` / `dc.neg` / `dc.ref` /
   `dc.hl`) are new in v5; `dc.ref` happens to equal the v5 `gray6` hex,
   which is not the same value as the frozen-legacy `dc.gray6` under the
   default palette version. Use `dc.ref` (not `dc.gray6`) for the
   reference-line role so it stays consistent whichever palette version
   is active.

### Automated migration

A codemod rewrites the removed v0.5.5 palette-token names (see the table
below) to their current equivalents — never at runtime, always as a visible
diff you review before applying:

```bash
python -m dartwork_mpl.colors._migrate path/to/script.py      # dry-run diff
python -m dartwork_mpl.colors._migrate --apply path/to/*.py   # write
```

Each rewrite is tagged *colours preserved* (a pure rename) or *review* (a
merge into a different palette). The run also prints an advisory table of the
per-token CIEDE2000 ΔE by which `teal` / `indigo` / `gray` shift under
`set_palette_version(5)`, so opting into the v5 values is an informed choice.

## v0.5.5 — categorical palette overhaul

A judge-panel redesign reworked the 24 curated `dc.*` palettes into a
more coherent, better-covered set. Every palette is still CIELAB-generated
on an even-L\* ladder and CVD + B&W verified — but several were renamed,
merged, or dropped. The token mapping:

| Old token       | New token          | Change |
| --------------- | ------------------ | ------ |
| `dc.spectrum*`  | `dc.vivid*`        | rename |
| `dc.coolwarm*`  | `dc.cool_warm*`    | rename (uniform diverging underscore) |
| `dc.bold*`      | `dc.vivid*`        | merged into `vivid` |
| `dc.corporate*` | `dc.trustworthy*`  | merged into `trustworthy` |
| `dc.warm_cool*` | `dc.blue_orange*`  | removed (weakest under CVD) — use `blue_orange` or `teal_coral` |

`pastel` / `dusty` were also re-designed into an intentional high-key /
low-key pair (shared hue plan, different L\* band).

**New palettes** you can now reach for: `neon` (max-chroma electric),
`ember` (warm-vibrant), and `purple_green` (tritan-robust diverging).

## v0.5.4 — palette cleanup, module & MCP renames

### Legacy `dc.*` aliases removed

The 7 original back-compat aliases (`Vivid`, `Sunset`, `Ocean`, `Pop`,
`Cyber`, `Autumn`, `Nordic`) no longer resolve — `dc.ocean2`, `dc.nordic1`,
… now raise the usual "not a valid color" error. Their shade index is
preserved when you switch to the curated replacement:

| Old token     | New token (0.5.4)  |
| ------------- | ------------------ |
| `dc.vivid*`   | `dc.bold*`         |
| `dc.sunset*`  | `dc.earth*`        |
| `dc.ocean*`   | `dc.teal*`         |
| `dc.pop*`     | `dc.spectrum*`     |
| `dc.cyber*`   | `dc.jewel*`        |
| `dc.autumn*`  | `dc.dusty*`        |
| `dc.nordic*`  | `dc.teal_indigo*`  |

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
| `dc.muted*`        | `dc.pastel*`      |
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
(`dc.ocean2` → `dc.teal2`).

| Legacy token (0.5.3 or earlier) | Current token (0.5.5) |
| ------------------------------- | --------------------- |
| `dc.Vivid*` / `dc.vivid*` (alias) | `dc.vivid*` |
| `dc.Sunset*` / `dc.sunset*`     | `dc.earth*`           |
| `dc.Ocean*` / `dc.ocean*`       | `dc.teal*`            |
| `dc.Pop*` / `dc.pop*`           | `dc.vivid*`           |
| `dc.Cyber*` / `dc.cyber*`       | `dc.jewel*`           |
| `dc.Autumn*` / `dc.autumn*`     | `dc.dusty*`           |
| `dc.Nordic*` / `dc.nordic*`     | `dc.teal_indigo*`     |
| `dc.spectrum*`                  | `dc.vivid*`           |
| `dc.bold*`                      | `dc.vivid*`           |
| `dc.coolwarm*`                  | `dc.cool_warm*`       |
| `dc.corporate*`                 | `dc.trustworthy*`     |
| `dc.warm_cool*`                 | `dc.blue_orange*`     |
| `dc.teal_seq*`                  | `dc.teal*`            |
| `dc.focus*`                     | `dc.teal_accent*`     |
| `dc.focus_warm*`                | `dc.coral_accent*`    |
| `dc.muted*`                     | `dc.pastel*`          |
| `dc.teal_amber_div*`            | `dc.teal_amber*`      |

> These map each old token to its **closest current palette** — the
> colours themselves were re-generated in the overhaul, so a migrated
> token is a starting point, not a byte-identical swap. Browse the live
> set on the [categorical palettes](color_system/categorical-palettes.md)
> page.

## color parsing (`dm.named` → `dm.color`)

`dm.named` is gone. The replacement is `dm.color`, a single string-parser
entry point that mirrors `dm.length`:

```python
# Before
red = dm.named("oc.red5")

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
from dartwork_mpl.colors import Color
```
