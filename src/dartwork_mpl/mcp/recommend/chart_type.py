"""Chart-type recommendation behind the ``suggest_chart_type`` tool.

Wraps ``dm.suggest_chart_type`` and normalises its label to a bundled
template stem so the returned template URIs always resolve.
"""

from pathlib import Path
from typing import Any

# The bundled plot templates (same location the template tools read).
_TEMPLATE_DIR = Path(__file__).parents[2] / "asset" / "prompt" / "05-templates"

# ``helpers.quality.suggest_chart_type`` speaks in *chart semantics*
# (``grouped_bar``, ``scatter_density``, ``hexbin``, …) while the bundled
# templates are keyed by canonical stems (``bar_grouped``, ``scatter``,
# …). This mapping normalizes recommender output to the template
# vocabulary before template URIs are built — without it, six of the
# recommender's output classes silently fell back to the wrong ``bar``
# template (or ``None``), breaking the advertised recommend →
# pull-template loop. Ids that already are template stems pass through.
_SUGGEST_TO_TEMPLATE: dict[str, str] = {
    "grouped_bar": "bar_grouped",
    "count_bar": "bar",
    "bar_line": "line",
    "multi_line": "line",
    "scatter_density": "scatter",
    "hexbin": "scatter",
}


def suggest(
    x_type: str, y_type: str | None, n_points: int, n_series: int
) -> dict[str, Any]:
    """The tool's reply: recommended template stem, basic/advanced URIs and rationale.

    ``basic_template_uri`` falls back to the ``bar`` template when no basic
    template has the recommended stem; ``advanced_template_uri`` is None when
    no advanced one exists.
    """
    from ...helpers import suggest_chart_type as _suggest

    raw = _suggest(
        x_type=x_type, y_type=y_type, n_points=n_points, n_series=n_series
    )
    # Normalize recommender semantics to the template vocabulary so
    # the returned id and URIs always resolve (see
    # ``_SUGGEST_TO_TEMPLATE``). The raw semantic label is kept in
    # the rationale when it differs.
    recommended = _SUGGEST_TO_TEMPLATE.get(raw, raw)

    basic_path = _TEMPLATE_DIR / f"{recommended}.py"
    advanced_path = _TEMPLATE_DIR / "advanced" / f"{recommended}.py"
    basic_uri = (
        f"dartwork-mpl://templates/{recommended}"
        if basic_path.exists()
        else "dartwork-mpl://templates/bar"
    )
    advanced_uri = (
        f"dartwork-mpl://templates/advanced/{recommended}"
        if advanced_path.exists()
        else None
    )

    semantic_note = (
        f" (recommender semantic: {raw!r} — rendered with the "
        f"{recommended!r} template)"
        if raw != recommended
        else ""
    )
    rationale = (
        f"x={x_type}, y={y_type}, n_points={n_points}, "
        f"n_series={n_series} → recommended: {recommended!r}"
        f"{semantic_note}. "
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
