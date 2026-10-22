"""Paired comparison of two arms per host, resampling cases (not repetitions).

    uv run python evals/agentic/compare.py RUN_DIR                  # arms noskill vs skill in one run
    uv run python evals/agentic/compare.py --a RUN_A --b RUN_B      # two runs (same wheel expected)

For each host: per case, average over repetitions; then the B-A difference in
success rate with a case-level bootstrap 95% CI, and the B/A token ratio with
a 10% noninferiority margin. Verdicts: improved / inconclusive / worse.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from common import read_json

MARGIN = 1.10  # tokens: B may use at most 10% more than A


def load_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def per_case(
    rows: list[dict], metric: str
) -> dict[str, tuple[float, float | None]]:
    """case -> (mean metric over reps, mean total tokens over reps)."""
    out: dict[str, list] = {}
    for r in rows:
        out.setdefault(r["case"], []).append(
            (float(bool(r.get(metric))), (r.get("tokens") or {}).get("total"))
        )
    res = {}
    for case, vals in out.items():
        toks = [t for _, t in vals if t]
        res[case] = (
            float(np.mean([m for m, _ in vals])),
            float(np.mean(toks)) if toks else None,
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
    diffs = (db[idx] - da[idx]).mean(axis=1)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    out = {
        "cases": len(cases),
        "success_a": round(float(da.mean()), 4),
        "success_b": round(float(db.mean()), 4),
        "success_diff": round(float((db - da).mean()), 4),
        "success_ci": [round(float(lo), 4), round(float(hi), 4)],
        "success_verdict": "improved"
        if lo > 0
        else "worse"
        if hi < 0
        else "inconclusive",
    }
    tc = [c for c in cases if a[c][1] and b[c][1]]
    if tc:
        ta = np.asarray([a[c][1] for c in tc])
        tb = np.asarray([b[c][1] for c in tc])
        idx = rng.integers(0, len(tc), size=(n_boot, len(tc)))
        ratios = tb[idx].sum(axis=1) / ta[idx].sum(axis=1)
        rlo, rhi = np.percentile(ratios, [2.5, 97.5])
        verdict = (
            "improved"
            if rhi < 1
            else "noninferior"
            if rhi <= MARGIN
            else "worse"
            if rlo > MARGIN
            else "inconclusive"
        )
        out.update(
            tokens_ratio=round(float(tb.sum() / ta.sum()), 4),
            tokens_ci=[round(float(rlo), 4), round(float(rhi), 4)],
            tokens_verdict=verdict,
        )
    return out


def compare_rows(
    rows_a: list[dict], rows_b: list[dict], metric: str = "task_success"
) -> list[dict]:
    out = []
    for host in sorted(
        {r["host"] for r in rows_a} & {r["host"] for r in rows_b}
    ):
        for subset, keep in (
            ("all", lambda r: True),
            ("held_out", lambda r: r.get("held_out")),
        ):
            ra = [r for r in rows_a if r["host"] == host and keep(r)]
            rb = [r for r in rows_b if r["host"] == host and keep(r)]
            res = paired(per_case(ra, metric), per_case(rb, metric))
            out.append(
                {"host": host, "subset": subset, "metric": metric, **res}
            )
    return out


def table(results: list[dict], label_a: str, label_b: str) -> str:
    lines = [
        f"| host | cases | {label_a} | {label_b} | diff [95% CI] | verdict | tokens B/A [95% CI] | tokens verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if not r.get("cases"):
            continue
        lines.append(
            f"| {r['host']} ({r['subset']}) | {r['cases']} | {r['success_a']:.2f} | {r['success_b']:.2f} "
            f"| {r['success_diff']:+.2f} [{r['success_ci'][0]:+.2f}, {r['success_ci'][1]:+.2f}] | {r['success_verdict']} "
            f"| {r.get('tokens_ratio', float('nan')):.2f} [{', '.join(f'{v:.2f}' for v in r.get('tokens_ci', []))}] "
            f"| {r.get('tokens_verdict', '-')} |"
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
    a = ap.parse_args()
    if a.run_dir:
        rows = load_rows(a.run_dir)
        rows_a = [r for r in rows if r.get("arm") == "noskill"]
        rows_b = [r for r in rows if r.get("arm") == "skill"]
        labels = ("noskill", "skill")
    elif a.a and a.b:
        rows_a, rows_b = load_rows(a.a), load_rows(a.b)
        wa = (
            (read_json(a.a / "run_meta.json") or {})
            .get("wheel", {})
            .get("sha256")
        )
        wb = (
            (read_json(a.b / "run_meta.json") or {})
            .get("wheel", {})
            .get("sha256")
        )
        if wa != wb:
            print(
                f"WARNING: different wheels ({wa} vs {wb}); this is not a skill-only comparison"
            )
        labels = (a.a.name, a.b.name)
    else:
        ap.error("give RUN_DIR (two arms) or --a and --b")
    print(table(compare_rows(rows_a, rows_b, a.metric), *labels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
