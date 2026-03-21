# dartwork-mpl Folder Structure Improvements

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

## Next Steps (Optional)

1. **Full integration**: Merge `asset_viz` module code directly into `explore.py`
2. **Documentation update**: Update all documentation to use new module names
3. **Test updates**: Update test files to use new imports
4. **Remove deprecated aliases**: In future major version (e.g., v1.0.0)

## Summary

The dartwork-mpl folder structure has been successfully improved with:
- Clear, descriptive module names
- No unnecessary nested directories
- Maintained backward compatibility
- Better organization for a general-purpose plotting utility

The library is now more intuitive and maintainable while preserving all functionality.