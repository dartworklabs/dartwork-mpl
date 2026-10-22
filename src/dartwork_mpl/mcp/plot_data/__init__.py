"""Plot-data validation for the MCP ``validate_plot_data`` tool.

``validate_data`` checks whether a JSON payload fits a bundled plot
template's expected data shape and returns the tool's reply.
``build_data_repair_report`` builds the version-1 review report (pure:
proposals never apply or execute changes) and ``serialize_data_repair_report``
encodes it as the tool's JSON string.
"""

from .repair import (
    DataRepairReport,
    build_data_repair_report,
    serialize_data_repair_report,
)
from .validate import validate_data

__all__ = [
    "DataRepairReport",
    "build_data_repair_report",
    "serialize_data_repair_report",
    "validate_data",
]
