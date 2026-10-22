"""Score an eval run, or self-test the scorer against references and controls.

    uv run python evals/agentic/score.py RUN_DIR [--host claude] [--case g01-line-gdp]
    uv run python evals/agentic/score.py --selftest

Per run unit (``RUN_DIR/<host>/<case>/<arm>-r<k>/``):

* ``execution_success`` — the agent's own run left a valid ``out/figure.png``
  and ``out/figure.pdf`` written during the run (the copies preserved in
  ``artifacts/`` right after the host exited) and a ``plot.py``.
* ``rerun_ok`` / ``rerun_matches`` — ``plot.py`` re-run in its venv in a fresh
  process via ``probe.py`` saves both files again and the PNG reproduces the
  original artifact. Oracle checks read the re-run figure, so they only count
  when it reproduces the original.
* ``task_success`` — execution_success, a reproducing re-run, every oracle
  check, and (explicit edits) preservation of every non-target property.
* ``inspection_observed`` — from ``run.json``: the host's tool events show the
  agent viewed an image identical to the final PNG.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import metrics
import numpy as np
import oracle
from common import (
    DEFAULT_ROOT,
    EVAL_DIR,
    FIXTURES,
    REPO,
    load_cases,
    read_json,
    write_json,
)
from matplotlib import image as mimage
from summary import summary_md

PROBE = EVAL_DIR / "probe.py"
SKIP = {
    ".venv",
    ".git",
    "out",
    "__pycache__",
    ".mplconfig",
    ".claude",
    ".agents",
}
RERUN_TIMEOUT = 300


def run_probe(python: Path, workdir: Path, script: str = "plot.py") -> dict:
    """Run probe.py on ``workdir/script`` with ``python``; return its JSON."""
    out = workdir / "probe.json"
    out.unlink(missing_ok=True)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(Path.home()),
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(workdir.parent / ".mplconfig"),
        "LANG": "C.UTF-8",
    }
    try:
        proc = subprocess.run(
            [str(python), "-I", str(PROBE), script, str(out)],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=RERUN_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
        (workdir / "probe.log").write_text(
            proc.stdout[-20000:] + "\n--- stderr\n" + proc.stderr[-20000:]
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"rerun timeout {RERUN_TIMEOUT}s",
            "snapshot": None,
        }
    data = read_json(out)
    if data is None:
        return {
            "ok": False,
            "error": f"probe crashed: {proc.stderr[-1500:]}",
            "snapshot": None,
        }
    return data


def _copy_project(src: Path, dst: Path) -> None:
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(
        src, dst, ignore=lambda d, names: [n for n in names if n in SKIP]
    )


def _saved(probe: dict, ext: str) -> str | None:
    for s in reversed(probe.get("saves", [])):
        p = Path(s["abspath"] or "")
        if p.name == f"figure.{ext}" and p.parent.name == "out":
            return str(p)
    return None


def valid_png(path: Path) -> bool:
    try:
        head = path.read_bytes()[:24]
    except OSError:
        return False
    return (
        head[:8] == b"\x89PNG\r\n\x1a\n"
        and int.from_bytes(head[16:20], "big") > 0
        and int.from_bytes(head[20:24], "big") > 0
    )


def valid_pdf(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return data[:5] == b"%PDF-" and b"%%EOF" in data[-2048:]


def png_matches(a: Path, b: Path, tol: float = 0.01) -> bool:
    try:
        x, y = mimage.imread(a), mimage.imread(b)
    except (OSError, ValueError, SyntaxError):
        return False
    return (
        x.shape == y.shape
        and float(np.abs(x.astype(float) - y.astype(float)).mean()) <= tol
    )


def evaluate(case: dict, probe: dict, base: dict | None) -> dict:
    """Oracle, defects and preservation for one re-run (shared with the self-test)."""
    rec: dict = {
        "rerun_ok": bool(probe.get("ok"))
        and bool(_saved(probe, "png"))
        and bool(_saved(probe, "pdf")),
        "rerun_error": probe.get("error") or probe.get("snapshot_error"),
        "snapshot_target": probe.get("target"),
        "checks": [],
    }
    if not probe.get("snapshot"):
        return rec
    d = metrics.defects(probe)
    rec["defects"], rec["defect_details"], rec["bbox_tight"] = (
        d["counts"],
        d["details"],
        d["bbox_tight"],
    )
    rec["checks"] = oracle.check_oracle(case["oracle"], probe, base)
    for group in ("values", "spec"):
        sub = [c for c in rec["checks"] if c["group"] == group]
        rec[group] = {"passed": sum(c["ok"] for c in sub), "total": len(sub)}
    if case["kind"] == "edit" and base and base.get("snapshot"):
        rec["preservation"] = metrics.preservation(
            base["snapshot"]["props"],
            probe["snapshot"]["props"],
            case["edit_scope"],
            case["target"],
        )
        rec["base_defects"] = metrics.defects(base)["counts"]
    rec["dm"] = {
        "styles": probe.get("styles"),
        "calls": probe.get("calls"),
        "lint": probe.get("lint"),
        "findings": probe["snapshot"].get("dm_findings"),
        "missing_glyphs": probe.get("missing_glyphs"),
    }
    rec["size_cm"] = [round(v, 2) for v in oracle.saved_size_cm(probe)]
    return rec


def _checks_pass(rec: dict) -> bool:
    pres = rec.get("preservation")
    return (
        bool(rec.get("checks"))
        and all(c["ok"] for c in rec["checks"])
        and (pres is None or pres["ok"] is not False)
    )


def score_unit(case: dict, unit: Path) -> dict:
    run = read_json(unit / "run.json") or {}
    project, art = unit / "project", unit / "artifacts"
    python = project / ".venv" / "bin" / "python"
    rec = {
        k: run.get(k)
        for k in (
            "run_id",
            "host",
            "arm",
            "rep",
            "model",
            "effort",
            "exit_code",
            "timed_out",
            "host_error",
            "wall_s",
            "turns",
            "tokens",
            "cost_usd",
            "skill",
            "host_version",
            "inspection",
            "harness_error",
        )
    }
    rec.update(
        {
            "case": case["id"],
            "kind": case["kind"],
            "lang": case["lang"],
            "purpose": case["purpose"],
            "held_out": case.get("held_out", False),
            "edit_scope": case.get("edit_scope"),
            "unit": str(unit),
        }
    )
    rec["inspection_observed"] = (run.get("inspection") or {}).get("observed")
    arts = run.get("artifacts") or {}
    rec["execution_success"] = bool(
        (project / "plot.py").exists()
        and valid_png(art / "figure.png")
        and valid_pdf(art / "figure.pdf")
        and arts.get("png_fresh")
        and arts.get("pdf_fresh")
    )
    if not (project / "plot.py").exists() or not python.exists():
        rec.update(
            rerun_ok=False,
            rerun_matches=False,
            task_success=False,
            rerun_error="no plot.py or venv",
        )
        return rec
    work = unit / "score" / "agent"
    _copy_project(project, work)
    probe = run_probe(python, work)
    base = None
    if case["kind"] == "edit":
        bdir = unit / "score" / "base"
        shutil.rmtree(bdir, ignore_errors=True)
        (bdir / "data").mkdir(parents=True)
        for name in case["data"]:
            shutil.copy(FIXTURES / "data" / name, bdir / "data" / name)
        shutil.copy(FIXTURES / "base" / case["base"], bdir / "plot.py")
        base = run_probe(python, bdir)
    rec.update(evaluate(case, probe, base))
    rerun_png = _saved(probe, "png")
    rec["rerun_matches"] = bool(
        rerun_png
        and rec["execution_success"]
        and png_matches(Path(rerun_png), art / "figure.png")
    )
    rec["task_success"] = bool(
        rec["execution_success"]
        and rec["rerun_ok"]
        and rec["rerun_matches"]
        and _checks_pass(rec)
    )
    return rec


def units(run_dir: Path) -> list[Path]:
    return sorted(p.parent for p in run_dir.glob("*/*/*/run.json"))


def score_run(
    run_dir: Path, hosts: list[str] | None, ids: list[str] | None, jobs: int
) -> list[dict]:
    cases = {c["id"]: c for c in load_cases()}
    todo = [
        (cases[u.parent.name], u)
        for u in units(run_dir)
        if u.parent.name in cases
        and (not ids or u.parent.name in ids)
        and (not hosts or u.parent.parent.name in hosts)
    ]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        rows = list(pool.map(lambda t: score_unit(*t), todo))
    for (_, unit), row in zip(todo, rows, strict=True):
        write_json(unit / "score.json", row)
    path = run_dir / "results.jsonl"
    prior = (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )
    fresh = {r["unit"] for r in rows}
    allrows = [r for r in prior if r.get("unit") not in fresh] + rows
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in allrows)
    )
    (run_dir / "summary.md").write_text(
        summary_md(allrows, run_dir), encoding="utf-8"
    )
    return rows


# ------------------------------------------------------------ self-test
def _known_defects(script: Path) -> dict[str, int]:
    """``# known-defect: text_outside=2 (reason)`` lines: true positives caused by dm itself."""
    out: dict[str, int] = {}
    for line in script.read_text(encoding="utf-8").splitlines():
        if line.startswith("# known-defect:"):
            kind, _, rest = line.split(":", 1)[1].strip().partition("=")
            out[kind.strip()] = int(rest.split()[0])
    return out


def _selftest_case(case: dict, out_root: Path, python: Path) -> str:
    ref = FIXTURES / "reference" / f"{case['id']}.py"
    if not ref.exists():
        return f"[skip] {case['id']}: no reference"
    work = out_root / case["id"]
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(FIXTURES / "data", work / "agent" / "data")
    shutil.copy(ref, work / "agent" / "plot.py")
    base = None
    if case["kind"] == "edit":
        shutil.copytree(FIXTURES / "data", work / "base" / "data")
        shutil.copy(FIXTURES / "base" / case["base"], work / "base" / "plot.py")
        base = run_probe(python, work / "base")
    rec = evaluate(case, run_probe(python, work / "agent"), base)
    bad = [f"{c['name']}: {c['detail']}" for c in rec["checks"] if not c["ok"]]
    if not rec["rerun_ok"]:
        bad.append(f"rerun failed: {rec.get('rerun_error')}")
    known = _known_defects(ref)
    for kind, n in (rec.get("defects") or {}).items():
        if kind != "total" and n > known.get(kind, 0):
            bad.append(f"defect {kind}={n} {rec['defect_details'].get(kind)}")
    pres = rec.get("preservation")
    if pres and pres["ok"] is False:
        bad.append(f"preservation changed {pres['changed']}")
    note = (
        f" (base defects {rec['base_defects']['total']})"
        if rec.get("base_defects")
        else ""
    )
    gone = [
        k for k, n in known.items() if (rec.get("defects") or {}).get(k, 0) < n
    ]
    note += f" [known dm defect(s) {gone} no longer reproduce]" if gone else ""
    return f"[{'FAIL' if bad else 'ok'}] {case['id']}{note}" + "".join(
        f"\n    - {b}" for b in bad
    )


def _selftest_control(ctl: Path, out_root: Path, python: Path) -> str:
    work = out_root / "controls" / ctl.stem
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(FIXTURES / "data", work / "data")
    shutil.copy(ctl, work / "plot.py")
    probe = run_probe(python, work)
    expect = [
        ln.split(":", 1)[1].strip()
        for ln in ctl.read_text().splitlines()
        if ln.startswith("# expect:")
    ]
    counts = metrics.defects(probe)["counts"] if probe.get("snapshot") else {}
    bad = [e for e in expect if counts.get(e, 0) < 1]
    return f"[{'FAIL' if bad else 'ok'}] control {ctl.stem}: expects {expect}, got {counts}"


def check_fixture_sums() -> list[str]:
    """The CSV inputs are frozen; a changed byte invalidates every oracle."""
    bad = []
    for line in (FIXTURES / "data" / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        if (
            hashlib.sha256((FIXTURES / "data" / name).read_bytes()).hexdigest()
            != digest
        ):
            bad.append(name)
    return bad


def selftest(out_root: Path, ids: list[str] | None, jobs: int) -> int:
    """Reference scripts must pass every check; controls must trip their detector."""
    python = REPO / ".venv" / "bin" / "python"
    drift = check_fixture_sums()
    print(f"[{'FAIL' if drift else 'ok'}] fixture checksums {drift or ''}")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        lines = list(
            pool.map(
                lambda c: _selftest_case(c, out_root, python), load_cases(ids)
            )
        )
        if not ids:
            lines += list(
                pool.map(
                    lambda p: _selftest_control(p, out_root, python),
                    sorted((FIXTURES / "controls").glob("*.py")),
                )
            )
    print("\n".join(lines))
    failures = sum(line.startswith("[FAIL]") for line in lines) + bool(drift)
    print(f"selftest: {failures} failing")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("run_dir", nargs="?", type=Path)
    ap.add_argument("--host", action="append")
    ap.add_argument("--case", action="append")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_ROOT / "selftest")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.out, a.case, a.jobs)
    if not a.run_dir:
        ap.error("RUN_DIR is required unless --selftest")
    rows = score_run(a.run_dir, a.host, a.case, a.jobs)
    print(f"scored {len(rows)} run units -> {a.run_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
