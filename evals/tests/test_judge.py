"""Verdicts, isolation proof and transcript parsing, without calling claude."""

from __future__ import annotations

import json

from evals import judge

MCP = judge.ARM_SPECS["mcp"]


def init(**over: object) -> dict[str, object]:
    event: dict[str, object] = {
        "type": "system",
        "subtype": "init",
        "tools": ["Read", "Skill", *judge.MCP_TOOLS],
        "mcp_servers": [{"name": "dartwork-mpl", "status": "connected"}],
        "skills": ["dartwork-mpl"],
        "plugins": [],
    }
    return event | over


def test_isolated_mcp_session_has_no_problems():
    assert judge.isolation_problems(init(), MCP) == []


def test_extra_skill_plugin_or_server_breaks_isolation():
    problems = judge.isolation_problems(
        init(
            skills=["dartwork-mpl", "dataviz"],
            plugins=[{"name": "superpowers"}],
            mcp_servers=[
                {"name": "dartwork-mpl", "status": "connected"},
                {"name": "github", "status": "connected"},
            ],
        ),
        MCP,
    )
    assert len(problems) == 3


def test_failed_server_and_missing_tool_break_isolation():
    problems = judge.isolation_problems(
        init(
            mcp_servers=[{"name": "dartwork-mpl", "status": "failed"}],
            tools=["Read", "Skill", "Bash"],
        ),
        MCP,
    )
    assert any("mcp_servers" in p for p in problems)
    assert any("extra ['Bash']" in p for p in problems)


def test_bare_arm_expects_no_skill():
    bare = judge.ARM_SPECS["bare"]
    event = init(
        tools=list(bare.tools), mcp_servers=[], skills=["dartwork-mpl"]
    )
    assert judge.isolation_problems(event, bare) == [
        "skills ['dartwork-mpl'], expected []"
    ]


def test_parse_stream_finds_the_last_rendered_figure():
    payload = {"out_dir": "/tmp/b", "report": {"status": "rendered"}}
    failed = {"out_dir": "/tmp/a", "report": {"status": "error"}}
    lines = [
        json.dumps(init()),
        "not json",
        *(
            json.dumps(e)
            for e in [
                tool_use("1", "print(1)"),
                tool_result("1", failed),
                tool_use("2", "fig = 1"),
                tool_result("2", payload),
                {"type": "result", "num_turns": 3, "total_cost_usd": 0.1},
            ]
        ),
    ]
    trace = judge.parse_stream(lines)
    assert trace.tool_names == [judge.RENDER, judge.RENDER]
    assert trace.result is not None
    assert judge.last_rendered(trace) == ("fig = 1", payload)


def tool_use(i: str, code: str) -> dict[str, object]:
    block = {
        "type": "tool_use",
        "id": i,
        "name": judge.RENDER,
        "input": {"code": code},
    }
    return {"type": "assistant", "message": {"content": [block]}}


def tool_result(i: str, payload: dict[str, object]) -> dict[str, object]:
    content = [{"type": "image"}, {"type": "text", "text": json.dumps(payload)}]
    block = {"type": "tool_result", "tool_use_id": i, "content": content}
    return {"type": "user", "message": {"content": [block]}}


FIGURE = {
    "panels": 1,
    "marks": ["bar"],
    "texts": ["North", "Q1", "2.5억"],
    "legend": False,
    "check": [{"rule": "TEXT_AT_EDGE", "severity": "INFO", "message": "m"}],
    "check_skipped": [],
}


def test_missing_facts_lists_each_absent_fact():
    expect = {
        "panels": 2,
        "marks": ["bar", "line"],
        "texts": ["north", "South"],
        "any_text": ["만", "억"],
        "legend": True,
    }
    assert judge.missing_facts(expect, FIGURE) == [
        "panels: 1, expected 2",
        "no line marks",
        "text 'South' not on the figure",
        "no legend",
    ]


def test_verdict_ok_ignores_info():
    ev = judge.Evidence(has_image=True, figure=FIGURE)
    assert judge.verdict(ev) == ("OK", [])


def test_verdict_defect_on_warning_lint_or_missing_fact():
    warned = FIGURE | {
        "check": [{"rule": "OVERLAP", "severity": "WARNING", "message": "x"}]
    }
    ev = judge.Evidence(
        has_image=True,
        figure=warned,
        lint_critical=["r1 (line 3)"],
        missing=["no legend"],
    )
    verdict, reasons = judge.verdict(ev)
    assert verdict == "DEFECT"
    assert len(reasons) == 3


def test_verdict_order_invalid_then_no_figure():
    assert (
        judge.verdict(judge.Evidence(isolation=["x"], has_image=True))[0]
        == "INVALID"
    )
    assert judge.verdict(judge.Evidence(harness_error="auth"))[0] == "INVALID"
    assert judge.verdict(judge.Evidence())[0] == "NO_FIGURE"
    no_rerun = judge.Evidence(has_image=True, probe_error="boom")
    assert judge.verdict(no_rerun)[0] == "DEFECT"
