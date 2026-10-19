"""Real Clients pin legacy wire responses and the opt-in JSON-string report.

Baselines were captured before the tool signature changed, separately on each
tested FastMCP runtime. Required-argument failures remain framework-owned errors.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

fastmcp = pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.server import mcp  # noqa: E402

_FIXTURE = json.loads(
    (
        Path(__file__).parent / "mcp/data_repair/fixtures/legacy_calls.json"
    ).read_text()
)
_REQUESTS = _FIXTURE["requests"]
_BASELINE = _FIXTURE["runtimes"][fastmcp.__version__]
_LEGACY = {item["id"]: item["response"] for item in _BASELINE["calls"]}
_SUPPORTED = {"scatter", "bar", "bar_horizontal", "histogram", "heatmap"}
_REPORT_REQUESTS = {
    item["id"]: item["arguments"]
    for item in _REQUESTS
    if item["id"].endswith("-valid")
    or item["id"]
    in {
        "malformed-json",
        "unknown-name",
        "unknown-malformed-precedence",
        "uppercase",
        "whitespace",
        "numeric-strings",
        "mismatched-pairs",
        "duplicate-key",
        "nonfinite",
    }
}
_REPORT_REQUESTS["deep-json"] = {
    "plot_type": "scatter",
    "data_json": "[" * 1100 + "0" + "]" * 1100,
}


def _envelope(result: Any) -> dict[str, Any]:
    """Observe text, structured framing and parsed data through the real Client."""
    return {
        "raw_text": [
            item.text for item in result.content if item.type == "text"
        ],
        "content": [item.model_dump(mode="json") for item in result.content],
        "structured_content": result.structured_content,
        "is_error": result.is_error,
        "data": result.data,
    }


@pytest.fixture(scope="module")
def wire() -> dict[str, Any]:
    """Collect one real production-server session for every independent assertion."""

    async def observe() -> dict[str, Any]:
        """Await all protocol calls and close the session even when a call fails."""
        async with fastmcp.Client(mcp) as client:
            tools = await client.list_tools()
            result = {
                "schema": next(
                    item.model_dump(mode="json")
                    for item in tools
                    if item.name == "validate_plot_data"
                ),
                "discovery": {
                    "tool_names": [item.name for item in tools],
                    "resource_uris": [
                        str(item.uri) for item in await client.list_resources()
                    ],
                    "resource_template_uris": [
                        item.uriTemplate
                        for item in await client.list_resource_templates()
                    ],
                    "prompt_names": [
                        item.name for item in await client.list_prompts()
                    ],
                },
                "omitted": {},
                "false": {},
                "reports": {},
            }
            for request in _REQUESTS:
                for mode, extra in (
                    ("omitted", {}),
                    ("false", {"report": False}),
                ):
                    call = await client.call_tool(
                        "validate_plot_data",
                        {**request["arguments"], **extra},
                        raise_on_error=False,
                    )
                    result[mode][request["id"]] = _envelope(call)
            for name, arguments in _REPORT_REQUESTS.items():
                call = await client.call_tool(
                    "validate_plot_data",
                    {**arguments, "report": True},
                    raise_on_error=False,
                )
                result["reports"][name] = _envelope(call)
            return result

    return asyncio.run(observe())


def _report(wire: dict[str, Any], name: str) -> dict[str, Any]:
    """Decode a successful string result while checking unchanged wire framing."""
    result = wire["reports"][name]
    assert result["is_error"] is False, result
    text = result["data"]
    assert isinstance(text, str)
    assert result["raw_text"] == [text]
    assert result["structured_content"] == {"result": text}
    expected_content = [dict(_LEGACY["scatter-valid"]["content"][0], text=text)]
    assert result["content"] == expected_content
    parsed = json.loads(text)
    assert parsed["version"] == 1
    assert parsed["effects"] == "none"
    assert parsed["scope"]["validity"] == "declared_fields_only"
    return parsed


def test_discovery_retains_exact_identities_and_order(wire):
    """The optional input adds no tool, resource, template or prompt identity."""
    assert wire["discovery"] == _BASELINE["discovery"]
    assert [len(items) for items in wire["discovery"].values()] == [
        18,
        10,
        9,
        2,
    ]


def test_schema_adds_only_optional_false_report_and_keeps_string_output(wire):
    """Required strings and the old output schema survive the additive argument."""
    actual = wire["schema"]
    original = _BASELINE["validate_schema"]
    assert actual["name"] == original["name"] == "validate_plot_data"
    assert actual["outputSchema"] == original["outputSchema"]
    inputs = actual["inputSchema"]
    assert inputs["required"] == ["plot_type", "data_json"]
    assert inputs["properties"]["report"]["default"] is False
    assert inputs["properties"]["report"]["type"] == "boolean"
    legacy_inputs = {**inputs, "properties": dict(inputs["properties"])}
    del legacy_inputs["properties"]["report"]
    assert legacy_inputs == original["inputSchema"]


@pytest.mark.parametrize("case", _REQUESTS, ids=lambda item: item["id"])
def test_omitted_calls_match_prechange_envelopes(wire, case):
    """All 18 shapes and malformed/unknown/wrong-argument responses stay exact."""
    assert wire["omitted"][case["id"]] == _LEGACY[case["id"]]


@pytest.mark.parametrize(
    "case",
    [
        item
        for item in _REQUESTS
        if {"plot_type", "data_json"} <= item["arguments"].keys()
    ],
    ids=lambda item: item["id"],
)
def test_false_calls_match_prechange_omitted_envelopes(wire, case):
    """The new explicit false path has the old omitted-input wire behavior."""
    assert wire["false"][case["id"]] == _LEGACY[case["id"]]


@pytest.mark.parametrize("name", ["wire-missing-plot", "wire-missing-data"])
def test_false_missing_required_arguments_remain_framework_errors(wire, name):
    """Missing required fields still fail; Pydantic echoes the new supplied flag."""
    result = wire["false"][name]
    assert result["is_error"] is True
    assert result["structured_content"] is None
    assert "Missing required argument" in result["raw_text"][0]
    assert "'report': False" in result["raw_text"][0]
    assert "Unexpected keyword argument" not in result["raw_text"][0]
    normalized = json.loads(json.dumps(result).replace(", 'report': False", ""))
    assert normalized == _LEGACY[name]


@pytest.mark.parametrize(
    "name", [item["id"] for item in _REQUESTS if item["id"].endswith("-valid")]
)
def test_report_distinguishes_five_supported_from_thirteen_recognized(
    wire, name
):
    """Membership comes from the existing 18-type catalog; coverage stays scoped."""
    report = _report(wire, name)
    arguments = _REPORT_REQUESTS[name]
    kind = arguments["plot_type"]
    assert report["plot_type"] == kind
    assert report["recognized"] is True
    assert report["supported"] == (kind in _SUPPORTED)
    assert report["status"] == (
        "valid" if kind in _SUPPORTED else "unsupported"
    )
    assert report["original"]["raw_json"] == arguments["data_json"]


@pytest.mark.parametrize(
    ("name", "normalized", "recognized", "supported", "status"),
    [
        ("uppercase", "scatter", True, True, "valid"),
        ("whitespace", " scatter ", False, False, "unsupported"),
        ("unknown-name", "nonesuch", False, False, "unsupported"),
        ("unknown-malformed-precedence", "nonesuch", False, False, "rejected"),
    ],
)
def test_report_preserves_lowercase_without_trimming(
    wire, name, normalized, recognized, supported, status
):
    """Lowercasing keeps the old name semantics, including literal whitespace."""
    report = _report(wire, name)
    assert (
        report["plot_type"],
        report["recognized"],
        report["supported"],
        report["status"],
    ) == (normalized, recognized, supported, status)


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("malformed-json", "invalid_json"),
        ("duplicate-key", "duplicate_key"),
        ("nonfinite", "nonfinite_token"),
        ("deep-json", "limit_exceeded"),
    ],
)
def test_report_refusals_select_bounded_parser_before_legacy_json_loads(
    wire, name, code
):
    """Strict refusals and extreme depth return reports instead of legacy text/errors."""
    report = _report(wire, name)
    assert report["status"] == "rejected"
    assert report["issues"][0]["code"] == code
    assert "candidate" not in report
    if name == "deep-json":
        assert "original" not in report


def test_report_returns_reviewable_candidate_and_manual_action(wire):
    """The public report preserves labels/originals and exposes separate proposals."""
    proposal = _report(wire, "numeric-strings")
    assert proposal["status"] == "proposal"
    assert proposal["requires_review"] is True
    assert proposal["original"]["data"] == {
        "categories": ["01"],
        "values": ["2.5"],
    }
    assert proposal["candidate"] == {
        "data": {"categories": ["01"], "values": [2.5]},
        "valid": True,
        "remaining_issues": [],
    }
    assert [
        (item["path"], item["before"], item["after"], item["requires_review"])
        for item in proposal["changes"]
    ] == [("/values/0", "2.5", 2.5, True)]
    manual = _report(wire, "mismatched-pairs")
    assert manual["status"] == "needs_input"
    assert manual["changes"] == []
    assert manual["issues"][0]["path"] == "/x"
    assert manual["issues"][0]["observed"] == {"lengths": [2, 1]}
    assert (
        "Restore the intended aligned observations"
        in manual["issues"][0]["action"]
    )
