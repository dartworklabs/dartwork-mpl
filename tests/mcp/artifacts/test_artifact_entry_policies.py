"""Actual registrations require explicit policy decisions and bound store authority."""

import ast
import asyncio
from pathlib import Path

import pytest

fastmcp = pytest.importorskip("fastmcp")
from dartwork_mpl._colors import _catalog  # noqa: E402
from dartwork_mpl.mcp.artifacts.transport import ENTRY_POLICIES  # noqa: E402
from dartwork_mpl.mcp.server import mcp  # noqa: E402

ROOT = Path(__file__).resolve().parents[3] / "src" / "dartwork_mpl"
# Existing exact routes have trusted-code/no-verified-identity gaps. The immutable
# historical inventory names every gap; additional registrations cannot enter it.
KNOWN_GAPS = frozenset(
    value
    for values in _catalog.load_v5_snapshot().mcp_discovery.values()
    for value in values
)


def assert_entry_policies(routes):
    """Each actual route has one declared local authority decision or named gap."""
    assert len(routes) == len(set(routes))
    assert set(routes) == KNOWN_GAPS | ENTRY_POLICIES.keys()
    assert KNOWN_GAPS.isdisjoint(ENTRY_POLICIES)
    assert ENTRY_POLICIES["render_plot"] == "local_user_store_bounded_execution"
    assert all(
        policy == "local_user_store_verified_read"
        for route, policy in ENTRY_POLICIES.items()
        if route != "render_plot"
    )


def assert_constructors(sources):
    """Only configuration wiring mints a handle; requests can never choose roots."""
    for name, source in sources.items():
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.endswith("input_access")
            ):
                assert name == "mcp/artifacts/input_access.py" or all(
                    not alias.name.startswith("_") for alias in node.names
                ), (name, "private authority import")
        aliases = {
            alias.asname or alias.name: alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            target = aliases.get(target, target)
            if target == "configure_store":
                assert name == "mcp/server.py", (name, target)
            if target == "ArtifactStore":
                assert name == "mcp/artifacts/store.py", (name, target)
            if target == "InputGrant":
                assert name == "mcp/artifacts/input_access.py", (name, target)
            if target == "authorize_inputs":
                assert name in {
                    "mcp/server.py",
                    "mcp/artifacts/input_lifecycle.py",
                }, (name, target)


def test_registered_entries_have_explicit_policy_or_named_identity_gap():
    """Discover actual tools/resources/templates/prompts against exact decisions."""

    async def workflow():
        """Read every category through a genuine connected Client."""
        async with fastmcp.Client(mcp) as client:
            routes = [item.name for item in await client.list_tools()]
            routes += [str(item.uri) for item in await client.list_resources()]
            routes += [
                item.uriTemplate
                for item in await client.list_resource_templates()
            ]
            routes += [item.name for item in await client.list_prompts()]
            assert_entry_policies(routes)

    asyncio.run(workflow())
    assert_constructors(
        {
            str(path.relative_to(ROOT)): path.read_text()
            for path in ROOT.rglob("*.py")
            if "asset" not in path.parts
        }
    )


@pytest.mark.parametrize(
    "route", ["undeclared_tool", "dartwork-mpl://undeclared/{id}"]
)
def test_undeclared_registration_is_rejected(route):
    """An injected unclassified tool or resource must fail the policy gate."""
    with pytest.raises(AssertionError):
        assert_entry_policies([*KNOWN_GAPS, *ENTRY_POLICIES, route])


@pytest.mark.parametrize(
    "call",
    [
        "configure_store(root)",
        "ArtifactStore(root)",
        "InputGrant(key, root, roots)",
        "authorize_inputs(path, callback)",
        "access.InputGrant(key, root, roots)",
        "access.authorize_inputs(path, callback)",
    ],
)
def test_request_handle_construction_is_rejected(call):
    """An illicit handle construction site cannot expand request authority."""
    with pytest.raises(AssertionError):
        assert_constructors(
            {
                "mcp/artifacts/transport.py": f"def illicit(root):\n    return {call}\n"
            }
        )


def test_aliased_input_authority_import_is_rejected():
    """Import aliases cannot hide unauthorized construction or policy rereads."""
    for symbol in ("InputGrant", "authorize_inputs"):
        with pytest.raises(AssertionError):
            assert_constructors(
                {
                    "mcp/artifacts/transport.py": f"from .input_access import {symbol} as mint\nmint(None, None)\n"
                }
            )
    with pytest.raises(AssertionError):
        assert_constructors(
            {
                "mcp/artifacts/transport.py": "from .input_access import _KEY as authority\n"
            }
        )
