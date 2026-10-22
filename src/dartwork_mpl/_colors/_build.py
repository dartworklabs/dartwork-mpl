"""Compile, gate, exact-check, and atomically publish generated color tables.

usage: python -m dartwork_mpl._colors._build
결정론: 같은 소스에서 byte-identical 출력 (timestamp·랜덤 없음, key 정렬).
"""

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .construction import atomic_write_text as _atomic_write_text
from .construction import compile_candidate_snapshot, load_v5_snapshot
from .construction import render_generated as _render_generated
from .verify import (
    compare_exact_surfaces,
    evaluate_catalog,
    load_quality_baseline,
)

__all__ = ["main"]

_OUT = Path(__file__).parent / "_generated.py"


def _has_exact_mismatches(comparisons: Mapping[str, object]) -> bool:
    """Return whether any exact-surface comparison retains mismatched leaves."""
    return any(
        bool(getattr(comparison, "mismatch_count", 0))
        for comparison in comparisons.values()
    )


def _print_gate_failures(violations: Sequence[object]) -> None:
    """Render shared gate failures without imposing a second policy."""
    for violation in violations:
        asset = getattr(violation, "asset", "catalog")
        metric = getattr(violation, "metric", "unknown")
        observed = getattr(violation, "observed", "unknown")
        allowed = getattr(violation, "allowed", "unknown")
        rule = getattr(violation, "rule", "unknown")
        print(
            f"GATE FAIL: {asset} {metric}: {observed} {rule} {allowed}",
            file=sys.stderr,
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run compile → gate → exact → render → check/publish once."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=_OUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    target = arguments.output

    candidate = compile_candidate_snapshot()
    quality_baseline = load_quality_baseline()
    gate_report = evaluate_catalog(candidate, quality_baseline)
    if not gate_report.passed:
        _print_gate_failures(gate_report.violations)
        return 1

    baseline = load_v5_snapshot()
    exact = compare_exact_surfaces(baseline, candidate)
    if _has_exact_mismatches(exact):
        print("EXACT FAIL: candidate differs from frozen v5", file=sys.stderr)
        return 1

    expected = _render_generated(candidate)
    expected_bytes = expected.encode("utf-8")
    fresh = target.is_file() and target.read_bytes() == expected_bytes
    if arguments.check:
        return 0 if fresh else 2
    if fresh:
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(target, expected)
    print(f"OK: {target} (exact and full-catalog gates green)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
