"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation, color manipulation,
code linting, and data validation.
"""

import json
import re

import matplotlib.colors as mcolors
from fastmcp import FastMCP

__all__ = ["register_tools"]


def register_tools(mcp: FastMCP) -> None:
    """
    Register all tools with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register tools with.
    """

    # ── GitHub Document Fetch ────────────────────────────────────────

    @mcp.tool()
    def fetch_github_document(url: str) -> str:
        """Fetch document content from a GitHub Raw URL.

        This tool retrieves the content of a document from GitHub's
        raw content URL. The URL should point to a raw file on GitHub,
        typically in the format:
        https://raw.githubusercontent.com/owner/repo/branch/path/to/file

        Parameters
        ----------
        url : str
            GitHub Raw URL to fetch the document from.
            Example: https://raw.githubusercontent.com/dartworklabs/
            dartwork-mpl/main/README.md

        Returns
        ----------
        str
            The content of the document as a string.

        Raises
        ----------
        ValueError
            If the URL is invalid or the request fails.
        """
        try:
            import httpx

            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            return response.text
        except ImportError:
            # Fallback to urllib if httpx is not available
            from urllib.request import urlopen

            try:
                with urlopen(url, timeout=10) as response:
                    return str(response.read().decode("utf-8"))
            except Exception as e:
                raise ValueError(f"Failed to fetch document: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to fetch document: {e}") from e

    # ── Color Tools ──────────────────────────────────────────────────

    @mcp.tool()
    def get_color_value(name: str) -> str:
        """Get the hex color code for a dartwork-mpl or matplotlib color name.

        Parameters
        ----------
        name : str
            Color name (e.g. 'dc.blue500', 'tw.sky400', 'oc.gray6').

        Returns
        -------
        str
            Hex color code (e.g. '#3b82f6') or an error message.
        """
        try:
            return mcolors.to_hex(mcolors.get_named_colors_mapping()[name])
        except KeyError:
            # Suggest similar colors
            all_names = list(mcolors.get_named_colors_mapping().keys())
            suggestions = [n for n in all_names if name.lower() in n.lower()][
                :5
            ]
            msg = f"Color '{name}' not found."
            if suggestions:
                msg += f" Similar: {suggestions}"
            return msg

    @mcp.tool()
    def mix_colors(color1: str, color2: str, ratio: float = 0.5) -> str:
        """Blend two colors and return the resulting hex code.

        Parameters
        ----------
        color1 : str
            First color name or hex code.
        color2 : str
            Second color name or hex code.
        ratio : float
            Weight of the first color (0.0 to 1.0). Default 0.5.

        Returns
        -------
        str
            Hex code of the blended color.
        """
        try:
            c1 = mcolors.to_rgb(color1)
            c2 = mcolors.to_rgb(color2)
            blended = tuple(
                ratio * a + (1 - ratio) * b
                for a, b in zip(c1, c2, strict=False)
            )
            return mcolors.to_hex(
                blended  # type: ignore[arg-type]
            )
        except Exception as e:
            return f"Error blending colors: {e}"

    @mcp.tool()
    def list_color_families() -> str:
        """List color families available in dartwork-mpl with sample colors.

        Returns a JSON object grouping colors by prefix
        (dc.*, tw.*, oc.*, etc.) with counts and examples.
        """
        mapping = mcolors.get_named_colors_mapping()
        prefixes = ["dc.", "tw.", "md.", "ad.", "cu.", "pr.", "oc."]
        families = {}
        for prefix in prefixes:
            colors = {
                k: mcolors.to_hex(v)
                for k, v in mapping.items()
                if k.startswith(prefix)
            }
            if colors:
                sample = dict(list(colors.items())[:5])
                families[prefix.rstrip(".")] = {
                    "count": len(colors),
                    "sample": sample,
                }
        return json.dumps(families, indent=2)

    # ── Code Linting Tool ────────────────────────────────────────────

    @mcp.tool()
    def lint_dartwork_mpl_code(code: str) -> str:
        """Analyze Python code for dartwork-mpl best practices.

        Checks for common antipatterns:
        - Using figsize= (violates Zero-Resize Policy)
        - Using dpi= in subplots/figure (should use mplstyle)
        - Using plt.subplots() instead of dm.subplots()
        - Using plt.figure() instead of dm.subplots()
        - Not using dartwork-mpl at all
        - Missing plot display or save call
        - Using width=/height= params on savefig
        - Using tight_layout() (conflicts with dartwork-mpl layout)
        - Using plt.style.use() instead of dartwork-mpl styles

        Parameters
        ----------
        code : str
            Python source code to analyze.

        Returns
        -------
        str
            Newline-separated list of warnings, or a success message.
        """
        issues = []

        # --- Critical: Zero-Resize Policy ---
        if "figsize=" in code:
            issues.append(
                "[CRITICAL] 'figsize=' detected — violates Zero-Resize Policy. "
                "dartwork-mpl controls figure dimensions via mplstyle presets. "
                "If you need a custom size, use dm.subplots() without figsize "
                "and adjust the mplstyle's figure.figsize setting."
            )

        # --- Warning: dpi in subplots/figure ---
        if re.search(r"(subplots|figure)\(.*dpi\s*=", code):
            issues.append(
                "[WARNING] 'dpi=' set in subplots/figure call. "
                "dartwork-mpl manages DPI via the mplstyle preset "
                "(default: 300 display, 500 savefig). Remove dpi= parameter."
            )

        # --- Warning: plt.subplots instead of dm.subplots ---
        if "plt.subplots(" in code and "dm.subplots(" not in code:
            issues.append(
                "[WARNING] Using plt.subplots() instead of dm.subplots(). "
                "dm.subplots() applies dartwork-mpl's default styles, fonts, "
                "and layout automatically."
            )

        # --- Warning: plt.figure instead of dm.subplots ---
        if "plt.figure(" in code and "dm.subplots(" not in code:
            issues.append(
                "[WARNING] Using plt.figure() instead of dm.subplots(). "
                "Use dm.subplots() to get properly styled figures."
            )

        # --- Info: not using dartwork-mpl ---
        if "dm." not in code and "dartwork_mpl" not in code:
            issues.append(
                "[WARNING] No dartwork-mpl usage detected. "
                "Import dartwork_mpl as dm and use dm.subplots() "
                "to apply the design system."
            )

        # --- Info: missing save/show ---
        if (
            "plt.show()" not in code
            and "savefig" not in code
            and "dm.show(" not in code
            and "dm.save_and_show(" not in code
        ):
            issues.append(
                "[NOTE] Script neither saves nor shows the plot. "
                "Add plt.show() or fig.savefig() at the end."
            )

        # --- Warning: tight_layout ---
        if "tight_layout" in code:
            issues.append(
                "[WARNING] tight_layout() detected. "
                "dartwork-mpl manages layout via dm.simple_layout() or "
                "constrained_layout. Prefer dm.simple_layout(fig) instead."
            )

        # --- Warning: plt.style.use ---
        if "plt.style.use" in code:
            issues.append(
                "[NOTE] plt.style.use() detected. "
                "dartwork-mpl automatically applies its styles on import. "
                "If you need a specific preset, pass it to dm.subplots(): "
                "dm.subplots(style=['font-scientific'])"
            )

        # --- Warning: width/height in savefig ---
        if re.search(r"savefig\(.*(?:width|height)\s*=", code):
            issues.append(
                "[WARNING] width=/height= in savefig() — this is not a "
                "standard matplotlib parameter and may cause errors."
            )

        # --- Info: recommend save_and_show ---
        if "savefig" in code and "save_and_show" not in code:
            issues.append(
                "[TIP] Consider using dm.save_and_show(fig, 'filename') "
                "instead of manual fig.savefig(). It handles bbox, DPI, "
                "and optionally shows the plot."
            )

        if not issues:
            return (
                "✅ No issues found. Code follows dartwork-mpl best practices."
            )
        return "\n".join(issues)

    # ── Data Validation Tool ─────────────────────────────────────────

    @mcp.tool()
    def validate_plot_data(plot_type: str, data_json: str) -> str:
        """Validate whether data structure matches a plot type's requirements.

        Parameters
        ----------
        plot_type : str
            Target plot type (e.g. 'tornado', 'scatter', 'bar', 'heatmap',
            'stacked_bar', 'violin', 'boxplot', 'pie', 'line').
        data_json : str
            JSON string representing the data to validate. The expected
            structure varies by plot type.

        Returns
        -------
        str
            Validation result with suggestions if issues are found.
        """
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

        validators = {
            "tornado": _validate_tornado,
            "scatter": _validate_scatter,
            "bar": _validate_bar,
            "heatmap": _validate_heatmap,
            "stacked_bar": _validate_stacked_bar,
            "pie": _validate_pie,
            "line": _validate_line,
        }

        validator = validators.get(plot_type.lower())
        if validator is None:
            return f"No validator for '{plot_type}'. Available: {list(validators.keys())}"

        return validator(data)

    # ── Utility Info Tool ────────────────────────────────────────────

    @mcp.tool()
    def dartwork_mpl_info() -> str:
        """Get a summary of dartwork-mpl capabilities and available MCP features.

        Returns a structured overview of all available resources, tools,
        and design system rules for quick reference.
        """
        return json.dumps(
            {
                "name": "dartwork-mpl",
                "description": "Publication-quality matplotlib design system",
                "design_rules": {
                    "zero_resize": "Never set figsize manually; use mplstyle presets",
                    "default_dpi": "300 (display), 500 (savefig)",
                    "default_figsize": "3.5 x 3.0 inches (Nature single-column)",
                    "font": "Roboto sans-serif family, weight 300, size 7.5pt",
                    "save_format": "Use dm.save_and_show() for consistent output",
                },
                "resources": [
                    "dartwork-mpl://guide/general-guide",
                    "dartwork-mpl://guide/layout-guide",
                    "dartwork-mpl://palette/colors",
                    "dartwork-mpl://palette/fonts",
                    "dartwork-mpl://styles/list",
                    "dartwork-mpl://styles/{preset}",
                    "dartwork-mpl://templates/list",
                    "dartwork-mpl://templates/{plot_type}",
                ],
                "tools": [
                    "fetch_github_document",
                    "get_color_value",
                    "mix_colors",
                    "list_color_families",
                    "lint_dartwork_mpl_code",
                    "validate_plot_data",
                    "dartwork_mpl_info",
                ],
                "prompts": ["create_plot", "style_review"],
                "style_presets": [
                    "base",
                    "dmpl",
                    "dmpl_light",
                    "font-minimal",
                    "font-poster",
                    "font-presentation",
                    "font-report",
                    "font-scientific",
                    "font-web",
                    "lang-kr",
                    "spine-no",
                    "spine-yes",
                    "theme-dark",
                    "theme-minimal",
                ],
                "plot_templates": [
                    "tornado",
                    "scatter",
                    "bar",
                    "heatmap",
                    "line",
                    "violin",
                    "stacked_bar",
                    "boxplot",
                    "pie",
                    "histogram",
                    "contour",
                    "twin_axis",
                ],
            },
            indent=2,
        )


# ── Private Validators ───────────────────────────────────────────────


def _validate_tornado(data: dict) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "positive" not in data and "negative" not in data:
        issues.append(
            "Need at least 'positive' and/or 'negative' value arrays."
        )
    if "categories" in data and "positive" in data:
        if len(data["categories"]) != len(data["positive"]):
            issues.append(
                "Length mismatch: 'categories' and 'positive' must have equal length."
            )
    return (
        "✅ Data structure valid for tornado plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_scatter(data: dict) -> str:
    issues = []
    if "x" not in data:
        issues.append("Missing 'x' key (list of x-coordinates).")
    if "y" not in data:
        issues.append("Missing 'y' key (list of y-coordinates).")
    if "x" in data and "y" in data and len(data["x"]) != len(data["y"]):
        issues.append("Length mismatch: 'x' and 'y' must have equal length.")
    return (
        "✅ Data structure valid for scatter plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_bar(data: dict) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "values" not in data:
        issues.append("Missing 'values' key (list of numeric values).")
    if "categories" in data and "values" in data:
        if len(data["categories"]) != len(data["values"]):
            issues.append(
                "Length mismatch: 'categories' and 'values' must have equal length."
            )
    return (
        "✅ Data structure valid for bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_heatmap(data: dict) -> str:
    issues = []
    if "matrix" not in data:
        issues.append("Missing 'matrix' key (2D array of numeric values).")
    elif not isinstance(data["matrix"], list) or not all(
        isinstance(row, list) for row in data["matrix"]
    ):
        issues.append("'matrix' must be a 2D array (list of lists).")
    return (
        "✅ Data structure valid for heatmap."
        if not issues
        else "\n".join(issues)
    )


def _validate_stacked_bar(data: dict) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key.")
    if "series" not in data:
        issues.append("Missing 'series' key (dict of series_name -> values).")
    elif isinstance(data["series"], dict):
        cat_len = len(data.get("categories", []))
        for name, vals in data["series"].items():
            if len(vals) != cat_len:
                issues.append(
                    f"Series '{name}' length ({len(vals)}) != categories length ({cat_len})."
                )
    return (
        "✅ Data structure valid for stacked bar."
        if not issues
        else "\n".join(issues)
    )


def _validate_pie(data: dict) -> str:
    issues = []
    if "labels" not in data:
        issues.append("Missing 'labels' key.")
    if "sizes" not in data:
        issues.append("Missing 'sizes' key (list of numeric values).")
    if "labels" in data and "sizes" in data:
        if len(data["labels"]) != len(data["sizes"]):
            issues.append(
                "Length mismatch: 'labels' and 'sizes' must have equal length."
            )
    return (
        "✅ Data structure valid for pie chart."
        if not issues
        else "\n".join(issues)
    )


def _validate_line(data: dict) -> str:
    issues = []
    if "x" not in data:
        issues.append("Missing 'x' key (list of x values or time points).")
    if "y" not in data and "series" not in data:
        issues.append(
            "Need 'y' (single series) or 'series' (dict of named series)."
        )
    return (
        "✅ Data structure valid for line plot."
        if not issues
        else "\n".join(issues)
    )
