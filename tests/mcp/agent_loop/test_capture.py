"""Real stdio, files and owned process trees pin evaluation capture boundaries."""

import asyncio
import base64
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from evaluate_agent_plot import evaluate, replay
from run_agent_plot_eval import (
    _admission_decision,
    _repair_admission,
    _reserve_stage,
    _stage_review,
    capture_process,
    recover,
    validate_capture,
)


def test_recovery_reads_every_member_without_execution(tmp_path):
    """Both exact five-member bundles survive restart without a third execution."""
    counter = tmp_path / "counter"
    store = tmp_path / "store"
    source = f"""from pathlib import Path
p = Path({str(counter)!r})
p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1, 2], [3, 4], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""

    async def render_twice():
        """Use the installed server entry point and an actual private store."""
        parameters = StdioServerParameters(
            command=str(Path(sys.executable).parent / "dartwork-mpl-mcp"),
            env={**os.environ, "DARTWORK_MPL_ARTIFACT_DIR": str(store)},
            cwd=str(tmp_path),
        )
        identities = []
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                for suffix in ("", "\nax.set_title('revision')\n"):
                    result = await client.call_tool(
                        "render_plot", {"code": source + suffix}
                    )
                    assert (
                        result.structuredContent["delivery_status"] == "ready"
                    )
                    identities.append(result.structuredContent["artifact_id"])
        return identities

    identities = asyncio.run(render_twice())
    assert counter.read_text() == "2"
    first = recover(identities, store, tmp_path / "first")
    second = recover(identities, store, tmp_path / "second")
    assert first["status"] == second["status"] == "ok"
    assert first["members"] == second["members"]
    assert first["hashes"] == second["hashes"]
    assert set(first["members"]) == set(identities)
    for identity, members in first["members"].items():
        assert set(members) == {
            "plot.png",
            "plot.pdf",
            "source.py",
            "report.json",
            "manifest.json",
        }
        for name, data in members.items():
            assert (
                hashlib.sha256(data).hexdigest()
                == first["hashes"][identity][name]
            )
    assert counter.read_text() == "2"


def test_capture_rejects_incomplete_or_contaminated_run(tmp_path):
    """Truncated framing, fixture drift and evaluator access cannot pass capture."""
    csv = tmp_path / "input.csv"
    csv.write_bytes(b"x,y\n1,2\n")
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    events = [
        {
            "type": "system",
            "subtype": "init",
            "session_id": "session",
            "model": "selected",
            "tools": ["Read", "mcp__dartwork_mpl__render_plot"],
            "mcp_servers": [{"name": "dartwork_mpl", "status": "connected"}],
        },
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session",
            "is_error": False,
        },
    ]
    path = tmp_path / "events.jsonl"
    path.write_text("".join(json.dumps(item) + "\n" for item in events))
    assert validate_capture(path, csv, digest, "selected")["status"] == "ok"
    rng = random.Random(20261020)
    raw = path.read_bytes()
    for cut in rng.sample(range(1, len(raw)), 12):
        path.write_bytes(raw[:cut])
        assert (
            validate_capture(path, csv, digest, "selected")["status"]
            == "failed"
        )
    path.write_bytes(raw)
    csv.write_bytes(b"x,y\n1,9\n")
    assert (
        "fixture_changed"
        in validate_capture(path, csv, digest, "selected")["reasons"]
    )
    csv.write_bytes(b"x,y\n1,2\n")
    events.insert(
        1,
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/outside/expected.json"},
                    }
                ]
            },
        },
    )
    path.write_text("".join(json.dumps(item) + "\n" for item in events))
    assert (
        "oracle_access"
        in validate_capture(path, csv, digest, "selected")["reasons"]
    )


@pytest.mark.parametrize(
    "limit", ["wall", "calls", "reader_calls", "bytes", "source", "render_time"]
)
def test_watchdog_stops_process_tree_and_keeps_partial_evidence(
    tmp_path, limit
):
    """External limits terminate an owned child plus detached grandchild."""
    child = tmp_path / "child.py"
    child.write_text("""import json, os, subprocess, sys, time
p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
print(json.dumps({'child_pid': p.pid}), flush=True)
time.sleep(0.15)
for i in range(100):
    print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'mcp__dartwork_mpl__render_plot','input':{'code':'x' * 1000}}]}}), flush=True)
    time.sleep(0.01)
time.sleep(60)
""")
    if limit == "reader_calls":
        child.write_text(
            child.read_text().replace(
                "mcp__dartwork_mpl__render_plot", "ReadMcpResourceTool"
            )
        )
    elif limit == "source":
        child.write_text(
            child.read_text().replace("'x' * 1000", "'x' * 600000")
        )
    elif limit == "render_time":
        child.write_text(
            child.read_text().replace(
                "'code':'x' * 1000", "'code':'x' * 1000,'timeout_seconds':21"
            )
        )
    result = capture_process(
        [sys.executable, str(child)],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=0.4 if limit == "wall" else 5,
        max_calls=1 if limit in ("calls", "reader_calls") else 1000,
        max_bytes=2000 if limit == "bytes" else 1000000,
    )
    assert (
        result["stop_reason"]
        == {
            "wall": "wall_limit",
            "calls": "call_limit",
            "reader_calls": "call_limit",
            "bytes": "byte_limit",
            "source": "source_limit",
            "render_time": "render_time_limit",
        }[limit]
    )
    assert result["cleanup_ok"]
    first = json.loads((tmp_path / "events.jsonl").read_text().splitlines()[0])
    with pytest.raises(ProcessLookupError):
        os.kill(first["child_pid"], 0)
    assert (tmp_path / "stderr.txt").exists()


def test_replay_keeps_exact_source_and_absolute_csv_until_finished(tmp_path):
    """Fresh-process replay reads the original absolute CSV without rewriting."""
    csv = tmp_path / "input.csv"
    csv.write_text("x,y\n1,2\n")
    source = tmp_path / "source.py"
    source.write_text(f"""import csv
import matplotlib.pyplot as plt
import dartwork_mpl as dm
path = {str(csv)!r}
with open(path) as f:
    rows = list(csv.DictReader(f))
dm.style.use('scientific')
figure, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([float(r['x']) for r in rows], [float(r['y']) for r in rows], linewidth=dm.lw(0))
dm.simple_layout(figure)
""")
    import io

    import matplotlib.image as mpimg
    import numpy as np

    async def original_png():
        """Render identical bytes through the production stdio exporter first."""
        parameters = StdioServerParameters(
            command=str(Path(sys.executable).parent / "dartwork-mpl-mcp"),
            env={
                **os.environ,
                "DARTWORK_MPL_ARTIFACT_DIR": str(tmp_path / "original-store"),
            },
            cwd=str(tmp_path),
        )
        async with (
            stdio_client(parameters) as (reader, writer),
            ClientSession(reader, writer) as client,
        ):
            await client.initialize()
            rendered = await client.call_tool(
                "render_plot",
                {"code": source.read_text(), "figure_var": "figure"},
            )
            assert rendered.structuredContent["delivery_status"] == "ready"
            return base64.b64decode(rendered.content[0].data)

    before = source.read_bytes(), csv.read_bytes()
    original = asyncio.run(original_png())
    result = replay(source, csv, "line", tmp_path / "replay", "figure")
    np.testing.assert_array_equal(
        mpimg.imread(io.BytesIO(original)),
        mpimg.imread(tmp_path / "replay/plot.png"),
    )
    assert result["status"] == "ok"
    assert result["source_sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert result["export"]["api"] == "dartwork_mpl.save_formats"
    assert result["observed"]["panels"][0]["lines"][0]["xy"] == [[1.0, 2.0]]
    assert (tmp_path / "replay/plot.png").read_bytes().startswith(b"\x89PNG")
    assert (source.read_bytes(), csv.read_bytes()) == before
    assert result["assessment"]["passed"] is False


def test_review_requires_selected_image_and_successful_report_receipt():
    """A template image or failed resource read cannot stand in for artifact review."""
    calls = [
        {
            "type": "tool_use",
            "id": "render",
            "name": "mcp__dartwork_mpl__render_plot",
            "input": {"code": "generated"},
        },
        {
            "type": "tool_use",
            "id": "report",
            "name": "ReadMcpResourceTool",
            "input": {"uri": "dartwork-mpl://artifacts/chosen/report.json"},
        },
    ]
    metadata = {
        "delivery_status": "ready",
        "artifact_id": "chosen",
        "files": [],
    }
    render = {
        "type": "tool_result",
        "tool_use_id": "render",
        "content": [
            {"type": "image", "data": "png"},
            {"type": "text", "text": json.dumps(metadata)},
        ],
    }
    report = {
        "type": "tool_result",
        "tool_use_id": "report",
        "content": [
            {
                "type": "text",
                "text": json.dumps({"status": "ok", "failed_checks": []}),
            }
        ],
    }
    events = [
        {"type": "assistant", "message": {"content": calls}},
        {"type": "user", "message": {"content": [render, report]}},
    ]
    assert _stage_review(events)["status"] == "ok"
    report["is_error"] = True
    assert "report_not_read" in _stage_review(events)["reasons"]
    report["is_error"] = False
    render["content"].pop(0)
    events.append(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "unrelated-template",
                        "content": [{"type": "image", "data": "png"}],
                    }
                ]
            },
        }
    )
    assert "image_not_exposed" in _stage_review(events)["reasons"]


def test_capture_accepts_builtin_inventory_and_rejects_custom_context(tmp_path):
    """Observed builtins are host metadata; custom agents/plugins remain contamination."""
    csv = tmp_path / "input.csv"
    csv.write_bytes(b"x,y\n1,2\n")
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    # Sanitized from the actual 2.1.303 smoke init: no user paths or credentials.
    initialized = {
        "type": "system",
        "subtype": "init",
        "model": "selected",
        "tools": [
            "Read",
            "ListMcpResourcesTool",
            "ReadMcpResourceTool",
            "mcp__dartwork_mpl__render_plot",
        ],
        "mcp_servers": [
            {"name": "dartwork_mpl", "status": "connected", "source": "dynamic"}
        ],
        "agents": [
            "claude",
            "Explore",
            "general-purpose",
            "Plan",
            "statusline-setup",
        ],
        "skills": [],
        "plugins": [
            {"name": name, "path": "builtin", "source": name + "@builtin"}
            for name in (
                "cc-plugin-agents-md",
                "cc-plugin-telemetry",
                "cc-plugin-plugin-authoring",
            )
        ],
        "additional_directories": [],
    }
    terminal = {"type": "result", "subtype": "success", "is_error": False}
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(initialized) + "\n" + json.dumps(terminal) + "\n"
    )
    assert validate_capture(path, csv, digest, "selected")["status"] == "ok"
    for mutation in (
        "agent",
        "plugin_name",
        "plugin_path",
        "plugin_source",
        "skills",
        "directory",
        "tool",
        "mcp",
    ):
        changed = json.loads(json.dumps(initialized))
        if mutation == "agent":
            changed["agents"].append("custom-agent")
        elif mutation.startswith("plugin_"):
            changed["plugins"][0][mutation.removeprefix("plugin_")] = "custom"
        elif mutation == "skills":
            changed["skills"] = ["custom-skill"]
        elif mutation == "directory":
            changed["additional_directories"] = ["/outside"]
        elif mutation == "tool":
            changed["tools"].append("Bash")
        else:
            changed["mcp_servers"].append(
                {"name": "other", "status": "connected"}
            )
        path.write_text(
            json.dumps(changed) + "\n" + json.dumps(terminal) + "\n"
        )
        assert (
            validate_capture(path, csv, digest, "selected")["status"]
            == "failed"
        ), mutation


def test_stage_budget_reservations_never_exceed_authorized_corpus_cap(tmp_path):
    """Explicit repair consumes only unused smoke caps and duplicate stages refuse."""
    ledger = tmp_path / "corpus.json"
    ledger.write_text(json.dumps({"attempts": ["smoke/line"], "started_at": 0}))
    old = tmp_path / "smoke/line/original"
    old.mkdir(parents=True)
    (old / "invocation.json").write_text(json.dumps({"budget_usd": 0.4}))
    for stage in ("original", "revision", "recovery"):
        assert (
            _reserve_stage(tmp_path, "smoke-repair/line/" + stage, 0.2)[
                "status"
            ]
            == "ok"
        )
    for label in ("baseline", "candidate"):
        for case in ("line", "groupedbar", "scatter", "custom2panel"):
            for stage, cap in (
                ("original", 2),
                ("revision", 2),
                ("recovery", 1),
            ):
                assert (
                    _reserve_stage(tmp_path, f"{label}/{case}/{stage}", cap)[
                        "status"
                    ]
                    == "ok"
                )
    before = ledger.read_bytes()
    assert json.loads(before)["invoked_budget_usd_cap"] == 41
    assert (
        _reserve_stage(tmp_path, "extra", 0.01)["reason"]
        == "corpus_budget_limit"
    )
    assert (
        _reserve_stage(tmp_path, "baseline/line/original", 2)["reason"]
        == "stage_already_attempted"
    )
    assert ledger.read_bytes() == before


def test_repair_admission_only_accepts_recorded_builtin_harness_failure():
    """The one repair cannot become a model-quality or partial-stage retry."""
    original = {
        "status": "failed",
        "stop_reason": "original_integration_failed",
        "stages": {
            "original": {
                "capture": {
                    "status": "failed",
                    "reasons": ["unexpected_context"],
                },
                "process": {
                    "stop_reason": "exit",
                    "returncode": 0,
                    "cleanup_ok": True,
                },
                "review": {"status": "ok"},
            }
        },
    }
    assert _repair_admission(original, 0.4)
    assert not _repair_admission(original, 0.2)
    for mutation in (
        "extra_stage",
        "quality_failure",
        "process_failure",
        "cleanup_failure",
        "failed_review",
        "other_reason",
    ):
        changed = json.loads(json.dumps(original))
        stage = changed["stages"]["original"]
        if mutation == "extra_stage":
            changed["stages"]["revision"] = {}
        elif mutation == "quality_failure":
            changed["stop_reason"] = "render_failed"
        elif mutation == "process_failure":
            stage["process"]["returncode"] = 1
        elif mutation == "cleanup_failure":
            stage["process"]["cleanup_ok"] = False
        elif mutation == "failed_review":
            stage["review"]["status"] = "failed"
        else:
            stage["capture"]["reasons"].append("oracle_access")
        assert not _repair_admission(changed, 0.4), mutation


def _write_test_admission(root: Path, review: str = "passed") -> None:
    """Create evaluator-owned admission evidence for an account-free host fixture."""
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    smoke_runs = {}
    for relative in ("smoke/line/run.json", "smoke-repair/line/run.json"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"status": "failed"}))
        smoke_runs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    record = {
        "policy": "phase0-observed-infrastructure-2026-10-20",
        "code_review": review,
        "smoke_runs": smoke_runs,
        "fresh_agent_recovery": "unverified",
        "observed": dict.fromkeys(
            (
                "image",
                "full_report",
                "resume",
                "configured_model",
                "cleanup",
                "real_stdio_recovery",
            ),
            True,
        ),
    }
    (root / "runtime/admission-decision.json").write_text(json.dumps(record))


@pytest.mark.parametrize("replay_limited", [False, True])
def test_failed_revision_keeps_exact_replay_before_workspace_cleanup(
    tmp_path, monkeypatch, replay_limited
):
    """A final report omission still preserves replay evidence before CSV deletion."""
    import time

    import run_agent_plot_eval as capture

    root = tmp_path / "evidence"
    (root / "runtime").mkdir(parents=True)
    (root / "runtime/selection.json").write_text(
        json.dumps({"model": "selected", "effort": "high"})
    )
    (root / "corpus.json").write_text(
        json.dumps({"started_at": time.time(), "attempts": []})
    )
    _write_test_admission(root)
    host = tmp_path / "owned-host"
    # Our synthetic host adapter executes the real stdio server, not a model.
    # Its revision deliberately omits report access. No live account is invoked.
    host.write_text(
        f"#!{sys.executable}\n"
        + r'''import asyncio, json, os, re, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl
args = sys.argv
config = json.load(open(args[args.index('--mcp-config') + 1]))['mcpServers']['dartwork_mpl']
revision = '--resume' in args
recovery = args[-1].startswith('Reopen both stored artifacts')
session = args[args.index('--resume' if revision else '--session-id') + 1]
code = """import csv
import matplotlib.pyplot as plt
import dartwork_mpl as dm
with open('line.csv') as handle:
    rows = [r for r in csv.DictReader(handle) if r['y'] not in ('', 'NA')]
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([float(r['x']) for r in rows], [float(r['y']) for r in rows], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""
if revision: code += "ax.set_title('revision')\n"
def emit(value):
    print(json.dumps(value), flush=True)
async def main():
    params = StdioServerParameters(command=config['command'], cwd=os.getcwd(), env={**os.environ, **config['env']})
    async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
        await client.initialize()
        emit({'type':'system','subtype':'init','session_id':session,'model':'selected','tools':['Read','ReadMcpResourceTool','mcp__dartwork_mpl__render_plot'],'mcp_servers':[{'name':'dartwork_mpl','status':'connected'}]})
        if recovery:
            assert not os.path.exists('line.csv')
            for index, identity in enumerate(re.findall(r'\b[0-9a-f]{32}\b', args[-1])):
                call_id='get'+str(index)
                emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':call_id,'name':'mcp__dartwork_mpl__get_plot_artifact','input':{'artifact_id':identity}}]}})
                stored=await client.call_tool('get_plot_artifact', {'artifact_id':identity})
                emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':call_id,'content':[b.model_dump(mode='json') for b in stored.content]}]}})
                uri='dartwork-mpl://artifacts/'+identity+'/report.json'
                emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':'report'+str(index),'name':'ReadMcpResourceTool','input':{'uri':uri}}]}})
                report=await client.read_resource(AnyUrl(uri))
                emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'report'+str(index),'content':[{'type':'text','text':report.contents[0].text}]}]}})
            emit({'type':'result','subtype':'success','session_id':session,'is_error':False,'usage':{},'total_cost_usd':0,'modelUsage':{'selected':{}}})
            return
        emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':'render','name':'mcp__dartwork_mpl__render_plot','input':{'code':code}}]}})
        rendered = await client.call_tool('render_plot', {'code':code})
        emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'render','content':[b.model_dump(mode='json') for b in rendered.content]}]}})
        if not revision:
            uri='dartwork-mpl://artifacts/'+rendered.structuredContent['artifact_id']+'/report.json'
            emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':'report','name':'ReadMcpResourceTool','input':{'uri':uri}}]}})
            report=await client.read_resource(AnyUrl(uri))
            emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'report','content':[{'type':'text','text':report.contents[0].text}]}]}})
        emit({'type':'result','subtype':'success','session_id':session,'is_error':False,'usage':{},'total_cost_usd':0,'modelUsage':{'selected':{}}})
asyncio.run(main())
'''
    )
    host.chmod(0o700)
    monkeypatch.setattr(capture, "_HOST", host)
    if replay_limited:
        real_replay = capture.replay

        def lowered_replay(*args, **kwargs):
            """Apply a tiny remaining replay allowance without changing source bytes."""
            evidence = args[3].parents[1]
            used = sum(
                path.stat().st_size
                for path in evidence.rglob("*")
                if path.is_file()
            )
            kwargs.update(
                evidence_root=evidence, max_evidence_bytes=used + 2048
            )
            return real_replay(*args, **kwargs)

        monkeypatch.setattr(capture, "replay", lowered_replay)
    directory = capture.run_episode("line", "baseline", root)
    state = json.loads((directory / "run.json").read_text())
    if replay_limited:
        assert state["stop_reason"] == "replay_evidence_limit"
        assert state["status"] == "failed"
        assert state["infrastructure_status"] == "failed"
        assert list(state["stages"]) == ["original"]
        assert state["replays"]["original"]["stop_reason"] == "evidence_limit"
        assert not (directory / "revision").exists()
        assert not (directory / "recovery").exists()
        ledger = json.loads((root / "corpus.json").read_text())
        assert set(ledger["stage_invocations"]) == {"baseline/line/original"}
        assert state["workspace_cleanup"]
        return
    assert state["stages"]["recovery"]["review"]["status"] == "ok"
    assert state["status"] == "failed"
    assert state["stop_reason"] == "workflow_failed"
    assert state["infrastructure_status"] == "ok"
    assert state["workflow_status"] == "failed"
    recovery_events = [
        json.loads(line)
        for line in (directory / "recovery/events.jsonl")
        .read_text()
        .splitlines()
    ]
    recovery_calls = [
        block["name"]
        for event in recovery_events
        if event.get("type") == "assistant"
        for block in event["message"]["content"]
        if block.get("type") == "tool_use"
    ]
    assert recovery_calls.count("mcp__dartwork_mpl__get_plot_artifact") == 2
    assert "mcp__dartwork_mpl__render_plot" not in recovery_calls
    assert state["recovery_hashes"]

    assert state["stages"]["revision"]["review"]["reasons"] == [
        "report_not_read"
    ]
    assert state["replays"]["revision"]["status"] == "ok"
    assert state["replays"]["revision"]["assessment"]["passed"]
    assert state["workspace_cleanup"]
    invocation = json.loads(
        (directory / "revision/invocation.json").read_text()
    )
    assert not Path(invocation["cwd"]).exists()
    assert (directory / "revision/source.py").read_bytes()
    assert (directory / "replay/revision/plot.png").exists()
    evaluated = evaluate(directory)
    assert evaluated["dimensions"]["delivery"]["passed"]
    assert evaluated["dimensions"]["declared_validation"]["passed"]
    assert evaluated["dimensions"]["semantic_replay"]["passed"]
    assert evaluated["dimensions"]["model_review"]["status"] == "failed"
    assert evaluated["dimensions"]["visual_review"]["status"] == "unchecked"
    assert evaluated["dimensions"]["human_code_edits"]["status"] == "unchecked"


def test_scored_admission_binds_both_failed_smokes_and_unknown_agent_recovery(
    tmp_path,
):
    """The explicit partial-readiness decision never upgrades smoke or missing recovery."""
    (tmp_path / "runtime").mkdir()
    evidence = {}
    for relative in ("smoke/line/run.json", "smoke-repair/line/run.json"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"status": "failed"}))
        evidence[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    decision = {
        "policy": "phase0-observed-infrastructure-2026-10-20",
        "code_review": "passed",
        "smoke_runs": evidence,
        "fresh_agent_recovery": "unverified",
        "observed": dict.fromkeys(
            (
                "image",
                "full_report",
                "resume",
                "configured_model",
                "cleanup",
                "real_stdio_recovery",
            ),
            True,
        ),
    }
    record = tmp_path / "runtime/admission-decision.json"
    record.write_text(json.dumps(decision))
    assert _admission_decision(tmp_path)["status"] == "ok"
    decision["code_review"] = "pending"
    record.write_text(json.dumps(decision))
    assert _admission_decision(tmp_path)["status"] == "failed"
    decision["code_review"] = "passed"
    decision["fresh_agent_recovery"] = "passed"
    record.write_text(json.dumps(decision))
    assert _admission_decision(tmp_path)["status"] == "failed"
    decision["fresh_agent_recovery"] = "unverified"
    record.write_text(json.dumps(decision))
    (tmp_path / "smoke/line/run.json").write_text(json.dumps({"status": "ok"}))
    assert _admission_decision(tmp_path)["status"] == "failed"
    assert not (tmp_path / "baseline").exists()


def test_evidence_copies_and_appends_refuse_bytes_above_ceiling(tmp_path):
    """Collector copies and top-level transcript duplication share the evidence cap."""
    from run_agent_plot_eval import _write_bytes

    (tmp_path / "existing").write_bytes(b"12345678")
    target = tmp_path / "member"
    assert not _write_bytes(target, b"123", tmp_path, max_bytes=10)
    assert not target.exists()
    assert _write_bytes(target, b"12", tmp_path, max_bytes=10)
    assert not _write_bytes(target, b"3", tmp_path, append=True, max_bytes=10)
    assert target.read_bytes() == b"12"


@pytest.mark.parametrize("label", ["baseline", "candidate"])
@pytest.mark.parametrize("admission", ["missing", "pending", "changed"])
def test_public_episode_rejects_admission_before_collector_or_host(
    tmp_path, monkeypatch, label, admission
):
    """Every scored entry point enforces the review decision before external work."""
    import run_agent_plot_eval as capture

    root = tmp_path / "corpus"
    _write_test_admission(
        root, "pending" if admission == "pending" else "passed"
    )
    (root / "runtime/selection.json").write_text(
        json.dumps({"model": "selected", "effort": "high"})
    )
    if admission == "missing":
        (root / "runtime/admission-decision.json").unlink()
    elif admission == "changed":
        (root / "smoke/line/run.json").write_text(json.dumps({"status": "ok"}))
    calls = []

    def collector_tripwire(request, output_dir):
        """Record an erroneously reached owned adapter without starting any host."""
        calls.append("collector")
        return {"status": "failed", "reason": "tripwire"}

    monkeypatch.setattr(capture, "_collect", collector_tripwire)
    directory = capture.run_episode("line", label, root)
    state = json.loads((directory / "run.json").read_text())
    assert calls == []
    assert state["status"] == "failed"
    assert state["stop_reason"] == "admission_rejected"
    assert state["admission_decision"]["status"] == "failed"
    assert state["stages"] == {}
    assert not (directory / "original").exists()
    assert not (root / "corpus.json").exists()


@pytest.mark.parametrize("output", ["stdout", "stderr", "members"])
def test_replay_enforces_shared_evidence_limit_during_execution(
    tmp_path, output
):
    """Replay streams and generated members cannot consume prior episode capacity."""
    csv = tmp_path / "input.csv"
    csv.write_text("x,y\n1,2\n")
    source = tmp_path / "source.py"
    source.write_text(
        """import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1], [2], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""
        + (
            "print('x' * (512 * 1024))\n"
            if output == "stdout"
            else "raise ValueError('x' * (512 * 1024))\n"
            if output == "stderr"
            else ""
        )
    )
    cap = 128 * 1024 if output != "members" else 4 * 1024
    (tmp_path / "prior-evidence").write_bytes(b"a" * (cap // 2))
    before = csv.read_bytes(), source.read_bytes()
    result = replay(
        source,
        csv,
        "line",
        tmp_path / "replay",
        evidence_root=tmp_path,
        max_evidence_bytes=cap,
    )
    assert result["status"] == "failed"
    assert result["stop_reason"] == "evidence_limit"
    assert result["process"]["cleanup_ok"]
    assert (csv.read_bytes(), source.read_bytes()) == before
    assert (
        sum(
            path.stat().st_size
            for path in tmp_path.rglob("*")
            if path.is_file()
        )
        <= cap
    )
    assert (
        json.loads((tmp_path / "replay/result.json").read_text())["stop_reason"]
        == "evidence_limit"
    )
    if output != "members":
        partial = tmp_path / "replay" / (output + ".txt")
        assert 0 < partial.stat().st_size < 512 * 1024
