"""Chart-type recommendation for the MCP ``suggest_chart_type`` tool.

``suggest`` returns the recommended template stem with the template URIs the
agent pulls next.
"""

from .chart_type import suggest

__all__ = ["suggest"]
