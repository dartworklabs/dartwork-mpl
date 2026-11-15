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
    # The same files the bundled skill ships, read through dm.guide.

    @mcp.resource("dartwork-mpl://guide/agent-entry")
    def agent_entry() -> str:
        """The agent skill (SKILL.md): preset, size, layout, save, data, review."""
        return guides.guide_text("skill")

    @mcp.resource(
        "dartwork-mpl://guide/anti-patterns", mime_type="application/yaml"
    )
    def anti_patterns() -> str:
        """Machine-readable anti-pattern catalog (the lint engine source)."""
        return guides.guide_text("anti-patterns")

    @mcp.resource("dartwork-mpl://guide/recipes")
    def recipes() -> str:
        """Native customisation recipes: lines, spines, canvases, regions."""
        return guides.guide_text("recipes")

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
        from ..color import LIBRARIES

        return colors.palette(LIBRARIES)

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
    # Templates are read through dm.guide (template/<id>,
    # template/advanced/<id>), the files the skill points at.

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

        The advanced tier adds synthetic data, reference lines and value
        labels; neither tier draws a title or source note. Falls back to
        the basic template if no advanced version exists yet. Both
        tiers use the same confined bare-ID lookup; invalid IDs return
        the existing not-found response.
        """
        return templates.advanced_template_source(plot_type)
