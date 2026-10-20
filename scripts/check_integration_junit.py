"""Require passing integration cases in the existing full-suite JUnit report.

This consumes pytest's local report; it never imports or reruns the tests.
Pytest remains responsible for failing the suite when any case fails.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_MODULES = (
    "tests.test_mcp",
    "tests.test_integration",
    "tests.test_cli",
    "tests.test_drift",
    "tests.mcp.agent_loop.test_oracle",
    "tests.mcp.agent_loop.test_capture",
)


def main() -> int:
    """Read one pytest report; return 1 for invalid XML or an unproven module."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        root = ET.parse(args.report).getroot()
        if root.tag not in {"testsuites", "testsuite"}:
            raise ValueError(f"unexpected root element {root.tag!r}")
    except (OSError, ET.ParseError, ValueError) as exc:
        print(
            f"Cannot read pytest JUnit report {args.report}: {exc}",
            file=sys.stderr,
        )
        return 1

    passed_modules = set()
    for case in root.iter("testcase"):
        if any(
            case.find(outcome) is not None
            for outcome in ("skipped", "failure", "error")
        ):
            continue
        classname = case.get("classname", "")
        for module in REQUIRED_MODULES:
            if classname == module or classname.startswith(module + "."):
                passed_modules.add(module)
    missing = set(REQUIRED_MODULES) - passed_modules
    if missing:
        print(
            "Required modules have no passing executed test: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )
        return 1
    print(f"OK: {len(REQUIRED_MODULES)} required modules passed executed tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
