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

    def test_migration_guide_returns_string(self) -> None:
        """Migration guide resource (added in 0.4.x) is registered and
        sources from ``asset/prompt/_legacy/migration-from-0.3.md``."""
        from dartwork_mpl.mcp.resources import register_resources

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "resource")
        register_resources(mock_mcp)

        assert "dartwork-mpl://guide/migration" in captured, (
            "guide/migration MCP URI must be registered"
        )
        body = captured["dartwork-mpl://guide/migration"]()
        assert isinstance(body, str)
        assert len(body) > 0
        # The bundled stub points at the docs site or the underlying md.
        assert "0.3" in body or "migration" in body.lower()

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
        """register_tools() should register at least 8 tools."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count >= 8

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
                "https://raw.githubusercontent.com/dartworklabs/dartwork-mpl/main/README.md"
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
                captured["fetch_github_document"](
                    "https://raw.githubusercontent.com/dartworklabs/foo.md"
                )

    def test_fetch_github_document_rejects_non_allowlist(self) -> None:
        """fetch_github_document rejects non-raw.githubusercontent.com URLs."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        for bad in (
            "http://raw.githubusercontent.com/foo",
            "https://example.com/file.md",
            "file:///etc/passwd",
            "ftp://server/x",
        ):
            with pytest.raises(ValueError, match="raw.githubusercontent.com"):
                captured["fetch_github_document"](bad)

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
            'fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))\n'
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
            "fig, ax = plt.subplots(figsize=(10, 6))\n"
            'dm.save_and_show(fig, "out")\n'
        )
        result = captured["lint_dartwork_mpl_code"](bad_code)
        assert "CRITICAL" in result
        assert "figsize" in result

    def test_lint_json_returns_list_of_dicts(self) -> None:
        """lint_dartwork_mpl_code_json returns a list of dicts with the
        documented schema for each issue."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad_code = (
            "import dartwork_mpl as dm\n"
            "fig, ax = plt.subplots(figsize=(10, 6))\n"
            'dm.save_and_show(fig, "out")\n'
        )
        result = captured["lint_dartwork_mpl_code_json"](bad_code)

        assert isinstance(result, list)
        assert len(result) >= 1
        # Every issue must be JSON-friendly with the documented keys.
        expected_keys = {
            "rule_id",
            "severity",
            "line",
            "column",
            "message",
            "fix_suggestion",
        }
        for issue in result:
            assert isinstance(issue, dict)
            assert expected_keys.issubset(issue.keys())
            assert isinstance(issue["rule_id"], str)
            assert issue["severity"] in {"critical", "warning", "info"}
            assert issue["line"] is None or isinstance(issue["line"], int)
            assert issue["column"] is None or isinstance(issue["column"], int)
            assert isinstance(issue["message"], str)
            assert issue["fix_suggestion"] is None or isinstance(
                issue["fix_suggestion"], str
            )

        # The figsize=(...) call should be flagged at least once.
        assert any("figsize" in issue["rule_id"] for issue in result)

    def test_lint_json_clean_code_returns_empty_list(self) -> None:
        """A clean snippet should produce no issues (empty list)."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        clean_code = (
            "import dartwork_mpl as dm\n"
            'fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))\n'
            'ax.plot([1, 2, 3], color="dc.blue500")\n'
            "dm.auto_layout(fig)\n"
            'dm.save_and_show(fig, "out")\n'
        )
        result = captured["lint_dartwork_mpl_code_json"](clean_code)
        assert result == []

    def test_dartwork_mpl_info_advertises_lint_json_tool(self) -> None:
        """``dartwork_mpl_info`` must list the new JSON sibling tool so
        agents can discover it."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["dartwork_mpl_info"]()
        info = json.loads(result)
        assert "lint_dartwork_mpl_code_json" in info["tools"]

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

    def test_validate_plot_data_supports_all_advertised_types(self) -> None:
        """``dartwork_mpl_info()`` advertises 18 plot templates;
        ``validate_plot_data`` must have a validator for every one."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        info = json.loads(captured["dartwork_mpl_info"]())
        advertised = set(info["plot_templates"])
        # Probe each advertised type with a deliberately empty payload
        # — any non-error response (✅ or a missing-key complaint)
        # proves a validator was wired up. Only the "no validator"
        # branch indicates a parity gap.
        for plot_type in advertised:
            result = captured["validate_plot_data"](plot_type, "{}")
            assert "no validator" not in result.lower(), (
                f"validate_plot_data missing handler for "
                f"advertised type {plot_type!r}"
            )

    # ── Strict validators: violin ──────────────────────────────────

    def test_validate_plot_data_violin_happy(self) -> None:
        """``groups`` + ``values`` (matching shapes) is accepted."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        good = json.dumps(
            {"groups": ["A", "B"], "values": [[1.0, 2.0, 3.0], [4, 5]]}
        )
        result = captured["validate_plot_data"]("violin", good)
        assert "valid" in result.lower()

        good_series = json.dumps(
            {"series": {"A": [1.0, 2.0, 3.0], "B": [4, 5]}}
        )
        assert (
            "valid"
            in captured["validate_plot_data"]("violin", good_series).lower()
        )

    def test_validate_plot_data_violin_empty_data(self) -> None:
        """An empty payload is rejected with a missing-key complaint."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["validate_plot_data"]("violin", "{}")
        assert "valid" not in result.lower() or "must" in result.lower()
        assert "groups" in result.lower() or "series" in result.lower()

    def test_validate_plot_data_violin_missing_values(self) -> None:
        """Providing only ``groups`` (without ``values`` or ``series``) fails."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps({"groups": ["A", "B"]})
        result = captured["validate_plot_data"]("violin", bad)
        assert "values" in result.lower() or "series" in result.lower()

    def test_validate_plot_data_violin_length_mismatch(self) -> None:
        """``groups`` and ``values`` must have equal length."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps(
            {"groups": ["A", "B", "C"], "values": [[1, 2], [3, 4]]}
        )
        result = captured["validate_plot_data"]("violin", bad)
        assert "length" in result.lower() or "mismatch" in result.lower()

    # ── Strict validators: boxplot ─────────────────────────────────

    def test_validate_plot_data_boxplot_happy(self) -> None:
        """Both ``groups+values`` and ``series`` payloads succeed."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        good = json.dumps(
            {"groups": ["A", "B"], "values": [[1, 2, 3], [4, 5, 6]]}
        )
        assert (
            "valid" in captured["validate_plot_data"]("boxplot", good).lower()
        )

    def test_validate_plot_data_boxplot_empty_data(self) -> None:
        """An empty payload fails with a missing-key complaint."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["validate_plot_data"]("boxplot", "{}")
        assert "groups" in result.lower() or "series" in result.lower()

    def test_validate_plot_data_boxplot_non_numeric(self) -> None:
        """Non-numeric inner samples are rejected."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps(
            {"groups": ["A", "B"], "values": [[1, 2, 3], ["x", "y"]]}
        )
        result = captured["validate_plot_data"]("boxplot", bad)
        assert "numeric" in result.lower()

    def test_validate_plot_data_boxplot_series_wrong_shape(self) -> None:
        """``series`` must be a dict, not a string or list."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps({"series": "not a dict"})
        result = captured["validate_plot_data"]("boxplot", bad)
        assert "dict" in result.lower() or "mapping" in result.lower()

    # ── Strict validators: histogram ───────────────────────────────

    def test_validate_plot_data_histogram_happy(self) -> None:
        """1-D numeric ``values`` (with optional ``bins``) is accepted."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        good = json.dumps({"values": [1, 2, 3, 4, 5], "bins": 10})
        assert (
            "valid" in captured["validate_plot_data"]("histogram", good).lower()
        )

        good_edges = json.dumps(
            {"values": [1, 2, 3, 4, 5], "bins": [0.0, 1.0, 2.0]}
        )
        assert (
            "valid"
            in captured["validate_plot_data"]("histogram", good_edges).lower()
        )

    def test_validate_plot_data_histogram_empty_data(self) -> None:
        """An empty payload fails with a missing-``values`` complaint."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["validate_plot_data"]("histogram", "{}")
        assert "values" in result.lower()

    def test_validate_plot_data_histogram_non_numeric_values(self) -> None:
        """Non-numeric samples are rejected."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps({"values": [1, "two", 3]})
        result = captured["validate_plot_data"]("histogram", bad)
        assert "numeric" in result.lower()

    def test_validate_plot_data_histogram_invalid_bins(self) -> None:
        """``bins`` must be a positive int or a numeric edge list."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps({"values": [1, 2, 3], "bins": 0})
        result = captured["validate_plot_data"]("histogram", bad)
        assert "bins" in result.lower()

    # ── Strict validators: contour ─────────────────────────────────

    def test_validate_plot_data_contour_happy(self) -> None:
        """A rectangular ``Z`` (with matching meshgrid) is accepted."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        good = json.dumps(
            {
                "Z": [[1, 2, 3], [4, 5, 6]],
                "X": [[0, 1, 2], [0, 1, 2]],
                "Y": [[0, 0, 0], [1, 1, 1]],
            }
        )
        assert (
            "valid" in captured["validate_plot_data"]("contour", good).lower()
        )

    def test_validate_plot_data_contour_empty_data(self) -> None:
        """An empty payload fails with a missing-``Z`` complaint."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["validate_plot_data"]("contour", "{}")
        assert "z" in result.lower()

    def test_validate_plot_data_contour_z_not_2d(self) -> None:
        """A flat 1-D ``Z`` is rejected."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps({"Z": [1, 2, 3, 4]})
        result = captured["validate_plot_data"]("contour", bad)
        assert "2-d" in result.lower() or "2d" in result.lower()

    def test_validate_plot_data_contour_meshgrid_shape_mismatch(self) -> None:
        """``X`` shape must match ``Z`` shape."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps({"Z": [[1, 2], [3, 4]], "X": [[1, 2, 3], [4, 5, 6]]})
        result = captured["validate_plot_data"]("contour", bad)
        assert "shape" in result.lower()

    # ── Strict validators: twin_axis ───────────────────────────────

    def test_validate_plot_data_twin_axis_happy(self) -> None:
        """Full nested ``left``/``right`` specs with matching ``y`` length."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        good = json.dumps(
            {
                "x": [1, 2, 3],
                "left": {"y": [10, 20, 30], "label": "Revenue"},
                "right": {"y": [0.1, 0.2, 0.3], "label": "Margin"},
            }
        )
        assert (
            "valid" in captured["validate_plot_data"]("twin_axis", good).lower()
        )

    def test_validate_plot_data_twin_axis_empty_data(self) -> None:
        """An empty payload fails with missing-key complaints."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["validate_plot_data"]("twin_axis", "{}").lower()
        assert "x" in result and "left" in result and "right" in result

    def test_validate_plot_data_twin_axis_missing_label(self) -> None:
        """``left`` and ``right`` must include both ``y`` and ``label``."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps(
            {
                "x": [1, 2, 3],
                "left": {"y": [10, 20, 30]},
                "right": {"y": [0.1, 0.2, 0.3], "label": "Margin"},
            }
        )
        result = captured["validate_plot_data"]("twin_axis", bad)
        assert "label" in result.lower()

    def test_validate_plot_data_twin_axis_length_mismatch(self) -> None:
        """``left.y`` length must match ``x`` length."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        bad = json.dumps(
            {
                "x": [1, 2, 3],
                "left": {"y": [10, 20], "label": "Revenue"},
                "right": {"y": [0.1, 0.2, 0.3], "label": "Margin"},
            }
        )
        result = captured["validate_plot_data"]("twin_axis", bad)
        assert "length" in result.lower()

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

    def test_dartwork_mpl_info_advertises_migration(self) -> None:
        """The 0.4.x patch added a `guide/migration` resource — it MUST
        appear in the resources list returned by ``dartwork_mpl_info``."""
        from dartwork_mpl.mcp.tools import register_tools

        mock_mcp = MagicMock()
        captured = _capture_decorators(mock_mcp, "tool")
        register_tools(mock_mcp)

        result = captured["dartwork_mpl_info"]()
        info = json.loads(result)
        assert "dartwork-mpl://guide/migration" in info["resources"]


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
        assert "dm.figsize" in result

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
