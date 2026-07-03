"""Smoke + error-path tests for the heavier MCP tools.

``find_template`` / ``apply_lint_fixes`` / ``render_template`` /
``suggest_chart_type`` / ``dartwork_mpl_info`` are the largest, least-
covered tools. These exercise their reliable, non-subprocess paths — a
valid call plus the blank/unknown branches — so the agent-facing contract
is guarded without a 30-second render subprocess.

Skips when ``fastmcp`` (optional dep) is absent, matching ``test_mcp.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.tools import register_tools


def _tools_map() -> dict:
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


class TestFindTemplate:
    def setup_method(self) -> None:
        self.find = _tools_map()["find_template"]

    def test_ranks_matches(self) -> None:
        out = self.find("horizontal bar comparison")
        assert isinstance(out, list)
        assert out, "a bar-related intent must match at least one template"
        assert "template_id" in out[0]
        assert "score" in out[0]

    def test_blank_intent_returns_empty(self) -> None:
        assert self.find("   ") == []

    def test_tier_tags_each_result(self) -> None:
        out = self.find("bar", tier="all")
        assert out  # 'bar' matches
        assert all("tier" in r for r in out)


class TestApplyLintFixes:
    def setup_method(self) -> None:
        self.apply = _tools_map()["apply_lint_fixes"]

    def test_rewrites_tight_layout(self) -> None:
        out = self.apply(
            "import matplotlib.pyplot as plt\n"
            "fig = plt.figure()\n"
            "fig.tight_layout()\n"
        )
        assert out["applied"], "tight_layout() must be an applied fix"
        assert "simple_layout" in out["fixed_code"]

    def test_clean_code_has_no_fixes(self) -> None:
        out = self.apply("x = 1\n")
        assert out["applied"] == []


class TestRenderTemplateUnknown:
    def setup_method(self) -> None:
        self.render = _tools_map()["render_template"]

    def test_unknown_template_short_circuits(self) -> None:
        # An unknown id resolves to no path -> the tool returns
        # 'unknown_template' *before* spawning any render subprocess.
        out = self.render("definitely_not_a_real_template")
        assert out["status"] == "unknown_template"
        assert out["png_base64"] is None
        assert "Available" in out["stderr"]


class TestSuggestChartType:
    def setup_method(self) -> None:
        self.suggest = _tools_map()["suggest_chart_type"]

    def test_returns_resolvable_recommendation(self) -> None:
        out = self.suggest("categorical", "continuous")
        assert out.get("recommended")
        assert "rationale" in out
        assert "basic_template_uri" in out


class TestDartworkMplInfo:
    def setup_method(self) -> None:
        self.info = _tools_map()["dartwork_mpl_info"]

    def test_reports_version_surface_and_name(self) -> None:
        import dartwork_mpl as dm

        # The tool surfaces the major.minor "version_surface" (e.g. "0.5"),
        # not the full patch version — assert that stable prefix + the name.
        major_minor = ".".join(dm.__version__.split(".")[:2])
        out = str(self.info())
        assert major_minor in out
        assert "dartwork-mpl" in out
