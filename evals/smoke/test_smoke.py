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
    """The review corpus is exactly ten fresh requests with only local inputs."""
    cases = [
        json.loads(p.read_text())
        for p in (smoke.HERE / "cases").glob("*/case.json")
    ]
    assert len(cases) == 10
    assert Counter(c["lang"] for c in cases) == {"ko": 5, "en": 5}
    assert Counter(c["kind"] for c in cases) == {"generate": 7, "edit": 3}
    for case in cases:
        assert set(case) == {"id", "kind", "lang", "request"}
        folder = smoke.HERE / "cases" / case["id"]
        assert (folder / "data.csv").is_file()
        assert (folder / "plot.py").is_file() == (case["kind"] == "edit")


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
