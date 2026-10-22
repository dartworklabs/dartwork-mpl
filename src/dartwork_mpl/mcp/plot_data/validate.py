"""The ``validate_plot_data`` tool's behaviour: dispatch to a shape validator or the v1 report."""

import json

from .repair import build_data_repair_report, serialize_data_repair_report
from .validators import (
    _validate_bar,
    _validate_bar_grouped,
    _validate_bar_horizontal,
    _validate_boxplot,
    _validate_contour,
    _validate_heatmap,
    _validate_histogram,
    _validate_line,
    _validate_pie,
    _validate_plot_3d,
    _validate_polar,
    _validate_scatter,
    _validate_small_multiples,
    _validate_stacked_bar,
    _validate_tornado,
    _validate_twin_axis,
    _validate_violin,
    _validate_waterfall,
)


def validate_data(plot_type: str, data_json: str, report: bool) -> str:
    """Validate ``data_json`` against ``plot_type``'s expected shape; the tool's exact reply.

    With ``report`` the reply is the serialized version-1 data-repair report
    (``plot_type`` lower-cased, recognised when a validator exists). Otherwise
    it is the validator's message, or a fixed message for invalid JSON, an
    unknown plot type, or a payload whose fields have the wrong types. Never
    raises for any string input.
    """
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

    if report:
        normalized = plot_type.lower()
        return serialize_data_repair_report(
            build_data_repair_report(
                normalized, data_json, recognized=normalized in validators
            )
        )

    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

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
