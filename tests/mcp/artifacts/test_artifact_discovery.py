"""Full live discovery and explicit historical projection have separate oracles."""

import asyncio
import json

import pytest

fastmcp = pytest.importorskip("fastmcp")
from dartwork_mpl._colors import _catalog  # noqa: E402
from dartwork_mpl.mcp.server import mcp  # noqa: E402

ADDITIONS = {
    "tool_names": ("render_plot", "get_plot_artifact", "delete_plot_inputs"),
    "resource_uris": (),
    "resource_template_uris": tuple(
        "dartwork-mpl://artifacts/{artifact_id}/" + name
        for name in (
            "plot.png",
            "plot.pdf",
            "source.py",
            "report.json",
            "manifest.json",
        )
    ),
    "prompt_names": (),
}


def assert_discovery(actual):
    """Compare exact categories/order against immutable legacy plus approved delta."""
    baseline = dict(_catalog.load_v5_snapshot().mcp_discovery)
    assert actual == {
        key: tuple(values) + ADDITIONS[key] for key, values in baseline.items()
    }


def test_live_discovery_is_legacy_core_plus_exact_extension():
    """Actual Clients, source AST and info all reveal the exact approved additions."""

    async def workflow():
        """Read every live protocol category and the info tool."""
        async with fastmcp.Client(mcp) as client:
            actual = {
                "tool_names": tuple(
                    item.name for item in await client.list_tools()
                ),
                "resource_uris": tuple(
                    str(item.uri) for item in await client.list_resources()
                ),
                "resource_template_uris": tuple(
                    item.uriTemplate
                    for item in await client.list_resource_templates()
                ),
                "prompt_names": tuple(
                    item.name for item in await client.list_prompts()
                ),
            }
            info = json.loads(
                (await client.call_tool("dartwork_mpl_info", {}))
                .content[0]
                .text
            )
            assert_discovery(actual)
            assert tuple(map(len, actual.values())) == (19, 10, 9, 2)
            assert actual == _catalog.scan_mcp_discovery()
            assert tuple(info["tools"]) == actual["tool_names"]
            assert (
                tuple(uri for uri in info["resources"] if "{" not in uri)
                == actual["resource_uris"]
            )
            assert (
                tuple(uri for uri in info["resources"] if "{" in uri)
                == actual["resource_template_uris"]
            )

    asyncio.run(workflow())


def test_historical_projection_preserves_all_other_fields():
    """Projection removes only eight approved literals and preserves unknown additions."""
    live = _catalog.scan_mcp_discovery()
    projected = _catalog.project_legacy_mcp_discovery(live)
    assert projected == dict(_catalog.load_v5_snapshot().mcp_discovery)
    augmented = {
        **live,
        "tool_names": live["tool_names"] + ("undeclared_tool",),
        "other": ("unchanged",),
    }
    result = _catalog.project_legacy_mcp_discovery(augmented)
    assert result["tool_names"] == projected["tool_names"] + (
        "undeclared_tool",
    )
    assert result["other"] == ("unchanged",)


@pytest.mark.parametrize("mutation", ["extra", "drop", "reorder"])
def test_discovery_gate_rejects_unapproved_changes(mutation):
    """Injected addition, removal and order drift fail the exact mechanical gate."""
    actual = _catalog.scan_mcp_discovery()
    tools = actual["tool_names"]
    actual["tool_names"] = {
        "extra": (*tools, "undeclared_tool"),
        "drop": tools[1:],
        "reorder": (tools[1], tools[0], *tools[2:]),
    }[mutation]
    with pytest.raises(AssertionError):
        assert_discovery(actual)


@pytest.mark.parametrize("kind", ["tool", "resource"])
def test_actual_extra_registration_fails_discovery_gate(kind):
    """An additional genuine registration cannot hide behind source filtering."""
    from dartwork_mpl.mcp.artifacts import (
        ConfigurationError,
        register_artifacts,
    )
    from dartwork_mpl.mcp.prompts import register_prompts
    from dartwork_mpl.mcp.resources import register_resources
    from dartwork_mpl.mcp.tools import register_tools

    instance = fastmcp.FastMCP("discovery-mutation")
    register_resources(instance)
    register_tools(instance)
    register_prompts(instance)
    register_artifacts(instance, ConfigurationError())
    if kind == "tool":

        @instance.tool()
        def undeclared_tool() -> str:
            """Deliberately undeclared route must fail exact discovery."""
            return "extra"
    else:

        @instance.resource("dartwork-mpl://undeclared/{identity}")
        def undeclared_resource(identity: str) -> str:
            """Deliberately undeclared resource must fail exact discovery."""
            return identity

    async def workflow():
        """Observe injected runtime registrations through the actual protocol."""
        async with fastmcp.Client(instance) as client:
            actual = {
                "tool_names": tuple(
                    item.name for item in await client.list_tools()
                ),
                "resource_uris": tuple(
                    str(item.uri) for item in await client.list_resources()
                ),
                "resource_template_uris": tuple(
                    item.uriTemplate
                    for item in await client.list_resource_templates()
                ),
                "prompt_names": tuple(
                    item.name for item in await client.list_prompts()
                ),
            }
            with pytest.raises(AssertionError):
                assert_discovery(actual)

    asyncio.run(workflow())
