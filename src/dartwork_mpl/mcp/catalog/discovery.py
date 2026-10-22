"""Discovery of the live MCP surface for ``dartwork_mpl_info``.

Tool, resource and prompt names are scanned from the wiring tables' source
(``tools.py``, ``resources.py``, ``prompts.py``, ``artifacts/transport.py``)
in registration order; plot templates and primitive styles are listed from
the bundled asset directories. Imports no MCP slice.
"""

import re
from pathlib import Path

# ── Agentic-catalog discovery ────────────────────────────────────────
#
# ``dartwork_mpl_info`` advertises the live MCP surface (tools,
# resources, plot templates, primitive styles). Deriving these from the
# registry — the decorator source for tools/resources/prompts, the
# bundled asset dirs for templates/styles — rather than a hand-maintained
# literal means adding a tool or template can never silently drift the
# advertised catalog out of sync. (We scan the source instead of FastMCP
# private state, which moved between fastmcp 2.x and 3.x.)

_MCP_DIR = Path(__file__).parents[1]
_ASSET_DIR = Path(__file__).parents[2] / "asset"
_TEMPLATE_DIR = _ASSET_DIR / "prompt" / "05-templates"
_MPLSTYLE_DIR = _ASSET_DIR / "mplstyle"


# Sync/async ``@mcp.tool()`` — empty- and keyword-arg forms.
_TOOL_DEF_RE = re.compile(
    r"@mcp\.tool\([^)]*\)\s*\n\s*(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE
)
# ``@mcp.resource("<uri>"...)`` — first string arg is the URI; ``\s*``
# spans the newline used by the multi-line (mime_type) form.
_RESOURCE_URI_RE = re.compile(r"""@mcp\.resource\(\s*["']([^"']+)["']""")
# ``@mcp.prompt(...)\n    def <name>(`` in prompts.py.
_PROMPT_DEF_RE = re.compile(
    r"@mcp\.prompt\([^)]*\)\s*\n\s*def\s+(\w+)\s*\(", re.MULTILINE
)


def _scan_source(filename: str, pattern: re.Pattern[str]) -> list[str]:
    """Return ``pattern`` captures from an MCP wiring table's source.

    ``filename`` is relative to the ``dartwork_mpl/mcp`` package. Returns
    ``[]`` when the file is unreadable rather than falling back to a stale
    literal — an empty catalog is honest; a drifting hardcoded one is not.
    """
    try:
        src = (_MCP_DIR / filename).read_text(encoding="utf-8")
    except OSError:
        return []
    return pattern.findall(src)


def _discover_tool_names() -> list[str]:
    """Full tool identities in server order, including artifact registrations."""
    return _scan_source("tools.py", _TOOL_DEF_RE) + _scan_source(
        "artifacts/transport.py", _TOOL_DEF_RE
    )


def _discover_resource_uris() -> list[str]:
    """All static and template URIs, including the artifact capability."""
    return _scan_source("resources.py", _RESOURCE_URI_RE) + _scan_source(
        "artifacts/transport.py", _RESOURCE_URI_RE
    )


def _discover_prompt_names() -> list[str]:
    """Names of every ``@mcp.prompt()`` in prompts.py."""
    return _scan_source("prompts.py", _PROMPT_DEF_RE)


def _discover_plot_templates() -> list[str]:
    """Stems of the bundled ``05-templates/*.py`` plot templates."""
    return sorted(p.stem for p in _TEMPLATE_DIR.glob("*.py"))


def _discover_primitive_mplstyles() -> list[str]:
    """Stems of the bundled primitive ``*.mplstyle`` files."""
    return sorted(p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle"))
