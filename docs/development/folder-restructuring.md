---
orphan: true
---

# dartwork-mpl Folder Structure Improvements

> **Historical reference.** This document records the v0.2.0–v0.3.x
> folder restructuring (`agent_utils` → `helpers`, `xplot` → `templates`,
> `helpers.formatting` → `helpers.labels`, `asset_viz` → `diagnostics`).
> It is kept as a reference for the migration contract (deprecation
> aliases, removal timeline) and is intentionally outside the main
> toctree. For an end-user-facing migration walk-through, see
> [Migration Guide](../migration.md). The "Outstanding follow-up"
> section at the bottom tracks remaining items.

## Completed Restructuring

### 1. ✅ Removed Unnecessary Nested Directory
- **Deleted**: `dartwork-mpl/dartwork-mpl/` - Empty nested directory that was created by accident
- **Result**: Cleaner root structure without confusing duplicates

### 2. ✅ Renamed Modules for Clarity

#### `agent_utils` → `helpers`
- **Old**: `src/dartwork_mpl/agent_utils/` - Name implied AI-agent-specific utilities
- **New**: `src/dartwork_mpl/helpers/` - Clear that these are general helper functions
- **Contents**:
  - `colors.py` - Color selection utilities
  - `data.py` - Data validation
  - `formatting.py` - Label and axis formatting
  - `io.py` - Figure I/O operations
  - `quality.py` - Quality checks and suggestions

#### `xplot` → `templates`
- **Old**: `src/dartwork_mpl/xplot/` - Unclear naming ("x" for extended?)
- **New**: `src/dartwork_mpl/templates/` - Clear that these are chart templates
- **Contents**:
  - `diverging_bar.py` - Diverging bar chart template

### 3. ✅ Added Backward Compatibility
- Deprecated aliases maintain compatibility:
  ```python
  import dartwork_mpl as dm
  dm.agent_utils  # Shows deprecation warning, still works
  dm.xplot        # Shows deprecation warning, still works
  ```
- Users get clear deprecation warnings pointing to new module names

### 4. ✅ Consolidated Asset Visualization
- `asset_viz` functions moved to a dedicated `diagnostics.py` module
  in the v0.3.x series (see issue #57). The legacy `asset_viz`
  subpackage is a thin deprecation shim that re-exports the same
  four helpers.
- `dm.explore` re-exports `classify_colormap` / `plot_colormaps` /
  `plot_colors` / `plot_fonts` so discovery-oriented workflows can
  reach every asset-introspection helper through a single module.

## Final Structure

```
dartwork-mpl/
├── src/dartwork_mpl/
│   ├── helpers/            # ✅ Renamed from agent_utils
│   │   ├── colors.py
│   │   ├── data.py
│   │   ├── formatting.py
│   │   ├── io.py
│   │   └── quality.py
│   ├── templates/          # ✅ Renamed from xplot
│   │   └── diverging_bar.py
│   ├── explore.py          # Re-exports diagnostics helpers
│   ├── diagnostics.py      # ✅ New home of the four asset helpers
│   ├── asset_viz/          # Deprecation shim — re-exports from diagnostics
│   ├── color/
│   ├── ui/
│   ├── mcp/
│   └── asset/
├── examples/               # User-facing examples (individual plots)
│   ├── single_plot_example.py
│   ├── single_plot_korean.py
│   └── README.md
├── docs/
│   └── examples_source/    # Documentation examples (Sphinx)
└── tests/

❌ Removed:
- dartwork-mpl/dartwork-mpl/ (nested duplicate)
```

## Benefits

1. **Clearer naming**: Module names now clearly indicate their purpose
2. **Better organization**: No confusing nested directories
3. **Backward compatibility**: Existing code continues to work with deprecation warnings
4. **Future-proof**: Structure supports gradual migration to new names

## Migration Guide for Users

### Old Code:
```python
import dartwork_mpl as dm

# Old way (still works but shows warning)
colors = dm.agent_utils.colors.auto_select_colors(5)
dm.xplot.plot_diverging_bar(data)
```

### New Code:
```python
import dartwork_mpl as dm

# New way (recommended)
colors = dm.helpers.colors.auto_select_colors(5)
dm.templates.plot_diverging_bar(data)
```

## Outstanding follow-up

Every item from the original "Next Steps" list has now shipped; the
only remaining work is the eventual removal of the deprecation shims,
which is scheduled for the next major release.

- ✅ **Merge `asset_viz` module into a dedicated module** — shipped in
  v0.3.x as `dartwork_mpl.diagnostics` (issue #57). The `asset_viz`
  subpackage is retained as a thin deprecation shim that re-exports
  the four helpers and emits a `DeprecationWarning` on import.
- Documentation and test migrations for the `agent_utils → helpers` and
  `xplot → templates` renames are complete (see CHANGELOG entries for
  the PRs in the #43–#51 range).
- Removal of the deprecated aliases themselves (`dm.agent_utils`,
  `dm.xplot`, `dm.helpers.formatting`, `dm.asset_viz`) is scheduled for
  the next major release and is called out in the CHANGELOG
  "Deprecated" sections.

## Summary

The dartwork-mpl folder structure has been successfully improved with:
- Clear, descriptive module names
- No unnecessary nested directories
- Maintained backward compatibility
- Better organization for a general-purpose plotting utility

The library is now more intuitive and maintainable while preserving all functionality.