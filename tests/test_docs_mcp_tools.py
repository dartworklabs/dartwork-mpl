"""mcp_server.md's Tools and Resources tables must match the live surface.

``docs/integrations/mcp_server.md`` hand-maintains ``### Tools`` and
``### Resources`` tables. Both drifted from ``dartwork_mpl.mcp``:

* the Tools table advertised 13 of the 16 registered tools —
  ``suggest_chart_type``, ``compose_layered_plot``, and
  ``render_template_advanced`` were added but never documented;
* the Resources table still listed the ``guide/general-guide`` and
  ``guide/layout-guide`` aliases removed in 0.5.4, and omitted the
  ``templates/advanced/{plot_type}`` resource that replaced them.

These guards parse each table and hold it against the same source
scanners (``_discover_tool_names`` / ``_discover_resource_uris``) that
``dartwork_mpl_info`` uses to report the live surface, so any
add/remove/rename that skips the docs fails loudly.

Requires the ``fastmcp`` optional dependency (skipped otherwise).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.tools import _discover_resource_uris, _discover_tool_names

_DOC = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "integrations"
    / "mcp_server.md"
)


def _section(heading: str) -> str:
    """Body of a ``### <heading>`` block, up to the next ``### `` heading."""
    text = _DOC.read_text(encoding="utf-8")
    m = re.search(rf"^### {re.escape(heading)}\b(.*?)^### ", text, re.S | re.M)
    assert m, f"### {heading} section not found in mcp_server.md"
    return m.group(1)


def _documented_tools() -> set[str]:
    """Tool names from the ``### Tools`` table.

    Scoped to the Tools section so the Prompts table (``create_plot``,
    ``style_review``) below it is not mistaken for tools.
    """
    return set(re.findall(r"^\|\s*`(\w+)\(", _section("Tools"), re.M))


def _documented_resources() -> set[str]:
    """Resource URIs from the ``### Resources`` table."""
    return set(re.findall(r"`(dartwork-mpl://[^`]+)`", _section("Resources")))


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


def test_doc_resource_table_matches_registered_resources() -> None:
    documented = _documented_resources()
    registered = set(_discover_resource_uris())

    missing = registered - documented
    extra = documented - registered
    assert not missing, (
        f"mcp_server.md Resources table is missing registered resources: "
        f"{sorted(missing)} — add a row for each"
    )
    assert not extra, (
        f"mcp_server.md Resources table lists URIs that are not registered "
        f"resources: {sorted(extra)} — remove or fix the row"
    )


def test_local_clone_docs_include_mcp_extra() -> None:
    """Local checkout launch examples must install the optional MCP deps.

    A checkout launched via ``uv run --directory`` does not necessarily have
    the ``fastmcp``/``httpx`` extra installed in its venv. Keep both the JSON
    client config and the generic stdio command on the documented
    ``--extra mcp`` path so copy-paste setups do not depend on ambient venv
    state.
    """
    text = _DOC.read_text(encoding="utf-8")

    assert '"--extra",\n        "mcp"' in text
    assert (
        "uv run --directory /path/to/dartwork-mpl --extra mcp dartwork-mpl-mcp"
    ) in text
