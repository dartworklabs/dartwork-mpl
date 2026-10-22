"""Paired comparison of two arms per host, resampling cases (not repetitions).

    uv run python evals/agentic/compare.py RUN_DIR                  # arms noskill vs skill in one run
    uv run python evals/agentic/compare.py --a RUN_A --b RUN_B      # two runs (must share the wheel)

Rows are first validated against each run's ``manifest.json``: every planned
(host, case, arm, rep) unit must have exactly one scored row. Missing or
duplicate units make the comparison ``incomplete`` (no verdict) unless
``--missing-as-failure`` applies the preregistered rule (missing = failure,
token usage unknown). Contaminated units always count as failures.

Per host: per case, average over repetitions; then the B-A difference in
success with a case-level bootstrap 95% CI. ``improved`` needs an unrounded
difference >= 0.10 AND a CI lower bound > 0; ``worse`` needs a CI upper bound
< 0; otherwise ``inconclusive``. Tokens: B/A ratio of totals with a 10%
noninferiority margin; any unit with unknown usage blocks the token verdict.

Every verdict is ``blocked`` when any compared unit ran without the
``--hide-grading`` sandbox (``sandboxed`` is not true, or the run's manifest
does not record ``hide_grading``): decision runs must be sandboxed.

The default output is the pre-registered skill A/B (``PREREGISTERED``):
two primary endpoints, two guardrails and descriptive secondaries.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from common import read_json

MARGIN = 1.10  # tokens: B may use at most 10% more than A
MIN_EFFECT = 0.10  # success: practical threshold for "improved"
TASK_MARGIN = 0.05  # guardrail: task success may drop at most 5 points

# Pre-registered 2026-10-22, before any skill-arm run (plan doc, same text).
PREREGISTERED = """\
Skill A/B (noskill vs skill, same wheel, --hide-grading, per host).
Primary 1 - inspection_observed: share of units whose agent viewed the final PNG
  after its last write (baseline noskill: claude 30/40, codex 31/40).
Primary 2 - API conformance: share of units whose final executed plot.py has zero
  dm.lint_code findings of severity critical or warning (raw figsize, tight_layout,
  plt.style.use, direct savefig, dpi argument, literal sizes/widths, oversize
  width, ...), linted with the wheel under test; info findings (e.g. a hex colour
  literal) are reported, not counted.
  Each primary: case-level bootstrap 95% CI of skill - noskill; improved needs a
  difference >= 0.10 and CI lower bound > 0; worse needs CI upper bound < 0.
Guardrails: task_success noninferior (CI lower bound of skill - noskill > -0.05);
  tokens noninferior (CI upper bound of skill/noskill total ratio <= 1.10).
Decision per host: the skill helps when at least one primary is improved, no
  primary is worse and both guardrails hold.
Secondary (descriptive, no verdict): visual defects per unit (incl.
  meaningless_decimals), unrequested preset overrides per unit (rcParams, fonts,
  figure/axes facecolor, style sheets; AST count), tokens, turns, wall time.
Contaminated units count as failures; any unsandboxed unit blocks every verdict.
"""
PRIMARY = ("inspection_observed", "lint_clean")
SECONDARY = {
    "defects": lambda r: (r.get("defects") or {}).get("total"),
    "meaningless_decimals": lambda r: (r.get("defects") or {}).get(
        "meaningless_decimals"
    ),
    "preset_overrides": lambda r: r.get("preset_overrides_total"),
    "lint_findings": lambda r: r.get("lint_findings"),
    "tokens": lambda r: (r.get("tokens") or {}).get("total"),
    "turns": lambda r: r.get("turns"),
    "wall_s": lambda r: r.get("wall_s"),
}


def load_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def planned_units(run_dir: Path) -> list[str]:
    manifest = read_json(run_dir / "manifest.json") or {}
    return [u for p in manifest.get("plans", []) for u in p["units"]]


def _uid(r: dict) -> str:
    return (
        r.get("unit_id")
        or f"{r['host']}/{r['case']}/{r.get('arm') or 'noskill'}-r{r.get('rep') or 1}"
    )


def validate(
    rows: list[dict], planned: list[str], missing_as_failure: bool
) -> tuple[list[dict], dict]:
    """Rows restricted to planned units; report missing/duplicate/unplanned units."""
    counts = Counter(_uid(r) for r in rows)
    missing = [u for u in planned if counts[u] == 0]
    dupes = [u for u, n in counts.items() if n > 1]
    unplanned = [u for u in counts if u not in set(planned)]
    kept = [r for r in rows if _uid(r) in set(planned) and counts[_uid(r)] == 1]
    if missing_as_failure:
        for u in missing:
            host, case, armrep = u.split("/")
            arm, rep = armrep.rsplit("-r", 1)
            kept.append(
                {
                    "host": host,
                    "case": case,
                    "arm": arm,
                    "rep": int(rep),
                    "unit_id": u,
                    "task_success": False,
                    "execution_success": False,
                    "tokens": None,
                    "missing": True,
                }
            )
    status = {
        "planned": len(planned),
        "missing": missing,
        "duplicates": dupes,
        "unplanned": unplanned,
        "complete": not dupes
        and (not missing or missing_as_failure)
        and bool(planned),
    }
    return kept, status


def unsandboxed(rows: list[dict]) -> list[str]:
    """Units that ran without the sandbox (missing-as-failure stand-ins excepted)."""
    return [
        _uid(r)
        for r in rows
        if not r.get("missing") and r.get("sandboxed") is not True
    ]


def _manifest_sandboxed(run_dir: Path) -> bool:
    cfg = (read_json(run_dir / "manifest.json") or {}).get("config") or {}
    return cfg.get("hide_grading") is True


def per_case(
    rows: list[dict], metric: str
) -> dict[str, tuple[float, float | None]]:
    """case -> (mean success over reps, mean total tokens over reps or None if any unknown)."""
    out: dict[str, list] = {}
    for r in rows:
        ok = bool(r.get(metric)) and not r.get("contaminated")
        tok = (r.get("tokens") or {}).get("total")
        out.setdefault(r["case"], []).append((float(ok), tok if tok else None))
    res = {}
    for case, vals in out.items():
        toks = [t for _, t in vals]
        res[case] = (
            float(np.mean([m for m, _ in vals])),
            None if None in toks else float(np.mean(toks)),
        )
    return res


def paired(a: dict, b: dict, n_boot: int = 10000, seed: int = 0) -> dict:
    cases = sorted(set(a) & set(b))
    if not cases:
        return {"cases": 0}
    rng = np.random.default_rng(seed)
    da = np.asarray([a[c][0] for c in cases])
    db = np.asarray([b[c][0] for c in cases])
    idx = rng.integers(0, len(cases), size=(n_boot, len(cases)))
    lo, hi = np.percentile((db[idx] - da[idx]).mean(axis=1), [2.5, 97.5])
    diff = float((db - da).mean())
    verdict = (
        "improved"
        if diff >= MIN_EFFECT and lo > 0
        else "worse"
        if hi < 0
        else "inconclusive"
    )
    out = {
        "cases": len(cases),
        "success_a": round(float(da.mean()), 4),
        "success_b": round(float(db.mean()), 4),
        "success_diff": diff,
        "success_ci": [round(float(lo), 4), round(float(hi), 4)],
        "success_verdict": verdict,
    }
    if any(a[c][1] is None or b[c][1] is None for c in cases):
        out["tokens_verdict"] = "blocked (unknown token usage)"
        return out
    ta = np.asarray([a[c][1] for c in cases])
    tb = np.asarray([b[c][1] for c in cases])
    ratios = tb[idx].sum(axis=1) / ta[idx].sum(axis=1)
    rlo, rhi = np.percentile(ratios, [2.5, 97.5])
    out.update(
        tokens_ratio=round(float(tb.sum() / ta.sum()), 4),
        tokens_ci=[round(float(rlo), 4), round(float(rhi), 4)],
        tokens_verdict="improved"
        if rhi < 1
        else "noninferior"
        if rhi <= MARGIN
        else "worse"
        if rlo > MARGIN
        else "inconclusive",
    )
    return out


def balance(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """Without a manifest, the arms must at least mirror each other: same cases, same reps, no duplicates."""

    def shape(rows):
        c = Counter((r["host"], r["case"], r.get("rep") or 1) for r in rows)
        return c, [k for k, n in c.items() if n > 1]

    sa, da = shape(rows_a)
    sb, db = shape(rows_b)
    missing = sorted(set(sa) ^ set(sb))
    return {
        "complete": not missing and not da and not db,
        "missing": missing,
        "duplicates": da + db,
    }


def compare_rows(
    rows_a: list[dict],
    rows_b: list[dict],
    metric: str = "task_success",
    status: dict | None = None,
) -> list[dict]:
    if status is None:
        status = balance(rows_a, rows_b)
    bad = _blocked(rows_a + rows_b, status)  # any unsandboxed unit blocks all
    out = []
    for host in sorted(
        {r["host"] for r in rows_a} | {r["host"] for r in rows_b}
    ):
        for subset, keep in (
            ("all", lambda r: True),
            ("held_out", lambda r: r.get("held_out")),
        ):
            ra = [r for r in rows_a if r["host"] == host and keep(r)]
            rb = [r for r in rows_b if r["host"] == host and keep(r)]
            res = paired(per_case(ra, metric), per_case(rb, metric))
            if status is not None and not status.get("complete"):
                res = {
                    "cases": res.get("cases", 0),
                    "success_verdict": "incomplete",
                    "tokens_verdict": "incomplete",
                    "missing": len(status.get("missing", [])),
                    "duplicates": len(status.get("duplicates", [])),
                }
            elif bad:
                res = {
                    "cases": res.get("cases", 0),
                    "success_verdict": bad,
                    "tokens_verdict": bad,
                }
            out.append(
                {"host": host, "subset": subset, "metric": metric, **res}
            )
    return out


def _blocked(rows: list[dict], status: dict | None) -> str | None:
    """Why no verdict may be given (unsandboxed units or run), else None."""
    n = len(unsandboxed(rows))
    if n:
        return f"blocked ({n} units ran without --hide-grading)"
    if status is not None and status.get("sandboxed_run") is False:
        return "blocked (run manifest does not record --hide-grading)"
    return None


def _num_case(rows: list[dict], get) -> dict[str, float | None]:
    out: dict[str, list] = {}
    for r in rows:
        out.setdefault(r["case"], []).append(get(r))
    return {c: None if None in v else float(np.mean(v)) for c, v in out.items()}


def _num_diff(a: dict, b: dict, n_boot: int = 10000, seed: int = 0) -> dict:
    cases = sorted(c for c in set(a) & set(b) if None not in (a[c], b[c]))
    if not cases:
        return {"cases": 0}
    da = np.asarray([a[c] for c in cases])
    db = np.asarray([b[c] for c in cases])
    idx = np.random.default_rng(seed).integers(
        0, len(cases), size=(n_boot, len(cases))
    )
    lo, hi = np.percentile((db[idx] - da[idx]).mean(axis=1), [2.5, 97.5])
    return {
        "cases": len(cases),
        "a": round(float(da.mean()), 4),
        "b": round(float(db.mean()), 4),
        "diff": round(float((db - da).mean()), 4),
        "ci": [round(float(lo), 4), round(float(hi), 4)],
    }


def endpoints(
    rows_a: list[dict], rows_b: list[dict], status: dict | None = None
) -> list[dict]:
    """The pre-registered A/B (``PREREGISTERED``) per host."""
    if status is None:
        status = balance(rows_a, rows_b)
    out = []
    for host in sorted({r["host"] for r in rows_a + rows_b}):
        ra = [r for r in rows_a if r["host"] == host]
        rb = [r for r in rows_b if r["host"] == host]
        res: dict = {"host": host}
        why = (
            "incomplete"
            if not status.get("complete")
            else _blocked(rows_a + rows_b, status)
        )
        for m in PRIMARY:
            p = paired(per_case(ra, m), per_case(rb, m))
            res[m] = {
                "a": p.get("success_a"),
                "b": p.get("success_b"),
                "diff": p.get("success_diff"),
                "ci": p.get("success_ci"),
                "verdict": why or p.get("success_verdict"),
            }
        p = paired(per_case(ra, "task_success"), per_case(rb, "task_success"))
        ci = p.get("success_ci")
        res["task_success"] = {
            "a": p.get("success_a"),
            "b": p.get("success_b"),
            "diff": p.get("success_diff"),
            "ci": ci,
            "verdict": why
            or (
                "noninferior"
                if ci and ci[0] > -TASK_MARGIN
                else "inferior"
                if ci and ci[1] < -TASK_MARGIN
                else "inconclusive"
            ),
        }
        res["tokens"] = {
            "ratio": p.get("tokens_ratio"),
            "ci": p.get("tokens_ci"),
            "verdict": why or p.get("tokens_verdict"),
        }
        res["secondary"] = {
            name: _num_diff(_num_case(ra, get), _num_case(rb, get))
            for name, get in SECONDARY.items()
        }
        if why:
            res["decision"] = why
        else:
            prim = [res[m]["verdict"] for m in PRIMARY]
            guards = res["task_success"]["verdict"] == "noninferior" and res[
                "tokens"
            ]["verdict"] in ("noninferior", "improved")
            res["decision"] = (
                "skill helps"
                if "improved" in prim and "worse" not in prim and guards
                else "no demonstrated gain"
            )
        out.append(res)
    return out


def endpoint_table(results: list[dict], label_a: str, label_b: str) -> str:
    def fmt(e):
        if e.get("a") is None:
            return str(e.get("verdict") or "-")
        ci = e.get("ci") or [float("nan")] * 2
        return (
            f"{e['a']:.2f} -> {e['b']:.2f} ({e['diff']:+.2f} [{ci[0]:+.2f}, {ci[1]:+.2f}]) "
            f"{e['verdict']}"
        )

    lines = [
        f"Arms: {label_a} -> {label_b}. Pre-registered endpoints (compare.PREREGISTERED).",
        "",
        "| host | primary: inspection_observed | primary: lint clean | guardrail: task success "
        "| guardrail: tokens B/A | decision |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        t = r["tokens"]
        tok = (
            f"{t['ratio']:.2f} [{t['ci'][0]:.2f}, {t['ci'][1]:.2f}] {t['verdict']}"
            if t.get("ratio") is not None
            else str(t.get("verdict"))
        )
        lines.append(
            f"| {r['host']} | {fmt(r['inspection_observed'])} | {fmt(r['lint_clean'])} "
            f"| {fmt(r['task_success'])} | {tok} | {r['decision']} |"
        )
    lines += [
        "",
        "Secondary (mean per unit, skill - noskill with case-bootstrap 95% CI; descriptive):",
        "",
        "| host | " + " | ".join(SECONDARY) + " |",
        "|---|" + "---|" * len(SECONDARY),
    ]
    for r in results:
        cells = []
        for name in SECONDARY:
            e = r["secondary"][name]
            cells.append(
                "-"
                if not e.get("cases")
                else f"{e['a']:.3g} -> {e['b']:.3g} ({e['diff']:+.3g} [{e['ci'][0]:+.3g}, {e['ci'][1]:+.3g}])"
            )
        lines.append(f"| {r['host']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _rows_and_status(
    run_a: Path, run_b: Path | None, missing_as_failure: bool
) -> tuple[list[dict], list[dict], dict, tuple]:
    if run_b is None:
        rows, status = validate(
            load_rows(run_a), planned_units(run_a), missing_as_failure
        )
        status["sandboxed_run"] = _manifest_sandboxed(run_a)
        ra = [r for r in rows if r.get("arm") == "noskill"]
        rb = [r for r in rows if r.get("arm") == "skill"]
        return ra, rb, status, ("noskill", "skill")
    ra, sa = validate(
        load_rows(run_a), planned_units(run_a), missing_as_failure
    )
    rb, sb = validate(
        load_rows(run_b), planned_units(run_b), missing_as_failure
    )
    status = {
        "complete": sa["complete"] and sb["complete"],
        "missing": sa["missing"] + sb["missing"],
        "duplicates": sa["duplicates"] + sb["duplicates"],
        "sandboxed_run": _manifest_sandboxed(run_a)
        and _manifest_sandboxed(run_b),
    }
    return ra, rb, status, (run_a.name, run_b.name)


def compare_runs(
    run_a: Path, run_b: Path | None, metric: str, missing_as_failure: bool
) -> tuple[list[dict], tuple]:
    """A/B within one run (arms) or across two runs; validated against the manifests."""
    ra, rb, status, labels = _rows_and_status(run_a, run_b, missing_as_failure)
    if run_b is not None:
        wa, wb = (
            (read_json(r / "manifest.json") or {})
            .get("wheel", {})
            .get("sha256")
            for r in (run_a, run_b)
        )
        if wa != wb:
            print(
                f"WARNING: different wheels ({wa} vs {wb}); this is not a skill-only comparison"
            )
    return compare_rows(ra, rb, metric, status), labels


def preregistered(
    run_a: Path, run_b: Path | None, missing_as_failure: bool
) -> tuple[list[dict], tuple]:
    """The pre-registered endpoints for one run's arms or two runs."""
    ra, rb, status, labels = _rows_and_status(run_a, run_b, missing_as_failure)
    return endpoints(ra, rb, status), labels


def table(results: list[dict], label_a: str, label_b: str) -> str:
    lines = [
        f"| host | cases | {label_a} | {label_b} | diff [95% CI] | verdict | tokens B/A [95% CI] | tokens verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if str(r.get("success_verdict")).startswith("blocked"):
            lines.append(
                f"| {r['host']} ({r['subset']}) | {r['cases']} | - | - | - | {r['success_verdict']} | - | blocked |"
            )
            continue
        if r.get("success_verdict") == "incomplete":
            lines.append(
                f"| {r['host']} ({r['subset']}) | {r['cases']} | - | - | - | incomplete "
                f"(missing {r['missing']}, duplicates {r['duplicates']}) | - | incomplete |"
            )
            continue
        if not r.get("cases"):
            continue
        ci = ", ".join(f"{v:.2f}" for v in r.get("tokens_ci", []))
        lines.append(
            f"| {r['host']} ({r['subset']}) | {r['cases']} | {r['success_a']:.2f} | {r['success_b']:.2f} "
            f"| {r['success_diff']:+.3f} [{r['success_ci'][0]:+.2f}, {r['success_ci'][1]:+.2f}] | {r['success_verdict']} "
            f"| {r.get('tokens_ratio', float('nan')):.2f} [{ci}] | {r.get('tokens_verdict', '-')} |"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("run_dir", nargs="?", type=Path)
    ap.add_argument("--a", type=Path)
    ap.add_argument("--b", type=Path)
    ap.add_argument(
        "--metric",
        choices=[
            "task_success",
            "execution_success",
            "inspection_observed",
            "lint_clean",
        ],
        help="one success metric (default: the pre-registered endpoints)",
    )
    ap.add_argument(
        "--missing-as-failure",
        action="store_true",
        help="preregistered rule: a planned unit without a result counts as a failure",
    )
    a = ap.parse_args()
    if not (a.run_dir or (a.a and a.b)):
        ap.error("give RUN_DIR (two arms) or --a and --b")
    run_a, run_b = (a.run_dir, None) if a.run_dir else (a.a, a.b)
    if a.metric:
        results, labels = compare_runs(
            run_a, run_b, a.metric, a.missing_as_failure
        )
        print(table(results, *labels))
    else:
        results, labels = preregistered(run_a, run_b, a.missing_as_failure)
        print(endpoint_table(results, *labels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
