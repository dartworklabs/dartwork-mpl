"""The ``validate_plot_data`` tool's behaviour: dispatch to a shape parser or the v1 report.

``validate_data`` is the edge: it decodes the JSON, picks the plot type's
parser and turns its ``PlotDataVerdict`` into the tool's reply text
(``reply``); the ``"✅ ..."`` success line exists only there.
"""

import json

from .repair import build_data_repair_report, serialize_data_repair_report
from .validators import PARSERS, Invalid, Malformed, Parsed, PlotDataVerdict


def reply(plot_type: str, verdict: PlotDataVerdict) -> str:
    """The tool's message for ``verdict``; ``plot_type`` is echoed as requested."""
    match verdict:
        case Parsed(label):
            return f"✅ Data structure valid for {label}."
        case Invalid(issues):
            return "\n".join(issues)
        case Malformed(error_type, detail):
            return (
                f"Invalid data structure for '{plot_type}': "
                f"{error_type}: {detail}. Check that each field has "
                f"the expected type (e.g. lists where lists are expected) "
                f"and that the top-level payload is a JSON object."
            )


def validate_data(plot_type: str, data_json: str, report: bool) -> str:
    """Validate ``data_json`` against ``plot_type``'s expected shape; the tool's exact reply.

    With ``report`` the reply is the serialized version-1 data-repair report
    (``plot_type`` lower-cased, recognised when a parser exists). Otherwise
    it is the parser's verdict as text, or a fixed message for invalid JSON,
    an unknown plot type, or a payload whose fields have the wrong types.
    Never raises for any string input.
    """
    if report:
        normalized = plot_type.lower()
        return serialize_data_repair_report(
            build_data_repair_report(
                normalized, data_json, recognized=normalized in PARSERS
            )
        )

    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    parse = PARSERS.get(plot_type.lower())
    if parse is None:
        return (
            f"No validator for '{plot_type}'. Available: {list(PARSERS.keys())}"
        )
    return reply(plot_type, parse(data))
