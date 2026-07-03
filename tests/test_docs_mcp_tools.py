"""The MCP tool table in mcp_server.md must list exactly the registered tools.

``docs/integrations/mcp_server.md`` hand-maintains a ``### Tools`` table.
When ``suggest_chart_type``, ``compose_layered_plot``, and
``render_template_advanced`` were added to ``dartwork_mpl.mcp.tools`` the
table was not updated, so the docs advertised 13 of the 16 registered tools
and an agent reading them would never learn the missing three existed. This
guard parses the table and holds it against ``_discover_tool_names`` — the
same source scanner ``dartwork_mpl_info`` uses to report the live surface —
so any tool add/remove/rename that skips the docs fails loudly.

Requires the ``fastmcp`` optional dependency (skipped otherwise).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.tools import _discover_tool_names

_DOC = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "integrations"
    / "mcp_server.md"
)


def _documented_tools() -> set[str]:
    """Tool names from the ``### Tools`` table of mcp_server.md.

    Scoped to the Tools section so the Prompts table (``create_plot``,
    ``style_review``) below it is not mistaken for tools.
    """
    text = _DOC.read_text(encoding="utf-8")
    m = re.search(r"^### Tools\b(.*?)^### ", text, re.S | re.M)
    assert m, "### Tools section not found in mcp_server.md"
    return set(re.findall(r"^\|\s*`(\w+)\(", m.group(1), re.M))


def test_doc_tool_table_matches_registered_tools() -> None:
    documented = _documented_tools()
    registered = set(_discover_tool_names())

    missing = registered - documented
    extra = documented - registered
    assert not missing, (
        f"mcp_server.md Tools table is missing registered tools: "
        f"{sorted(missing)} — add a row for each"
    )
    assert not extra, (
        f"mcp_server.md Tools table lists names that are not registered "
        f"tools: {sorted(extra)} — remove or fix the row"
    )
