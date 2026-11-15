"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation, color manipulation,
code linting, and data validation.
"""

from typing import Any

from fastmcp import FastMCP

from . import catalog, colors, docs_fetch, lint, templates
from .plot_data import validate_data

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
    async def fetch_github_document(url: str) -> str:
        """Fetch document content from a GitHub Raw URL.

        Only ``https://raw.githubusercontent.com/`` URLs are accepted —
        other schemes (``file://``, ``http://``, ``ftp://``) and other
        hosts, credentials and nondefault ports are rejected before connection.
        At most five redirects are checked the same way. One ten-second total
        deadline covers redirects and body streaming. Only identity encoding
        and at most1 MiB received bytes are accepted; UTF-8 replacement may
        produce up to3 MiB UTF-8 text. Responses close on every exit.

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
        return await docs_fetch.fetch_raw_github(url)

    # ── Color Tools ──────────────────────────────────────────────────

    @mcp.tool()
    def get_color_value(name: str) -> str:
        """Get the hex color code for a dartwork-mpl or matplotlib color name.

        Parameters
        ----------
        name : str
            Color name (e.g. 'dc.blue6', 'tw.sky400', 'oc.gray6').

        Returns
        -------
        str
            Hex color code (e.g. '#3b82f6') or an error message.
        """
        return colors.color_value(name)

    @mcp.tool()
    def mix_colors(color1: str, color2: str, ratio: float = 0.5) -> str:
        """Blend two colors in OKLab space and return the resulting hex code.

        Delegates to the public :func:`dartwork_mpl.mix_colors`, which
        blends along an OKLab authoring path rather than gamma-encoded sRGB.
        This generally improves perceptual regularity, but does not promise
        perfectly equal visible steps. The MCP tool therefore always agrees
        with what ``dm.mix_colors`` produces in generated plot code.

        Parameters
        ----------
        color1 : str
            First color name or hex code.
        color2 : str
            Second color name or hex code.
        ratio : float
            Weight of the first color (0.0 to 1.0). Default 0.5.
            Maps to ``dm.mix_colors``' ``alpha`` parameter.

        Returns
        -------
        str
            Hex code of the blended color.
        """
        return colors.mix(color1, color2, ratio)

    @mcp.tool()
    def list_color_families() -> str:
        """List color families available in dartwork-mpl with sample colors.

        Returns a JSON object grouping colors by prefix
        (dc.*, tw.*, oc.*, etc.) with counts and examples.
        """
        from ..color import LIBRARIES

        return colors.list_families(LIBRARIES)

    # ── Code Linting Tool ────────────────────────────────────────────

    @mcp.tool()
    def lint_dartwork_mpl_code(code: str) -> str:
        """Lint Python source against the dartwork-mpl anti-pattern catalog.

        Returns one ``[severity] rule-id (line N): message → fix`` line per
        finding, or ``No issues found.``. The source is never executed;
        literal ``cmap=`` and colour names are checked against matplotlib's
        registries (``sorted(matplotlib.colormaps)``,
        ``matplotlib.colors.get_named_colors_mapping()``).

        Parameters
        ----------
        code : str
            Python source to analyze.

        Returns
        -------
        str
            Lint report.
        """
        return lint.lint_text(code)

    @mcp.tool()
    def lint_dartwork_mpl_code_json(code: str) -> list[dict[str, Any]]:
        """Lint Python source against the dartwork-mpl anti-pattern
        catalog and return a structured JSON-friendly list of issues.

        Each issue is a dict with keys:

        - ``rule_id``: str (e.g. ``"figsize-direct"``)
        - ``severity``: ``"critical" | "warning" | "info"``
        - ``line``: int (1-based)
        - ``message``: str
        - ``fix_suggestion``: str | ``None``

        Companion to :func:`lint_dartwork_mpl_code` which returns a
        formatted text report for human reading. This tool is preferred
        when an agent wants to programmatically pick fixes.

        Valid names come from ``sorted(matplotlib.colormaps)`` and
        ``matplotlib.colors.get_named_colors_mapping()``. Literal checks
        share the text tool's static scope and never execute source.

        Parameters
        ----------
        code : str
            Python source to analyze.

        Returns
        -------
        list[dict]
            Structured issues; an empty list means no issues found.
        """
        return lint.lint_records(code)

    @mcp.tool()
    def find_template(
        intent: str, top_k: int = 5, tier: str | None = None
    ) -> list[dict[str, Any]]:
        """Rank the bundled AI plot templates against a free-text intent.

        Thin MCP wrapper over :func:`dartwork_mpl.guide.search`, which
        scores each template's title, use case, data shape and tags by the
        words it shares with ``intent``.

        Parameters
        ----------
        intent : str
            Free-text plot goal, e.g. ``"horizontal bar comparison"``.
        top_k : int, optional
            Maximum number of matches to return, by default 5.
        tier : str | None, optional
            ``"basic"`` (or ``None``, the default) searches the 18 minimal
            templates, ``"advanced"`` the 18 narrative ones, ``"all"`` both.

        Returns
        -------
        list[dict]
            ``{"template_id", "tier", "id", "title", "use_case"}`` per match,
            best first; ``id`` is the ``dm.guide.read`` reference id.
        """
        return templates.find(intent, top_k, tier)

    @mcp.tool()
    def render_template(
        plot_type: str,
        return_format: str = "base64",
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a bundled plot template and return the rendered PNG.

        Useful for MCP UIs that can display inline images (Claude
        Desktop, Cursor MCP UI extensions): the agent can offer a
        thumbnail of "here's what `tornado` looks like before I
        adapt it to your data" without round-tripping through a
        filesystem.

        Parameters
        ----------
        plot_type : str
            Template id (e.g. ``"bar"``, ``"line"``, ``"plot_3d"``).
        return_format : str, optional
            ``"base64"`` (default) returns a base64-encoded PNG string
            under the ``png_base64`` key. ``"path"`` returns the
            temp-file path under ``"png_path"`` instead. Use the path
            variant only when the MCP client can read local files. Each successful
            path is a unique0600 regular temp file; callers own its lifetime.
        timeout_seconds : float, optional
            Hard timeout for the subprocess. Default 30 s. Diagnostic channels are
            bounded to64 KiB UTF-8, including any visible truncation marker.

        Returns
        -------
        dict
            ``{"status": "ok"|"unknown_template"|"render_error"|
            "timeout", "plot_type": str, "png_base64": str|None,
            "png_path": str|None, "stderr": str}``.
        """
        return templates.render_basic(plot_type, return_format, timeout_seconds)

    # ── Figure Validation Tool (execute + validate) ──────────────────

    @mcp.tool()
    def validate_generated_plot(
        code: str,
        figure_var: str = "fig",
        timeout_seconds: float = 20.0,
        chart_type_hint: str | None = None,
    ) -> dict[str, Any]:
        """Execute a dartwork-mpl script in an isolated subprocess and
        return the structured ``dm.validate_figure`` report, plus
        optional semantic checks against an expected chart type.

        This closes the loop between *"agent generated some plot code"*
        and *"is the rendered figure actually free of overflow, clipping,
        and asymmetric margins?"* — issues that the lint pass can't see.
        The code runs in a fresh ``python`` subprocess with the ``Agg``
        backend forced on, so it never blocks on a GUI window and can
        be timed out cleanly.

        When ``chart_type_hint`` is supplied, the tool also runs a
        small set of *semantic* checks against the rendered axes —
        pie charts with too many slices, scatters with too few points,
        bars with no annotations, etc. These supplement the visual
        check by catching plot choices that *render fine* but read
        poorly.

        Parameters
        ----------
        code : str
            Python source. Should construct a ``matplotlib`` figure and
            bind it to the variable name ``figure_var`` (default
            ``"fig"``). The lint pass runs first; critical lint issues
            short-circuit before any code is executed.
        figure_var : str, optional
            Name of the variable holding the figure. Default ``"fig"``.
        timeout_seconds : float, optional
            Hard timeout for the subprocess. Default 20 s.
        chart_type_hint : str | None, optional
            Plot-type id (``"pie"``, ``"scatter"``, ``"bar"``,
            ``"line"``, etc.) the code is meant to produce. When set,
            the tool runs additional semantic checks and reports them
            under ``"semantic_warnings"``. Default ``None`` (skip).

        Returns
        -------
        dict
            Every response includes ``status``, ``lint``, ``visual_warnings``,
            ``stdout: str``, ``stderr: str``, ``validation_complete: bool`` and
            ``failed_checks: list[str]``. ``ok`` means validation completed,
            even if warnings exist. Tolerated check failures instead return
            ``validation_incomplete`` with original check IDs and incomplete
            validation. ``lint_blocked``, ``exec_error``, ``no_figure`` and
            ``timeout`` are also incomplete; known failed IDs survive errors.
            ``visual_warnings`` items are ``{"severity",
            "check_id", "message", "detail"}`` dicts. ``semantic_warnings``
            items are ``{"check_id", "message"}`` dicts — only present
            (and possibly empty) when ``chart_type_hint`` was supplied.

        Notes
        -----
        - The subprocess inherits the parent Python; it relies on
          ``dartwork_mpl`` being importable in the current
          environment.
        - This tool **executes the provided code**. It is intended
          for trusted agent-generated snippets, not arbitrary user
          input from the web. It isolates Matplotlib state, not OS access:
          cwd and real save effects are inherited. Hostile snippets can mutate
          the runner; this is not a security sandbox. Internal results use a
          private temporary file that is cleaned up independently of logs.
        """
        from .execution import to_wire, validate_plot

        return to_wire(
            validate_plot(code, figure_var, timeout_seconds, chart_type_hint)
        )

    # ── Data Validation Tool ─────────────────────────────────────────

    @mcp.tool()
    def validate_plot_data(
        plot_type: str, data_json: str, report: bool = False
    ) -> str:
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
        report : bool, optional
            Return a version-1 JSON report encoded in a string, with
            reviewable suggestions for the five supported plot types.
            Defaults to False for the existing validation messages.

        Returns
        -------
        str
            Validation message, or a JSON-string report when report is True.
            Reports preserve admitted originals and propose separate candidates;
            they never apply changes or create other effects.
        """
        return validate_data(plot_type, data_json, report)

    # ── Chart Recommendation & Composition ───────────────────────────

    @mcp.tool()
    def compose_layered_plot(
        plot_type: str, layers: list[str] | None = None, tier: str = "advanced"
    ) -> dict[str, Any]:
        """Return a starting template with the requested annotation
        layers explicitly identified.

        This is a *guidance* tool, not a code rewriter — it returns the
        relevant template source (basic or advanced) and a checklist of
        which annotation/composition layers to apply. The agent then
        edits the returned code to fit its data.

        Supported layer keywords
        ------------------------
        ``"reference_line"`` (axhline / axvline at a target)
        | ``"event_window"`` (axvspan to mark a period)
        | ``"value_labels"`` (per-bar / per-point text)
        | ``"trendline"`` (np.polyfit + ax.plot for scatters)
        | ``"highlight"`` (one accent-colored bar / point)
        | ``"callout"`` (ax.annotate with arrow)
        | ``"gradient_palette"`` (dm.cspace across series)
        | ``"source_footnote"`` (fig.text bottom-left).

        Parameters
        ----------
        plot_type : str
            Plot type id (e.g. ``"bar"``, ``"scatter"``).
        layers : list[str] | None, optional
            Layer keywords to highlight. ``None`` = return the canonical
            advanced template (which already shows the full layered
            pattern).
        tier : str, optional
            ``"basic"`` returns the minimal template; ``"advanced"``
            (default) returns the tier-2 narrative version.

        Returns
        -------
        dict
            ``{"status": str, "tier": str, "code": str, "layers": list,
            "applied": list, "missing": list}``. ``"applied"`` lists
            layers detected in the returned code; ``"missing"`` lists
            requested layers that are NOT yet in the canonical
            template and would need to be added by hand.
        """
        return templates.compose(plot_type, layers, tier)

    @mcp.tool()
    def render_template_advanced(
        plot_type: str,
        return_format: str = "base64",
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Render the tier-2 (advanced) version of a bundled template.

        Companion to :func:`render_template` for the basic tier. The
        advanced templates include real-feeling synthetic data,
        reference lines and value labels. Like the basic tier they draw
        no title, subtitle or source note; add one only when the user
        asks (``dm.add_note`` for a source line).

        Falls back to the basic tier and returns ``status:"fell_back"``
        if no advanced version exists for the requested plot type yet.

        Parameters
        ----------
        plot_type : str
            Template id (e.g. ``"bar"``, ``"scatter"``).
        return_format : str, optional
            ``"base64"`` (default) or ``"path"`` — same as
            :func:`render_template`.
        timeout_seconds : float, optional
            Hard subprocess timeout. Default 30 s. Diagnostics retain bounded
            prefixes and complete markers; render errors fit2,000 characters.

        Returns
        -------
        dict
            ``{"status": "ok"|"fell_back"|"unknown_template"|
            "render_error"|"timeout", "plot_type": str, "tier": str,
            "png_base64": str|None, "png_path": str|None,
            "stderr": str}``.
        """
        return templates.render_advanced(
            plot_type, return_format, timeout_seconds
        )

    # ── Utility Info Tool ────────────────────────────────────────────

    @mcp.tool()
    def dartwork_mpl_info() -> str:
        """Get a summary of dartwork-mpl capabilities and available MCP features.

        Returns a structured overview of all available resources, tools,
        and design system rules for quick reference, aligned with the
        bundled skill that ``dm.guide`` reads.
        """
        return catalog.info_payload()
