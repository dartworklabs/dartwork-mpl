"""Tests for the MCP server module.

Requires the ``fastmcp`` optional dependency.
All tests are skipped when ``fastmcp`` is not installed.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

fastmcp = pytest.importorskip("fastmcp")


# ── Helpers ──────────────────────────────────────────────────────────


def _capture_decorators(mock_mcp, decorator_name: str) -> dict:
    """Create a fake decorator that captures registered functions."""
    captured = {}

    def fake_decorator(*args, **kwargs):
        # Handle both @mcp.tool() and @mcp.resource("uri")
        uri = args[0] if args else None

        def inner(fn):
            key = uri if uri else fn.__name__
            captured[key] = fn
            return fn

        return inner

    setattr(mock_mcp, decorator_name, fake_decorator)
    return captured


# ── Server Tests ─────────────────────────────────────────────────────


class TestMcpServer:
    """Tests for mcp server instantiation and registration."""

    def test_mcp_instance_is_fastmcp(self) -> None:
        """The mcp object should be a FastMCP instance."""
        from dartwork_mpl.mcp.server import mcp

        assert hasattr(mcp, "run")
        assert hasattr(mcp, "resource")
        assert hasattr(mcp, "tool")
        assert hasattr(mcp, "prompt")

    def test_mcp_server_name(self) -> None:
        """The server is named 'dartwork-mpl'."""
        from dartwork_mpl.mcp.server import mcp

        assert mcp.name == "dartwork-mpl"


# ── Resource Tests ───────────────────────────────────────────────────


class TestMcpResources:
    """Tests for resource registration."""

    def test_register_resources_no_error(self) -> None:
        """register_resources() should not raise on a mock server."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        register_resources(mock_mcp)

    def test_register_resources_count(self) -> None:
        """register_resources() should register at least 8 resources."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        register_resources(mock_mcp)
        assert mock_mcp.resource.call_count >= 8

    def test_general_guide_returns_string(self) -> None:
        """General guide resource returns a non-empty string."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        guide = captured["dartwork-mpl://guide/general-guide"]()
        assert isinstance(guide, str)
        assert len(guide) > 0

    def test_layout_guide_returns_string(self) -> None:
        """Layout guide resource returns a non-empty string."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        guide = captured["dartwork-mpl://guide/layout-guide"]()
        assert isinstance(guide, str)
        assert len(guide) > 0

    def test_palette_colors_returns_json(self) -> None:
        """palette/colors resource returns valid JSON with color entries."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        result = captured["dartwork-mpl://palette/colors"]()
        colors = json.loads(result)
        assert isinstance(colors, dict)
        assert len(colors) > 0

    def test_palette_fonts_returns_json(self) -> None:
        """palette/fonts resource returns valid JSON list."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        result = captured["dartwork-mpl://palette/fonts"]()
        fonts = json.loads(result)
        assert isinstance(fonts, list)

    def test_styles_list_returns_json(self) -> None:
        """styles/list resource returns valid JSON list of presets."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        result = captured["dartwork-mpl://styles/list"]()
        presets = json.loads(result)
        assert isinstance(presets, list)
        assert "dmpl" in presets

    def test_templates_list_returns_json(self) -> None:
        """templates/list resource returns valid JSON list of types."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        result = captured["dartwork-mpl://templates/list"]()
        templates = json.loads(result)
        assert isinstance(templates, list)
        assert "tornado" in templates
        assert "scatter" in templates


# ── Tool Tests ───────────────────────────────────────────────────────


class TestMcpTools:
    """Tests for tool registration."""

    def test_register_tools_no_error(self) -> None:
        """register_tools() should not raise on a mock server."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        register_tools(mock_mcp)

    def test_register_tools_count(self) -> None:
        """register_tools() should register at least 7 tools."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count >= 7

    def test_fetch_github_document_success(self) -> None:
        """fetch_github_document returns content on success."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        mock_resp = MagicMock()
        mock_resp.text = "# Hello World"

        with patch("httpx.get", return_value=mock_resp):
            result = captured["fetch_github_document"](
                "https://example.com/file.md"
            )
            assert result == "# Hello World"

    def test_fetch_github_document_error(self) -> None:
        """fetch_github_document raises ValueError on failure."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        with patch("httpx.get", side_effect=Exception("timeout")):
            with pytest.raises(ValueError, match="Failed"):
                captured["fetch_github_document"]("https://invalid.example.com")

    def test_get_color_value_known(self) -> None:
        """get_color_value returns hex for a known color."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["get_color_value"]("red")
        assert result.startswith("#")

    def test_get_color_value_unknown(self) -> None:
        """get_color_value returns error message for unknown color."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["get_color_value"]("nonexistent_color_xyz")
        assert "not found" in result

    def test_mix_colors(self) -> None:
        """mix_colors returns a valid hex code."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["mix_colors"]("red", "blue", 0.5)
        assert result.startswith("#")

    def test_list_color_families(self) -> None:
        """list_color_families returns valid JSON."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["list_color_families"]()
        families = json.loads(result)
        assert isinstance(families, dict)

    def test_lint_clean_code(self) -> None:
        """lint_dartwork_mpl_code returns success for clean code."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        clean_code = (
            "import dartwork_mpl as dm\n"
            'fig, ax = dm.subplots(width="13cm", aspect="standard")\n'
            'ax.plot([1, 2, 3], color="dc.blue500")\n'
            "dm.auto_layout(fig)\n"
            'dm.save_and_show(fig, "out")\n'
        )
        result = captured["lint_dartwork_mpl_code"](clean_code)
        assert "No issues found" in result

    def test_lint_detects_figsize(self) -> None:
        """lint_dartwork_mpl_code detects figsize= antipattern."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad_code = (
            "import dartwork_mpl as dm\n"
            "fig, ax = dm.subplots(figsize=(10, 6))\n"
            'dm.save_and_show(fig, "out")\n'
        )
        result = captured["lint_dartwork_mpl_code"](bad_code)
        assert "CRITICAL" in result
        assert "figsize" in result

    def test_validate_plot_data_bar_valid(self) -> None:
        """validate_plot_data accepts valid bar chart data."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        data = json.dumps(
            {"categories": ["A", "B", "C"], "values": [10, 20, 30]}
        )
        result = captured["validate_plot_data"]("bar", data)
        assert "valid" in result.lower()

    def test_validate_plot_data_bar_invalid(self) -> None:
        """validate_plot_data catches missing 'values' key."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        data = json.dumps({"categories": ["A", "B"]})
        result = captured["validate_plot_data"]("bar", data)
        assert "values" in result.lower()

    def test_dartwork_mpl_info(self) -> None:
        """dartwork_mpl_info returns valid JSON summary."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["dartwork_mpl_info"]()
        info = json.loads(result)
        assert info["name"] == "dartwork-mpl"
        assert "resources" in info
        assert "tools" in info
        assert "prompts" in info


# ── Prompt Tests ─────────────────────────────────────────────────────


class TestMcpPrompts:
    """Tests for prompt registration."""

    def test_register_prompts_no_error(self) -> None:
        """register_prompts() should not raise on a mock server."""
        from dartwork_mpl.mcp.prompts import register_prompts

        mock_mcp = MagicMock()
        register_prompts(mock_mcp)

    def test_register_prompts_count(self) -> None:
        """register_prompts() should register at least 2 prompts."""
        from dartwork_mpl.mcp.prompts import register_prompts

        mock_mcp = MagicMock()
        register_prompts(mock_mcp)
        assert mock_mcp.prompt.call_count >= 2

    def test_create_plot_prompt(self) -> None:
        """create_plot prompt returns a non-empty system message."""
        from dartwork_mpl.mcp.prompts import register_prompts

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "prompt")
        register_prompts(mock_mcp)

        result = captured["create_plot"]("bar chart of temperature over time")
        assert isinstance(result, str)
        assert "dartwork-mpl" in result
        assert "dm.subplots" in result

    def test_style_review_prompt(self) -> None:
        """style_review prompt returns a non-empty review template."""
        from dartwork_mpl.mcp.prompts import register_prompts

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "prompt")
        register_prompts(mock_mcp)

        code = "fig, ax = plt.subplots(figsize=(10, 6))"
        result = captured["style_review"](code)
        assert isinstance(result, str)
        assert "Review Checklist" in result
        assert "figsize" in result


# ── Package Export Tests ─────────────────────────────────────────────


class TestMcpPackage:
    """Tests for the mcp package exports."""

    def test_mcp_package_exports(self) -> None:
        """The mcp package __init__ exports 'mcp'."""
        from dartwork_mpl.mcp import mcp

        assert mcp is not None
