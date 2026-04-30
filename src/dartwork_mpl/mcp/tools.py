"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation, color manipulation,
code linting, and data validation.
"""

import json

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
        """Analyze Python code against the dartwork-mpl anti-pattern
        catalog (asset/prompt/02-anti-patterns.yaml).

        Returns a newline-separated list of
        ``[SEVERITY] rule-id (line N): message`` entries, or a success
        line.

        Parameters
        ----------
        code : str
            Python source to analyze.

        Returns
        -------
        str
            Lint report.
        """
        from dartwork_mpl.lint import format_report
        from dartwork_mpl.lint import lint as _lint

        return format_report(_lint(code))

    # ── Data Validation Tool ─────────────────────────────────────────

    @mcp.tool()
    def validate_plot_data(plot_type: str, data_json: str) -> str:
        """Validate whether data structure matches a plot type's requirements.

        Parameters
        ----------
        plot_type : str
            Target plot type. Supports the full 12-template catalog
            advertised by ``dartwork_mpl_info()``: ``'tornado'``,
            ``'scatter'``, ``'bar'``, ``'heatmap'``, ``'stacked_bar'``,
            ``'pie'``, ``'line'``, ``'violin'``, ``'boxplot'``,
            ``'histogram'``, ``'contour'``, ``'twin_axis'``.
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
            "violin": _validate_violin,
            "boxplot": _validate_boxplot,
            "histogram": _validate_histogram,
            "contour": _validate_contour,
            "twin_axis": _validate_twin_axis,
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
        and design system rules for quick reference. Aligned with the
        0.4 SSOT in ``asset/prompt/`` (00-index, 01-policy,
        02-anti-patterns, 03-recipes, 05-templates).
        """
        # Resolve composite preset names dynamically from the bundled
        # presets.json so this stays in sync with the actual style
        # registry.
        from pathlib import Path

        presets_path = (
            Path(__file__).parent.parent / "asset" / "mplstyle" / "presets.json"
        )
        try:
            composite_presets = sorted(
                json.loads(presets_path.read_text(encoding="utf-8")).keys()
            )
        except Exception:
            composite_presets = [
                "scientific",
                "report",
                "report-kr",
                "presentation",
                "poster",
                "minimal",
                "web",
                "dark",
            ]

        # Static list of registered prompts. We previously poked at
        # ``mcp._prompt_manager._prompts`` to enumerate dynamically, but
        # that private attribute is not part of fastmcp's public API
        # and shifted between 2.x and 3.x. The set of prompts we ship
        # is small and changes alongside this file, so the static list
        # is both simpler and forward-compatible. Keep this in sync
        # with ``register_prompts`` in ``prompts.py``.
        registered_prompts = ["create_plot", "style_review"]

        return json.dumps(
            {
                "name": "dartwork-mpl",
                "version_surface": "0.4",
                "description": "Publication-quality matplotlib design system",
                "design_rules": {
                    "width_aspect": (
                        "Use dm.subplots(width='13cm', aspect='standard'). "
                        "width accepts cm/in/mm strings, dm.cm/inch/mm "
                        "helpers, or a raw number (cm). aspect is one of "
                        "{square, portrait, standard, golden, wide, "
                        "cinema} or a positive float."
                    ),
                    "max_width": "17 cm",
                    "layout": (
                        "Call dm.auto_layout(fig) after plotting. "
                        "dm.simple_layout(fig) is reserved for advanced "
                        "GridSpec cases. tight_layout() is forbidden."
                    ),
                    "default_dpi": "Controlled by the active style preset.",
                    "font": (
                        "Sans-serif family; sizes scaled via dm.fs(n), "
                        "weights via dm.fw(n), line widths via dm.lw(n)."
                    ),
                    "save_format": (
                        "Use dm.save_formats(fig, 'name', formats=('png','pdf'), "
                        "dpi=300) for scripts or dm.save_and_show(fig, 'name') "
                        "for notebooks."
                    ),
                    "color": (
                        "Use named palettes (oc.*, tw.*, dc.*, md.*, "
                        "ad.*, cu.*, pr.*); raw hex is allowed but "
                        "discouraged."
                    ),
                    "retired_policies": [
                        "Zero-Resize Policy (retired in 0.4.0; replaced "
                        "by free-form width input plus a lint consistency "
                        "guard). Mentioning the phrase triggers the "
                        "`zero-resize-mention` lint warning."
                    ],
                },
                "resources": [
                    # 0.4 SSOT URIs
                    "dartwork-mpl://guide/agent-entry",
                    "dartwork-mpl://guide/policy",
                    "dartwork-mpl://guide/anti-patterns",
                    "dartwork-mpl://guide/recipes",
                    "dartwork-mpl://api/index",
                    "dartwork-mpl://api/{name}",
                    # Palettes / styles / templates
                    "dartwork-mpl://palette/colors",
                    "dartwork-mpl://palette/fonts",
                    "dartwork-mpl://styles/list",
                    "dartwork-mpl://styles/{preset}",
                    "dartwork-mpl://templates/list",
                    "dartwork-mpl://templates/{plot_type}",
                    # Legacy aliases (deprecated; retained for 0.3 clients)
                    "dartwork-mpl://guide/general-guide (deprecated alias)",
                    "dartwork-mpl://guide/layout-guide (deprecated alias)",
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
                "prompts": registered_prompts,
                "style_presets": {
                    "composite": composite_presets,
                    "primitive_mplstyle": [
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
                },
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


def _validate_violin(data: dict) -> str:
    """Validate data for a violin plot.

    Accepts either a list-of-lists (each inner list = one violin's
    samples) or a dict mapping group label → samples list.
    """
    issues = []
    if "groups" not in data and "data" not in data:
        issues.append(
            "Need 'data' (list of arrays, one per violin) or 'groups' "
            "(dict of label -> samples)."
        )
    payload = data.get("groups", data.get("data"))
    if isinstance(payload, dict):
        for name, vals in payload.items():
            if not isinstance(vals, list) or not all(
                isinstance(v, (int, float)) for v in vals
            ):
                issues.append(
                    f"Group '{name}' must be a list of numeric samples."
                )
    elif isinstance(payload, list):
        for i, vals in enumerate(payload):
            if not isinstance(vals, list) or not all(
                isinstance(v, (int, float)) for v in vals
            ):
                issues.append(f"Violin {i} must be a list of numeric samples.")
    elif payload is not None:
        issues.append(
            "'data'/'groups' must be a list of lists or a dict of named lists."
        )
    return (
        "✅ Data structure valid for violin plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_boxplot(data: dict) -> str:
    """Validate data for a boxplot.

    Same shape as a violin plot — list-of-lists or dict of named
    lists, one box per group.
    """
    issues = []
    if "groups" not in data and "data" not in data:
        issues.append(
            "Need 'data' (list of arrays, one per box) or 'groups' "
            "(dict of label -> samples)."
        )
    payload = data.get("groups", data.get("data"))
    if isinstance(payload, dict):
        for name, vals in payload.items():
            if not isinstance(vals, list) or not all(
                isinstance(v, (int, float)) for v in vals
            ):
                issues.append(
                    f"Group '{name}' must be a list of numeric samples."
                )
    elif isinstance(payload, list):
        for i, vals in enumerate(payload):
            if not isinstance(vals, list) or not all(
                isinstance(v, (int, float)) for v in vals
            ):
                issues.append(f"Box {i} must be a list of numeric samples.")
    elif payload is not None:
        issues.append(
            "'data'/'groups' must be a list of lists or a dict of named lists."
        )
    return (
        "✅ Data structure valid for boxplot."
        if not issues
        else "\n".join(issues)
    )


def _validate_histogram(data: dict) -> str:
    """Validate data for a histogram. Expects a 1-D numeric array."""
    issues = []
    if "values" not in data and "data" not in data:
        issues.append(
            "Missing 'values' (or 'data') key — a 1-D list of numeric samples."
        )
    samples = data.get("values", data.get("data"))
    if samples is not None:
        if not isinstance(samples, list):
            issues.append("'values' must be a 1-D list of numbers.")
        elif not all(isinstance(v, (int, float)) for v in samples):
            issues.append(
                "'values' must contain only numeric samples (int/float)."
            )
    return (
        "✅ Data structure valid for histogram."
        if not issues
        else "\n".join(issues)
    )


def _validate_contour(data: dict) -> str:
    """Validate data for a contour plot.

    Required: ``Z`` (2-D array). Optional: ``X``, ``Y`` (meshgrid). If
    ``X``/``Y`` are present they must share ``Z``'s shape.
    """
    issues = []
    if "Z" not in data and "z" not in data:
        issues.append("Missing 'Z' key — a 2-D array of values to contour.")
    Z = data.get("Z", data.get("z"))
    if Z is not None:
        if not isinstance(Z, list) or not all(
            isinstance(row, list) for row in Z
        ):
            issues.append("'Z' must be a 2-D array (list of lists).")
        elif Z and any(len(row) != len(Z[0]) for row in Z):
            issues.append("'Z' rows must all have equal length.")
    for key in ("X", "Y"):
        grid = data.get(key, data.get(key.lower()))
        if grid is None:
            continue
        if not isinstance(grid, list) or not all(
            isinstance(row, list) for row in grid
        ):
            issues.append(f"'{key}' must be a 2-D array (list of lists).")
        elif Z is not None and isinstance(Z, list) and Z:
            if len(grid) != len(Z) or any(len(r) != len(Z[0]) for r in grid):
                issues.append(
                    f"'{key}' shape must match 'Z' shape "
                    f"({len(Z)}x{len(Z[0]) if Z else 0})."
                )
    return (
        "✅ Data structure valid for contour plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_twin_axis(data: dict) -> str:
    """Validate data for a twin-axis chart.

    Expected: shared ``x`` plus ``left`` and ``right`` series (each
    same length as ``x``).
    """
    issues = []
    if "x" not in data:
        issues.append("Missing 'x' key (shared x values).")
    if "left" not in data:
        issues.append("Missing 'left' key (primary-axis y values).")
    if "right" not in data:
        issues.append("Missing 'right' key (secondary-axis y values).")
    if all(k in data for k in ("x", "left", "right")):
        n = len(data["x"])
        if len(data["left"]) != n:
            issues.append(
                f"'left' length ({len(data['left'])}) != 'x' length ({n})."
            )
        if len(data["right"]) != n:
            issues.append(
                f"'right' length ({len(data['right'])}) != 'x' length ({n})."
            )
    return (
        "✅ Data structure valid for twin-axis plot."
        if not issues
        else "\n".join(issues)
    )
