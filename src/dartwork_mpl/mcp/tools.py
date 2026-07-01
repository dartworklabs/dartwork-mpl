"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation, color manipulation,
code linting, and data validation.
"""

import json
import math
import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

import matplotlib.colors as mcolors
from fastmcp import FastMCP

__all__ = ["register_tools"]


def _version_surface() -> str:
    """Major.minor of the installed dartwork-mpl (e.g. ``"0.5"``).

    Derived from the distribution metadata so the advertised surface
    tracks the actual release instead of a hand-maintained literal that
    silently drifts — the same registry-derivation principle used for
    the tool/template catalog below.
    """
    try:
        ver = _pkg_version("dartwork-mpl")
    except PackageNotFoundError:
        return "unknown"
    parts = ver.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else ver


# ── Agentic-catalog discovery ────────────────────────────────────────
#
# ``dartwork_mpl_info`` advertises the live MCP surface (tools,
# resources, plot templates, primitive styles). Deriving these from the
# registry — the decorator source for tools/resources/prompts, the
# bundled asset dirs for templates/styles — rather than a hand-maintained
# literal means adding a tool or template can never silently drift the
# advertised catalog out of sync. (We scan the source instead of FastMCP
# private state, which moved between fastmcp 2.x and 3.x.)

_ASSET_DIR = Path(__file__).parent.parent / "asset"
_TEMPLATE_DIR = _ASSET_DIR / "prompt" / "05-templates"
_MPLSTYLE_DIR = _ASSET_DIR / "mplstyle"

# ``@mcp.tool()\n    def <name>(`` — empty- and keyword-arg forms.
_TOOL_DEF_RE = re.compile(
    r"@mcp\.tool\([^)]*\)\s*\n\s*def\s+(\w+)\s*\(", re.MULTILINE
)
# ``@mcp.resource("<uri>"...)`` — first string arg is the URI; ``\s*``
# spans the newline used by the multi-line (mime_type) form.
_RESOURCE_URI_RE = re.compile(r"""@mcp\.resource\(\s*["']([^"']+)["']""")
# ``@mcp.prompt(...)\n    def <name>(`` in prompts.py.
_PROMPT_DEF_RE = re.compile(
    r"@mcp\.prompt\([^)]*\)\s*\n\s*def\s+(\w+)\s*\(", re.MULTILINE
)


def _scan_source(filename: str, pattern: re.Pattern[str]) -> list[str]:
    """Return ``pattern`` captures from a sibling module's source.

    Returns ``[]`` when the file is unreadable rather than falling back
    to a stale literal — an empty catalog is honest; a drifting hardcoded
    one is not.
    """
    try:
        src = (Path(__file__).parent / filename).read_text(encoding="utf-8")
    except OSError:
        return []
    return pattern.findall(src)


def _discover_tool_names() -> list[str]:
    """Names of every ``@mcp.tool()`` in this module, in source order."""
    return _scan_source("tools.py", _TOOL_DEF_RE)


def _discover_resource_uris() -> list[str]:
    """URIs of every ``@mcp.resource(...)`` in resources.py."""
    return _scan_source("resources.py", _RESOURCE_URI_RE)


def _discover_prompt_names() -> list[str]:
    """Names of every ``@mcp.prompt()`` in prompts.py."""
    return _scan_source("prompts.py", _PROMPT_DEF_RE)


def _discover_plot_templates() -> list[str]:
    """Stems of the bundled ``05-templates/*.py`` plot templates."""
    return sorted(p.stem for p in _TEMPLATE_DIR.glob("*.py"))


def _discover_primitive_mplstyles() -> list[str]:
    """Stems of the bundled primitive ``*.mplstyle`` files."""
    return sorted(p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle"))


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
                    f"Failed to fetch {url}: {type(exc).__name__}: {exc}"
                ) from exc
        except Exception as exc:
            raise ValueError(
                f"Failed to fetch {url}: {type(exc).__name__}: {exc}"
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
        # Validate ``ratio`` up front: an out-of-[0, 1] or non-finite
        # weight extrapolates beyond the two endpoints, yielding RGB
        # outside [0, 1] and a malformed hex. Reject it with an
        # actionable message instead of leaking matplotlib's downstream
        # "RGBA values should be within 0-1 range" / NaN errors.
        if not math.isfinite(ratio):
            return (
                "Error: ratio must be a finite number between 0.0 and 1.0 "
                f"(weight of color1), got {ratio!r}."
            )
        if not 0.0 <= ratio <= 1.0:
            return (
                "Error: ratio must be between 0.0 and 1.0 "
                f"(weight of color1), got {ratio!r}."
            )
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
            variant only when the MCP client can read local files.
        timeout_seconds : float, optional
            Hard timeout for the subprocess. Default 30 s.

        Returns
        -------
        dict
            ``{"status": "ok"|"unknown_template"|"render_error"|
            "timeout", "plot_type": str, "png_base64": str|None,
            "png_path": str|None, "stderr": str}``.
        """
        import base64
        import subprocess
        import sys
        import tempfile
        import textwrap
        from pathlib import Path as _Path

        from .. import prompt as _prompt_mod

        template_dir = _prompt_mod._PROMPT_DIR / "05-templates"
        path = template_dir / f"{plot_type.lower()}.py"
        if not path.exists():
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

            try:
                proc = subprocess.run(
                    [sys.executable, "-c", runner],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                return {
                    "status": "timeout",
                    "plot_type": plot_type,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": (f"Render exceeded {exc.timeout}s timeout."),
                }

            pngs = sorted(out_base.parent.glob("*.png"))
            if proc.returncode != 0 or not pngs:
                return {
                    "status": "render_error",
                    "plot_type": plot_type,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": (proc.stderr or proc.stdout)[:2000],
                }

            png_bytes = pngs[0].read_bytes()
            if return_format == "path":
                # Copy out of the TemporaryDirectory before it
                # cleans up, but stash in a stable location the
                # caller can read.
                persistent = _Path(tempfile.gettempdir()) / (
                    f"dartwork-mpl-render-{plot_type}.png"
                )
                persistent.write_bytes(png_bytes)
                return {
                    "status": "ok",
                    "plot_type": plot_type,
                    "png_base64": None,
                    "png_path": str(persistent),
                    "stderr": proc.stderr.strip(),
                }
            return {
                "status": "ok",
                "plot_type": plot_type,
                "png_base64": base64.b64encode(png_bytes).decode("ascii"),
                "png_path": None,
                "stderr": proc.stderr.strip(),
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
            ``{"status": "ok"|"lint_blocked"|"exec_error"|"no_figure"
            |"timeout", "lint": list[...], "visual_warnings":
            list[...], "semantic_warnings": list[...], "stderr":
            str}``. ``visual_warnings`` items are ``{"severity",
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
          input from the web. The subprocess is sandboxed only in
          the sense that it cannot affect the caller's matplotlib
          state.
        """
        import json
        import subprocess
        import sys
        import textwrap

        from dartwork_mpl.lint import lint as _lint

        lint_issues = [
            {
                "rule_id": i.rule_id,
                "severity": i.severity,
                "line": i.line,
                "message": i.message,
                "fix_suggestion": i.fix_suggestion,
            }
            for i in _lint(code)
        ]
        critical = [i for i in lint_issues if i["severity"] == "critical"]
        if critical:
            return {
                "status": "lint_blocked",
                "lint": lint_issues,
                "visual_warnings": [],
                "stderr": (
                    "Critical lint issues must be fixed before execution: "
                    + ", ".join(str(i["rule_id"]) for i in critical)
                ),
            }

        runner = textwrap.dedent(
            """\
            import json
            import sys
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            ns: dict = {{"__name__": "__sandbox__"}}
            user_code = sys.stdin.read()
            try:
                exec(compile(user_code, "<agent-snippet>", "exec"), ns)
            except Exception as exc:
                json.dump(
                    {{
                        "status": "exec_error",
                        "exc_type": type(exc).__name__,
                        "exc_msg": str(exc),
                    }},
                    sys.stdout,
                )
                sys.exit(0)

            fig = ns.get({figure_var!r})
            if fig is None:
                # Fall back to whatever Pyplot tracked.
                figs = plt.get_fignums()
                if figs:
                    fig = plt.figure(figs[-1])
            if fig is None:
                json.dump(
                    {{"status": "no_figure"}},
                    sys.stdout,
                )
                sys.exit(0)

            from dartwork_mpl import validate_figure

            warnings = validate_figure(fig, quiet=True)

            # ── Semantic checks (only when a chart-type hint is given) ──
            # Catch plot choices that render fine but read poorly:
            # too many pie slices, too few scatter points, bars with
            # no value labels, etc.
            chart_hint = {chart_type_hint!r}
            semantic = []
            if chart_hint:
                hint = chart_hint.lower()
                ax_list = list(fig.axes)

                def _ax_has_text(ax):
                    # Annotation density proxy: number of Text artists
                    # the user explicitly added (excludes tick labels,
                    # title, axis labels which exist by default).
                    return any(
                        bool(getattr(t, "get_text", lambda: "")())
                        for t in getattr(ax, "texts", [])
                    )

                for i, ax in enumerate(ax_list):
                    label = f"axes[{{i}}]"
                    if hint == "pie":
                        wedges = [
                            p for p in ax.patches
                            if type(p).__name__ == "Wedge"
                        ]
                        if len(wedges) > 7:
                            semantic.append({{
                                "check_id": "pie_too_many_slices",
                                "message": (
                                    f"{{label}} has {{len(wedges)}} pie "
                                    "slices; >7 is hard to read. "
                                    "Consider bar_horizontal sorted "
                                    "by share."
                                ),
                            }})
                    elif hint == "scatter":
                        n_points = sum(
                            len(coll.get_offsets())
                            for coll in ax.collections
                            if hasattr(coll, "get_offsets")
                        )
                        if 0 < n_points < 5:
                            semantic.append({{
                                "check_id": "scatter_too_few_points",
                                "message": (
                                    f"{{label}} has only "
                                    f"{{n_points}} points; weak signal."
                                ),
                            }})
                    elif hint in ("bar", "bar_grouped",
                                  "bar_horizontal", "stacked_bar"):
                        bars = [
                            p for p in ax.patches
                            if type(p).__name__ == "Rectangle"
                        ]
                        if bars and not _ax_has_text(ax):
                            semantic.append({{
                                "check_id": "bar_missing_value_labels",
                                "message": (
                                    f"{{label}} has {{len(bars)}} bars "
                                    "but no value labels — readers will "
                                    "have to eyeball the y-axis."
                                ),
                            }})
                    elif hint == "line":
                        if not ax.lines:
                            semantic.append({{
                                "check_id": "line_no_lines",
                                "message": (
                                    f"{{label}} declared as a line chart "
                                    "but has no Line2D artists."
                                ),
                            }})
                    elif hint == "histogram":
                        bars = [
                            p for p in ax.patches
                            if type(p).__name__ == "Rectangle"
                        ]
                        if bars and len(bars) < 10:
                            semantic.append({{
                                "check_id": "histogram_too_few_bins",
                                "message": (
                                    f"{{label}} has only {{len(bars)}} "
                                    "bins; consider more for a smoother "
                                    "shape (10 to 50 is typical)."
                                ),
                            }})

            json.dump(
                {{
                    "status": "ok",
                    "visual_warnings": [
                        {{
                            "severity": w.severity.name
                            if hasattr(w.severity, "name")
                            else str(w.severity),
                            "check_id": w.check_id,
                            "message": w.message,
                            "detail": w.detail,
                        }}
                        for w in warnings
                    ],
                    "semantic_warnings": semantic,
                }},
                sys.stdout,
            )
            """
        ).format(figure_var=figure_var, chart_type_hint=chart_type_hint)

        try:
            proc = subprocess.run(
                [sys.executable, "-c", runner],
                input=code,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "status": "timeout",
                "lint": lint_issues,
                "visual_warnings": [],
                "stderr": f"Subprocess exceeded {exc.timeout}s timeout.",
            }

        stderr = proc.stderr.strip()
        try:
            payload: dict[str, Any] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {
                "status": "exec_error",
                "lint": lint_issues,
                "visual_warnings": [],
                "stderr": stderr or proc.stdout[:1000],
            }

        payload["lint"] = lint_issues
        payload.setdefault("visual_warnings", [])
        # Only surface ``semantic_warnings`` when a hint was supplied —
        # otherwise the key is dropped so the response shape stays
        # backwards-compatible for callers that don't pass the hint.
        if chart_type_hint is None:
            payload.pop("semantic_warnings", None)
        else:
            payload.setdefault("semantic_warnings", [])
        payload["stderr"] = stderr
        return payload

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

        # Defensive guard: several legacy validators index/``len()`` fields
        # without a type check, so a present-but-wrong-type field (e.g. a
        # scalar where a list is expected) or a non-dict top-level payload
        # would leak a raw ``TypeError``/``KeyError`` to the MCP client.
        # Convert those into an actionable structured-error message.
        try:
            return validator(data)
        except (TypeError, KeyError, ValueError, AttributeError) as exc:
            return (
                f"Invalid data structure for '{plot_type}': "
                f"{type(exc).__name__}: {exc}. Check that each field has "
                f"the expected type (e.g. lists where lists are expected) "
                f"and that the top-level payload is a JSON object."
            )

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
            ``advanced_template_uri`` is ``None`` when no tier-2 version
            exists yet for the recommended plot type.
        """
        from .. import prompt as _prompt_mod
        from .. import suggest_chart_type as _suggest

        recommended = _suggest(
            x_type=x_type, y_type=y_type, n_points=n_points, n_series=n_series
        )

        # Map suggest output to a template id where possible.
        template_dir = _prompt_mod._PROMPT_DIR / "05-templates"
        basic_path = template_dir / f"{recommended}.py"
        advanced_path = template_dir / "advanced" / f"{recommended}.py"
        basic_uri = (
            f"dartwork-mpl://template/{recommended}"
            if basic_path.exists()
            else "dartwork-mpl://template/bar"
        )
        advanced_uri = (
            f"dartwork-mpl://template/advanced/{recommended}"
            if advanced_path.exists()
            else None
        )

        rationale = (
            f"x={x_type}, y={y_type}, n_points={n_points}, "
            f"n_series={n_series} → recommended: {recommended!r}. "
            "Tier-1 templates show the minimal API call; tier-2 (advanced) "
            "templates add reference lines, value labels, narrative title, "
            "and source footnote — copy the advanced version when you "
            "want the agent's generated plot to read like a finished "
            "report figure."
        )
        return {
            "recommended": recommended,
            "basic_template_uri": basic_uri,
            "advanced_template_uri": advanced_uri,
            "rationale": rationale,
        }

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
        from .. import prompt as _prompt_mod

        layers = list(layers or [])
        template_dir = _prompt_mod._PROMPT_DIR / "05-templates"
        if tier == "advanced":
            path = template_dir / "advanced" / f"{plot_type.lower()}.py"
            if not path.exists():
                # Fall back to basic if advanced doesn't exist yet.
                path = template_dir / f"{plot_type.lower()}.py"
                tier = "basic"
        elif tier == "basic":
            path = template_dir / f"{plot_type.lower()}.py"
        else:
            return {
                "status": "invalid_tier",
                "tier": tier,
                "code": "",
                "layers": layers,
                "applied": [],
                "missing": [],
            }

        if not path.exists():
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
            "highlight": ("dc.sunset5", "accent", 'marker="D"'),
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
            Hard subprocess timeout. Default 30 s.

        Returns
        -------
        dict
            ``{"status": "ok"|"fell_back"|"unknown_template"|
            "render_error"|"timeout", "plot_type": str, "tier": str,
            "png_base64": str|None, "png_path": str|None,
            "stderr": str}``.
        """
        import base64
        import subprocess
        import sys
        import tempfile
        import textwrap
        from pathlib import Path as _Path

        from .. import prompt as _prompt_mod

        template_dir = _prompt_mod._PROMPT_DIR / "05-templates"
        advanced_path = template_dir / "advanced" / f"{plot_type.lower()}.py"
        basic_path = template_dir / f"{plot_type.lower()}.py"

        if advanced_path.exists():
            path = advanced_path
            tier = "advanced"
            fell_back = False
        elif basic_path.exists():
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

            try:
                proc = subprocess.run(
                    [sys.executable, "-c", runner],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                return {
                    "status": "timeout",
                    "plot_type": plot_type,
                    "tier": tier,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": f"Render exceeded {exc.timeout}s timeout.",
                }

            pngs = sorted(out_base.parent.glob("*.png"))
            if proc.returncode != 0 or not pngs:
                return {
                    "status": "render_error",
                    "plot_type": plot_type,
                    "tier": tier,
                    "png_base64": None,
                    "png_path": None,
                    "stderr": (proc.stderr or proc.stdout)[:2000],
                }

            png_bytes = pngs[0].read_bytes()
            status = "fell_back" if fell_back else "ok"
            if return_format == "path":
                persistent = _Path(tempfile.gettempdir()) / (
                    f"dartwork-mpl-render-advanced-{plot_type}.png"
                )
                persistent.write_bytes(png_bytes)
                return {
                    "status": status,
                    "plot_type": plot_type,
                    "tier": tier,
                    "png_base64": None,
                    "png_path": str(persistent),
                    "stderr": proc.stderr.strip(),
                }
            return {
                "status": status,
                "plot_type": plot_type,
                "tier": tier,
                "png_base64": base64.b64encode(png_bytes).decode("ascii"),
                "png_path": None,
                "stderr": proc.stderr.strip(),
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
        # Resolve composite preset names dynamically from the bundled
        # presets.json so this stays in sync with the actual style
        # registry.
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

        return json.dumps(
            {
                "name": "dartwork-mpl",
                "version_surface": _version_surface(),
                "description": "Publication-quality matplotlib design system",
                "design_rules": {
                    "width_aspect": (
                        "Use plt.subplots(figsize=dm.figsize('13cm', 'standard')). "
                        "width accepts unit strings (cm/in/mm/pt) or Length "
                        "values (dm.cm/inch/mm/pt, dm.col1, dm.col2); bare "
                        "int/float are rejected. aspect is one of "
                        "{square, portrait, standard, golden, wide, "
                        "cinema} or a positive float."
                    ),
                    "max_width": "17 cm",
                    "layout": (
                        "Call dm.simple_layout(fig) after plotting. "
                        "Default margin=0 snaps content flush to the "
                        "figure edge; pass margin='2%' or dm.mm(2) for "
                        "a buffer. dm.auto_layout is a deprecated alias. "
                        "tight_layout() is forbidden."
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
                "resources": _discover_resource_uris(),
                "tools": _discover_tool_names(),
                "prompts": _discover_prompt_names(),
                "style_presets": {
                    "composite": composite_presets,
                    "primitive_mplstyle": _discover_primitive_mplstyles(),
                },
                "plot_templates": _discover_plot_templates(),
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
