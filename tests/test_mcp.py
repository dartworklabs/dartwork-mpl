"""Tests for the MCP server module.

Requires the ``fastmcp`` optional dependency.
All tests are skipped when ``fastmcp`` is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

    def test_register_resources_calls_resource_decorator(self) -> None:
        """register_resources() should call mcp.resource()."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        register_resources(mock_mcp)
        assert mock_mcp.resource.call_count >= 2

    def test_general_guide_returns_string(self) -> None:
        """General guide resource returns a non-empty string."""
        from dartwork_mpl.mcp.resources import register_resources

        # Use a real FastMCP to actually exercise the inner functions
        mock_mcp = MagicMock()
        captured_fns = {}

        def fake_resource(uri):
            def decorator(fn):
                captured_fns[uri] = fn
                return fn

            return decorator

        mock_mcp.resource = fake_resource
        register_resources(mock_mcp)

        guide = captured_fns["dartwork-mpl://guide/general-guide"]()
        assert isinstance(guide, str)
        assert len(guide) > 0

    def test_layout_guide_returns_string(self) -> None:
        """Layout guide resource returns a non-empty string."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured_fns = {}

        def fake_resource(uri):
            def decorator(fn):
                captured_fns[uri] = fn
                return fn

            return decorator

        mock_mcp.resource = fake_resource
        register_resources(mock_mcp)

        guide = captured_fns["dartwork-mpl://guide/layout-guide"]()
        assert isinstance(guide, str)
        assert len(guide) > 0


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

    def test_fetch_github_document_success(self) -> None:
        """fetch_github_document returns content on success."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured_fns = {}

        def fake_tool():
            def decorator(fn):
                captured_fns[fn.__name__] = fn
                return fn

            return decorator

        mock_mcp.tool = fake_tool
        register_tools(mock_mcp)

        fetch_fn = captured_fns["fetch_github_document"]

        # Mock httpx.get
        mock_resp = MagicMock()
        mock_resp.text = "# Hello World"

        with patch("httpx.get", return_value=mock_resp):
            result = fetch_fn("https://example.com/file.md")
            assert result == "# Hello World"

    def test_fetch_github_document_error(self) -> None:
        """fetch_github_document raises ValueError on failure."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured_fns = {}

        def fake_tool():
            def decorator(fn):
                captured_fns[fn.__name__] = fn
                return fn

            return decorator

        mock_mcp.tool = fake_tool
        register_tools(mock_mcp)

        fetch_fn = captured_fns["fetch_github_document"]

        with patch("httpx.get", side_effect=Exception("timeout")):
            with pytest.raises(ValueError, match="Failed"):
                fetch_fn("https://invalid.example.com")


class TestMcpPackage:
    """Tests for the mcp package exports."""

    def test_mcp_package_exports(self) -> None:
        """The mcp package __init__ exports 'mcp'."""
        from dartwork_mpl.mcp import mcp

        assert mcp is not None
