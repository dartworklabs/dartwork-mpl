"""The ``compose_layered_plot`` reply: a starting template plus its annotation-layer checklist.

``_select`` ends in one ``ComposeOutcome`` variant; ``compose`` matches it
exhaustively into the legacy reply dict.
"""

from dataclasses import dataclass
from typing import Any, TypeAlias

from . import bundled

# Heuristic detection — purely lexical so it stays cheap and lets the agent
# see "yes, the advanced template already does this, no need to add it again."
_DETECT_PATTERNS = {
    "reference_line": ("axhline(", "axvline("),
    "event_window": ("axvspan(", "axhspan("),
    "value_labels": ("ax.text(", "ax.bar_label(", "dm.label_bars("),
    "trendline": ("np.polyfit", "polyfit"),
    "highlight": ("dc.amber5", "accent", 'marker="D"'),
    "callout": ("ax.annotate(", "arrowprops="),
    "gradient_palette": ("dm.cspace(", ".cspace("),
    "source_footnote": ("fig.text(", "Source:"),
}


@dataclass(frozen=True)
class Composed:
    """The template source of ``tier`` and the layers detected in it, in catalogue order."""

    tier: str
    code: str
    applied: tuple[str, ...]


@dataclass(frozen=True)
class InvalidTier:
    """The requested tier is neither ``advanced`` nor ``basic``."""

    tier: str


@dataclass(frozen=True)
class NoTemplate:
    """No template exists for the plot type in ``tier`` (after any fallback)."""

    tier: str


ComposeOutcome: TypeAlias = Composed | InvalidTier | NoTemplate


def _select(plot_type: str, tier: str) -> ComposeOutcome:
    """Read the template for ``tier``; ``advanced`` falls back to ``basic``."""
    if tier == "advanced":
        code = bundled.source(plot_type, advanced=True)
        if code is None:
            # Fall back to basic if advanced doesn't exist yet.
            code = bundled.source(plot_type)
            tier = "basic"
    elif tier == "basic":
        code = bundled.source(plot_type)
    else:
        return InvalidTier(tier)
    if code is None:
        return NoTemplate(tier)
    applied = tuple(
        layer
        for layer, patterns in _DETECT_PATTERNS.items()
        if any(p in code for p in patterns)
    )
    return Composed(tier, code, applied)


def compose(
    plot_type: str, layers: list[str] | None, tier: str
) -> dict[str, Any]:
    """Template source for ``tier`` with the requested layers marked applied or missing.

    ``advanced`` falls back to the basic tier when no advanced template
    exists; an unknown tier or plot type returns ``invalid_tier`` /
    ``unknown_template``. Layer detection is lexical over the source.
    """
    layers = list(layers or [])
    match _select(plot_type, tier):
        case InvalidTier(tier):
            return {
                "status": "invalid_tier",
                "tier": tier,
                "code": "",
                "layers": layers,
                "applied": [],
                "missing": [],
            }
        case NoTemplate(tier):
            available = bundled.names()
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
        case Composed(tier, code, applied):
            return {
                "status": "ok",
                "tier": tier,
                "code": code,
                "layers": layers,
                "applied": list(applied),
                "missing": [layer for layer in layers if layer not in applied],
            }
