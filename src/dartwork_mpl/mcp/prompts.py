"""MCP Prompts for dartwork-mpl.

This module defines interactive prompts that guide users through
creating and reviewing dartwork-mpl plots.
"""

from fastmcp import FastMCP

__all__ = ["register_prompts"]


def register_prompts(mcp: FastMCP) -> None:
    """
    Register all prompts with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register prompts with.
    """

    @mcp.prompt()
    def create_plot(description: str, data_sample: str = "") -> str:
        """Generate a dartwork-mpl plot script from a description.

        Parameters
        ----------
        description : str
            Natural language description of the desired plot
            (e.g. "tornado chart comparing energy savings across 5 buildings").
        data_sample : str
            Optional sample data in JSON or CSV format.
        """
        data_section = ""
        if data_sample:
            data_section = f"""
## Data Sample
```
{data_sample}
```
Use this real data in the generated script.
"""

        return f"""You are an expert data visualization engineer using **dartwork-mpl**, a publication-quality matplotlib design system.

## Task
Generate a complete Python script that creates the following plot:

**Description**: {description}
{data_section}
## Mandatory Rules
1. **Import**: `import dartwork_mpl as dm` and `import matplotlib.pyplot as plt`
2. **Figure creation**: Use `dm.subplots()` — NEVER `plt.subplots()` or `plt.figure()`
3. **Zero-Resize Policy**: Do NOT set `figsize=`, `dpi=`, or any size parameters
4. **Colors**: Use dartwork-mpl colors (e.g. `"dc.blue500"`, `"dc.red500"`, `"dc.green500"`)
5. **Save/Show**: End with `plt.show()` or `dm.save_and_show(fig, "output")`
6. **Layout**: Do NOT use `tight_layout()`. Use `dm.simple_layout(fig)` if needed
7. **Font sizing**: Do NOT set font sizes manually — they are managed by mplstyle
8. **Style presets**: If a specific style is needed, pass it: `dm.subplots(style=['font-scientific'])`

## Available Style Presets
- `font-scientific` — journal paper (7.5pt base)
- `font-presentation` — slides (larger fonts)
- `font-poster` — poster (largest fonts)
- `font-report` — technical reports
- `lang-kr` — Korean language support
- `theme-dark` — dark background
- `theme-minimal` — minimal decorations
- `spine-no` / `spine-yes` — spine visibility

## Color Families
- `dc.*` — dartwork core palette (dc.blue500, dc.red500, dc.green500, etc.)
- `tw.*` — Tailwind CSS colors
- `oc.*` — Open Color palette

Generate clean, well-commented code that follows these rules strictly.
"""

    @mcp.prompt()
    def style_review(code: str) -> str:
        """Review and fix a dartwork-mpl script for style compliance.

        Parameters
        ----------
        code : str
            Python source code to review.
        """
        return f"""You are a strict code reviewer for **dartwork-mpl**, a publication-quality matplotlib design system.

## Code to Review
```python
{code}
```

## Review Checklist
Check the code against ALL of these rules and provide fixes:

### Critical (Must Fix)
- [ ] Uses `dm.subplots()` instead of `plt.subplots()` or `plt.figure()`
- [ ] No `figsize=` parameter (Zero-Resize Policy)
- [ ] No `dpi=` parameter in figure/subplots calls
- [ ] No `tight_layout()` — use `dm.simple_layout(fig)` instead

### Style (Should Fix)
- [ ] Colors use dartwork-mpl names (`dc.*`, `tw.*`, `oc.*`) not raw hex
- [ ] No manual font size overrides (fontsize=, size=)
- [ ] Uses `dm.save_and_show()` instead of manual `fig.savefig()`
- [ ] No `plt.style.use()` — pass styles to `dm.subplots(style=[...])`

### Quality (Recommend)
- [ ] Axis labels are set
- [ ] Legend is properly placed (if multiple series)
- [ ] Code is well-commented
- [ ] Data is cleanly separated from plotting logic

## Output Format
For each issue found:
1. **Issue**: What's wrong
2. **Location**: Line number or code snippet
3. **Fix**: Corrected code

Then provide the complete corrected script.
"""
