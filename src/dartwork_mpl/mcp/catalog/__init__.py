"""What the MCP server and its environment offer: ``dartwork_mpl_info`` and the font list.

``info_payload`` returns the ``dartwork_mpl_info`` JSON reply; the live tool,
resource and prompt names are scanned from the wiring tables' source, so
this slice imports no other MCP slice. ``font_names`` is the
``dartwork-mpl://palette/fonts`` reply.
"""

from .fonts import font_names
from .info import info_payload

__all__ = ["font_names", "info_payload"]
