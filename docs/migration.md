---
orphan: true
---

# Migration Guide

This guide collects every rename / deprecation that has shipped on PyPI
(v0.4.0 onwards), ordered newest first. Each removed symbol now raises
`AttributeError` / `ModuleNotFoundError` / `TypeError` with a message
naming its replacement. The `dartwork_mpl.asset_viz` and
`dartwork_mpl.helpers.formatting` submodule aliases still import with a
`DeprecationWarning` and are scheduled for removal in **v1.0**.

> **New to dartwork-mpl?** You don't need this page. Head to the
> [Quick Start](usage_guide/quickstart.md) — it uses the current API
> end-to-end.

## At a glance

| Old surface                           | New surface                                          |
| ------------------------------------- | ---------------------------------------------------- |
| `dm.install_llm_txt()` / `uninstall_llm_txt()` | `dm.get_agent_doc(name)` / `dm.agent_doc_path(name)` (or MCP `dartwork-mpl://guide/*`) |
| `dm.subplots(width=..., aspect=...)`  | `plt.subplots(figsize=dm.figsize(...))`              |
| `dm.figure(width=..., aspect=...)`    | `plt.figure(figsize=dm.figsize(...))`                |
| `dm.subplots(..., style=...)`         | call `dm.style.use(...)` first, then `plt.subplots`  |
| `plt.tight_layout()`                  | `dm.simple_layout(fig)`                              |
| `dm.auto_layout(fig)`                 | `dm.simple_layout(fig)` (auto_layout is a deprecation alias) |
| `dm.simple_layout(fig, margins=(...), bbox=..., bound_margin=..., gtol=..., importance_weights=...)` | `dm.simple_layout(fig, margin="2%", ml=..., mr=..., mt=..., mb=...)` (new keyword API) |
| `dartwork_mpl.helpers.formatting`     | `dartwork_mpl.helpers.labels`                        |
| `dartwork_mpl.asset_viz`              | `dartwork_mpl.diagnostics`                           |
| `dm.style_spines(ax, color=c, linewidth=w, which=ws)` | `for s in ws: ax.spines[s].set_color(c); ax.spines[s].set_linewidth(w)` |
| `dm.add_grid(ax)`                     | `ax.grid(True, color="oc.gray3", alpha=0.3, linewidth=0.5); ax.set_axisbelow(True)` |
| `dm.minimal_axes(ax)`                 | see [Minimal axes recipe](usage_guide/recipes.md#minimal-axes-tufte-style) |
| `dm.auto_select_colors(n_series=N, color_type=K, highlight_index=I)` | `dm.make_palette(N, kind=K, highlight=I)` |
| `dm.named("oc.red5")`                 | `dm.color("oc.red5")` (also accepts hex / `rgb(...)` / `oklch(...)` / `oklab(...)`) |
| `from dartwork_mpl.color import ...`  | `from dartwork_mpl.colors import ...` (submodule renamed) |

## `dm.named` removal & `color` → `colors` submodule rename

`dm.named` is gone. The replacement is `dm.color`, a single
string-parser entry point that mirrors `dm.length`:

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

## `dm.subplots` / `dm.figure` removal

The `dm.subplots` / `dm.figure` wrappers around the matplotlib figure
constructors are gone. Use `plt.subplots` / `plt.figure` directly and
pass `figsize=dm.figsize(width, aspect)`:

```python
# Before
fig, ax = dm.subplots(width="13cm", aspect="standard")

# Now
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
```

If you also passed `style=`, call `dm.style.use(...)` first:

```python
# Before
fig, ax = dm.subplots(width="13cm", aspect="standard", style="scientific")

# Now
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
```

`dm.figsize(width, aspect)` accepts a unit-string width (`"13cm"`,
`"5in"`, `"170mm"`, `"24pt"`) or a `Length` value (`dm.cm(13)`,
`dm.col1`, `dm.col2`), and four equivalent aspect forms — token
(`"wide"`), numeric ratio (`0.6`), unit-string height (`"12cm"`), or
`Length` height (`dm.cm(12)`). Bare `int` / `float` widths are
rejected.

## v0.4.x → v0.5.0

**The `install_llm_txt` installer was removed (#170).** It copied the
bundled prompt corpus into IDE-specific folders; the corpus is now read
at runtime instead, so there is nothing to install. `dm.install_llm_txt`
/ `dm.uninstall_llm_txt` / `dm.INSTALL_TARGETS` raise `AttributeError`.

| Removed | Replacement |
|---|---|
| `dm.install_llm_txt(...)` | `dm.get_agent_doc(name)` / `dm.agent_doc_path(name)` — `name` ∈ `AGENTS`, `CLAUDE`, `llms`, `llms-full` — or the MCP `dartwork-mpl://guide/*` resources |
| `dm.uninstall_llm_txt(...)` | nothing — the corpus is read at runtime, so there is no install to undo |
| `dm.INSTALL_TARGETS` | nothing — install targets no longer exist |

**`ipython` is no longer a core dependency (#248).** Only `dm.show()`
(inline SVG display in Jupyter) needs it, so it moved to the `notebook`
optional extra. `dm.show()` raises a clear `ImportError` naming the
extra when IPython is absent; every other entry point is unaffected.

| Old install | New install |
|---|---|
| `pip install dartwork-mpl` (pulled in ~30 MB of IPython deps) | `pip install "dartwork-mpl[notebook]"` if you use `dm.show()` |

## v0.4.0 → v0.4.1 — API audit round 3 (#141)

Five thin wrappers around 1–3 line matplotlib calls were retired. The
curated default kwargs they encoded now live as snippets in
[`usage_guide/recipes.md`](usage_guide/recipes.md):

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

## v0.4.0 → v0.4.1 — API audit round 2 (#141)

Eight more wrappers retired; each is a single matplotlib call now:

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
