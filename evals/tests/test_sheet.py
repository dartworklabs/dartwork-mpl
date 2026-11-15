"""The summary and contact sheet from a fake run directory."""

from __future__ import annotations

import json
from pathlib import Path

from evals import sheet

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def fake_run(tmp_path: Path) -> Path:
    run = tmp_path / "20260101-000000"
    for case, arm, verdict in [
        ("bar", "bare", "OK"),
        ("bar", "skill", "DEFECT"),
        ("line", "bare", "NO_FIGURE"),
    ]:
        out = run / case / arm
        out.mkdir(parents=True)
        record = {
            "case": case,
            "arm": arm,
            "verdict": verdict,
            "reasons": ["check WARNING OVERLAP: <b>x</b>"]
            if verdict == "DEFECT"
            else [],
            "prompt": f"draw {case}",
            "tools": ["Bash", "Bash"],
            "seconds": 10,
            "turns": 4,
            "cost_usd": 0.25,
            "image": "figure.png" if verdict != "NO_FIGURE" else None,
            "source": "source.py",
            "figure": {
                "check": [
                    {"rule": "TEXT_AT_EDGE", "severity": "INFO", "message": "m"}
                ]
            },
        }
        (out / "result.json").write_text(json.dumps(record))
        if record["image"]:
            (out / "figure.png").write_bytes(PNG)
    (run / "run.json").write_text(
        json.dumps({"cases": ["bar", "line"], "arms": ["bare", "skill"]})
    )
    return run


def test_summary_marks_missing_runs_notrun(tmp_path: Path):
    run = fake_run(tmp_path)
    data = sheet.summary(sheet.load(run), ["bar", "line"], ["bare", "skill"])
    assert data["verdicts"] == {
        "bar": {"bare": "OK", "skill": "DEFECT"},
        "line": {"bare": "NO_FIGURE", "skill": "NOTRUN"},
    }
    assert data["cost_usd"] == 0.75


def test_report_writes_a_self_contained_page(tmp_path: Path):
    run = fake_run(tmp_path)
    table = sheet.write_report(run)
    assert "OK total" in table
    page = (run / "index.html").read_text()
    assert page.count("data:image/png;base64,") == 2
    assert "&lt;b&gt;x&lt;/b&gt;" in page  # findings are escaped
    assert "Bash x2" in page
    assert 'href="bar/skill/source.py"' in page
    assert (
        json.loads((run / "summary.json").read_text())["totals"]["bare"]["OK"]
        == 1
    )
