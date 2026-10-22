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
            out.append(
                {"host": host, "subset": subset, "metric": metric, **res}
            )
    return out


def compare_runs(
    run_a: Path, run_b: Path | None, metric: str, missing_as_failure: bool
) -> tuple[list[dict], tuple]:
    """A/B within one run (arms) or across two runs; validated against the manifests."""
    if run_b is None:
        rows, status = validate(
            load_rows(run_a), planned_units(run_a), missing_as_failure
        )
        ra = [r for r in rows if r.get("arm") == "noskill"]
        rb = [r for r in rows if r.get("arm") == "skill"]
        return compare_rows(ra, rb, metric, status), ("noskill", "skill")
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
    }
    wa = (
        (read_json(run_a / "manifest.json") or {})
        .get("wheel", {})
        .get("sha256")
    )
    wb = (
        (read_json(run_b / "manifest.json") or {})
        .get("wheel", {})
        .get("sha256")
    )
    if wa != wb:
        print(
            f"WARNING: different wheels ({wa} vs {wb}); this is not a skill-only comparison"
        )
    return compare_rows(ra, rb, metric, status), (run_a.name, run_b.name)


def table(results: list[dict], label_a: str, label_b: str) -> str:
    lines = [
        f"| host | cases | {label_a} | {label_b} | diff [95% CI] | verdict | tokens B/A [95% CI] | tokens verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
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
        default="task_success",
        choices=["task_success", "execution_success"],
    )
    ap.add_argument(
        "--missing-as-failure",
        action="store_true",
        help="preregistered rule: a planned unit without a result counts as a failure",
    )
    a = ap.parse_args()
    if a.run_dir:
        results, labels = compare_runs(
            a.run_dir, None, a.metric, a.missing_as_failure
        )
    elif a.a and a.b:
        results, labels = compare_runs(a.a, a.b, a.metric, a.missing_as_failure)
    else:
        ap.error("give RUN_DIR (two arms) or --a and --b")
    print(table(results, *labels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
