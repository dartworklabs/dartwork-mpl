# Migration Guide

This guide covers the rename / deprecation events that have shipped
since v0.1, with one-shot migration scripts at the end. Every legacy
import path still works, but they all emit a `DeprecationWarning` and
will be removed in v1.0.

## At a glance

| Old path                              | New path                              | Deprecated since | Remove in |
| ------------------------------------- | ------------------------------------- | ---------------- | --------- |
| `dartwork_mpl.agent_utils`            | `dartwork_mpl.helpers`                | v0.2.0           | v1.0.0    |
| `dartwork_mpl.xplot`                  | `dartwork_mpl.templates`              | v0.2.0           | v1.0.0    |
| `dartwork_mpl.helpers.formatting`     | `dartwork_mpl.helpers.labels`         | v0.3.x           | v1.0.0    |
| `dartwork_mpl.asset_viz`              | `dartwork_mpl.diagnostics`            | v0.3.x           | v1.0.0    |

The four diagnostic helpers (`classify_colormap`, `plot_colormaps`,
`plot_colors`, `plot_fonts`) are also reachable as `dm.<name>` at the
top level, which is the recommended way to call them and is not
affected by any of the renames below.

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
fig, ax = dm.subplots(style="scientific")
```

Stack styles or override defaults inline:

```python
fig, axes = dm.subplots(2, 2, style=["font-libertine", "theme-dark"])
fig, ax = dm.subplots(style="report", figsize=(10, 6), dpi=150)
```

### `dm.auto_layout(fig)`

When `simple_layout` doesn't quite handle long labels or multi-line
titles, call `auto_layout` instead — it iteratively shrinks the axes
until no text overflows the canvas:

```python
dm.auto_layout(fig)              # automatic margin negotiation
dm.simple_layout(fig)            # fast, fine for most cases
```

### `dm.set_xmargin(ax)` / `dm.set_ymargin(ax)`

Set data-side margins as a fraction of the visible range:

```python
dm.set_xmargin(ax, margin=0.1)   # 10 % padding on each side
dm.set_ymargin(ax, margin=0.05)
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
import in-place. It covers all four renames:

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

## Sanity-check before upgrading to v1.0

Once v1.0 lands, the legacy paths above will be removed. Until then,
you can audit your project for them with:

```bash
grep -rE "(dartwork_mpl\.agent_utils|dartwork_mpl\.xplot|dartwork_mpl\.helpers\.formatting|dartwork_mpl\.asset_viz)" \
     --include='*.py' .
```

Anything that comes back is something v1.0 will break.

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
   dependencies = ["dartwork-mpl>=0.3,<1.0"]
   ```

3. **Surface deprecation warnings in CI** — add
   `-W default::DeprecationWarning` to the pytest invocation in your
   CI workflow so you find legacy usage before v1.0 forces you to.

## Getting help

- Detailed version notes:
  [CHANGELOG](https://github.com/dartworklabs/dartwork-mpl/blob/main/CHANGELOG.md)
- Current API reference: [API documentation](api/index.rst)
- Open an issue: [GitHub Issues](https://github.com/dartworklabs/dartwork-mpl/issues)
