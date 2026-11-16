"""Verdicts, isolation proof and transcript parsing, without calling claude."""

from __future__ import annotations

import json

from evals import judge

SKILL = judge.ARM_SPECS["skill"]


def init(**over: object) -> dict[str, object]:
    event: dict[str, object] = {
        "type": "system",
        "subtype": "init",
        "tools": list(SKILL.tools),
        "mcp_servers": [],
        "skills": ["dartwork-mpl"],
        "plugins": [],
    }
    return event | over


def test_isolated_skill_session_has_no_problems():
    assert judge.isolation_problems(init(), SKILL) == []


def test_extra_skill_plugin_or_server_breaks_isolation():
    problems = judge.isolation_problems(
        init(
            skills=["dartwork-mpl", "dataviz"],
            plugins=[{"name": "superpowers"}],
            mcp_servers=[{"name": "github", "status": "connected"}],
        ),
        SKILL,
    )
    assert len(problems) == 3


def test_missing_tool_breaks_isolation():
    problems = judge.isolation_problems(
        init(tools=["Bash", "Read", "Write", "Edit"]), SKILL
    )
    assert problems == ["tools differ: extra [], missing ['Skill']"]


def test_bare_arm_expects_no_skill():
    bare = judge.ARM_SPECS["bare"]
    event = init(tools=list(bare.tools))
    assert judge.isolation_problems(event, bare) == [
        "skills ['dartwork-mpl'], expected []"
    ]


def test_parse_stream_collects_calls_results_and_the_result():
    use = {"type": "tool_use", "id": "1", "name": "Bash", "input": {}}
    done = {"type": "tool_result", "tool_use_id": "1", "content": "ok"}
    lines = [
        json.dumps(init()),
        "not json",
        json.dumps({"type": "assistant", "message": {"content": [use]}}),
        json.dumps({"type": "user", "message": {"content": [done]}}),
        json.dumps({"type": "result", "num_turns": 3}),
    ]
    trace = judge.parse_stream(lines)
    assert trace.init is not None
    assert trace.tool_names == ["Bash"]
    assert trace.results["1"] == done
    assert trace.result == {"type": "result", "num_turns": 3}


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
