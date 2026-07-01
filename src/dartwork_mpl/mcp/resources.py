"""MCP Resources for dartwork-mpl guides.

This module defines resources that expose dartwork-mpl usage guides,
color palettes, fonts, styles, and plot templates
through the Model Context Protocol.
"""

import inspect
import json
from pathlib import Path

import matplotlib.colors as mcolors
from fastmcp import FastMCP
from matplotlib import font_manager

from ..util import get_prompt

__all__ = ["register_resources"]

# Path to bundled mplstyle files
_MPLSTYLE_DIR = Path(__file__).parent.parent / "asset" / "mplstyle"

# Path to the SSOT prompt directory (00-index, 01-policy, 03-recipes,
# 05-templates/, _legacy/, ...)
_PROMPT_DIR = Path(__file__).parent.parent / "asset" / "prompt"
_TEMPLATE_DIR = _PROMPT_DIR / "05-templates"


def register_resources(mcp: FastMCP) -> None:
    """
    Register all resources with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register resources with.
    """

    # ── Guide Resources ──────────────────────────────────────────────
    #
    # 0.4 SSOT layout (asset/prompt/00-index, 01-policy, 02-anti-patterns,
    # 03-recipes, 05-templates, _legacy). The legacy general-guide /
    # layout-guide URIs are retained for back-compat — they delegate to
    # 00-index and to a layout-focused passage of 01-policy respectively.

    @mcp.resource("dartwork-mpl://guide/agent-entry")
    def agent_entry() -> str:
        """Agent entry point — decision tree + always-true facts."""
        return get_prompt("00-index")

    @mcp.resource("dartwork-mpl://guide/policy")
    def policy() -> str:
        """0.4 policy: width, aspect, layout, color, font, save."""
        return get_prompt("01-policy")

    @mcp.resource(
        "dartwork-mpl://guide/anti-patterns", mime_type="application/yaml"
    )
    def anti_patterns() -> str:
        """Machine-readable anti-pattern catalog (the lint engine source)."""
        path = _PROMPT_DIR / "02-anti-patterns.yaml"
        return path.read_text(encoding="utf-8")

    @mcp.resource("dartwork-mpl://guide/recipes")
    def recipes() -> str:
        """Intent → function-call cookbook."""
        return get_prompt("03-recipes")

    @mcp.resource("dartwork-mpl://guide/general-guide")
    def general_guide() -> str:
        """DEPRECATED alias for guide/agent-entry."""
        return get_prompt("00-index")

    @mcp.resource("dartwork-mpl://guide/layout-guide")
    def layout_guide() -> str:
        """DEPRECATED alias for guide/policy (kept for 0.3 clients)."""
        return get_prompt("01-policy")

    @mcp.resource("dartwork-mpl://guide/migration")
    def migration_guide() -> str:
        """0.3 → 0.4 migration pointer.

        The full migration guide lives at ``docs/migration.md`` and is
        rendered at the GitHub Pages URL below. The bundled stub that
        used to back this resource was removed in T5 of the AI-readiness
        roadmap (see ``docs/superpowers/specs/2026-05-01-ai-readiness-0.5-roadmap.md``)
        so that the prompt corpus has a single source of truth in the
        rendered docs rather than a stub-and-fallback split.
        """
        return (
            "0.3 → 0.4 migration guide: "
            "https://dartworklabs.github.io/dartwork-mpl/migration.html\n\n"
            "For an automated rewrite, call the migrate_legacy_code MCP "
            "tool (or dm.migrate_legacy_code in Python)."
        )

    # ── API Reference ────────────────────────────────────────────────

    @mcp.resource("dartwork-mpl://api/index")
    def api_index() -> str:
        """List of public dartwork-mpl callables (from __all__)."""
        from .. import __all__ as public_names

        return json.dumps(sorted(public_names), indent=2)

    @mcp.resource("dartwork-mpl://api/{name}")
    def api_function(name: str) -> str:
        """Signature + first paragraph of docstring for a public name.

        Parameters
        ----------
        name : str
            A name from ``dartwork_mpl.__all__``.
        """
        import dartwork_mpl as dm

        if not hasattr(dm, name):
            return f"No public name {name!r}. See dartwork-mpl://api/index."
        obj = getattr(dm, name)
        try:
            sig = str(inspect.signature(obj))
        except (TypeError, ValueError):
            sig = "(...)"
        doc = inspect.getdoc(obj) or ""
        first_para = doc.split("\n\n", 1)[0]
        return f"{name}{sig}\n\n{first_para}"

    # ── Palette Resources ────────────────────────────────────────────

    @mcp.resource("dartwork-mpl://palette/colors")
    def palette_colors() -> str:
        """Get the full list of dartwork-mpl registered colors with hex codes.

        Returns a JSON object where keys are color names (e.g. 'dc.trustworthy0')
        and values are hex codes. Only dartwork-mpl prefixed colors are included:
        dc.*, tw.*, md.*, ad.*, cu.*, pr.*, oc.*
        """
        from ..colors._loader import COLOR_LIBRARIES

        prefixes = [prefix for _key, prefix, _fn, _label in COLOR_LIBRARIES]
        colors = {
            k: mcolors.to_hex(v)
            for k, v in mcolors.get_named_colors_mapping().items()
            if any(k.startswith(prefix) for prefix in prefixes)
        }
        return json.dumps(colors, indent=2)

    @mcp.resource("dartwork-mpl://palette/fonts")
    def palette_fonts() -> str:
        """Get a sorted list of all fonts available to matplotlib."""
        fonts = sorted({f.name for f in font_manager.fontManager.ttflist})
        return json.dumps(fonts, indent=2)

    # ── Style Preset Resources ───────────────────────────────────────

    @mcp.resource("dartwork-mpl://styles/list")
    def styles_list() -> str:
        """List all available dartwork-mpl mplstyle presets.

        Returns a JSON array of preset names (without .mplstyle extension)
        that can be queried individually via dartwork-mpl://styles/{preset}.
        """
        if not _MPLSTYLE_DIR.exists():
            return json.dumps([])
        presets = sorted([p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle")])
        return json.dumps(presets, indent=2)

    @mcp.resource("dartwork-mpl://styles/{preset}")
    def style_preset(preset: str) -> str:
        """Get the content of a specific dartwork-mpl mplstyle preset.

        Parameters
        ----------
        preset : str
            Name of the style preset (e.g. 'dmpl', 'font-scientific',
            'theme-dark', 'lang-kr', 'spine-no').

        Available presets: base, dmpl, dmpl_light, font-minimal,
        font-poster, font-presentation, font-report, font-scientific,
        font-web, lang-kr, spine-no, spine-yes, theme-dark, theme-minimal.
        """
        style_file = _MPLSTYLE_DIR / f"{preset}.mplstyle"
        if not style_file.exists():
            available = sorted(
                [p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle")]
            )
            return f"Style preset '{preset}' not found. Available presets: {available}"
        return style_file.read_text(encoding="utf-8")

    # ── Plot Template Resources ──────────────────────────────────────
    #
    # Templates live in asset/prompt/05-templates/{plot_type}.py and
    # are the single source of truth — the lint engine and drift CI
    # read the same files.

    @mcp.resource("dartwork-mpl://templates/list")
    def templates_list() -> str:
        """List all available plot template types."""
        names = sorted(p.stem for p in _TEMPLATE_DIR.glob("*.py"))
        return json.dumps(names, indent=2)

    @mcp.resource("dartwork-mpl://templates/{plot_type}")
    def plot_templates(plot_type: str) -> str:
        """Get the bundled Python template for a specific plot type.

        Available types: bar, bar_grouped, bar_horizontal, boxplot,
        contour, heatmap, histogram, line, pie, plot_3d, polar,
        scatter, small_multiples, stacked_bar, tornado, twin_axis,
        violin, waterfall.
        """
        path = _TEMPLATE_DIR / f"{plot_type.lower()}.py"
        if not path.exists():
            available = sorted(p.stem for p in _TEMPLATE_DIR.glob("*.py"))
            return f"No template for {plot_type!r}. Available: {available}"
        return path.read_text(encoding="utf-8")

    @mcp.resource("dartwork-mpl://templates/advanced/{plot_type}")
    def plot_templates_advanced(plot_type: str) -> str:
        """Get the bundled tier-2 (advanced) template for a plot type.

        The advanced tier adds synthetic data, reference lines, value
        labels, a narrative title, and a source footnote. Falls back to
        the basic template if no advanced version exists yet — so the
        ``suggest_chart_type`` / ``create_plot`` URIs always resolve.
        """
        advanced = _TEMPLATE_DIR / "advanced" / f"{plot_type.lower()}.py"
        if advanced.exists():
            return advanced.read_text(encoding="utf-8")
        basic = _TEMPLATE_DIR / f"{plot_type.lower()}.py"
        if basic.exists():
            return basic.read_text(encoding="utf-8")
        available = sorted(p.stem for p in _TEMPLATE_DIR.glob("*.py"))
        return f"No template for {plot_type!r}. Available: {available}"
