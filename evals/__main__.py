"""``python -m evals run [--cases a,b] [--arms skill,bare] [--model M] [--jobs N]`` / ``report DIR``."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from . import harness, judge, sheet

RUNS = Path(__file__).resolve().parent / "runs"


def run_safely(
    case: harness.Case, arm: str, out: Path, model: str, shared: harness.Setup
) -> dict[str, Any]:
    """One run; a harness crash is recorded as INVALID, never lost."""
    try:
        record = harness.run_one(case, arm, out, model, shared)
    except Exception as exc:  # noqa: BLE001 - every run must leave a verdict
        out.mkdir(parents=True, exist_ok=True)
        record = {
            "case": case.name,
            "arm": arm,
            "verdict": "INVALID",
            "reasons": [f"harness error: {type(exc).__name__}: {exc}"],
            "prompt": case.prompt,
            "provenance": shared.provenance,
            "trace": traceback.format_exc(),
        }
        (out / "result.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1)
        )
    print(f"{record['verdict']:9} {case.name}/{arm}", flush=True)
    return record


def main(argv: list[str] | None = None) -> int:
    """Run the matrix or rebuild a run's report."""
    parser = argparse.ArgumentParser(prog="python -m evals")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser(
        "run", help="run every case in every arm with claude -p"
    )
    run.add_argument(
        "--cases", help="comma-separated case names (default: all)"
    )
    run.add_argument("--arms", default="bare,skill")
    run.add_argument("--model", default=harness.DEFAULT_MODEL)
    run.add_argument("--jobs", type=int, default=3)
    for name, help_text in [
        ("report", "rebuild index.html and summary.json"),
        ("rejudge", "judge recorded runs again, without claude"),
    ]:
        sub.add_parser(name, help=help_text).add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "rejudge":
        by_name = {c.name: c for c in harness.load_cases()}
        for path in sorted(args.run_dir.glob("*/*/result.json")):
            record = harness.rejudge(path.parent, by_name)
            print(f"{record['verdict']:9} {record['case']}/{record['arm']}")
    if args.command in ("report", "rejudge"):
        print(sheet.write_report(args.run_dir))
        return 0
    cases = harness.load_cases(args.cases.split(",") if args.cases else None)
    arms = [a for a in args.arms.split(",") if a]
    if unknown := set(arms) - set(judge.ARMS):
        parser.error(f"unknown arms: {sorted(unknown)}")
    out = RUNS / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    names = [c.name for c in cases]
    jobs = [(c, a) for c in cases for a in arms]
    with tempfile.TemporaryDirectory(prefix="dmpl-eval-wheel-") as dist:
        shared = harness.setup(Path(dist))
        meta = {"cases": names, "arms": arms, "model": args.model}
        meta["provenance"] = shared.provenance
        (out / "run.json").write_text(json.dumps(meta, indent=1))
        with ThreadPoolExecutor(max_workers=max(args.jobs, 1)) as pool:
            list(
                pool.map(
                    lambda j: run_safely(
                        j[0], j[1], out / j[0].name / j[1], args.model, shared
                    ),
                    jobs,
                )
            )
    print(sheet.write_report(out, names, arms))
    print(f"contact sheet: {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
