"""The ``dartwork_mpl_info`` payload: capabilities, design rules and the live MCP surface."""

import json
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .discovery import (
    _discover_plot_templates,
    _discover_primitive_mplstyles,
    _discover_prompt_names,
    _discover_resource_uris,
    _discover_tool_names,
)


def _version_surface() -> str:
    """Major.minor of the installed dartwork-mpl (e.g. ``"0.5"``).

    Derived from the distribution metadata so the advertised surface
    tracks the actual release instead of a hand-maintained literal —
    the same registry-derivation principle used for the tool/template
    catalog below. Note this reflects the *installed* metadata, so an
    editable dev checkout reports the version captured at install time
    until it is reinstalled.
    """
    try:
        ver = _pkg_version("dartwork-mpl")
    except PackageNotFoundError:
        return "unknown"
    parts = ver.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else ver


def info_payload() -> str:
    """The tool's JSON reply (2-space indent).

    Composite presets come from the style slice's registry (the bundled
    ``presets.json``, loaded once when ``dartwork_mpl`` is imported); tools,
    resources, prompts, templates and primitive styles come from
    ``discovery``.
    """
    # The style slice's preset registry, so this stays in sync with the
    # presets ``dm.style.use`` accepts.
    from ...style import style as shipped_style

    composite_presets = sorted(shipped_style.presets_dict())

    return json.dumps(
        {
            "name": "dartwork-mpl",
            "version_surface": _version_surface(),
            "description": "Publication-quality matplotlib design system",
            "design_system_apis": {
                "semantic_tokens": (
                    "dm.tokens.fs_*/lw_*/space/scatter_size + as_dict()/version()"
                    " - preset-tracking design tokens"
                ),
                "locale_formatters": (
                    "dm.format_axis_myriad (East-Asian 10^4 labels), "
                    "dm.format_axis_year (two-digit year + suffix)"
                ),
                "grid_sizing": (
                    "dm.figsize_grid(panel_width, aspect, ncols=, nrows=, gap=)"
                    " - per-panel physical sizing"
                ),
                "accessibility": (
                    "dm.validate_figure now includes TEXT_CONTRAST / MIN_FONT_SIZE / "
                    "GRAYSCALE_SAFETY checks"
                ),
            },
            "design_rules": {
                "width_aspect": (
                    "Use native plt.subplots or plt.figure with figsize=dm.figsize(...), "
                    "including GridSpec/nested GridSpec. "
                    "width accepts unit strings (cm/in/mm/pt) or Length "
                    "values (dm.cm/inch/mm/pt, dm.col1, dm.col2); bare "
                    "int/float are rejected. aspect is one of "
                    "{square, portrait, standard, golden, wide, "
                    "cinema} or a positive height/width ratio, unit-string height "
                    "or Length height. Explicit width and height are freely chosen. "
                    "Explicit dimensions/style and venue/template constraints > "
                    "prior project context > purpose defaults: paper -> scientific; "
                    "report/document/dashboard -> report; talk/slides -> presentation. "
                    "Paper 9/17 cm and report 13-17 cm are draft candidates, not standards/caps. "
                    "Slide ratio/full-slide/inset and panel complexity inform initial size. "
                    "Ask one short question only for material ambiguity; reuse known context. "
                    "For quick drafts state provisional preset/size. "
                    "Use -kr for Korean plot text only. Geometry-only edits retain preset/data/style."
                ),
                "max_width": (
                    "No API maximum; 17 cm is a page-fit lint reference. "
                    "Retain explicit user or template dimensions."
                ),
                "layout": (
                    "Call dm.simple_layout(fig) after plotting. "
                    "Default margin=0 snaps content flush to the "
                    "figure edge; pass margin='2%' or dm.mm(2) for "
                    "a buffer. dm.auto_layout was removed in 0.5.4; use dm.simple_layout. "
                    "tight_layout() is forbidden."
                ),
                "default_dpi": "Controlled by the active style preset.",
                "font": (
                    "Presets supply defaults; explicit scoped user values win. "
                    "dm.fs(n)/dm.lw(n) add n pt to global font.size/lines.linewidth; "
                    "dm.fw(n) adds 100*n weight units. For one more step use the "
                    "current artist getter plus delta; retain exact absolute values. "
                    "Literal-size/width warnings are advisory: review/report them, "
                    "never erase explicit intent or hide warnings. Apply the preset "
                    "before retained overrides and local edits. Change only requested "
                    "artist properties; preserve data, unrelated style, canvas, legend "
                    "and preset. Axis labels differ from tick labels; avoid global "
                    "font changes for label-only edits. Native setters/properties/help "
                    "or official installed-version docs expose further properties. "
                    "The 18 templates are starters, not limits on native chart types."
                ),
                "save_format": (
                    "Use dm.save_formats(fig, 'name', formats=('png','pdf'), "
                    "dpi=300) for scripts or dm.save_and_show(fig, 'name') "
                    "for notebooks. Keep bbox_inches=None (the default) for exact "
                    "physical canvas size; tight crops to content. DPI controls raster "
                    "density; PNG sizes quantize to whole pixels."
                ),
                "color": (
                    "Use named palettes (oc.*, tw.*, dc.*, md.*, "
                    "ad.*, cu.*, pr.*) for defaults; retain user-specified hex "
                    "or native matplotlib colors. dc.* construction uses OKLab L, "
                    "OKLCH C/h, and ΔEOK. Modeled relative Y is an "
                    "optional shipped-output compatibility lock, not an "
                    "authoring space or a display measurement. "
                    "CIELAB/CIEDE2000 and named CVD simulations are "
                    "model-specific diagnostics; WCAG contrast "
                    "luminance is separate."
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
