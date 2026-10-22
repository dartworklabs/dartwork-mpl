"""The ``compose_layered_plot`` reply: a starting template plus its annotation-layer checklist."""

from typing import Any

from . import bundled


def compose(
    plot_type: str, layers: list[str] | None, tier: str
) -> dict[str, Any]:
    """Template source for ``tier`` with the requested layers marked applied or missing.

    ``advanced`` falls back to the basic tier when no advanced template
    exists; an unknown tier or plot type returns ``invalid_tier`` /
    ``unknown_template``. Layer detection is lexical over the source.
    """
    layers = list(layers or [])
    template_dir = bundled._TEMPLATE_DIR
    if tier == "advanced":
        path = bundled._resolve_template_path(plot_type, advanced=True)
        if path is None:
            # Fall back to basic if advanced doesn't exist yet.
            path = bundled._resolve_template_path(plot_type)
            tier = "basic"
    elif tier == "basic":
        path = bundled._resolve_template_path(plot_type)
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
