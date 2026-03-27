# Migration Guide

This guide helps you migrate your code when upgrading dartwork-mpl versions.

## v0.1.x to v0.2.0+

### Module Renames

Several modules have been renamed for better clarity and consistency. The old names
are still available as deprecated aliases but will be removed in v1.0.

#### `agent_utils` → `helpers`

The `agent_utils` module has been renamed to `helpers` to better reflect its
general-purpose utility nature:

```python
# Old (deprecated - will show warning)
from dartwork_mpl import agent_utils
from dartwork_mpl.agent_utils import auto_select_colors

# New (recommended)
from dartwork_mpl import helpers
from dartwork_mpl.helpers import auto_select_colors
```

#### `xplot` → `templates`

The `xplot` module has been renamed to `templates` to better describe its
purpose as ready-to-use visualization templates:

```python
# Old (deprecated - will show warning)
from dartwork_mpl.xplot import plot_diverging_bar
import dartwork_mpl.xplot as xp

# New (recommended)
from dartwork_mpl.templates import plot_diverging_bar
import dartwork_mpl.templates as tpl

# Also available from top-level
import dartwork_mpl as dm
dm.plot_diverging_bar(...)  # If exported at top level
```

### New Features in v0.2.0+

These features are new additions that don't require migration but are worth adopting:

#### Enhanced Figure Creation

New `dm.subplots()` and `dm.figure()` functions with integrated styling:

```python
# New way - style applied during creation
fig, ax = dm.subplots(style='scientific')

# Replaces this pattern
dm.style.use('scientific')
fig, ax = plt.subplots()
```

#### Content-Aware Layout

New `auto_layout()` function for handling text overflow:

```python
# Automatically prevents text overflow
dm.auto_layout(fig)

# Can be used alongside or instead of simple_layout
dm.simple_layout(fig)  # Still available and recommended for most cases
```

#### Responsive Margins

New margin control functions:

```python
# Set data margins as percentage of range
dm.set_xmargin(ax, margin=0.1)  # 10% margin
dm.set_ymargin(ax, margin=0.05)  # 5% margin
```

### Deprecation Timeline

| Feature | Deprecated in | Will be removed in | Alternative |
|---------|--------------|-------------------|-------------|
| `agent_utils` module | v0.2.0 | v1.0.0 | Use `helpers` module |
| `xplot` module | v0.2.0 | v1.0.0 | Use `templates` module |

### Handling Deprecation Warnings

To silence deprecation warnings while you migrate your code:

```python
import warnings

# Silence specific dartwork-mpl deprecation warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='dartwork_mpl')
    from dartwork_mpl.xplot import plot_diverging_bar  # Old import
```

However, we recommend updating your imports as soon as possible to avoid issues
when upgrading to v1.0.

### Migration Script

For large codebases, you can use this script to find deprecated imports:

```bash
# Find all uses of deprecated modules
grep -r "from dartwork_mpl.agent_utils" . --include="*.py"
grep -r "from dartwork_mpl.xplot" . --include="*.py"
grep -r "import dartwork_mpl.agent_utils" . --include="*.py"
grep -r "import dartwork_mpl.xplot" . --include="*.py"
```

Or use this Python script to automatically update imports:

```python
import os
import re
from pathlib import Path

def update_imports(directory):
    """Update deprecated imports in all Python files."""

    replacements = [
        (r'from dartwork_mpl\.agent_utils', 'from dartwork_mpl.helpers'),
        (r'import dartwork_mpl\.agent_utils', 'import dartwork_mpl.helpers'),
        (r'dartwork_mpl\.agent_utils', 'dartwork_mpl.helpers'),
        (r'from dartwork_mpl\.xplot', 'from dartwork_mpl.templates'),
        (r'import dartwork_mpl\.xplot', 'import dartwork_mpl.templates'),
        (r'dartwork_mpl\.xplot', 'dartwork_mpl.templates'),
    ]

    for py_file in Path(directory).rglob('*.py'):
        with open(py_file, 'r') as f:
            content = f.read()

        original = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)

        if content != original:
            with open(py_file, 'w') as f:
                f.write(content)
            print(f"Updated: {py_file}")

# Run on your project
update_imports('.')
```

## Future Versions

### v0.3.0+ (Current)

The v0.3.x series focuses on stability and bug fixes. No breaking changes are
planned.

### v1.0.0 (Future)

The v1.0.0 release will:
- Remove all deprecated aliases (`agent_utils`, `xplot`)
- Stabilize the API with semantic versioning guarantees
- Potentially reorganize internal module structure (with migration paths)

## Getting Help

If you encounter issues during migration:

1. Check the [CHANGELOG](https://github.com/dartworklabs/dartwork-mpl/blob/main/CHANGELOG.md) for detailed version notes
2. Review the [API documentation](api/index.rst) for current module structure
3. Open an issue on [GitHub](https://github.com/dartworklabs/dartwork-mpl/issues) if you need assistance

## Best Practices

To minimize migration pain in the future:

1. **Use top-level imports when available:**
   ```python
   import dartwork_mpl as dm
   dm.simple_layout(fig)  # Preferred over module imports
   ```

2. **Pin your dependencies:**
   ```toml
   # pyproject.toml
   dependencies = [
       "dartwork-mpl>=0.3,<1.0",  # Avoid unexpected breaking changes
   ]
   ```

3. **Run tests with deprecation warnings enabled:**
   ```bash
   python -W default::DeprecationWarning -m pytest
   ```

4. **Update incrementally:**
   - First update deprecated imports
   - Then adopt new features
   - Finally remove workarounds that new features obsolete