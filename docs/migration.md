# Migration Guide

This guide covers the rename / deprecation events that have shipped
since v0.1, ordered newest first. The 0.3 width tokens, `FS_*`
figsize tuples, `cm2in`, the `dartwork_mpl.constant` module, and the
`figsize=` / `dpi=` arguments to `dm.subplots` / `dm.figure` were
**removed in v0.4.0** — accessing them now raises `AttributeError` /
`ModuleNotFoundError` / `TypeError`. The older `agent_utils` /
`xplot` / `helpers.formatting` / `asset_viz` shims still emit a
`DeprecationWarning` and are scheduled for removal in **v1.0**.

## At a glance

| Old surface                           | New surface                                | Deprecated since | Remove in |
| ------------------------------------- | ------------------------------------------ | ---------------- | --------- |
| `dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`    | `width="9cm"` / `dm.col1` / `dm.col2`      | v0.4.0           | v0.4.0 (already removed) |
| `dm.WIDTHS`                           | iterate explicit widths                    | v0.4.0           | v0.4.0 (already removed) |
| `dm.FS_SINGLE` / `FS_DOUBLE` / etc.   | `dm.subplots(width=..., aspect=...)`       | v0.4.0           | v0.4.0 (already removed) |
| `dm.cm2in(...)`                       | `dm.cm(...)` (returns `Inches`)            | v0.4.0           | v0.4.0 (already removed) |
| `figsize=` argument                   | `width=` + `aspect=`                       | v0.4.0 (lint)    | v0.4.0 (already removed) |
| `dpi=` argument                       | active style preset                        | v0.4.0 (lint)    | v0.4.0 (already removed) |
| `dartwork_mpl.constant` module        | `dartwork_mpl.units` + width / aspect API  | v0.4.0           | v0.4.0 (already removed) |
| `plt.tight_layout()`                  | `dm.auto_layout(fig)`                      | v0.4.0 (lint)    | —         |
| `dartwork_mpl.agent_utils`            | `dartwork_mpl.helpers`                     | v0.2.0           | v1.0.0    |
| `dartwork_mpl.xplot`                  | `dartwork_mpl.templates`                   | v0.2.0           | v1.0.0    |
| `dartwork_mpl.helpers.formatting`     | `dartwork_mpl.helpers.labels`              | v0.3.x           | v1.0.0    |
| `dartwork_mpl.asset_viz`              | `dartwork_mpl.diagnostics`                 | v0.3.x           | v1.0.0    |

## v0.4.x → v0.5.0 — API audit round 3 (#141)

5 wrapper functions removed using the *knowledge-encapsulation* criterion:
AI agents can reproduce these in one shot without spec.

| Removed | Replacement |
|---|---|
| `dm.format_axis_percent(ax, axis, decimals)` | `ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=decimals))` |
| `dm.format_axis_labels(ax, x_label, x_unit, ...)` | `ax.set_xlabel(f"{x_label} ({x_unit})")` (compose inline) |
| `dm.add_frame(ax, color, linewidth)` | `for s in ax.spines.values(): s.set_visible(True); s.set_color(color); s.set_linewidth(linewidth)` |
| `dm.add_value_labels(ax, x, y, ...)` | inline text loop: `for xi, yi in zip(x, y): ax.text(xi, yi+offset, f"{yi:.1f}", ...)` |
| `dm.set_xmargin(ax, margin, left, right)` | `ax.margins(x=margin)` plus optional `ax.set_xlim((left, right))` |
| `dm.set_ymargin(ax, margin, bottom, top)` | same shape, y axis: `ax.margins(y=margin)` |

## v0.4.x → v0.5.0 — API audit round 2 (#141)

8 thin-wrapper utility functions were removed. Each can be replaced by
one or two plain matplotlib calls.

| Removed | Replacement |
|---|---|
| `dm.hide_spines(ax, which)` | `for s in (which or ["top","right"]): ax.spines[s].set_visible(False)` |
| `dm.hide_all_spines(ax)` | `for s in ax.spines.values(): s.set_visible(False)` |
| `dm.show_only_spines(ax, which)` | `for s in ["top","right","bottom","left"]: ax.spines[s].set_visible(s in which)` |
| `dm.remove_grid(ax)` | `ax.grid(False)` |
| `dm.format_axis_thousands(ax)` | `ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{x:,.0f}"))` |
| `dm.save_figure(fig, path, ...)` | `Path(path).parent.mkdir(parents=True, exist_ok=True); dm.save_formats(fig, str(path), ...)` |
| `dm.create_figure_with_style(style)` | `dm.style.use(style); fig = plt.figure(figsize=(cm(17), cm(17)*0.6), dpi=200)` |
| `dm.templates.diverging_bar.get_source_code()` | `pathlib.Path(__file__).read_text()` |

For `format_axis_thousands`, add the following at your callsite:

```python
from matplotlib import ticker
formatter = ticker.FuncFormatter(lambda x, p: f"{x:,.0f}")   # sep=","
# Non-comma separator:
# formatter = ticker.FuncFormatter(lambda x, p: f"{x:,.0f}".replace(",", sep))
ax.yaxis.set_major_formatter(formatter)   # or ax.xaxis for axis="x"
```

## v0.3.x → v0.4.0

0.4 reshapes the figure-creation surface around two ideas:

1. **Width is free-form.** Pass any unit-suffixed string
   (`"13cm"`, `"6.7in"`, `"170mm"`), a helper call (`dm.cm(13)`,
   `dm.inch(6.7)`, `dm.mm(170)`), or the academic-column sugar
   `dm.col1` / `dm.col2`. The fixed 4-tier `SW`/`MW`/`TW`/`DW`
   constants are deprecated.
2. **Aspect is a height/width ratio**, separated from width. Six
   named tokens cover the common cases; pass a positive float for
   anything else.
3. **The 0.3 surface is gone, not deprecated.** The 0.4.0 cut
   pulled the planned 0.5.0 removals forward, so the table above
   marks every 0.3 width / FS / `cm2in` / `figsize=` / `dpi=` entry
   as already removed. There is no `DeprecationWarning` grace period
   — old call sites raise immediately. Migrate them all in one pass.

A new `dm.lint` module checks code against a 15-rule anti-pattern
catalog so editor tooling, MCP clients, and CI all share the same
ground truth.

### Width tokens → `width="..."`

```python
# DEPRECATED — fires `width-token` lint warning
fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.75))

# 0.4 — width string, aspect token
fig, ax = dm.subplots(width="9cm", aspect="standard")

# 0.4 — academic column sugar
fig, ax = dm.subplots(width=dm.col1, aspect="standard")
```

Same idea for the rest of the 4-tier ladder:

| 0.3                       | 0.4 (preferred)                 |
| ------------------------- | ------------------------------- |
| `dm.SW` (≈ 9 cm)          | `width="9cm"` or `dm.col1`      |
| `dm.MW` (≈ 12 cm)         | `width="12cm"`                  |
| `dm.TW` (≈ 14.5 cm)       | `width="14.5cm"` (or `"15cm"`)  |
| `dm.DW` (≈ 17 cm)         | `width="17cm"` or `dm.col2`     |
| `dm.WIDTHS` (tuple)       | iterate explicit widths inline  |

### `figsize=` → `width=` + `aspect=`

`figsize=` is the most common 0.3 idiom and is the single biggest
source of mismatched figures across a multi-figure report. The
`figsize-direct` lint rule flags any remaining usage:

```python
# DEPRECATED — fires `figsize-direct` lint critical
fig, ax = plt.subplots(figsize=(dm.cm2in(13), dm.cm2in(10)))

# 0.4
fig, ax = dm.subplots(width="13cm", aspect=10 / 13)
```

`FS_*` tuples follow the same path:

```python
# DEPRECATED — fires `width-token` lint warning
fig, ax = plt.subplots(figsize=dm.FS_SINGLE)

# 0.4
fig, ax = dm.subplots(width="9cm", aspect="standard")
```

### Aspect tokens

Aspect is **height ÷ width**. Six named tokens are recognised:

| Token        | Ratio (h/w) | Typical use                     |
| ------------ | ----------- | ------------------------------- |
| `"square"`   | `1.0`       | scatter, correlation matrices   |
| `"portrait"` | `5 / 4`     | tall multi-row dashboards       |
| `"standard"` | `3 / 4`     | default: time series, bar/line  |
| `"golden"`   | `1 / 1.618` | classic publication figures     |
| `"wide"`     | `2 / 3`     | landscape charts, talks         |
| `"cinema"`   | `1 / 2`     | very wide trend strips          |

Or pass a positive float directly:

```python
fig, ax = dm.subplots(width="13cm", aspect=0.6)
```

`validate_figure` warns on extreme aspects (< 0.3 or > 4.0).

### `plt.subplots` → `dm.subplots`

```python
# DEPRECATED — fires `plt-subplots-figsize` lint critical when
# combined with a figsize= argument
fig, axes = plt.subplots(2, 2, figsize=(dm.DW, dm.DW * 0.5))

# 0.4
fig, axes = dm.subplots(2, 2, width="17cm", aspect=0.5)
```

`dm.subplots` forwards everything else (`sharex`, `sharey`,
`width_ratios`, `height_ratios`, `gridspec_kw`, `subplot_kw`,
`squeeze`) straight through to matplotlib. The `style=` argument
also still works, e.g. `dm.subplots(width="13cm", style="report-kr")`.

### `tight_layout` → `auto_layout`

```python
# DEPRECATED — fires `tight-layout` lint critical
plt.tight_layout()
fig.tight_layout()

# 0.4
dm.auto_layout(fig)
```

`auto_layout` iteratively shrinks the axes box until no text
overflows the canvas, so it survives long labels, multi-line
titles, and twinx() right-spine cases that `tight_layout` mangles.
`dm.simple_layout(fig)` still exists but is reserved for advanced
GridSpec arrangements where `auto_layout` cannot solve the bbox.

### `dm.cm2in` → `dm.cm`

`cm2in(x)` converted cm to a plain `float`. `dm.cm(x)` returns an
`Inches` value (a `float` subclass) that arithmetic preserves, so
`dm.cm(9) * 2` stays in inches and round-trips through
`parse_width` cleanly. `dm.inch(x)` and `dm.mm(x)` are the
analogous helpers for the other two units.

```python
# DEPRECATED — emits DeprecationWarning
inches = dm.cm2in(9)

# 0.4
inches = dm.cm(9)               # Inches(3.5433...)
inches = dm.inch(3.5)           # Inches(3.5)
inches = dm.mm(170)             # Inches(6.6929...)
```

### Module renames carried forward

The earlier rename pairs (`agent_utils → helpers`,
`xplot → templates`, `helpers.formatting → helpers.labels`,
`asset_viz → diagnostics`) are still deprecated and continue to
work in 0.4 with a `DeprecationWarning`. See the v0.1.x → v0.2.0
and v0.3.x sections below for the canonical replacements.

### "Zero-Resize Policy" wording is retired

Pre-0.4 docs framed figure sizing as a "Zero-Resize Policy"
enforced by the style preset. 0.4 replaces that with **free width
input plus a lint consistency guard** (the `oversize-width` and
`width-token` rules). Any project rule that still cites the
"Zero-Resize Policy" should be rewritten in terms of `dm.subplots`
+ `dm.lint`.

### New: `dm.lint`

`dm.lint.lint(code)` runs the 15-rule anti-pattern catalog over a
Python source string. It is the same engine the MCP
`lint_dartwork_mpl_code` tool and `dartwork-mpl lint` CLI use, so
your editor, your CI, and your AI assistant all see the same
violations.

```python
import dartwork_mpl as dm

source = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6.7, 4.0))
plt.tight_layout()
"""

issues = dm.lint.lint(source)
for issue in issues:
    print(issue.rule_id, issue.severity, issue.message)
print(dm.lint.format_report(issues))
```

The full rule list (`figsize-direct`, `tight-layout`,
`width-token`, `oversize-width`, `fontsize-literal`,
`linewidth-literal`, `raw-hex-color`, `jet-cmap`, …) lives in
`asset/prompt/02-anti-patterns.yaml` and is also reachable as the
MCP resource `dartwork-mpl://guide/anti-patterns`.

## v0.1.x → v0.2.0

### `agent_utils` → `helpers`

Renamed to make clear these are general-purpose utilities, not
AI-agent-specific.

```python
# Old (deprecated — emits DeprecationWarning)
from dartwork_mpl import agent_utils
from dartwork_mpl.agent_utils.colors import auto_select_colors

# New (recommended)
from dartwork_mpl import helpers
from dartwork_mpl.helpers.colors import auto_select_colors
```

### `xplot` → `templates`

Renamed to better describe its purpose: a small, curated set of
ready-to-use plot templates.

```python
# Old (deprecated)
from dartwork_mpl.xplot import plot_diverging_bar
import dartwork_mpl.xplot as xp

# New
from dartwork_mpl.templates import plot_diverging_bar
import dartwork_mpl.templates as tpl

# Or — preferred — top-level
import dartwork_mpl as dm
dm.plot_diverging_bar(...)
```

## v0.3.x

### `helpers.formatting` → `helpers.labels`

The `formatting` submodule of `helpers` was renamed to `labels` to
remove a long-standing name clash with the top-level
`dartwork_mpl.formatting` module (which houses the `format_axis_*`
tick formatters). The contents (`format_axis_labels`, `optimize_legend`,
`add_value_labels`) are unchanged.

```python
# Old (deprecated)
from dartwork_mpl.helpers.formatting import format_axis_labels

# New
from dartwork_mpl.helpers.labels import format_axis_labels
# Or via the namespace:
import dartwork_mpl as dm
dm.helpers.labels.format_axis_labels(...)
```

### `asset_viz` → `diagnostics`

The four asset-inspection helpers (`classify_colormap`,
`plot_colormaps`, `plot_colors`, `plot_fonts`) moved to a single
top-level `dartwork_mpl.diagnostics` module. The old `asset_viz`
subpackage is now a thin shim that re-exports the same four names.
Behaviour is unchanged.

```python
# Old (deprecated)
from dartwork_mpl.asset_viz import plot_colors, plot_fonts

# New (canonical)
from dartwork_mpl.diagnostics import plot_colors, plot_fonts

# Best — top-level (was already supported, also unchanged)
import dartwork_mpl as dm
dm.plot_colors()
dm.plot_fonts()
```

## Worth adopting

These additions don't *require* migration but pay off if you bump
into them:

### `dm.subplots()` / `dm.figure()`

Apply a style during figure creation, in one call:

```python
# Before
dm.style.use("scientific")
fig, ax = plt.subplots()

# After
fig, ax = dm.subplots(width="13cm", style="scientific")
```

Stack styles or override defaults inline:

```python
fig, axes = dm.subplots(
    2, 2, width="17cm", aspect=0.5,
    style=["font-libertine", "theme-dark"],
)
```

### `dm.auto_layout(fig)`

When `simple_layout` doesn't quite handle long labels or multi-line
titles, call `auto_layout` instead — it iteratively shrinks the axes
until no text overflows the canvas:

```python
dm.auto_layout(fig)              # automatic margin negotiation
dm.simple_layout(fig)            # fast, fine for advanced GridSpec
```

### `dm.validate_with_fixes(fig)`

A lightweight quality check that returns *and* fixes common figure
issues (margin asymmetry, pie label cutoff, etc.):

```python
result = dm.validate_with_fixes(fig)
print(result.report())
```

## Silencing legacy warnings

If you can't migrate everything immediately:

```python
import warnings
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="dartwork_mpl",
)
```

For test runs, instead surface them so you don't lose track:

```bash
python -W default::DeprecationWarning -m pytest
```

## One-shot migration script

For larger codebases, run this once to rewrite every deprecated
import in-place. It covers the v0.2.0 / v0.3.x renames; the 0.3→0.4
width token migration is intentionally left for a manual review
because the right replacement (`dm.col1` vs `width="9cm"` vs an
explicit `dm.subplots` rewrite) depends on the surrounding code:

```python
import re
from pathlib import Path

REPLACEMENTS = [
    # Module-level renames
    (r"\bdartwork_mpl\.agent_utils\b", "dartwork_mpl.helpers"),
    (r"\bdartwork_mpl\.xplot\b", "dartwork_mpl.templates"),
    (r"\bdartwork_mpl\.asset_viz\b", "dartwork_mpl.diagnostics"),
    # Submodule rename
    (
        r"\bdartwork_mpl\.helpers\.formatting\b",
        "dartwork_mpl.helpers.labels",
    ),
]


def migrate(directory: str) -> None:
    """Rewrite deprecated imports under *directory* in-place."""
    for py in Path(directory).rglob("*.py"):
        original = py.read_text()
        updated = original
        for pattern, replacement in REPLACEMENTS:
            updated = re.sub(pattern, replacement, updated)
        if updated != original:
            py.write_text(updated)
            print(f"updated: {py}")


if __name__ == "__main__":
    import sys

    migrate(sys.argv[1] if len(sys.argv) > 1 else ".")
```

Save as `migrate_dartwork.py` and run `python migrate_dartwork.py` in
your project root. Diff the result with version control, run your
test suite, and commit.

For the 0.4 width / aspect rewrite, run `dm.lint.lint(source)` on
each file and walk the issues — every flagged line points at the
specific replacement.

## Sanity-check before upgrading to v0.5 / v1.0

Once 0.5 lands, the 0.3 width tokens (`SW`, `MW`, `TW`, `DW`,
`WIDTHS`, `FS_*`, `cm2in`) will be removed. v1.0 drops the older
`agent_utils` / `xplot` / `helpers.formatting` / `asset_viz`
shims as well. You can audit your project for them with:

```bash
grep -rE "(dartwork_mpl\.agent_utils|dartwork_mpl\.xplot|dartwork_mpl\.helpers\.formatting|dartwork_mpl\.asset_viz)" \
     --include='*.py' .

grep -rE "\bdm\.(SW|MW|TW|DW|WIDTHS|FS_[A-Z]+|cm2in)\b" \
     --include='*.py' .
```

Anything that comes back is something the next breaking release
will remove.

## Best practices going forward

1. **Use top-level imports when available.** `dm.simple_layout(fig)`
   is shorter and survives any internal reorganization that keeps the
   public API stable:

   ```python
   import dartwork_mpl as dm
   dm.simple_layout(fig)
   ```

2. **Pin a range, not an exact version.** Patch and minor releases
   shouldn't break you; majors will:

   ```toml
   # pyproject.toml
   dependencies = ["dartwork-mpl>=0.4,<1.0"]
   ```

3. **Surface deprecation warnings in CI** — add
   `-W default::DeprecationWarning` to the pytest invocation in your
   CI workflow so you find legacy usage before the next breaking
   release forces you to.

4. **Run `dm.lint` in pre-commit.** A 15-rule scan catches the
   common 0.3-isms (figsize, tight_layout, hex colors, jet cmap)
   before they hit review.

## Getting help

- Detailed version notes:
  [CHANGELOG](https://github.com/dartworklabs/dartwork-mpl/blob/main/CHANGELOG.md)
- Current API reference: [API documentation](api/index.rst)
- Open an issue: [GitHub Issues](https://github.com/dartworklabs/dartwork-mpl/issues)
