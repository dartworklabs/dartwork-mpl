"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation, color manipulation,
code linting, and data validation.
"""

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from . import catalog, colors, docs_fetch, recommend
from ._platform import resolve_template_path
from .plot_data import validate_data

__all__ = ["register_tools"]

_ASSET_DIR = Path(__file__).parent.parent / "asset"
_TEMPLATE_DIR = _ASSET_DIR / "prompt" / "05-templates"


def _resolve_template_path(
    plot_type: str, *, advanced: bool = False
) -> Path | None:
    """Delegate template lookup to the shared confined MCP asset boundary.

    Preserve the private compatibility surface while returning the resolved
    regular file checked by that boundary, or None for invalid/missing IDs.
    """
    return resolve_template_path(plot_type, advanced=advanced)


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
        from .._colors._loader import COLOR_LIBRARIES

        return colors.list_families(COLOR_LIBRARIES)

    # ── Code Linting Tool ────────────────────────────────────────────

    @mcp.tool()
    def lint_dartwork_mpl_code(code: str) -> str:
        """Analyze Python code against the dartwork-mpl anti-pattern
        catalog (asset/prompt/02-anti-patterns.yaml).

        Returns a newline-separated list of
        ``[SEVERITY] rule-id (line N): message`` entries, or a success
        line.

        Literal cmap/color names in conventional ax/plt plotting calls
        (and imported pyplot aliases) are checked against live matplotlib
        registries without executing source. Discover valid colormaps via
        ``sorted(matplotlib.colormaps)`` and named colors via
        ``matplotlib.colors.get_named_colors_mapping()``; existing tools
        ``get_color_value`` and ``list_color_families`` help inspect colors.
        The resource ``dartwork-mpl://palette/colors`` lists exact package
        color names and values.
        For example, ``cmap="coolwarm"`` and ``color="dc.blue6"`` are valid.
        Dynamic expressions and unknown receivers are left unchecked;
        live custom names and explicit inline literal registrations are
        accepted. Implicit/dynamic inline map registration defers map checks.
        Direct named-color mapping updates and dynamic assignment keys
        similarly defer color checks, while map checks still run.

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
        - ``column``: int (absolute zero-based Python character offset within source) or ``None``
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
    def find_template(
        intent: str, top_k: int = 5, tier: str | None = None
    ) -> list[dict[str, Any]]:
        """Rank the bundled AI plot templates against a free-text intent.

        Thin MCP wrapper over :func:`dartwork_mpl.prompt.find_template`.
        Each template ships with a metadata block (use_case, difficulty,
        data_shape, tags, narrative) generated into
        ``asset/prompt/05-templates/_index.json`` at build time. The
        function tokenises ``intent`` and counts how many tokens appear
        in each template's metadata text.

        Parameters
        ----------
        intent : str
            Free-text plot goal, e.g. ``"horizontal bar comparison"``.
        top_k : int, optional
            Maximum number of matches to return, by default 5.
        tier : str | None, optional
            ``"basic"`` searches the 18 tier-1 minimal templates;
            ``"advanced"`` searches the 18 tier-2 narrative templates
            (real-feeling data, reference lines, annotation overlays);
            ``"all"`` searches both. ``None`` (default) keeps the
            original behaviour: basic tier only, no ``tier`` field on
            each result. When ``tier`` is non-``None`` each result
            carries ``"tier"`` so callers using ``"all"`` can
            distinguish hits.

        Returns
        -------
        list[dict]
            ``{"template_id", "score", **metadata}`` per match (plus
            ``"tier"`` when ``tier`` is non-``None``). Empty list when
            ``intent`` is blank or no template overlaps.
        """
        from dartwork_mpl.prompt import find_template as _find_template

        return _find_template(intent, top_k=top_k, tier=tier)

    @mcp.tool()
    def apply_lint_fixes(code: str) -> dict[str, Any]:
        """Apply safe identifier-level rewrites for a curated subset
        of lint rules, then return the fixed source plus the diff
        between before/after lint runs.

        Wraps :func:`dartwork_mpl.lint.apply_lint_fixes`. Currently
        rewrites ``plt.style.use → dm.style.use`` and the no-arg
        ``plt.tight_layout() / fig.tight_layout()`` calls →
        ``dm.simple_layout(fig)``. Context-dependent rules (e.g.
        ``figsize-direct`` — which needs the agent to choose a width
        and aspect token) are left untouched and surfaced in
        ``unfixed`` so the agent knows what's still pending.

        Parameters
        ----------
        code : str
            Python source.

        Returns
        -------
        dict
            ``{"fixed_code": str, "applied": list[Issue],
            "unfixed": list[Issue]}``. Each Issue is a dict shaped
            like :func:`lint_dartwork_mpl_code_json` entries.
        """
        from dartwork_mpl.lint import apply_lint_fixes as _apply

        fixed_code, applied, unfixed = _apply(code)

        def _serialise(issue: Any) -> dict[str, Any]:
            return {
                "rule_id": issue.rule_id,
                "severity": issue.severity,
                "line": issue.line,
                "column": issue.column,
                "message": issue.message,
                "fix_suggestion": issue.fix_suggestion,
            }

        return {
            "fixed_code": fixed_code,
            "applied": [_serialise(i) for i in applied],
            "unfixed": [_serialise(i) for i in unfixed],
        }

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
        import base64
        import sys
        import tempfile
        import textwrap
        from pathlib import Path as _Path

        from ._platform import (
            diagnostic,
            publish_png,
            run_child,
            strip_diagnostic,
        )

        template_dir = _TEMPLATE_DIR
        path = _resolve_template_path(plot_type)
        if path is None:
            available = sorted(p.stem for p in template_dir.glob("*.py"))
            return {
                "status": "unknown_template",
                "plot_type": plot_type,
                "png_base64": None,
                "png_path": None,
                "stderr": (
                    f"No template named {plot_type!r}. Available: {available}"
                ),
            }

        with tempfile.TemporaryDirectory() as tmp:
            out_base = _Path(tmp) / "out"
            # The template ends with ``dm.save_formats(fig, "<name>")``
            # which writes to ``<cwd>/<name>.png``. We just need to
            # run it in our tmp dir and read whatever PNG appears.
            runner = textwrap.dedent(
                """\
                import os, sys
                os.chdir({tmp!r})
                import matplotlib
                matplotlib.use("Agg")
                sys.path.insert(0, {tmpdir!r})
                exec(compile(open({path!r}).read(), {path!r}, "exec"),
                     {{"__name__": "__render__"}})
                """
            ).format(
                tmp=str(out_base.parent),
                tmpdir=str(out_base.parent),
                path=str(path),
            )

            proc = run_child(
                [sys.executable, "-c", runner], timeout_seconds=timeout_seconds
            )
            if proc.timed_out:
                return {
                    "status": "timeout",
                    "plot_type": plot_type,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": f"Render exceeded {timeout_seconds}s timeout.",
                }

            pngs = sorted(out_base.parent.glob("*.png"))
            if proc.returncode != 0 or not pngs:
                return {
                    "status": "render_error",
                    "plot_type": plot_type,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": diagnostic(
                        proc.stderr or proc.stdout,
                        "stderr" if proc.stderr else "stdout",
                        char_limit=2000,
                        marked=(
                            proc.stderr_truncated
                            if proc.stderr
                            else proc.stdout_truncated
                        ),
                    ),
                }

            png_bytes = pngs[0].read_bytes()
            if return_format == "path":
                try:
                    persistent = publish_png(
                        png_bytes, f"dartwork-mpl-render-{plot_type}-"
                    )
                except OSError:
                    return {
                        "status": "render_error",
                        "plot_type": plot_type,
                        "png_base64": None,
                        "png_path": None,
                        "stderr": "Template output publication failed.",
                    }
                return {
                    "status": "ok",
                    "plot_type": plot_type,
                    "png_base64": None,
                    "png_path": str(persistent),
                    "stderr": strip_diagnostic(
                        proc.stderr, "stderr", marked=proc.stderr_truncated
                    ),
                }
            return {
                "status": "ok",
                "plot_type": plot_type,
                "png_base64": base64.b64encode(png_bytes).decode("ascii"),
                "png_path": None,
                "stderr": strip_diagnostic(
                    proc.stderr, "stderr", marked=proc.stderr_truncated
                ),
            }

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
        from .execution import validate_plot

        return validate_plot(code, figure_var, timeout_seconds, chart_type_hint)

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
    def suggest_chart_type(
        x_type: str,
        y_type: str | None = None,
        n_points: int = 50,
        n_series: int = 1,
    ) -> dict[str, Any]:
        """Recommend a chart type from data characteristics.

        Thin MCP wrapper over :func:`dartwork_mpl.suggest_chart_type`
        that also returns pointers to the matching template (both basic
        and advanced tiers) so the agent can pull the canonical example
        directly.

        Parameters
        ----------
        x_type : str
            ``"continuous"``, ``"categorical"``, or ``"temporal"``.
        y_type : str | None, optional
            ``"continuous"``, ``"categorical"``, ``"count"``, or
            ``None`` (e.g. for a histogram of a single variable).
        n_points : int, optional
            Total number of data points. Influences density-aware picks
            (scatter vs. heatmap). Default 50.
        n_series : int, optional
            Number of series being compared. Default 1.

        Returns
        -------
        dict
            ``{"recommended": str, "basic_template_uri": str,
            "advanced_template_uri": str | None, "rationale": str}``.
            ``recommended`` is a canonical template stem (normalized via
            ``_SUGGEST_TO_TEMPLATE``), so it always resolves through
            ``render_template`` / ``find_template``; when the raw
            recommender label differed (e.g. ``scatter_density``), the
            semantic label is preserved in ``rationale``.
            ``advanced_template_uri`` is ``None`` when no tier-2 version
            exists yet for the recommended plot type.
        """
        return recommend.suggest(x_type, y_type, n_points, n_series)

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
        layers = list(layers or [])
        template_dir = _TEMPLATE_DIR
        if tier == "advanced":
            path = _resolve_template_path(plot_type, advanced=True)
            if path is None:
                # Fall back to basic if advanced doesn't exist yet.
                path = _resolve_template_path(plot_type)
                tier = "basic"
        elif tier == "basic":
            path = _resolve_template_path(plot_type)
        else:
            return {
                "status": "invalid_tier",
                "tier": tier,
                "code": "",
                "layers": layers,
                "applied": [],
                "missing": [],
            }

        if path is None:
            available = sorted(p.stem for p in template_dir.glob("*.py"))
            return {
                "status": "unknown_template",
                "tier": tier,
                "code": (
                    f"No template named {plot_type!r}. Available: {available}"
                ),
                "layers": layers,
                "applied": [],
                "missing": layers,
            }

        code = path.read_text(encoding="utf-8")

        # Heuristic detection — purely lexical so it stays cheap and
        # lets the agent see "yes, the advanced template already does
        # this, no need to add it again."
        detect_patterns = {
            "reference_line": ("axhline(", "axvline("),
            "event_window": ("axvspan(", "axhspan("),
            "value_labels": ("ax.text(", "ax.bar_label("),
            "trendline": ("np.polyfit", "polyfit"),
            "highlight": ("dc.amber5", "accent", 'marker="D"'),
            "callout": ("ax.annotate(", "arrowprops="),
            "gradient_palette": ("dm.cspace(", ".cspace("),
            "source_footnote": ("fig.text(", "Source:"),
        }
        applied: list[str] = []
        for layer, patterns in detect_patterns.items():
            if any(p in code for p in patterns):
                applied.append(layer)
        missing = [layer for layer in layers if layer not in applied]

        return {
            "status": "ok",
            "tier": tier,
            "code": code,
            "layers": layers,
            "applied": applied,
            "missing": missing,
        }

    @mcp.tool()
    def render_template_advanced(
        plot_type: str,
        return_format: str = "base64",
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Render the tier-2 (advanced) version of a bundled template.

        Companion to :func:`render_template` for the basic tier. The
        advanced templates include real-feeling synthetic data,
        reference lines, value labels, a narrative title with takeaway
        subtitle, and a source footnote — they read like finished
        report figures.

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
        import base64
        import sys
        import tempfile
        import textwrap
        from pathlib import Path as _Path

        from ._platform import (
            diagnostic,
            publish_png,
            run_child,
            strip_diagnostic,
        )

        template_dir = _TEMPLATE_DIR
        advanced_path = _resolve_template_path(plot_type, advanced=True)
        basic_path = _resolve_template_path(plot_type)

        if advanced_path is not None:
            path = advanced_path
            tier = "advanced"
            fell_back = False
        elif basic_path is not None:
            path = basic_path
            tier = "basic"
            fell_back = True
        else:
            available = sorted(p.stem for p in template_dir.glob("*.py"))
            return {
                "status": "unknown_template",
                "plot_type": plot_type,
                "tier": "none",
                "png_base64": None,
                "png_path": None,
                "stderr": (
                    f"No template named {plot_type!r}. "
                    f"Available basic: {available}. "
                    f"Available advanced: "
                    f"{sorted(p.stem for p in (template_dir / 'advanced').glob('*.py'))}."
                ),
            }

        with tempfile.TemporaryDirectory() as tmp:
            out_base = _Path(tmp) / "out"
            runner = textwrap.dedent(
                """\
                import os, sys
                os.chdir({tmp!r})
                import matplotlib
                matplotlib.use("Agg")
                sys.path.insert(0, {tmpdir!r})
                exec(compile(open({path!r}).read(), {path!r}, "exec"),
                     {{"__name__": "__render__"}})
                """
            ).format(
                tmp=str(out_base.parent),
                tmpdir=str(out_base.parent),
                path=str(path),
            )

            proc = run_child(
                [sys.executable, "-c", runner], timeout_seconds=timeout_seconds
            )
            if proc.timed_out:
                return {
                    "status": "timeout",
                    "plot_type": plot_type,
                    "tier": tier,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": f"Render exceeded {timeout_seconds}s timeout.",
                }

            pngs = sorted(out_base.parent.glob("*.png"))
            if proc.returncode != 0 or not pngs:
                return {
                    "status": "render_error",
                    "plot_type": plot_type,
                    "tier": tier,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": diagnostic(
                        proc.stderr or proc.stdout,
                        "stderr" if proc.stderr else "stdout",
                        char_limit=2000,
                        marked=(
                            proc.stderr_truncated
                            if proc.stderr
                            else proc.stdout_truncated
                        ),
                    ),
                }

            png_bytes = pngs[0].read_bytes()
            status = "fell_back" if fell_back else "ok"
            if return_format == "path":
                try:
                    persistent = publish_png(
                        png_bytes, f"dartwork-mpl-render-advanced-{plot_type}-"
                    )
                except OSError:
                    return {
                        "status": "render_error",
                        "plot_type": plot_type,
                        "tier": tier,
                        "png_base64": None,
                        "png_path": None,
                        "stderr": "Template output publication failed.",
                    }
                return {
                    "status": status,
                    "plot_type": plot_type,
                    "tier": tier,
                    "png_base64": None,
                    "png_path": str(persistent),
                    "stderr": strip_diagnostic(
                        proc.stderr, "stderr", marked=proc.stderr_truncated
                    ),
                }
            return {
                "status": status,
                "plot_type": plot_type,
                "tier": tier,
                "png_base64": base64.b64encode(png_bytes).decode("ascii"),
                "png_path": None,
                "stderr": strip_diagnostic(
                    proc.stderr, "stderr", marked=proc.stderr_truncated
                ),
            }

    # ── Utility Info Tool ────────────────────────────────────────────

    @mcp.tool()
    def dartwork_mpl_info() -> str:
        """Get a summary of dartwork-mpl capabilities and available MCP features.

        Returns a structured overview of all available resources, tools,
        and design system rules for quick reference. Aligned with the
        design-language SSOT in ``asset/prompt/`` (00-index, 01-policy,
        02-anti-patterns, 03-recipes, 05-templates).
        """
        return catalog.info_payload()
