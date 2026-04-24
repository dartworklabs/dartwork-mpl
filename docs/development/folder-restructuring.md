# dartwork-mpl Folder Structure Improvements

> **Historical reference.** This document records the v0.2.0 folder
> restructuring (`agent_utils` → `helpers`, `xplot` → `templates`). The
> content below is kept as a reference for the migration contract
> (deprecation aliases, removal timeline) and is not a live task list.
> Remaining follow-up work is tracked as GitHub issues rather than as
> bullets in this file — see the "Outstanding follow-up" section at
> the bottom.

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
- `asset_viz` functions now accessible through `explore` module
- Future: Fully merge `asset_viz` into `explore.py` for better organization
- Both modules serve the same purpose: exploring and visualizing library assets

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
│   ├── explore.py          # Enhanced with asset_viz functions
│   ├── asset_viz/          # To be fully merged into explore.py
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

Items from the original "Next Steps" list have been split out. Only
the first one is still pending; the others have all shipped.

- **Merge `asset_viz` module into `explore.py`** — tracked in
  [issue #57](https://github.com/dartworklabs/dartwork-mpl/issues/57).
- Documentation and test migrations for the `agent_utils → helpers` and
  `xplot → templates` renames are complete (see CHANGELOG entries for
  the PRs in the #43–#51 range).
- Removal of the deprecated aliases themselves (`dm.agent_utils`,
  `dm.xplot`, `dm.helpers.formatting`) is scheduled for the next major
  release and is called out in the CHANGELOG "Deprecated" sections.

## Summary

The dartwork-mpl folder structure has been successfully improved with:
- Clear, descriptive module names
- No unnecessary nested directories
- Maintained backward compatibility
- Better organization for a general-purpose plotting utility

The library is now more intuitive and maintainable while preserving all functionality.