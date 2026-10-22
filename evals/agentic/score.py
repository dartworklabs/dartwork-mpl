"""Score an eval run, or self-test the scorer against references and controls.

    uv run python evals/agentic/score.py RUN_DIR [--host claude] [--case g01-line-gdp]
    uv run python evals/agentic/score.py --selftest

Per run unit (``RUN_DIR/<host>/<case>/<arm>-r<k>/``, the records tree):

* ``execution_success``: the agent's own run left ``out/figure.png`` and
  ``out/figure.pdf`` (copied to ``artifacts/`` when the host exited) that are
  valid (PNG decodes; the PDF parses and renders a page whose aspect matches
  the PNG), were written during the run, and are not older than the final
  ``plot.py`` (an edit that was never executed fails).
* ``rerun_ok`` / ``rerun_matches``: ``plot.py`` re-run in a fresh process in
  the unit's venv saves both files again, the re-run PDF is valid, and the
  re-run PNG is pixel-identical to the original (measured same-env noise: 0).
  Oracle checks read the re-run figure, so they only count when it matches.
* ``task_success``: execution, a matching re-run, every check ``ok`` (an
  unchecked result is not a pass), explicit-edit preservation, and not
  ``contaminated``.
* ``sandboxed``: the unit ran under ``--hide-grading`` with the records, the
  work root and this repo hidden; then the sandbox is the enforcement.
* ``contamination_text``: text evidence (``contamination.py``): the run-time
  result OR a recheck of the stored transcript with the current rule, never
  cleared. It sets ``contaminated`` (never a success) only for unsandboxed
  units; under the sandbox it is an advisory field.
* ``inspection_observed``: from ``run.json`` (see run.py).
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import conformance
import metrics
import numpy as np
import oracle
import run as runner
from common import (
    DEFAULT_ROOT,
    EVAL_DIR,
    FIXTURES,
    REPO,
    load_cases,
    read_json,
    write_json,
)
from contamination import gating
from PIL import Image
from summary import summary_md

PROBE = EVAL_DIR / "probe.py"
LINT = EVAL_DIR / "lint_source.py"
# Anti-pattern findings for the conformance endpoint; "info" rules (e.g. a hex
# colour literal) are informational in the catalog and reported separately.
LINT_SEVERITIES = ("critical", "warning")
SKIP = {
    ".venv",
    ".git",
    "out",
    "__pycache__",
    ".mplconfig",
    ".claude",
    ".agents",
    ".wheel",
}
RERUN_TIMEOUT = 300
ASPECT_TOL = 0.02


_LINTERS: dict = {}
_LINTER_LOCK = threading.Lock()
LINT_CACHE = Path.home() / ".cache" / "dartwork-mpl-evals" / "lint-envs"
_SESSION: dict = {}


def _session_dir() -> Path:
    """This scoring session's own lint-env directory: new, mode 0700, removed at exit.

    Created with an exclusive ``mkdir`` under a random name, so nothing
    planted beforehand (in the records, a project or the cache) is ever
    reused; envs are never looked up by path.
    """
    if "dir" not in _SESSION:
        LINT_CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
        d = LINT_CACHE / f"session-{os.getpid()}-{secrets.token_hex(6)}"
        d.mkdir(mode=0o700)  # FileExistsError if it already exists
        os.chmod(d, 0o700)
        _SESSION["dir"] = d
        atexit.register(shutil.rmtree, d, True)
    return _SESSION["dir"]


def _install_env(env: Path, whl: Path, python: str) -> None:
    subprocess.run(
        ["uv", "venv", "--quiet", "--python", python, str(env)], check=True
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--quiet",
            "--python",
            str(env / "bin" / "python"),
            str(whl),
        ],
        check=True,
        timeout=900,
    )


def trusted_linter(run_dir: Path | None) -> dict:
    """An interpreter the agents never touched, with the run's wheel installed.

    The run's wheel (``RUN/wheel/*.whl``) is checked against the manifest's
    sha256 and installed, once per wheel and scoring session, into this
    session's own 0700 directory (``_session_dir``) outside every records and
    work tree. Without a run wheel (unit tests, selftest) the harness's own
    interpreter is used.
    """
    whl = next((run_dir / "wheel").glob("*.whl"), None) if run_dir else None
    if whl is None:
        return {
            "python": sys.executable,
            "wheel_sha256": None,
            "env": "harness",
        }
    digest = hashlib.sha256(whl.read_bytes()).hexdigest()
    want = (
        (read_json(run_dir / "manifest.json") or {}).get("wheel") or {}
    ).get("sha256")
    if want and want != digest:
        raise RuntimeError(f"{whl} does not match the manifest wheel sha256")
    with _LINTER_LOCK:
        if digest not in _LINTERS:
            env = _session_dir() / digest[:16]
            cfg = (read_json(run_dir / "manifest.json") or {}).get(
                "config"
            ) or {}
            _install_env(env, whl, cfg.get("python", "3.12"))
            _LINTERS[digest] = {
                "python": str(env / "bin" / "python"),
                "wheel_sha256": digest,
                "env": str(env),
            }
    return _LINTERS[digest]


def lint_final_source(linter: dict, plot: Path) -> dict:
    """``dm.lint_code`` of the final source with the trusted interpreter.

    Runs inside bwrap with a read-only root and the repo, records and work
    trees hidden (only the linter's environment re-exposed, read-only); the
    source goes in on stdin and is parsed, never executed.
    """
    py = linter["python"]
    hide = [
        *runner.repo_roots(),
        DEFAULT_ROOT.resolve(),
        runner.DEFAULT_WORK.resolve(),
    ]
    argv = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    argv += [a for h in hide for a in ("--tmpfs", str(h))]
    argv += ["--tmpfs", "/tmp"]
    if linter["env"] != "harness":
        argv += ["--ro-bind", linter["env"], linter["env"]]
    else:  # the harness venv and its editable source live in the repo
        for keep in (Path(sys.prefix), REPO / "src"):
            argv += ["--ro-bind", str(keep), str(keep)]
    code = LINT.read_text(encoding="utf-8")
    try:
        proc = subprocess.run(
            [*argv, "--", py, "-I", "-c", code, "-"],
            input=plot.read_text(encoding="utf-8", errors="replace"),
            capture_output=True,
            text=True,
            timeout=120,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(Path.home()),
                "LANG": "C.UTF-8",
                "MPLCONFIGDIR": "/tmp/mpl",
            },
        )
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        out = {"findings": None, "error": f"{type(exc).__name__}: {exc}"}
    return {
        **out,
        "interpreter": py,
        "wheel_sha256": linter["wheel_sha256"],
        "sandbox": "bwrap-ro",
    }


def source_metrics(case: dict, plot: Path, run_dir: Path | None = None) -> dict:
    """API conformance (lint) and unrequested preset overrides of the final plot.py.

    Nothing from the project is executed: the lint runs with ``trusted_linter``
    and the override count parses the source in this process.
    """
    if not plot.exists():
        return {
            "lint": None,
            "lint_findings": None,
            "lint_findings_all": None,
            "lint_clean": None,
            "preset_overrides": None,
            "preset_overrides_total": None,
        }
    lint = lint_final_source(trusted_linter(run_dir), plot)
    over = conformance.preset_overrides(
        plot.read_text(encoding="utf-8", errors="replace"),
        tuple(case.get("allowed_overrides", [])),
    )
    sev = lint.get("severity") or {}
    n = (
        None
        if lint.get("findings") is None
        else sum(v for k, v in sev.items() if k in LINT_SEVERITIES)
    )
    return {
        "lint": lint,
        "lint_findings": n,
        "lint_findings_all": lint.get("findings"),
        "lint_clean": None if n is None else n == 0,
        "preset_overrides": over,
        "preset_overrides_total": over.get("total"),
    }


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
        p = Path(s.get("abspath") or "")
        if p.name == f"figure.{ext}" and p.parent.name == "out":
            return str(p)
    return None


# ------------------------------------------------------------ artifact checks
def png_pixels(path: Path) -> np.ndarray | None:
    try:
        with Image.open(path) as im:
            return np.asarray(im.convert("RGBA"))
    except (OSError, ValueError, SyntaxError):
        return None


def valid_png(path: Path) -> bool:
    px = png_pixels(path)
    return px is not None and px.shape[0] > 0 and px.shape[1] > 0


def pdf_check(path: Path, png: Path | None = None) -> tuple[bool, str]:
    """Parse the PDF (pdfinfo), render page 1 (pdftoppm), compare its aspect with the PNG."""
    if not path.exists() or path.stat().st_size == 0:
        return False, "missing or empty"
    if shutil.which("pdfinfo"):
        r = subprocess.run(
            ["pdfinfo", str(path)], capture_output=True, text=True, timeout=60
        )
        pages = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
        size = re.search(
            r"^Page size:\s+([\d.]+) x ([\d.]+) pts", r.stdout, re.M
        )
        if r.returncode or not pages or int(pages.group(1)) < 1 or not size:
            return (
                False,
                f"pdfinfo failed: {(r.stderr or r.stdout).strip()[:160]}",
            )
        w, h = float(size.group(1)), float(size.group(2))
    else:  # fallback: at least one page object with a media box
        data = path.read_bytes()
        box = re.search(
            rb"/MediaBox\s*\[\s*([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s*\]",
            data,
        )
        if not re.search(rb"/Type\s*/Page\b", data) or not box:
            return False, "no page object with a MediaBox"
        x0, y0, x1, y1 = (float(v) for v in box.groups())
        w, h = x1 - x0, y1 - y0
    if shutil.which("pdftoppm"):
        with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
            r = subprocess.run(
                [
                    "pdftoppm",
                    "-r",
                    "12",
                    "-png",
                    "-singlefile",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    str(path),
                    str(Path(tmp) / "page"),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode or not (Path(tmp) / "page.png").exists():
                return (
                    False,
                    f"pdftoppm could not render page 1: {r.stderr.strip()[:160]}",
                )
    if w <= 0 or h <= 0:
        return False, "degenerate page size"
    if png is not None:
        px = png_pixels(png)
        if px is None:
            return False, "no PNG to compare"
        want = px.shape[0] / px.shape[1]
        if abs(h / w - want) > ASPECT_TOL * want:
            return False, f"page aspect {h / w:.3f} vs PNG {want:.3f}"
    return True, f"page {w:.0f}x{h:.0f} pt"


def valid_pdf(path: Path) -> bool:
    return pdf_check(path)[0]


def png_matches(a: Path, b: Path) -> bool:
    """Exact decoded-pixel equality (same-env re-runs are deterministic)."""
    x, y = png_pixels(a), png_pixels(b)
    return (
        x is not None
        and y is not None
        and x.shape == y.shape
        and bool(np.array_equal(x, y))
    )


def execution(unit: Path, project: Path, run: dict) -> tuple[bool, list[str]]:
    """Was the final plot.py executed by the agent, leaving valid outputs?"""
    art = unit / "artifacts"
    png, pdf, plot = art / "figure.png", art / "figure.pdf", project / "plot.py"
    why = []
    if not plot.exists():
        why.append("no plot.py")
    if not valid_png(png):
        why.append("original PNG missing or undecodable")
    ok_pdf, detail = pdf_check(pdf, png if valid_png(png) else None)
    if not ok_pdf:
        why.append(f"original PDF invalid ({detail})")
    started = run.get("started_ts")
    for f in (png, pdf):
        if (
            f.exists()
            and started is not None
            and f.stat().st_mtime < started - 1
        ):
            why.append(f"{f.name} was not written during the run")
        if (
            f.exists()
            and plot.exists()
            and f.stat().st_mtime < plot.stat().st_mtime
        ):
            why.append(
                f"{f.name} is older than the final plot.py (last edit never executed)"
            )
    if started is None:
        why.append("no run start time recorded")
    return not why, why


# ------------------------------------------------------------ evaluation
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
    rec["checks"] = oracle.check_oracle(
        case["oracle"],
        probe,
        base,
        auxiliary=case.get("auxiliary", []),
        figure=True,
    )
    for group in ("values", "spec"):
        sub = [c for c in rec["checks"] if c["group"] == group]
        rec[group] = {
            "passed": sum(c["ok"] is True for c in sub),
            "unchecked": sum(c["ok"] is None for c in sub),
            "total": len(sub),
        }
    if case["kind"] == "edit":
        rec["preservation"] = metrics.preservation(
            ((base or {}).get("snapshot") or {}).get("props"),
            probe["snapshot"]["props"],
            case["edit_scope"],
            case["target"],
            case.get("max_new_texts"),
        )
        if base and base.get("snapshot"):
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


def checks_pass(rec: dict) -> bool:
    pres = rec.get("preservation")
    return (
        bool(rec.get("checks"))
        and all(c["ok"] is True for c in rec["checks"])
        and (pres is None or pres["ok"] is not False)
    )


def score_unit(case: dict, unit: Path) -> dict:
    run = read_json(unit / "run.json") or {}
    project = Path(run.get("project") or unit / "project")
    python = project / ".venv" / "bin" / "python"
    rec = {
        k: run.get(k)
        for k in (
            "run_id",
            "unit_id",
            "host",
            "arm",
            "rep",
            "model",
            "effort",
            "exit_code",
            "timed_out",
            "termination",
            "host_error",
            "wall_s",
            "turns",
            "tokens",
            "cost_usd",
            "skill",
            "skill_usage",
            "skills_invoked",
            "host_version",
            "inspection",
            "contamination",
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
    # The run-time flag and the recheck are OR-ed: a recheck never clears.
    # Without the sandbox every finding gates. Under it, findings the sandbox
    # neutralised (paths it hid) are advisory; grading names and paths it did
    # not hide (e.g. another session's transcript under HOME) still gate.
    at_run = run.get("contamination")
    recheck = runner.recheck_contamination(run, unit)
    flagged = bool((at_run or {}).get("contaminated")) or bool(
        (recheck or {}).get("contaminated")
    )
    rec["sandboxed"] = runner.sandboxed(run, unit)
    rec["contamination_text"] = {
        "flagged": flagged,
        "hits": sorted(
            {*(at_run or {}).get("hits", []), *(recheck or {}).get("hits", [])}
        )[:20],
        "at_run": at_run,
        "recheck": recheck,
    }
    covered = runner.covered_by_sandbox(run)
    gate = gating(at_run, covered) + gating(recheck, covered)
    rec["contamination_text"]["gating"] = gate[:20]
    rec["contaminated"] = flagged and (not rec["sandboxed"] or bool(gate))
    rec["execution_success"], rec["execution_problems"] = execution(
        unit, project, run
    )
    rec.update(source_metrics(case, project / "plot.py", unit.parents[2]))
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
    rerun_png, rerun_pdf = _saved(probe, "png"), _saved(probe, "pdf")
    rerun_pdf_ok = (
        bool(rerun_pdf)
        and pdf_check(Path(rerun_pdf), Path(rerun_png) if rerun_png else None)[
            0
        ]
    )
    rec["rerun_ok"] = bool(rec["rerun_ok"] and rerun_pdf_ok)
    rec["rerun_matches"] = bool(
        rerun_png
        and rec["execution_success"]
        and png_matches(Path(rerun_png), unit / "artifacts" / "figure.png")
    )
    rec["task_success"] = bool(
        rec["execution_success"]
        and rec["rerun_ok"]
        and rec["rerun_matches"]
        and checks_pass(rec)
        and not rec["contaminated"]
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
        "".join(
            json.dumps(r, ensure_ascii=False, default=str) + "\n"
            for r in allrows
        )
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
    probe = run_probe(python, work / "agent")
    rec = evaluate(case, probe, base)
    bad = [
        f"{c['name']}: {c['ok']} {c['detail']}"
        for c in rec["checks"]
        if c["ok"] is not True
    ]
    if not rec["rerun_ok"]:
        bad.append(f"rerun failed: {rec.get('rerun_error')}")
    pdf = _saved(probe, "pdf")
    if pdf and not pdf_check(Path(pdf), Path(_saved(probe, "png") or ""))[0]:
        bad.append(
            f"PDF invalid: {pdf_check(Path(pdf), Path(_saved(probe, 'png') or ''))[1]}"
        )
    known = _known_defects(ref)
    for kind, n in (rec.get("defects") or {}).items():
        if kind != "total" and n > known.get(kind, 0):
            bad.append(f"defect {kind}={n} {rec['defect_details'].get(kind)}")
    pres = rec.get("preservation")
    if pres and pres["ok"] is False:
        bad.append(
            f"preservation changed {pres['changed']} added {pres.get('added')}"
        )
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
