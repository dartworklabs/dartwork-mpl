"""Tests for the MCP server module.

Requires the ``fastmcp`` optional dependency.
All tests are skipped when ``fastmcp`` is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

fastmcp = pytest.importorskip("fastmcp")


class TestMcpServer:
    """Tests for mcp server instantiation and registration."""

    def test_mcp_instance_is_fastmcp(self) -> None:
        """The mcp object should be a FastMCP instance."""
        from dartwork_mpl.mcp.server import mcp

        assert hasattr(mcp, "run")
        assert hasattr(mcp, "resource")
        assert hasattr(mcp, "tool")

    def test_mcp_server_name(self) -> None:
        """The server is named 'dartwork-mpl'."""
        from dartwork_mpl.mcp.server import mcp

        assert mcp.name == "dartwork-mpl"


class TestMcpResources:
    """Tests for resource registration."""

    def test_register_resources_no_error(self) -> None:
        """register_resources() should not raise on a mock server."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        register_resources(mock_mcp)

    def test_register_resources_calls_resource_decorator(
        self,
    ) -> None:
        """register_resources() should call mcp.resource()."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        register_resources(mock_mcp)
        assert mock_mcp.resource.call_count >= 2


class TestMcpTools:
    """Tests for tool registration."""

    def test_register_tools_no_error(self) -> None:
        """register_tools() should not raise on a mock server."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        register_tools(mock_mcp)

    def test_register_tools_calls_tool_decorator(self) -> None:
        """register_tools() should call mcp.tool()."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count >= 1


class TestMcpPackage:
    """Tests for the mcp package exports."""

    def test_mcp_package_exports(self) -> None:
        """The mcp package __init__ exports 'mcp'."""
        from dartwork_mpl.mcp import mcp

        assert mcp is not None
