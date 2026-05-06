"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation, color manipulation,
code linting, and data validation.
"""

import json
from typing import Any

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

        Only ``https://raw.githubusercontent.com/`` URLs are accepted —
        other schemes (``file://``, ``http://``, ``ftp://``) and other
        hosts are rejected. This is a defence-in-depth check; the tool
        is intended for fetching dartwork-mpl docs from the canonical
        GitHub Raw host.

        Parameters
        ----------
        url : str
            GitHub Raw URL. Example:
            ``https://raw.githubusercontent.com/dartworklabs/dartwork-mpl/main/README.md``

        Returns
        -------
        str
            The content of the document as a string.

        Raises
        ------
        ValueError
            If the URL is not on ``raw.githubusercontent.com`` or the
            request fails.
        """
        allowed_prefix = "https://raw.githubusercontent.com/"
        if not url.startswith(allowed_prefix):
            raise ValueError(
                f"fetch_github_document only accepts URLs starting with "
                f"{allowed_prefix!r}; got {url!r}"
            )
        try:
            import httpx

            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            return response.text
        except ImportError:
            from urllib.request import urlopen

            try:
                with urlopen(url, timeout=10) as response:
                    return str(response.read().decode("utf-8"))
            except Exception as exc:
                raise ValueError(
                    f"Failed to fetch {url}: {type(exc).__name__}"
                ) from exc
        except Exception as exc:
            raise ValueError(
                f"Failed to fetch {url}: {type(exc).__name__}"
            ) from exc

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
        except (ValueError, KeyError, TypeError) as e:
            # ``to_rgb`` raises ``ValueError`` for unknown / malformed
            # colors and ``KeyError`` for missing names; ``TypeError``
            # for non-string inputs. We intentionally do not surface
            # the full traceback to the agent — the message is enough.
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

    @mcp.tool()
    def lint_dartwork_mpl_code_json(code: str) -> list[dict[str, Any]]:
        """Lint Python source against the dartwork-mpl anti-pattern
        catalog and return a structured JSON-friendly list of issues.

        Each issue is a dict with keys:

        - ``rule_id``: str (e.g. ``"figsize-direct"``)
        - ``severity``: ``"critical" | "warning" | "info"``
        - ``line``: int (1-based) or ``None``
        - ``column``: int (0-based, byte offset within source) or ``None``
        - ``message``: str
        - ``fix_suggestion``: str | ``None``

        Companion to :func:`lint_dartwork_mpl_code` which returns a
        formatted text report for human reading. This tool is preferred
        when an agent wants to programmatically pick fixes.

        Parameters
        ----------
        code : str
            Python source to analyze.

        Returns
        -------
        list[dict]
            Structured issues; an empty list means no issues found.
        """
        from dartwork_mpl.lint import lint as _lint

        return [
            {
                "rule_id": i.rule_id,
                "severity": i.severity,
                "line": i.line,
                "column": i.column,
                "message": i.message,
                "fix_suggestion": i.fix_suggestion,
            }
            for i in _lint(code)
        ]

    @mcp.tool()
    def find_template(intent: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Rank the bundled AI plot templates against a free-text intent.

        Thin MCP wrapper over :func:`dartwork_mpl.prompt.find_template`.
        Each template ships with a metadata block (use_case, difficulty,
        data_shape, tags) generated into
        ``asset/prompt/05-templates/_index.json`` at build time. The
        function tokenises ``intent`` and counts how many tokens appear
        in each template's metadata text.

        Parameters
        ----------
        intent : str
            Free-text plot goal, e.g. ``"horizontal bar comparison"``.
        top_k : int, optional
            Maximum number of matches to return, by default 5.

        Returns
        -------
        list[dict]
            ``{"template_id", "score", **metadata}`` per match. Empty
            list when ``intent`` is blank or no template overlaps.
        """
        from dartwork_mpl.prompt import find_template as _find_template

        return _find_template(intent, top_k=top_k)

    @mcp.tool()
    def migrate_legacy_code(code: str) -> str:
        """Rewrite 0.3-era dartwork-mpl source toward the 0.4 idioms.

        Two passes are applied:

        1. **Safe substitutions**: ``dm.cm2in`` → ``dm.cm``,
           ``plt.style.use`` → ``dm.style.use``.
        2. **Hint comments** are inserted above lines using the
           context-dependent patterns the agent must rewrite by hand —
           the deprecated width tokens (``dm.SW``/``MW``/``TW``/``DW``,
           ``dm.FS_*``, ``dm.WIDTHS[...]``), the removed
           ``dm.subplots`` / ``dm.figure`` calls, bare
           ``figsize=(w, h)`` tuples, ``tight_layout()`` calls, and the
           removed ``dm.agent_utils`` / ``dm.xplot`` namespaces.

        The output is always returned (never raises). Run
        :func:`lint_dartwork_mpl_code_json` on the result to confirm no
        critical issues remain after the agent applies the manual hints.

        Parameters
        ----------
        code : str
            0.3-era Python source.

        Returns
        -------
        str
            Rewritten source with ``# TODO(dm-migrate): …`` comments
            above the lines that need agent attention. Inputs without
            matching patterns are returned unchanged.
        """
        from dartwork_mpl.lint import migrate_legacy_code as _migrate

        return _migrate(code)

    # ── Data Validation Tool ─────────────────────────────────────────

    @mcp.tool()
    def validate_plot_data(plot_type: str, data_json: str) -> str:
        """Validate whether data structure matches a plot type's requirements.

        Parameters
        ----------
        plot_type : str
            Target plot type. Supports the full 18-template catalog
            advertised by ``dartwork_mpl_info()``: ``'tornado'``,
            ``'scatter'``, ``'bar'``, ``'bar_horizontal'``,
            ``'bar_grouped'``, ``'heatmap'``, ``'stacked_bar'``,
            ``'pie'``, ``'line'``, ``'violin'``, ``'boxplot'``,
            ``'histogram'``, ``'contour'``, ``'twin_axis'``,
            ``'waterfall'``, ``'small_multiples'``, ``'polar'``,
            ``'plot_3d'``.
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
            "bar_horizontal": _validate_bar_horizontal,
            "bar_grouped": _validate_bar_grouped,
            "heatmap": _validate_heatmap,
            "stacked_bar": _validate_stacked_bar,
            "pie": _validate_pie,
            "line": _validate_line,
            "violin": _validate_violin,
            "boxplot": _validate_boxplot,
            "histogram": _validate_histogram,
            "contour": _validate_contour,
            "twin_axis": _validate_twin_axis,
            "waterfall": _validate_waterfall,
            "small_multiples": _validate_small_multiples,
            "polar": _validate_polar,
            "plot_3d": _validate_plot_3d,
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
        except (OSError, ValueError):
            # OSError: ``read_text`` failed (file missing / unreadable).
            # ValueError: ``json.loads`` raised ``JSONDecodeError`` (a
            # ValueError subclass) on a corrupt presets bundle. Either
            # way we fall back to the static list.
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
                        "Use plt.subplots(figsize=dm.figsize('13cm', 'standard')). "
                        "width accepts unit strings (cm/in/mm) or Inches "
                        "values (dm.cm/inch/mm, dm.col1, dm.col2); bare "
                        "int/float are rejected. aspect is one of "
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
                    "dartwork-mpl://guide/migration",
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
                    "lint_dartwork_mpl_code_json",
                    "migrate_legacy_code",
                    "find_template",
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
                    "bar_horizontal",
                    "bar_grouped",
                    "heatmap",
                    "line",
                    "violin",
                    "stacked_bar",
                    "boxplot",
                    "pie",
                    "histogram",
                    "contour",
                    "twin_axis",
                    "waterfall",
                    "small_multiples",
                    "polar",
                    "plot_3d",
                ],
            },
            indent=2,
        )


# ── Private Validators ───────────────────────────────────────────────


def _validate_tornado(data: dict[str, Any]) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "positive" not in data and "negative" not in data:
        issues.append(
            "Need at least 'positive' and/or 'negative' value arrays."
        )
    if (
        "categories" in data
        and "positive" in data
        and len(data["categories"]) != len(data["positive"])
    ):
        issues.append(
            "Length mismatch: 'categories' and 'positive' must have equal length."
        )
    return (
        "✅ Data structure valid for tornado plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_scatter(data: dict[str, Any]) -> str:
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


def _validate_bar(data: dict[str, Any]) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "values" not in data:
        issues.append("Missing 'values' key (list of numeric values).")
    if (
        "categories" in data
        and "values" in data
        and len(data["categories"]) != len(data["values"])
    ):
        issues.append(
            "Length mismatch: 'categories' and 'values' must have equal length."
        )
    return (
        "✅ Data structure valid for bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_heatmap(data: dict[str, Any]) -> str:
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


def _validate_stacked_bar(data: dict[str, Any]) -> str:
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


def _validate_pie(data: dict[str, Any]) -> str:
    issues = []
    if "labels" not in data:
        issues.append("Missing 'labels' key.")
    if "sizes" not in data:
        issues.append("Missing 'sizes' key (list of numeric values).")
    if (
        "labels" in data
        and "sizes" in data
        and len(data["labels"]) != len(data["sizes"])
    ):
        issues.append(
            "Length mismatch: 'labels' and 'sizes' must have equal length."
        )
    return (
        "✅ Data structure valid for pie chart."
        if not issues
        else "\n".join(issues)
    )


def _validate_line(data: dict[str, Any]) -> str:
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


def _validate_grouped_samples(
    data: dict[str, Any], plot_label: str
) -> list[str]:
    """Shared strict validator for violin/boxplot grouped samples.

    Accepts one of two shapes:

    1. ``groups`` (list of string labels) **and** ``values``
       (list of numeric lists, one inner list per group).
       ``len(groups) == len(values)`` and each inner list must be
       non-empty and numeric.
    2. ``series`` (mapping of label → list of numeric samples).
       Each value list must be non-empty and numeric.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        issues.append(f"'{plot_label}' data must be a JSON object (dict).")
        return issues

    has_pair = "groups" in data and "values" in data
    has_series = "series" in data

    if not has_pair and not has_series:
        issues.append(
            "Need either 'groups' (list of labels) + 'values' "
            "(list of numeric lists), or 'series' (dict of label -> "
            "numeric list)."
        )
        return issues

    if has_pair:
        groups = data["groups"]
        values = data["values"]
        if not isinstance(groups, list) or not all(
            isinstance(g, str) for g in groups
        ):
            issues.append("'groups' must be a list of string labels.")
        if not isinstance(values, list) or not all(
            isinstance(v, list) for v in values
        ):
            issues.append("'values' must be a list of lists of numbers.")
        elif isinstance(groups, list) and len(groups) != len(values):
            issues.append(
                f"Length mismatch: 'groups' ({len(groups)}) != "
                f"'values' ({len(values)})."
            )
        if isinstance(values, list):
            for i, inner in enumerate(values):
                if not isinstance(inner, list):
                    continue
                if len(inner) < 1:
                    issues.append(
                        f"'values[{i}]' must contain at least one sample."
                    )
                if not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in inner
                ):
                    issues.append(
                        f"'values[{i}]' must contain only numeric samples "
                        f"(int/float)."
                    )

    if has_series:
        series = data["series"]
        if not isinstance(series, dict):
            issues.append(
                "'series' must be a dict mapping label -> numeric list."
            )
        else:
            for name, inner in series.items():
                if not isinstance(name, str):
                    issues.append(
                        f"'series' key {name!r} must be a string label."
                    )
                if not isinstance(inner, list):
                    issues.append(
                        f"'series[{name!r}]' must be a list of numbers."
                    )
                    continue
                if len(inner) < 1:
                    issues.append(
                        f"'series[{name!r}]' must contain at least one sample."
                    )
                if not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in inner
                ):
                    issues.append(
                        f"'series[{name!r}]' must contain only numeric "
                        f"samples (int/float)."
                    )

    return issues


def _validate_violin(data: dict[str, Any]) -> str:
    """Validate data for a violin plot.

    See :func:`_validate_grouped_samples` for the accepted shapes.
    """
    issues = _validate_grouped_samples(data, "violin")
    return (
        "✅ Data structure valid for violin plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_boxplot(data: dict[str, Any]) -> str:
    """Validate data for a boxplot.

    See :func:`_validate_grouped_samples` for the accepted shapes.
    """
    issues = _validate_grouped_samples(data, "boxplot")
    return (
        "✅ Data structure valid for boxplot."
        if not issues
        else "\n".join(issues)
    )


def _validate_histogram(data: dict[str, Any]) -> str:
    """Validate data for a histogram.

    Required: ``values`` — a 1-D list of numbers.
    Optional: ``bins`` — either a positive integer or a 1-D list of
    numeric bin edges.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return "histogram data must be a JSON object (dict)."

    if "values" not in data:
        issues.append("Missing 'values' key — a 1-D list of numeric samples.")
    else:
        samples = data["values"]
        if not isinstance(samples, list):
            issues.append("'values' must be a 1-D list of numbers.")
        elif not all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in samples
        ):
            issues.append(
                "'values' must contain only numeric samples (int/float)."
            )

    if "bins" in data:
        bins = data["bins"]
        if isinstance(bins, bool):
            issues.append("'bins' must be a positive int or list of edges.")
        elif isinstance(bins, int):
            if bins < 1:
                issues.append("'bins' (int) must be >= 1.")
        elif isinstance(bins, list):
            if not all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in bins
            ):
                issues.append("'bins' list must contain only numeric edges.")
            elif len(bins) < 2:
                issues.append("'bins' list must contain at least two edges.")
        else:
            issues.append(
                "'bins' must be a positive int or a list of numeric edges."
            )

    return (
        "✅ Data structure valid for histogram."
        if not issues
        else "\n".join(issues)
    )


def _validate_contour(data: dict[str, Any]) -> str:
    """Validate data for a contour plot.

    Required: ``Z`` — a 2-D array (list of lists) with rows of equal
    length and at least one row/column.
    Optional: ``X``, ``Y`` — meshgrid 2-D arrays with the same shape
    as ``Z``.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return "contour data must be a JSON object (dict)."

    if "Z" not in data:
        issues.append("Missing 'Z' key — a 2-D array of values to contour.")
        Z = None
    else:
        Z = data["Z"]
        if not isinstance(Z, list) or not all(
            isinstance(row, list) for row in Z
        ):
            issues.append("'Z' must be a 2-D array (list of lists).")
            Z = None
        elif len(Z) < 1 or len(Z[0]) < 1:
            issues.append("'Z' must have at least one row and one column.")
            Z = None
        elif any(len(row) != len(Z[0]) for row in Z):
            issues.append("'Z' rows must all have equal length.")
            Z = None
        elif not all(
            all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in row
            )
            for row in Z
        ):
            issues.append("'Z' must contain only numeric values (int/float).")

    for key in ("X", "Y"):
        if key not in data:
            continue
        grid = data[key]
        if not isinstance(grid, list) or not all(
            isinstance(row, list) for row in grid
        ):
            issues.append(f"'{key}' must be a 2-D array (list of lists).")
            continue
        if Z is not None:
            z_rows = len(Z)
            z_cols = len(Z[0])
            if len(grid) != z_rows or any(len(r) != z_cols for r in grid):
                issues.append(
                    f"'{key}' shape must match 'Z' shape ({z_rows}x{z_cols})."
                )
                continue
        if not all(
            all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in row
            )
            for row in grid
        ):
            issues.append(
                f"'{key}' must contain only numeric values (int/float)."
            )

    return (
        "✅ Data structure valid for contour plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_twin_axis(data: dict[str, Any]) -> str:
    """Validate data for a twin-axis chart.

    Required:

    * ``x`` — a list of numeric values.
    * ``left`` — a dict with keys ``y`` (numeric list, same length
      as ``x``) and ``label`` (string).
    * ``right`` — same shape as ``left``.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return "twin_axis data must be a JSON object (dict)."

    x = data.get("x")
    if "x" not in data:
        issues.append("Missing 'x' key (list of shared x values).")
    elif not isinstance(x, list):
        issues.append("'x' must be a list of numbers.")
    elif not all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in x
    ):
        issues.append("'x' must contain only numeric values (int/float).")

    n = len(x) if isinstance(x, list) else None

    for side in ("left", "right"):
        if side not in data:
            issues.append(f"Missing '{side}' key (dict with 'y' and 'label').")
            continue
        spec = data[side]
        if not isinstance(spec, dict):
            issues.append(
                f"'{side}' must be a dict with 'y' (numeric list) and "
                f"'label' (string)."
            )
            continue
        if "y" not in spec:
            issues.append(f"'{side}' is missing required 'y' key.")
        else:
            y = spec["y"]
            if not isinstance(y, list):
                issues.append(f"'{side}.y' must be a list of numbers.")
            else:
                if not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in y
                ):
                    issues.append(
                        f"'{side}.y' must contain only numeric values "
                        f"(int/float)."
                    )
                if n is not None and len(y) != n:
                    issues.append(
                        f"'{side}.y' length ({len(y)}) != 'x' length ({n})."
                    )
        if "label" not in spec:
            issues.append(f"'{side}' is missing required 'label' key.")
        elif not isinstance(spec["label"], str):
            issues.append(f"'{side}.label' must be a string.")

    return (
        "✅ Data structure valid for twin-axis plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_bar_horizontal(data: dict[str, Any]) -> str:
    """Validate data for a horizontal bar chart.

    Same shape as a vertical bar: ``categories`` + ``values``.
    """
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "values" not in data:
        issues.append("Missing 'values' key (list of numeric values).")
    if (
        "categories" in data
        and "values" in data
        and len(data["categories"]) != len(data["values"])
    ):
        issues.append(
            "Length mismatch: 'categories' and 'values' must have equal length."
        )
    return (
        "✅ Data structure valid for horizontal bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_bar_grouped(data: dict[str, Any]) -> str:
    """Validate data for a grouped (dodged) bar chart.

    Expected: ``categories`` + ``series`` (dict of series_name -> values),
    each series same length as ``categories``.
    """
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
                    f"Series '{name}' length ({len(vals)}) != "
                    f"categories length ({cat_len})."
                )
    return (
        "✅ Data structure valid for grouped bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_waterfall(data: dict[str, Any]) -> str:
    """Validate data for a waterfall (bridge) chart.

    Expected: ``labels`` + ``deltas`` (signed contributions). Optional
    ``is_total`` flag list selects total/anchor bars.
    """
    issues = []
    if "labels" not in data:
        issues.append("Missing 'labels' key (list of step labels).")
    if "deltas" not in data:
        issues.append("Missing 'deltas' key (list of signed numeric values).")
    if (
        "labels" in data
        and "deltas" in data
        and len(data["labels"]) != len(data["deltas"])
    ):
        issues.append(
            "Length mismatch: 'labels' and 'deltas' must have equal length."
        )
    if (
        "is_total" in data
        and "deltas" in data
        and len(data["is_total"]) != len(data["deltas"])
    ):
        issues.append("Length mismatch: 'is_total' must align with 'deltas'.")
    return (
        "✅ Data structure valid for waterfall plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_small_multiples(data: dict[str, Any]) -> str:
    """Validate data for small multiples / faceted panels.

    Expected: ``panels`` (list of {label, x, y} dicts). Each panel's
    ``x`` and ``y`` arrays must have equal length.
    """
    issues = []
    if "panels" not in data:
        issues.append(
            "Missing 'panels' key (list of {label, x, y} panel dicts)."
        )
    elif not isinstance(data["panels"], list):
        issues.append("'panels' must be a list.")
    else:
        for i, panel in enumerate(data["panels"]):
            if not isinstance(panel, dict):
                issues.append(f"Panel #{i} is not a dict.")
                continue
            if "x" not in panel or "y" not in panel:
                issues.append(f"Panel #{i} missing 'x' or 'y'.")
                continue
            if len(panel["x"]) != len(panel["y"]):
                issues.append(f"Panel #{i}: 'x' and 'y' length mismatch.")
    return (
        "✅ Data structure valid for small multiples."
        if not issues
        else "\n".join(issues)
    )


def _validate_polar(data: dict[str, Any]) -> str:
    """Validate data for a polar / radar chart.

    Expected: ``categories`` (axis labels) + ``values`` (one value per
    category). For multi-series radar, ``values`` may be a dict of
    series_name -> values.
    """
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of axis labels).")
    if "values" not in data:
        issues.append(
            "Missing 'values' key (list, or dict of series_name -> list)."
        )
    if "categories" in data and "values" in data:
        cat_len = len(data["categories"])
        vals = data["values"]
        if isinstance(vals, dict):
            for name, series in vals.items():
                if len(series) != cat_len:
                    issues.append(
                        f"Series '{name}' length ({len(series)}) != "
                        f"categories length ({cat_len})."
                    )
        elif isinstance(vals, list) and len(vals) != cat_len:
            issues.append(
                "Length mismatch: 'values' must equal 'categories' length."
            )
    return (
        "✅ Data structure valid for polar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_plot_3d(data: dict[str, Any]) -> str:
    """Validate data for a 3D scatter / surface plot.

    Expected: ``x``, ``y``, ``z`` arrays of equal length (scatter)
    or 2D ``z`` matrix matching ``x`` x ``y`` (surface).
    """
    issues = [
        f"Missing '{key}' key." for key in ("x", "y", "z") if key not in data
    ]
    if all(k in data for k in ("x", "y", "z")):
        z = data["z"]
        if isinstance(z, list) and z and isinstance(z[0], list):
            # Surface: 2D z, x and y are 1D.
            if len(z) != len(data["y"]):
                issues.append(
                    "Surface mode: rows of 'z' must match 'y' length."
                )
            if z and len(z[0]) != len(data["x"]):
                issues.append(
                    "Surface mode: cols of 'z' must match 'x' length."
                )
        else:
            # Scatter: x, y, z all 1D and equal length.
            if not (len(data["x"]) == len(data["y"]) == len(z)):
                issues.append(
                    "Scatter mode: 'x', 'y', and 'z' must have equal length."
                )
    return (
        "✅ Data structure valid for 3D plot."
        if not issues
        else "\n".join(issues)
    )
