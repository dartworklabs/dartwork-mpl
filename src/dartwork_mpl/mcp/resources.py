"""MCP Resources for dartwork-mpl guides.

This module defines resources that expose dartwork-mpl usage guides,
color palettes, fonts, styles, and plot templates
through the Model Context Protocol.
"""

from fastmcp import FastMCP

from . import catalog, colors, guides, templates

__all__ = ["register_resources"]

_MODELED_Y_LIMITATION = (
    "Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 "
    "sRGB; it is not a measurement of a particular display, perceived "
    "brightness, or OKLab `L`."
)


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
    # SSOT layout (asset/prompt/00-index, 01-policy, 02-anti-patterns,
    # 03-recipes, 05-templates, _legacy).

    @mcp.resource("dartwork-mpl://guide/agent-entry")
    def agent_entry() -> str:
        """Agent entry point — decision tree + always-true facts."""
        return guides.guide_text("00-index")

    @mcp.resource("dartwork-mpl://guide/policy")
    def policy() -> str:
        """Policy: layout plus the OKLab/OKLCH color-metric split."""
        return guides.guide_text("01-policy")

    @mcp.resource(
        "dartwork-mpl://guide/anti-patterns", mime_type="application/yaml"
    )
    def anti_patterns() -> str:
        """Machine-readable anti-pattern catalog (the lint engine source)."""
        return guides.anti_pattern_catalog()

    @mcp.resource("dartwork-mpl://guide/recipes")
    def recipes() -> str:
        """Intent → function-call cookbook."""
        return guides.guide_text("03-recipes")

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
        return guides.migration_pointer()

    # ── API Reference ────────────────────────────────────────────────

    @mcp.resource("dartwork-mpl://api/index")
    def api_index() -> str:
        """List of public dartwork-mpl callables (from __all__)."""
        from .. import __all__ as public_names

        return guides.api_index(public_names)

    @mcp.resource("dartwork-mpl://api/{name}")
    def api_function(name: str) -> str:
        """Signature + first paragraph of docstring for a public name.

        Parameters
        ----------
        name : str
            A name from ``dartwork_mpl.__all__``.
        """
        import dartwork_mpl as dm

        return guides.api_entry(dm, name)

    # ── Palette Resources ────────────────────────────────────────────

    @mcp.resource("dartwork-mpl://palette/colors")
    def palette_colors() -> str:
        """Get the registered colors, whose ``dc.*`` values stay exact.

        The JSON keys are names such as ``dc.blue6`` and the values are hex
        codes. It includes the prefixes dc.*, tw.*, md.*, ad.*, cu.*, pr.*,
        and oc.*. Modeled relative Y is an optional shipped-output
        compatibility lock, not a second construction space.

        Modeled relative CIE Y (`relative_y`) is calculated from nominal D65
        sRGB; it is not a measurement of a particular display, perceived
        brightness, or OKLab `L`.
        """
        from .._colors._loader import COLOR_LIBRARIES

        return colors.palette(COLOR_LIBRARIES)

    @mcp.resource("dartwork-mpl://palette/fonts")
    def palette_fonts() -> str:
        """Get a sorted list of all fonts available to matplotlib."""
        return catalog.font_names()

    # ── Style Preset Resources ───────────────────────────────────────

    @mcp.resource("dartwork-mpl://styles/list")
    def styles_list() -> str:
        """List all available dartwork-mpl mplstyle presets.

        Returns a JSON array of preset names (without .mplstyle extension)
        that can be queried individually via dartwork-mpl://styles/{preset}.
        """
        return templates.style_list()

    @mcp.resource("dartwork-mpl://styles/{preset}")
    def style_preset(preset: str) -> str:
        """Read a bundled style by a case-preserving bare ID, or return not-found text.

        Parameters
        ----------
        preset : str
            Name of the style preset (e.g. 'dmpl', 'font-scientific',
            'theme-dark', 'lang-kr', 'spine-no').

        Available presets: base, dmpl, dmpl_light, font-minimal,
        font-poster, font-presentation, font-report, font-scientific,
        font-web, lang-kr, spine-no, spine-yes, theme-dark, theme-minimal.
        """
        return templates.style_source(preset)

    # ── Plot Template Resources ──────────────────────────────────────
    #
    # Templates live in asset/prompt/05-templates/{plot_type}.py and
    # are the single source of truth — the lint engine and drift CI
    # read the same files.

    @mcp.resource("dartwork-mpl://templates/list")
    def templates_list() -> str:
        """List all available plot template types."""
        return templates.template_list()

    @mcp.resource("dartwork-mpl://templates/{plot_type}")
    def plot_templates(plot_type: str) -> str:
        """Read a bundled template by case-insensitive bare ID, or not-found text.

        Available types: bar, bar_grouped, bar_horizontal, boxplot,
        contour, heatmap, histogram, line, pie, plot_3d, polar,
        scatter, small_multiples, stacked_bar, tornado, twin_axis,
        violin, waterfall.
        """
        return templates.template_source(plot_type)

    @mcp.resource("dartwork-mpl://templates/advanced/{plot_type}")
    def plot_templates_advanced(plot_type: str) -> str:
        """Get the bundled tier-2 (advanced) template for a plot type.

        The advanced tier adds synthetic data, reference lines, value
        labels, a narrative title, and a source footnote. Falls back to
        the basic template if no advanced version exists yet — so the
        ``suggest_chart_type`` / ``create_plot`` URIs always resolve. Both
        tiers use the same confined bare-ID lookup; invalid IDs return
        the existing not-found response.
        """
        return templates.advanced_template_source(plot_type)
