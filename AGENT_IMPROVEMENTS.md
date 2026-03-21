# dartwork-mpl Agent Improvements

## Overview

This document describes the improvements made to dartwork-mpl to better support AI agents and automated code generation for creating high-quality visualizations.

## New Features Added

### 1. Agent Coding Rules (`coding-rules.md`)

A comprehensive guide specifically for AI agents that includes:
- Essential import patterns
- Style selection guidelines
- Figure creation patterns
- Color usage rules
- Layout optimization rules
- Typography and labeling rules
- Common mistakes to avoid
- Quick reference templates

**Location**: `src/dartwork_mpl/asset/prompt/coding-rules.md`

### 2. Chart Templates Module (`templates/`)

Pre-built, production-ready chart templates following best practices:

#### Financial Templates (`templates/financial.py`)
- `create_dual_axis_chart()` - Bar + line charts for revenue/margin
- `create_waterfall_chart()` - Bridge charts for P&L analysis
- `create_multiple_comparison()` - Multi-panel peer comparisons
- `create_band_chart()` - Price charts with valuation bands

#### Scientific Templates (`templates/scientific.py`)
- `create_multi_panel_figure()` - Publication-quality multi-panel layouts
- `create_scatter_with_fit()` - Scatter plots with regression and residuals
- `create_heatmap()` - Scientific heatmaps with proper annotations

#### Business Templates (`templates/business.py`)
- `create_dashboard_layout()` - Executive dashboard layouts
- `create_kpi_cards()` - KPI card visualizations
- `create_trend_comparison()` - Multi-series trend analysis

### 3. Agent Utilities (`agent_utils.py`)

Helper functions for common tasks:
- `validate_data()` - Input data validation and cleaning
- `auto_select_colors()` - Intelligent color scheme selection
- `format_axis_labels()` - Consistent label formatting
- `optimize_legend()` - Smart legend placement
- `add_value_labels()` - Data point labeling
- `save_figure()` - Consistent output handling
- `suggest_chart_type()` - Chart type recommendation
- `check_figure_quality()` - Quality assurance checks

### 4. Enhanced Validation (`validate_enhanced.py`)

Extended validation with auto-fix capabilities:
- `get_fix_suggestions()` - Generate fix code for warnings
- `validate_with_fixes()` - Validate and auto-apply fixes
- `check_agent_requirements()` - Check coding standards compliance
- `generate_validation_report()` - Comprehensive quality reports

### 5. Updated General Guide

Added "Agent Best Practices" section to the general guide with:
- Quick start templates
- Helper function usage examples
- Template usage examples
- Common pitfalls to avoid

## Usage Examples

### Basic Usage with Templates

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import dartwork_mpl as dm
from dartwork_mpl.templates.financial import create_dual_axis_chart

dm.style.use("report-kr")

# Create chart using template
fig, (ax1, ax2) = create_dual_axis_chart(
    quarters=["Q1", "Q2", "Q3", "Q4"],
    bar_values=[100, 120, 115, 130],
    line_values=[15.2, 16.5, 14.8, 17.2],
    bar_label="Revenue",
    line_label="Margin"
)

dm.save_formats(fig, "output/chart", formats=("png",))
plt.close(fig)
```

### Using Agent Utilities

```python
from dartwork_mpl.agent_utils import (
    validate_data,
    auto_select_colors,
    check_figure_quality
)

# Validate and clean data
x, y = validate_data(x_data, y_data, allow_nan=False)

# Auto-select appropriate colors
colors = auto_select_colors(n_series=5, color_type="categorical")

# Check quality before saving
issues = check_figure_quality(fig)
if not issues:
    print("✅ Quality check passed")
```

### Validation with Auto-Fix

```python
from dartwork_mpl.validate_enhanced import validate_with_fixes

# Validate and auto-fix common issues
warnings, fixes = validate_with_fixes(
    fig,
    auto_apply=True,  # Automatically apply simple fixes
    verbose=True      # Print diagnostic information
)

if not warnings:
    print("✅ No visual issues detected")
```

## Benefits for Agents

1. **Consistency**: Templates ensure consistent styling across all charts
2. **Error Prevention**: Validation catches common mistakes before they happen
3. **Auto-Fixes**: Many issues can be automatically resolved
4. **Best Practices**: Built-in patterns follow publication standards
5. **Type Safety**: Helper functions include proper type hints
6. **Quality Assurance**: Comprehensive validation ensures production quality

## Integration Guide

### For AI Agent Developers

1. Always import `coding-rules.md` as part of your agent's context
2. Use templates when possible instead of building from scratch
3. Run validation before returning results to users
4. Apply auto-fixes when warnings are detected
5. Include quality reports in agent responses

### For End Users

When prompting agents to create charts:
1. Specify the chart type (e.g., "dual-axis", "waterfall")
2. Mention if you need Korean language support
3. Request validation reports if quality is critical
4. Ask for specific output formats (PNG, SVG, PDF)

## Testing

Run the complete example to see all features in action:

```bash
python3 examples/complete_dashboard_example.py
```

This generates:
- Revenue & margin dual-axis chart
- Profit bridge waterfall chart
- Peer comparison panels
- Multi-line trends
- Executive dashboard with multiple chart types

## File Structure

```
dartwork-mpl/
├── src/dartwork_mpl/
│   ├── agent_utils.py          # Helper utilities
│   ├── templates/               # Chart templates
│   │   ├── __init__.py
│   │   ├── financial.py
│   │   ├── scientific.py
│   │   └── business.py
│   ├── validate_enhanced.py    # Enhanced validation
│   └── asset/prompt/
│       ├── coding-rules.md     # Agent guidelines
│       └── general-guide.md    # Updated with agent section
└── examples/
    └── complete_dashboard_example.py
```

## Next Steps

Potential future improvements:
- Add more chart templates (Sankey, Gantt, etc.)
- Implement style recommendation based on data type
- Add accessibility checks (color blindness, contrast)
- Create interactive chart builder UI
- Add data preprocessing utilities
- Implement automated chart narration

## Support

For issues or feature requests related to agent functionality:
- Check `coding-rules.md` for guidelines
- Review example code in `examples/`
- Validate charts using enhanced validation
- Report issues with full validation reports

---

These improvements make dartwork-mpl more agent-friendly while maintaining backward compatibility and adhering to best practices for publication-quality visualizations.