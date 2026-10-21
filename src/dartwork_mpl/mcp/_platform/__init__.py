"""Business-agnostic mechanism shared by the MCP slices (ADR 0005 platform unit).

Two mechanisms live here and nothing else: bounded capture of a trusted child
process (``process``: ``run_child``, the ``diagnostic`` / ``strip_diagnostic``
log views and ``publish_png``), and confinement of bundled asset IDs to regular
files under their roots (``assets``: ``resolve_template_path``,
``resolve_style_path``). Neither knows which tool calls it. This unit imports
no MCP slice; slices import only the names below.
"""

from .assets import resolve_style_path, resolve_template_path
from .process import diagnostic, publish_png, run_child, strip_diagnostic

__all__ = [
    "diagnostic",
    "publish_png",
    "resolve_style_path",
    "resolve_template_path",
    "run_child",
    "strip_diagnostic",
]
