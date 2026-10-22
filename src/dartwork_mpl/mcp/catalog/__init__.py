"""Capability summary for the MCP ``dartwork_mpl_info`` tool.

``info_payload`` returns the tool's JSON reply. The live tool, resource and
prompt names are scanned from the wiring tables' source, so this slice
imports no other MCP slice.
"""

from .info import info_payload

__all__ = ["info_payload"]
