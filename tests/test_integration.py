"""End-to-end integration tests for the AI-assisted surface.

Catches regressions that unit tests miss:

- :class:`TestMcpSurfaceContract`: every advertised MCP tool and
  resource must list **and** respond. Adding/removing a tool requires
  updating the expected set here, so silent API drift is loud.
- :class:`TestAgentDocAccess`: every name in
  :data:`dartwork_mpl.AGENT_DOCS` must resolve to a non-empty file in
  either the wheel-bundled location or the repo-root fallback.

These tests are the canonical guardrails for the *integration surface*
that ships to PyPI / GitHub Raw consumers.
"""

from __future__ import annotations

import asyncio
import json

import pytest

import dartwork_mpl as dm

fastmcp = pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.tools import _discover_plot_templates  # noqa: E402

# Tools we promise to keep on the MCP surface. Adding or removing one
# is a deliberate decision — this test forces the choice into the
# diff so a reviewer sees it.
EXPECTED_MCP_TOOLS: frozenset[str] = frozenset(
    {
        "fetch_github_document",
        "get_color_value",
        "mix_colors",
        "list_color_families",
        "lint_dartwork_mpl_code",
        "lint_dartwork_mpl_code_json",
        "apply_lint_fixes",
        "migrate_legacy_code",
        "find_template",
        "render_template",
        "validate_plot_data",
        "validate_generated_plot",
        "suggest_chart_type",
        "compose_layered_plot",
        "render_template_advanced",
        "dartwork_mpl_info",
    }
)

EXPECTED_MCP_RESOURCE_URIS: frozenset[str] = frozenset(
    {
        "dartwork-mpl://guide/agent-entry",
        "dartwork-mpl://guide/policy",
        "dartwork-mpl://guide/anti-patterns",
        "dartwork-mpl://guide/recipes",
        "dartwork-mpl://guide/general-guide",
        "dartwork-mpl://guide/layout-guide",
        "dartwork-mpl://guide/migration",
        "dartwork-mpl://api/index",
        "dartwork-mpl://palette/colors",
        "dartwork-mpl://palette/fonts",
        "dartwork-mpl://styles/list",
        "dartwork-mpl://templates/list",
    }
)

EXPECTED_MCP_PROMPTS: frozenset[str] = frozenset(
    {"create_plot", "style_review"}
)


def _fastmcp_has_public_introspection() -> bool:
    """True if the active FastMCP exposes ``list_tools`` / ``call_tool``
    as zero-arg public methods.

    The contract tests below introspect the live MCP catalog. FastMCP
    3.x lifted ``list_tools`` / ``list_resources`` / ``list_prompts``
    / ``read_resource`` / ``call_tool`` to the public surface and made
    them callable without a ``context`` argument. FastMCP 2.x still
    requires a ``context`` (only available inside an actual request),
    so in-process introspection is not possible there.

    The ``pyproject.toml`` pin is ``fastmcp>=2.13.3,<4``: we keep the
    floor for downstream 2.x consumers but skip these contract tests
    on 2.x. The non-contract tests (drift, render-via-API) still run.
    """
    from dartwork_mpl.mcp.server import mcp

    method = getattr(type(mcp), "list_tools", None)
    if method is None:
        return False
    # FastMCP 3.x: zero required positional args after self.
    import inspect

    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    required = [
        p
        for p in list(sig.parameters.values())[1:]  # skip self
        if p.default is inspect.Parameter.empty
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    return len(required) == 0


@pytest.mark.skipif(
    not _fastmcp_has_public_introspection(),
    reason=(
        "FastMCP 2.x requires a request context for in-process "
        "introspection; contract tests cover only 3.x."
    ),
)
class TestMcpSurfaceContract:
    """Locks the MCP tool/resource/prompt catalog."""

    def setup_method(self) -> None:
        from dartwork_mpl.mcp.server import mcp

        self.mcp = mcp

    def _run(self, coro):
        return asyncio.run(coro)

    def test_tool_set_matches_contract(self) -> None:
        tools = self._run(self.mcp.list_tools())
        got = {t.name for t in tools}
        assert got == EXPECTED_MCP_TOOLS, (
            f"MCP tool surface drift.\n"
            f"  added: {got - EXPECTED_MCP_TOOLS}\n"
            f"  removed: {EXPECTED_MCP_TOOLS - got}"
        )

    def test_resource_set_matches_contract(self) -> None:
        resources = self._run(self.mcp.list_resources())
        got = {str(r.uri) for r in resources}
        assert got == EXPECTED_MCP_RESOURCE_URIS, (
            f"MCP resource surface drift.\n"
            f"  added: {got - EXPECTED_MCP_RESOURCE_URIS}\n"
            f"  removed: {EXPECTED_MCP_RESOURCE_URIS - got}"
        )

    def test_prompt_set_matches_contract(self) -> None:
        prompts = self._run(self.mcp.list_prompts())
        got = {p.name for p in prompts}
        assert got == EXPECTED_MCP_PROMPTS

    def test_every_resource_responds(self) -> None:
        """Each advertised resource must return a non-empty body."""
        resources = self._run(self.mcp.list_resources())
        for r in resources:
            payload = self._run(self.mcp.read_resource(str(r.uri)))
            body = payload.contents[0].content
            assert body and len(body) > 5, (
                f"resource {r.uri} returned an empty body"
            )

    def test_three_template_uris_respond(self) -> None:
        """Templated resources (``api/{name}`` etc.) work too."""
        for uri in (
            "dartwork-mpl://api/figsize",
            "dartwork-mpl://styles/dmpl",
            "dartwork-mpl://templates/bar",
        ):
            payload = self._run(self.mcp.read_resource(uri))
            body = payload.contents[0].content
            assert body and len(body) > 5

    def test_render_template_returns_png(self) -> None:
        """``render_template`` must produce a non-trivial PNG."""
        result = self._run(
            self.mcp.call_tool("render_template", {"plot_type": "bar"})
        )
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "ok"
        assert payload["png_base64"] is not None
        # PNGs that actually contain pixels are much larger than the
        # 100-byte header threshold below.
        assert len(payload["png_base64"]) > 1000

    @pytest.mark.parametrize("plot_type", _discover_plot_templates())
    def test_every_bundled_template_renders(self, plot_type: str) -> None:
        """Every bundled ``05-templates/*.py`` (18 basic + the advanced tier)
        ships in the wheel and is served over MCP, but only ``bar`` was
        execution-tested — a template could regress at *runtime* while lint
        and the separate docs-gallery copy stayed green. Render each tier."""
        for tool in ("render_template", "render_template_advanced"):
            result = self._run(
                self.mcp.call_tool(tool, {"plot_type": plot_type})
            )
            payload = json.loads(result.content[0].text)
            assert payload["status"] in ("ok", "fell_back"), (
                f"{tool}({plot_type}) -> {payload['status']}: "
                f"{payload.get('stderr', '')[:400]}"
            )
            assert payload["png_base64"] and len(payload["png_base64"]) > 1000

    def test_validate_generated_plot_lint_blocks_critical(self) -> None:
        """``validate_generated_plot`` must short-circuit on critical
        lint before attempting to exec the snippet."""
        bad = (
            "import matplotlib.pyplot as plt\n"
            "fig, ax = plt.subplots(figsize=(6.7, 4.0))\n"
            "plt.tight_layout()\n"
        )
        result = self._run(
            self.mcp.call_tool("validate_generated_plot", {"code": bad})
        )
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "lint_blocked"
        rule_ids = {i["rule_id"] for i in payload["lint"]}
        assert "figsize-direct" in rule_ids
        assert "tight-layout" in rule_ids

    def test_apply_lint_fixes_round_trip(self) -> None:
        bad = (
            "import matplotlib.pyplot as plt\n"
            "plt.style.use('ggplot')\n"
            "plt.tight_layout()\n"
        )
        result = self._run(
            self.mcp.call_tool("apply_lint_fixes", {"code": bad})
        )
        payload = json.loads(result.content[0].text)
        assert "dm.style.use" in payload["fixed_code"]
        assert "dm.simple_layout" in payload["fixed_code"]
        applied_ids = {i["rule_id"] for i in payload["applied"]}
        assert {"plt-style-use", "tight-layout"} <= applied_ids


class TestAgentDocAccess:
    """Every bundled onboarding doc must be reachable through
    :func:`dartwork_mpl.get_agent_doc` and :func:`agent_doc_path`.
    """

    @pytest.mark.parametrize("name", dm.AGENT_DOCS)
    def test_get_agent_doc_returns_non_empty(self, name: str) -> None:
        body = dm.get_agent_doc(name)
        assert body
        assert len(body) > 100

    @pytest.mark.parametrize("name", dm.AGENT_DOCS)
    def test_agent_doc_path_exists(self, name: str) -> None:
        p = dm.agent_doc_path(name)
        assert p.exists()

    def test_unknown_doc_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            dm.get_agent_doc("not-a-real-doc")
