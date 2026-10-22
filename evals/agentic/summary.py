"""Markdown summary of ``results.jsonl`` rows (written by score.py)."""

from __future__ import annotations

import statistics
from pathlib import Path

from compare import compare_rows, table

KINDS = [
    "text_outside",
    "text_clipped",
    "text_overlap",
    "legend_covers_data",
    "duplicate_text",
    "missing_glyphs",
]


def _med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _fmt(x, nd=0):
    return "-" if x is None else f"{x:,.{nd}f}"


def _frac(rs, key):
    return f"{sum(bool(r.get(key)) for r in rs)}/{len(rs)}"


def _checks(rs, group):
    p = sum((r.get(group) or {}).get("passed", 0) for r in rs)
    t = sum((r.get(group) or {}).get("total", 0) for r in rs)
    return f"{p}/{t}" if t else "-"


def summary_md(rows: list[dict], run_dir: Path) -> str:
    out = [
        f"# Agent eval summary — `{run_dir.name}`",
        "",
        "| host | arm | model | units | execution | task | inspected | median turns | median tokens "
        "| median time (s) | defects (units with any) | values checks | spec checks | explicit edits preserved |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    groups = sorted({(r["host"], r.get("arm") or "noskill") for r in rows})
    for host, arm in groups:
        rs = [
            r
            for r in rows
            if r["host"] == host and (r.get("arm") or "noskill") == arm
        ]
        explicit = [
            r
            for r in rs
            if (r.get("preservation") or {}).get("scope") == "explicit"
        ]
        insp = [r for r in rs if r.get("inspection_observed") is not None]
        out.append(
            f"| {host} | {arm} | {rs[0].get('model')} | {len(rs)} | {_frac(rs, 'execution_success')} "
            f"| {_frac(rs, 'task_success')} | {_frac(insp, 'inspection_observed') if insp else 'n/a'} "
            f"| {_fmt(_med([r.get('turns') for r in rs]))} | {_fmt(_med([(r.get('tokens') or {}).get('total') for r in rs]))} "
            f"| {_fmt(_med([r.get('wall_s') for r in rs]))} "
            f"| {sum((r.get('defects') or {}).get('total', 0) for r in rs)} ({sum(bool((r.get('defects') or {}).get('total')) for r in rs)}) "
            f"| {_checks(rs, 'values')} | {_checks(rs, 'spec')} "
            f"| {sum(bool(r['preservation']['ok']) for r in explicit)}/{len(explicit)} |"
        )
    out += [
        "",
        "Defects by type (sum over units):",
        "",
        "| host | arm | " + " | ".join(KINDS) + " |",
        "|---|---|" + "---|" * len(KINDS),
    ]
    for host, arm in groups:
        rs = [
            r
            for r in rows
            if r["host"] == host and (r.get("arm") or "noskill") == arm
        ]
        out.append(
            f"| {host} | {arm} | "
            + " | ".join(
                str(sum((r.get("defects") or {}).get(k, 0) for r in rs))
                for k in KINDS
            )
            + " |"
        )
    arms = {r.get("arm") for r in rows}
    if {"noskill", "skill"} <= arms:
        out += [
            "",
            "## Paired comparison (skill vs noskill, case-level bootstrap)",
            "",
            table(
                compare_rows(
                    [r for r in rows if r.get("arm") == "noskill"],
                    [r for r in rows if r.get("arm") == "skill"],
                ),
                "noskill",
                "skill",
            ),
        ]
    out += [
        "",
        "## Units",
        "",
        "| case | host | arm/rep | exec | task | inspected | turns | tokens | time (s) | defects | values | spec | preserved | failed checks |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(
        rows,
        key=lambda r: (
            r["case"],
            r["host"],
            r.get("arm") or "",
            r.get("rep") or 0,
        ),
    ):
        failed = [c["name"] for c in r.get("checks", []) if not c["ok"]]
        if r.get("execution_success") and not r.get("rerun_matches"):
            failed.append("re-run does not reproduce artifact")
        pres = r.get("preservation") or {}
        if pres.get("ok") is False:
            failed.append(f"changed {pres['changed_n']} non-target props")
        flag = " (held-out)" if r.get("held_out") else ""
        insp = r.get("inspection_observed")
        out.append(
            f"| {r['case']}{flag} | {r['host']} | {r.get('arm')}/{r.get('rep')} | {'yes' if r.get('execution_success') else 'NO'} "
            f"| {'yes' if r.get('task_success') else 'NO'} | {'-' if insp is None else 'yes' if insp else 'no'} "
            f"| {_fmt(r.get('turns'))} | {_fmt((r.get('tokens') or {}).get('total'))} | {_fmt(r.get('wall_s'))} "
            f"| {(r.get('defects') or {}).get('total', '-')} | {_checks([r], 'values')} | {_checks([r], 'spec')} "
            f"| {pres.get('rate', '-') if pres else '-'} | {', '.join(failed) or '-'} |"
        )
    out += ["", "Metric definitions: `evals/agentic/README.md`."]
    return "\n".join(out) + "\n"
