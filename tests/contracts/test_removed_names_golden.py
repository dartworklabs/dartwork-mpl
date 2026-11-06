"""Golden for every output that reports a removed ``dm`` name.

Root decision D2 keeps these outputs as contracts while the removed-name
metadata moves to one registry:

- ``dm.<name>`` access: the exception type and the full message;
- ``dm.migrate_legacy_code``: the whole rewritten source, for each removed
  name used as a reference and as a call, for similar names that must stay
  untouched, and for statements where several hints meet;
- ``dm.lint_code``: every issue of the removed-name rules (id, line,
  column, snippet) and those rules' severity, detector, message, why and fix;
- the MCP ``migrate_legacy_code`` and lint tools: name, description, input
  and output schema, and the order of every tool.

``tests/contracts/fixtures/removed_names_golden.json`` is an independent
record: the inputs and the outputs of origin/main d952266b, recorded before
the registry existed (its ``recorded_from`` field). Nothing here derives an
expected value from the registry, so a wrong registry cannot make this pass.
A difference is a change to a published output, which needs its own
decision; never re-record the fixture to make this test pass.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

import dartwork_mpl as dm
from dartwork_mpl.lint import load_rules

FIXTURE = Path(__file__).parent / "fixtures" / "removed_names_golden.json"


def _runtime(name: str) -> dict[str, str]:
    """What ``dm.<name>`` raises, or the type it resolves to."""
    try:
        value = getattr(dm, name)
    except AttributeError as exc:
        return {"type": type(exc).__qualname__, "message": str(exc)}
    return {"resolved": type(value).__qualname__}


def _lint(source: str, ids: list[str]) -> list[list[Any]]:
    """The issues of the rules ``ids`` in ``source``."""
    return [
        [issue.rule_id, issue.line, issue.column, issue.snippet]
        for issue in dm.lint_code(source)
        if issue.rule_id in ids
    ]


def _rule_fields(rule_id: str) -> dict[str, Any] | None:
    """A bundled rule's published fields, or None when it is gone."""
    for rule in load_rules():
        if rule.id == rule_id:
            return {
                "severity": rule.severity,
                "detector_kind": rule.detector_kind,
                "detector_value": rule.detector_value,
                "message": rule.message,
                "why": rule.why,
                "fix_suggestion": rule.fix_suggestion,
            }
    return None


def _mcp_surface(names: list[str]) -> dict[str, Any]:
    """Every tool's name in order, and the contracts of the tools ``names``."""
    import fastmcp

    from dartwork_mpl.mcp.server import mcp

    async def listed() -> list[Any]:
        async with fastmcp.Client(mcp) as client:
            return list(await client.list_tools())

    tools = asyncio.run(listed())
    return {
        "tool_names": [tool.name for tool in tools],
        "tools": {
            tool.name: {
                "description": tool.description,
                "inputSchema": tool.inputSchema,
                "outputSchema": tool.outputSchema,
            }
            for tool in tools
            if tool.name in names
        },
    }


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    """The recorded inputs and outputs."""
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_removed_name_access_raises_the_recorded_error(
    golden: dict[str, Any],
) -> None:
    """``dm.<name>`` raises the same exception type and message."""
    changed = {
        name: {"now": _runtime(name), "recorded": recorded}
        for name, recorded in golden["runtime"].items()
        if _runtime(name) != recorded
    }
    assert not changed


def test_migrate_legacy_code_rewrites_as_recorded(
    golden: dict[str, Any],
) -> None:
    """Every recorded source migrates to the same bytes."""
    changed = [
        {"source": case["source"], "now": now, "recorded": case["migrated"]}
        for case in golden["cases"]
        if (now := dm.migrate_legacy_code(case["source"])) != case["migrated"]
    ]
    assert not changed


def test_removed_name_rules_keep_their_published_fields(
    golden: dict[str, Any],
) -> None:
    """Severity, detector, message, why and fix of each removed-name rule."""
    current = {
        rule_id: _rule_fields(rule_id) for rule_id in golden["lint_rules"]
    }
    assert current == golden["lint_rules"]


def test_removed_name_rules_report_as_recorded(golden: dict[str, Any]) -> None:
    """The removed-name rules find the same places with the same text."""
    ids = list(golden["lint_rules"])
    changed = [
        {"source": case["source"], "now": now, "recorded": case["lint"]}
        for case in golden["cases"]
        if (now := _lint(case["source"], ids)) != case["lint"]
    ]
    assert not changed
    for case in golden["cases"]:
        for issue in dm.lint_code(case["source"]):
            recorded = golden["lint_rules"].get(issue.rule_id)
            if recorded is not None:
                assert issue.message == recorded["message"]
                assert issue.fix_suggestion == recorded["fix_suggestion"]
                assert issue.severity == recorded["severity"]


def test_mcp_lint_and_migrate_tools_keep_their_surface(
    golden: dict[str, Any],
) -> None:
    """Tool order and the lint/migrate tools' docstrings and schemas."""
    pytest.importorskip("fastmcp")
    assert _mcp_surface(list(golden["mcp"]["tools"])) == golden["mcp"]
