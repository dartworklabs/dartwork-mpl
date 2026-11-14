"""Model-free checks for receipts, case shape and real filesystem isolation."""

import importlib.util
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "smoke_runner", Path(__file__).with_name("run_smoke.py")
)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def test_case_inventory_is_balanced_and_has_no_answers():
    """The review corpus is thirty-eight requests with only local inputs."""
    cases = [
        json.loads(p.read_text())
        for p in (smoke.HERE / "cases").glob("*/case.json")
    ]
    assert len(cases) == 38
    assert Counter(c["lang"] for c in cases) == {"ko": 18, "en": 20}
    assert Counter(c["kind"] for c in cases) == {
        "generate": 22,
        "edit": 7,
        "repair": 4,
        "series": 5,
    }
    for case in cases:
        series = case["kind"] == "series"
        assert set(case) == {"id", "kind", "lang", "request"} | (
            {"followups"} if series else set()
        )
        # A series is the same figure changed at least three times.
        assert len(smoke.turn_requests(case)) >= (4 if series else 1)
        assert (len(smoke.turn_requests(case)) > 1) == series
        folder = smoke.HERE / "cases" / case["id"]
        assert (folder / "data.csv").is_file()
        assert (folder / "plot.py").is_file() == smoke.has_base(case)
        assert sorted(p.name for p in folder.iterdir()) == sorted(
            ["case.json", "data.csv", *(["plot.py"] * smoke.has_base(case))]
        )


def test_edit_and_repair_start_from_a_base_and_generate_does_not():
    """A base script is rendered, validated and kept apart from the revision."""
    assert smoke.has_base({"kind": "edit"})
    assert smoke.has_base({"kind": "repair"})
    assert not smoke.has_base({"kind": "generate"})
    assert smoke.final_script({"kind": "repair"}) == "revision.py"
    assert smoke.final_script({"kind": "generate"}) == "plot.py"


def test_warning_ids_keep_only_warnings_once_each():
    """INFO findings are hints; a WARNING id repeated across saves counts once."""
    reports = [
        {
            "findings": [
                {"check_id": "TICK_OVERLAP", "severity": "WARNING"},
                {"check_id": "TICK_CROWD", "severity": "INFO"},
            ]
        },
        {
            "findings": [
                {"check_id": "TICK_OVERLAP", "severity": "WARNING"},
                {"check_id": "LEGEND_ON_DATA", "severity": "WARNING"},
            ]
        },
    ]
    assert smoke.warning_ids(reports) == ["LEGEND_ON_DATA", "TICK_OVERLAP"]
    assert smoke.warning_ids([]) == []


def test_summary_shows_the_base_warnings_beside_the_final_ones(tmp_path):
    """A repair is read as before → after; a figure with no base shows none."""
    records = [
        {
            "case": "r01",
            "host": "claude",
            "execution": "success",
            "validator": "re-ran",
            "warnings": [],
            "base_validator": "re-ran",
            "base_warnings": ["LEGEND_ON_DATA"],
            "tokens": None,
            "turns": 3,
        },
        {
            "case": "g01",
            "host": "codex",
            "execution": "success",
            "validator": "re-ran",
            "warnings": ["TICK_OVERLAP"],
            "tokens": None,
            "turns": 2,
        },
    ]
    smoke.summary(tmp_path, records)
    rows = (tmp_path / "SUMMARY.md").read_text().splitlines()
    repair = next(r for r in rows if "r01/claude" in r).split("|")
    fresh = next(r for r in rows if "g01/codex" in r).split("|")
    header = next(r for r in rows if r.startswith("| Case")).split("|")
    base = header.index(" Base WARNING ids ")
    assert repair[base].strip() == "LEGEND_ON_DATA"
    assert repair[base + 1].strip() == "none"
    assert fresh[base].strip() == "no base"
    assert fresh[base + 1].strip() == "TICK_OVERLAP"


def test_native_usage_preserves_cache_fields_and_missing_values():
    """Missing usage is unknown, and native host counters are retained."""
    assert smoke.usage("claude", [])["tokens"] is None
    assert smoke.usage("codex", [])["turns"] is None
    rows = [
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 9,
                "cached_input_tokens": 4,
                "output_tokens": 2,
            },
        }
    ] * 2
    assert smoke.usage("codex", rows)["tokens"] == {
        "input_tokens": 18,
        "cached_input_tokens": 8,
        "output_tokens": 4,
    }
    result = {
        "type": "result",
        "usage": {"cache_read_input_tokens": 5},
        "num_turns": 3,
    }
    assert smoke.usage("claude", [result])["turns"] == 3


def test_os_sandbox_blocks_repository_results_siblings_and_external_writes():
    """Actual child reads/writes are denied while its own CSV remains readable."""
    smoke.WORK.mkdir(parents=True, exist_ok=True)
    smoke.ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=smoke.WORK) as folder:
        project = Path(folder).resolve()
        (project / "data.csv").write_text("input")
        (project / ".venv/bin").mkdir(parents=True)
        (project / ".venv/bin/python").symlink_to("/usr/bin/python3")
        smoke.probe(project, smoke.hidden_paths(), smoke.environment(project))
        outside = smoke.WORK / "forbidden-write.txt"
        code = "from pathlib import Path; Path('allowed').write_text('ok'); Path(__import__('sys').argv[1]).write_text('bad')"
        result = subprocess.run(
            smoke.sandbox(
                ["/usr/bin/python3", "-c", code, str(outside)],
                project,
                smoke.hidden_paths(),
            ),
            cwd=project,
            capture_output=True,
        )
        assert result.returncode != 0
        assert (project / "allowed").read_text() == "ok"
        assert not outside.exists()


def test_unsafe_run_ids_and_unknown_cases_are_rejected_without_models():
    """Selection cannot escape the result root or silently run a different case."""
    for args in (["--run-id", "../escape"], ["--cases", "unknown"]):
        with pytest.raises(SystemExit) as exc:
            from unittest.mock import patch

            with patch("sys.argv", ["run_smoke.py", *args]):
                smoke.main()
        assert exc.value.code == 2


def test_host_version_startup_with_captured_pipes_needs_no_model_calls():
    """Node and native CLI startup must work with Seatbelt-confined outputs."""
    with tempfile.TemporaryDirectory(dir=smoke.WORK) as folder:
        project = Path(folder).resolve()
        (project / ".tmp").mkdir()
        (project / ".codex").mkdir()
        for host in ("claude", "codex"):
            unit = smoke.ROOT / (project.name + "-" + host)
            unit.mkdir()
            record = smoke.run_host(
                smoke.sandbox(
                    [smoke.executable(host), "--version"],
                    project,
                    smoke.hidden_paths(),
                ),
                project,
                smoke.environment(project),
                unit,
                10,
            )
            assert record["exit_code"] == 0
            assert (unit / "events.jsonl").stat().st_size > 0
            import shutil

            shutil.rmtree(unit)


def test_timeout_kills_child_group_and_keeps_partial_transcript():
    """An overdue process cannot leave its child running after receipt creation."""
    with tempfile.TemporaryDirectory(dir=smoke.WORK) as folder:
        project = Path(folder).resolve()
        record = smoke.run_host(
            [
                "/usr/bin/python3",
                "-c",
                "import time; print('started',flush=True); time.sleep(30)",
            ],
            project,
            smoke.environment(project),
            project,
            0.2,
        )
        assert record["timed_out"] is True
        assert record["exit_code"] != 0
        assert (project / "events.jsonl").read_text().strip() == "started"


def _claude_read(tool_id, path, at, called_at=None):
    """A timestamped Claude image Read call and its successful image result."""
    call = {
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "id": tool_id,
                    "input": {"file_path": path},
                }
            ]
        }
    }
    result = {
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": [{"type": "image"}],
                }
            ]
        }
    }
    return [
        {
            "received_at": at if called_at is None else called_at,
            "line": json.dumps(call),
        },
        {"received_at": at, "line": json.dumps(result)},
    ]


def test_viewing_another_image_with_the_same_name_is_not_inspection(tmp_path):
    """Only a view of the final artifact's own path counts, relative or absolute."""
    final = tmp_path / "out" / "figure.png"
    draft = _claude_read("t1", str(tmp_path / "draft" / "figure.png"), 20)
    relative = _claude_read("t2", "out/figure.png", 20)

    assert smoke.inspection(
        "claude", [], [], final, 10, draft, tmp_path
    ).startswith("unknown")
    assert smoke.inspection(
        "claude", [], [], final, 10, relative, tmp_path
    ).startswith("yes")

    def rollout(path):
        return [
            {
                "timestamp": "2026-11-11T00:00:20Z",
                "payload": {
                    "type": "function_call",
                    "name": "view_image",
                    "arguments": json.dumps({"path": path}),
                },
            }
        ]

    assert smoke.inspection(
        "codex", [], rollout("draft/figure.png"), final, 10, (), tmp_path
    ).startswith("unknown")
    assert smoke.inspection(
        "codex", [], rollout(str(final)), final, 10, (), tmp_path
    ).startswith("attempted")


def _codex_exec_view(path, at, image=True, call_id="call_1"):
    """Codex's code tool: a script that views an image, and what came back."""
    stamp = f"2026-11-11T00:00:{at:02d}Z"
    output = [{"type": "input_text", "text": "Script completed"}]
    if image:
        output.append(
            {"type": "input_image", "image_url": "data:image/png;base64,AA"}
        )
    return [
        {
            "timestamp": stamp,
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "call_id": call_id,
                "input": f"const r=await tools.view_image({{path:{json.dumps(path)}}});image(r.image_url);\n",
            },
        },
        {
            "timestamp": stamp,
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": call_id,
                "output": output,
            },
        },
    ]


def test_an_image_viewed_through_codex_code_tool_is_inspection(tmp_path):
    """Rounds 1 to 4 recorded "unknown" for every Codex unit although the
    model was sent the PNG each time: Codex views images from inside its
    ``exec`` tool, not through a ``view_image`` function call."""
    final = tmp_path / "out" / "figure.png"
    # 2026-11-11T00:00:00Z, so second 20 is after a write at +10.
    midnight = 1794355200

    def seen(rows, written_at=10):
        return smoke.inspection(
            "codex", [], rows, final, midnight + written_at, (), tmp_path
        )

    assert seen(_codex_exec_view(str(final), 20)).startswith("yes")
    assert seen(_codex_exec_view("out/figure.png", 20)).startswith("yes")
    # Before the last write, another file, or no image came back: not this.
    assert seen(_codex_exec_view(str(final), 5)).startswith("unknown")
    assert seen(
        _codex_exec_view(str(tmp_path / "out" / "original.png"), 20)
    ).startswith("unknown")
    assert seen(_codex_exec_view(str(final), 20, image=False)).startswith(
        "unknown"
    )


def test_replay_can_write_only_inside_its_own_directory():
    """A replayed script cannot create outputs in the host's project folder."""
    smoke.WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="unit-", dir=smoke.WORK) as folder:
        project = Path(folder).resolve()
        replay = project / "replay"
        replay.mkdir()
        (project / "out").mkdir()
        (project / "input.txt").write_text("readable")

        def run(code):
            return subprocess.run(
                smoke.sandbox(
                    ["/usr/bin/python3", "-c", code], project, [], replay
                ),
                capture_output=True,
                text=True,
                check=False,
            ).returncode

        host_side = project / "out" / "figure.png"
        assert run(f"open({str(host_side)!r}, 'w').write('x')") != 0
        assert not host_side.exists()
        assert run(f"open({str(replay / 'figure.png')!r}, 'w').write('x')") == 0
        assert run(f"print(open({str(project / 'input.txt')!r}).read())") == 0


def test_host_outputs_require_both_real_files(tmp_path):
    """Host-produced outputs are a real PNG and PDF, never a symlink."""
    out = tmp_path / "out"
    out.mkdir()
    assert not smoke.host_outputs(tmp_path)
    (out / "figure.png").write_bytes(b"p")
    assert not smoke.host_outputs(tmp_path)
    (out / "figure.pdf").write_bytes(b"d")
    assert smoke.host_outputs(tmp_path)
    (out / "figure.pdf").unlink()
    (out / "figure.pdf").symlink_to(out / "figure.png")
    assert not smoke.host_outputs(tmp_path)


def test_a_read_requested_before_the_final_write_counts_by_its_result_time(
    tmp_path,
):
    """The image result's arrival, not the request, is compared with the write."""
    final = tmp_path / "out" / "figure.png"
    requested_early = _claude_read("t1", str(final), 20, called_at=5)
    returned_early = _claude_read("t2", str(final), 5, called_at=5)

    assert smoke.inspection(
        "claude", [], [], final, 10, requested_early, tmp_path
    ).startswith("yes")
    assert smoke.inspection(
        "claude", [], [], final, 10, returned_early, tmp_path
    ).startswith("unknown")


def test_every_case_input_is_tracked_by_git():
    """A case's CSV and base script exist on a fresh checkout, not only here.

    ``*.csv`` is ignored repository-wide, so a new case's ``data.csv`` is left
    out of a commit unless the ignore rule lets it through.
    """
    tracked = set(
        subprocess.run(
            ["git", "ls-files", "cases"],
            cwd=smoke.HERE,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    )
    on_disk = {
        path.relative_to(smoke.HERE).as_posix()
        for path in (smoke.HERE / "cases").glob("*/*")
        if path.is_file()
    }
    assert on_disk - tracked == set()


def test_replay_finds_what_the_host_left_in_out_and_keeps_only_new_files(
    tmp_path, monkeypatch
):
    """Round 3: a revision reviewed against ``out/original`` could not re-run.

    The review loop writes ``dm.review(fig, stem, baseline="out/original")``,
    so the replayed script reads a file the host left in ``out/``. The replay
    gets a copy of that folder; only what the replay itself wrote is kept as
    a re-rendered output.
    """
    smoke.WORK.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        smoke,
        "REPLAY",
        "import json, runpy, sys\n"
        "runpy.run_path(sys.argv[1], run_name='__main__')\n"
        "open('validator.json', 'w').write(json.dumps([{'findings': []}]))\n",
    )
    with tempfile.TemporaryDirectory(prefix="unit-", dir=smoke.WORK) as folder:
        project = Path(folder).resolve()
        (project / "out").mkdir()
        (project / "out" / "original.review.json").write_text("{}")
        (project / "out" / "figure.png").write_text("host")
        (project / "revision.py").write_text(
            "open('out/original.review.json').read()\n"
            "open('out/figure.png', 'w').write('replayed')\n"
        )
        reports = smoke.replay(
            project,
            "revision.py",
            "/usr/bin/python3",
            smoke.environment(project),
            [],
            tmp_path,
        )
        assert reports == [{"findings": []}]
        assert (project / "out" / "figure.png").read_text() == "host"
        kept = sorted(p.name for p in (tmp_path / "replay-artifacts").iterdir())
        assert kept == ["figure.png"]
        assert (tmp_path / "replay-artifacts/figure.png").read_text() == (
            "replayed"
        )


FAKE_HOST = r"""
import json, sys, time
from pathlib import Path
plan = json.loads(sys.argv[1])
for count, line in enumerate(sys.stdin, 1):
    Path(f"got-{count}").write_text(json.loads(line)["message"]["content"][0]["text"])
    step = plan.get(str(count), "answer")
    if step == "hang":
        time.sleep(60)
    if step == "die":
        sys.exit(3)
    print(json.dumps({"type": "assistant"}), flush=True)
    print(json.dumps({"type": "result", "is_error": False,
                      "usage": {"output_tokens": count}, "num_turns": 1}), flush=True)
"""


def _fake_turns(project, plan, messages, timeout=10):
    """Run the stand-in host through ``run_turns``; no model, no sandbox."""
    (project / "host.py").write_text(FAKE_HOST)
    settled = []

    def settle(index):
        # The host has this turn's message and has not been sent the next.
        settled.append((index, sorted(p.name for p in project.glob("got-*"))))

    turns = smoke.run_turns(
        ["/usr/bin/python3", "host.py", json.dumps(plan)],
        messages,
        project,
        smoke.environment(project),
        project,
        timeout,
        settle,
    )
    return turns, settled


def test_a_series_sends_one_message_per_answer_and_settles_in_between(tmp_path):
    """Each turn is judged before the host hears the next request."""
    turns, settled = _fake_turns(tmp_path, {}, ["first", "second", "third"])
    assert [t["exit_code"] for t in turns] == [0, 0, 0]
    assert not any(t["timed_out"] for t in turns)
    assert settled == [
        (1, ["got-1"]),
        (2, ["got-1", "got-2"]),
        (3, ["got-1", "got-2", "got-3"]),
    ]
    assert (tmp_path / "got-2").read_text() == "second"
    rows = smoke.events(tmp_path / "events.jsonl")
    assert [r["type"] for r in rows] == ["assistant", "result"] * 3


def test_a_turn_that_runs_out_of_time_ends_the_series(tmp_path):
    """The deadline is per turn; later requests are never sent."""
    turns, settled = _fake_turns(
        tmp_path, {"2": "hang"}, ["first", "second", "third"], timeout=0.5
    )
    assert [t["timed_out"] for t in turns] == [False, True]
    assert turns[1]["exit_code"] is None
    assert [index for index, _ in settled] == [1]
    assert not (tmp_path / "got-3").exists()


def test_a_host_that_dies_mid_turn_ends_the_series_without_waiting(tmp_path):
    """A dead host is a failed turn at once, not a timeout."""
    turns, settled = _fake_turns(
        tmp_path, {"2": "die"}, ["first", "second", "third"], timeout=60
    )
    assert [t["exit_code"] for t in turns] == [0, 3]
    assert turns[1]["timed_out"] is False and turns[1]["wall_s"] < 10
    assert [index for index, _ in settled] == [1]


def test_a_later_process_adds_to_the_transcript(tmp_path):
    """The turns of a Codex series are separate processes with one transcript."""
    for word in ("one", "two"):
        smoke.run_host(
            ["/usr/bin/python3", "-c", f"print({word!r})"],
            tmp_path,
            smoke.environment(tmp_path),
            tmp_path,
            10,
        )
    assert (tmp_path / "events.jsonl").read_text().split() == ["one", "two"]


def test_host_commands_keep_one_conversation(tmp_path):
    """Claude reads its turns from stdin; Codex resumes the first turn's thread."""
    claude = smoke.host_command("claude", None, tmp_path)
    at = claude.index("--input-format")
    assert claude[at - 1 : at + 2] == ["-p", "--input-format", "stream-json"]
    once = smoke.host_command("claude", "draw it", tmp_path)
    assert once[1:3] == ["-p", "draw it"] and "--input-format" not in once
    codex = smoke.host_command("codex", "now sort it", tmp_path, "thread-7")
    assert codex[1:3] == ["exec", "resume"]
    assert codex[-2:] == ["thread-7", "now sort it"] and "-C" not in codex
    first = smoke.host_command("codex", "draw it", tmp_path)
    assert first[1] == "exec" and "resume" not in first
    assert first[first.index("-C") + 1] == str(tmp_path)


def test_usage_of_a_series_adds_up_its_answers():
    """One result per user message; the counters of a conversation are summed."""
    rows = [
        {
            "type": "result",
            "usage": {"output_tokens": n, "cache_read_input_tokens": 10},
            "num_turns": n,
            "is_error": False,
        }
        for n in (2, 3)
    ]
    assert smoke.usage("claude", rows) == {
        "tokens": {"output_tokens": 5, "cache_read_input_tokens": 20},
        "turns": 5,
        "host_error": False,
    }
    assert smoke.usage("claude", rows[:1])["tokens"] == rows[0]["usage"]


def test_summary_lists_a_series_turn_by_turn(tmp_path):
    """A series is read as what each turn left, not only the last figure."""
    turn = {
        "outputs": True,
        "validator": "re-ran",
        "tokens": None,
        "turns": 4,
        "wall_s": 61.0,
        "opened_final_png": "yes",
    }
    record = {
        "case": "s01",
        "host": "claude",
        "execution": "failure",
        "validator": "re-ran",
        "warnings": ["LEGEND_ON_DATA"],
        "tokens": None,
        "turns": 8,
        "turns_asked": 4,
        "turn_records": [
            {**turn, "turn": 1, "warnings": []},
            {**turn, "turn": 2, "warnings": ["LEGEND_ON_DATA"]},
        ],
    }
    smoke.summary(tmp_path, [record])
    rows = (tmp_path / "SUMMARY.md").read_text().splitlines()
    turns = [r.split("|") for r in rows if "turns/" in r]
    assert [r[2].split("]")[0].strip() for r in turns] == ["[1 of 4", "[2 of 4"]
    assert [r[4].strip() for r in turns] == ["none", "LEGEND_ON_DATA"]


def test_a_resumed_codex_session_reports_running_totals():
    """Codex counts from the start of the session; a turn is the rise since."""
    rows = [
        {"type": "thread.started"},
        {"type": "turn.completed", "usage": {"output_tokens": 1457}},
        {"type": "thread.started"},
        {"type": "turn.completed", "usage": {"output_tokens": 1861}},
        {"type": "thread.started"},
    ]
    turns, total = smoke.series_usage("codex", rows, [0, 2, 4])
    assert [t["tokens"] for t in turns] == [
        {"output_tokens": 1457},
        {"output_tokens": 404},
    ]
    assert total["tokens"] == {"output_tokens": 1861}
    answers = [
        {"type": "result", "usage": {"output_tokens": n}, "num_turns": 1}
        for n in (5, 8)
    ]
    turns, total = smoke.series_usage("claude", answers, [0, 1, 2])
    assert [t["tokens"] for t in turns] == [
        {"output_tokens": 5},
        {"output_tokens": 8},
    ]
    assert total["tokens"] == {"output_tokens": 13}


def test_the_turn_table_keeps_only_the_counters(tmp_path):
    """Nested host detail stays in run.json; the table shows the counts."""
    turn = {
        "turn": 1,
        "outputs": True,
        "validator": "re-ran",
        "warnings": [],
        "tokens": {"output_tokens": 7, "iterations": [{"output_tokens": 7}]},
        "turns": 2,
        "opened_final_png": "yes",
    }
    record = {
        "case": "s01",
        "host": "claude",
        "execution": "success",
        "validator": "re-ran",
        "warnings": [],
        "tokens": None,
        "turns": 2,
        "turns_asked": 1,
        "turn_records": [turn],
    }
    smoke.summary(tmp_path, [record])
    row = next(
        r
        for r in (tmp_path / "SUMMARY.md").read_text().splitlines()
        if "turns/1" in r
    )
    assert '{"output_tokens": 7}' in row and "iterations" not in row
