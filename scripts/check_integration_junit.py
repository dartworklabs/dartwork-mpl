"""Require passing integration cases in the existing full-suite JUnit report.

This consumes pytest's local report; it never imports or reruns the tests.
Pytest remains responsible for failing the suite when any case fails.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Explicit all-extras inventory: original integration gates + agent-loop
# evidence, fastmcp-dependent contracts/artifacts, data-repair collection,
# and UI modules exercising fastapi/pydantic. See docs/development/ci-execution.md.
REQUIRED_MODULES = (
    "tests.test_mcp",
    "tests.test_integration",
    "tests.test_cli",
    "tests.test_drift",
    "tests.mcp.agent_loop.test_oracle",
    "tests.mcp.agent_loop.test_capture",
    "tests.test_docs_mcp_tools",
    "tests.test_docstring_catalogs",
    "tests.test_mcp_asset_boundary",
    "tests.test_mcp_data_repair_contract",
    "tests.test_mcp_heavy_tools",
    "tests.test_mcp_render_smoke",
    "tests.test_mcp_tool_hardening",
    "tests.test_mcp_validation_contract",
    "tests.test_mcp_validators_complete",
    "tests.mcp.artifacts.test_artifact_boundaries",
    "tests.mcp.artifacts.test_artifact_discovery",
    "tests.mcp.artifacts.test_artifact_entry_policies",
    "tests.mcp.artifacts.test_artifact_execution",
    "tests.mcp.artifacts.test_artifact_policy",
    "tests.mcp.artifacts.test_artifact_protocol",
    "tests.mcp.artifacts.test_artifact_store",
    "tests.mcp.artifacts.test_input_access",
    "tests.mcp.artifacts.test_input_commit_observer",
    "tests.mcp.artifacts.test_input_delivery",
    "tests.mcp.artifacts.test_input_io",
    "tests.mcp.artifacts.test_input_lifecycle",
    "tests.mcp.artifacts.test_input_policy",
    "tests.mcp.artifacts.test_input_recovery",
    "tests.mcp.artifacts.test_input_stdio",
    "tests.mcp.artifacts.test_input_store",
    "tests.mcp.data_repair.test_limits",
    "tests.mcp.data_repair.test_properties",
    "tests.mcp.data_repair.test_reports",
    "tests.test_ui_boundary",
    "tests.test_ui_files",
    "tests.test_ui_http_security",
    "tests.test_ui_hardening",
    "tests.test_ui_init",
    "tests.test_ui_param",
    "tests.test_ui_security",
    "tests.test_ui_widget",
)


# Closed focused inventory; independent CLI tests pin every member.
ARTIFACT_MODULES = (
    "tests.mcp.artifacts.test_artifact_boundaries",
    "tests.mcp.artifacts.test_artifact_discovery",
    "tests.mcp.artifacts.test_artifact_entry_policies",
    "tests.mcp.artifacts.test_artifact_execution",
    "tests.mcp.artifacts.test_artifact_policy",
    "tests.mcp.artifacts.test_artifact_protocol",
    "tests.mcp.artifacts.test_artifact_store",
    "tests.mcp.artifacts.test_input_access",
    "tests.mcp.artifacts.test_input_commit_observer",
    "tests.mcp.artifacts.test_input_delivery",
    "tests.mcp.artifacts.test_input_io",
    "tests.mcp.artifacts.test_input_lifecycle",
    "tests.mcp.artifacts.test_input_policy",
    "tests.mcp.artifacts.test_input_recovery",
    "tests.mcp.artifacts.test_input_stdio",
    "tests.mcp.artifacts.test_input_store",
)


def main() -> int:
    """Read pytest XML; reject unproven modules and protected errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--scope", choices=("full", "artifacts"), default="full"
    )
    args = parser.parse_args()
    required = (
        ARTIFACT_MODULES if args.scope == "artifacts" else REQUIRED_MODULES
    )
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
    failed_modules = set()
    skipped_modules = set()
    for case in root.iter("testcase"):
        classname = case.get("classname", "")
        for module in required:
            if classname != module and not classname.startswith(module + "."):
                continue
            if any(
                case.find(outcome) is not None
                for outcome in ("failure", "error")
            ):
                failed_modules.add(module)
            elif case.find("skipped") is not None:
                skipped_modules.add(module)
            else:
                passed_modules.add(module)
    missing = set(required) - passed_modules
    if args.scope == "artifacts" and skipped_modules:
        print(
            "Required artifact modules contain skipped cases: "
            + ", ".join(sorted(skipped_modules)),
            file=sys.stderr,
        )
        return 1
    if failed_modules:
        print(
            "Required modules contain failures/errors: "
            + ", ".join(sorted(failed_modules)),
            file=sys.stderr,
        )
    if missing:
        print(
            "Required modules have no passing executed test: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )
        return 1
    if failed_modules:
        return 1
    print(f"OK: {len(required)} required modules passed executed tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
