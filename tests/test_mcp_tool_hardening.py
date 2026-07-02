"""Hardening tests for MCP tool input-validation and error paths.

``mcp/tools.py`` is the lowest-covered module (75%); the uncovered lines
are almost entirely the tools' error / edge branches — exactly the
contract an MCP client (an AI agent feeding possibly-malformed input)
leans on. These exercise those branches directly so a regression there
fails CI instead of surfacing a raw traceback to the agent.

Skips when ``fastmcp`` (optional dep) is absent, matching ``test_mcp.py``.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp import tools as _tools
from dartwork_mpl.mcp.tools import register_tools


def _tools_map() -> dict:
    """Register the tools on a mock server; return ``{tool_name: fn}``."""
    captured: dict = {}

    def fake_tool(*_args, **_kwargs):
        def inner(fn):
            captured[fn.__name__] = fn
            return fn

        return inner

    mock = MagicMock()
    mock.tool = fake_tool
    register_tools(mock)
    return captured


class TestValidatePlotData:
    """The ``validate_plot_data`` tool's error contract."""

    def setup_method(self) -> None:
        self.validate = _tools_map()["validate_plot_data"]

    def test_invalid_json_is_reported(self) -> None:
        assert self.validate("scatter", "{not valid json").startswith(
            "Invalid JSON"
        )

    def test_unknown_plot_type_lists_available(self) -> None:
        out = self.validate("nonesuch", "{}")
        assert "No validator" in out
        assert "nonesuch" in out

    def test_malformed_payload_becomes_structured_error(self) -> None:
        # scatter's validator does ``len(data["x"])``; a scalar x raises
        # TypeError, which the defensive guard must convert to an
        # actionable message rather than leak the traceback.
        out = self.validate("scatter", json.dumps({"x": 5, "y": 6}))
        assert "Invalid data structure" in out

    def test_valid_scatter_passes(self) -> None:
        out = self.validate("scatter", json.dumps({"x": [1, 2], "y": [3, 4]}))
        assert out.startswith("✅")  # ✅

    def test_scatter_length_mismatch(self) -> None:
        out = self.validate("scatter", json.dumps({"x": [1, 2, 3], "y": [4]}))
        assert "Length mismatch" in out


class TestValidators:
    """Individual ``_validate_*`` helpers' issue branches."""

    def test_tornado_valid_and_mismatch(self) -> None:
        assert _tools._validate_tornado(
            {"categories": ["a"], "positive": [1]}
        ).startswith("✅")
        assert "Length mismatch" in _tools._validate_tornado(
            {"categories": ["a", "b"], "positive": [1]}
        )

    def test_bar_missing_and_mismatch(self) -> None:
        assert "Missing 'values'" in _tools._validate_bar({"categories": ["a"]})
        assert "Length mismatch" in _tools._validate_bar(
            {"categories": ["a", "b"], "values": [1]}
        )

    def test_heatmap_requires_2d(self) -> None:
        assert "2D array" in _tools._validate_heatmap({"matrix": [1, 2, 3]})
        assert _tools._validate_heatmap(
            {"matrix": [[1, 2], [3, 4]]}
        ).startswith("✅")

    def test_stacked_bar_series_length(self) -> None:
        out = _tools._validate_stacked_bar(
            {"categories": ["a", "b"], "series": {"s1": [1]}}
        )
        assert "s1" in out and "length" in out.lower()

    def test_pie_length_mismatch(self) -> None:
        assert "Length mismatch" in _tools._validate_pie(
            {"labels": ["a", "b"], "sizes": [1]}
        )

    def test_line_needs_y_or_series(self) -> None:
        out = _tools._validate_line({"x": [1, 2, 3]})
        assert "y" in out.lower() and "series" in out.lower()


class TestFetchGithubDocumentSSRF:
    """The fetch tool must only reach raw.githubusercontent.com (SSRF guard)."""

    def setup_method(self) -> None:
        self.fetch = _tools_map()["fetch_github_document"]

    def test_rejects_arbitrary_host(self) -> None:
        with pytest.raises(ValueError, match="raw.githubusercontent.com"):
            self.fetch("https://evil.example.com/payload")

    def test_rejects_plain_http_scheme(self) -> None:
        # Must be *https* on the exact host — http:// is not the allowed
        # prefix, so it is rejected before any network call.
        with pytest.raises(ValueError):
            self.fetch("http://raw.githubusercontent.com/a/b/main/x.md")


class TestColorTools:
    def setup_method(self) -> None:
        m = _tools_map()
        self.get_color = m["get_color_value"]
        self.mix = m["mix_colors"]

    def test_known_color_returns_hex(self) -> None:
        assert self.get_color("red").startswith("#")

    def test_unknown_color_reports_not_found(self) -> None:
        assert "not found" in self.get_color("zzz_no_such_color").lower()

    def test_mix_out_of_range_ratio(self) -> None:
        assert self.mix("red", "blue", ratio=1.5).startswith("Error: ratio")

    def test_mix_unknown_color_is_handled(self) -> None:
        out = self.mix("zzz_no_such_color", "blue")
        assert out.startswith("Error blending colors")
