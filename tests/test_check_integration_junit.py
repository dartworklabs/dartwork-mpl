"""The CI guard requires a passing executed case from each protected module."""

import random
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

CHECKER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_integration_junit.py"
)
MODULES = (
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
    "src.dartwork_mpl.mcp.plot_data.tests.test_validators",
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
    "src.dartwork_mpl.mcp.plot_data.tests.test_limits",
    "src.dartwork_mpl.mcp.plot_data.tests.test_properties",
    "src.dartwork_mpl.mcp.plot_data.tests.test_reports",
    "src.dartwork_mpl.mcp._platform.tests.test_process",
    "src.dartwork_mpl.ui.tests.test_ui_boundary",
    "src.dartwork_mpl.ui.saving.tests.test_ui_files",
    "tests.test_ui_http_security",
    "src.dartwork_mpl.ui.render.tests.test_ui_hardening",
    "src.dartwork_mpl.ui.tests.test_ui_init",
    "src.dartwork_mpl.ui.state.tests.test_ui_viewer_state",
    "src.dartwork_mpl.ui.render.tests.test_ui_render",
    "src.dartwork_mpl.ui.params.tests.test_ui_widget",
    "src.dartwork_mpl.ui.tests.test_ui_wire_golden",
)


def _check(
    path: Path, scope: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the public CLI against a real report without any project imports."""
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)]
        + (["--scope", scope] if scope is not None else []),
        capture_output=True,
        text=True,
        check=False,
    )


def _report(path: Path, cases: list[tuple[str, str | None]]) -> None:
    """Write pytest-shaped JUnit cases, optionally carrying an outcome child."""
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="pytest")
    for index, (classname, outcome) in enumerate(cases):
        case = ET.SubElement(
            suite, "testcase", classname=classname, name=f"test_case_{index}"
        )
        if outcome is not None:
            ET.SubElement(case, outcome)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


@pytest.mark.parametrize("suffix", ["", ".TestPublicAPI"])
def test_accepts_passed_cases_with_module_or_class_names(
    tmp_path: Path, suffix: str
) -> None:
    """Both top-level and class-based pytest cases prove module execution."""
    path = tmp_path / "junit.xml"
    _report(path, [(module + suffix, None) for module in MODULES])
    result = _check(path)
    assert result.returncode == 0, result.stderr
    assert f"{len(MODULES)} required modules" in result.stdout


@pytest.mark.parametrize(
    "outcome", ["missing", "zero", "skipped", "failure", "error"]
)
@pytest.mark.parametrize("module", MODULES)
def test_rejects_each_module_without_a_passed_case(
    tmp_path: Path, module: str, outcome: str
) -> None:
    """Passing siblings cannot conceal a missing, empty, skipped, or failed file."""
    cases = [(sibling, None) for sibling in MODULES if sibling != module]
    if outcome not in {"missing", "zero"}:
        cases.append((module + ".TestPublicAPI", outcome))
    path = tmp_path / "junit.xml"
    _report(path, cases)
    if outcome == "zero":
        tree = ET.parse(path)
        ET.SubElement(tree.getroot(), "testsuite", name=module, tests="0")
        tree.write(path)
    result = _check(path)
    assert result.returncode == 1
    assert module in result.stderr
    assert "no passing executed test" in result.stderr


@pytest.mark.parametrize("suffix", ["_extra", "2", "ish.TestAPI"])
def test_similar_module_prefix_cannot_satisfy_missing_module(
    tmp_path: Path, suffix: str
) -> None:
    """A different module whose name shares a prefix must never count."""
    path = tmp_path / "junit.xml"
    _report(
        path,
        [(module, None) for module in MODULES[1:]]
        + [(MODULES[0] + suffix, None)],
    )
    result = _check(path)
    assert result.returncode == 1
    assert MODULES[0] in result.stderr


@pytest.mark.parametrize("content", [None, "<testsuites>", "<unrelated />"])
def test_missing_or_malformed_report_has_an_actionable_error(
    tmp_path: Path, content: str | None
) -> None:
    """An unreadable or wrong-format artifact fails closed without traceback."""
    path = tmp_path / "junit.xml"
    if content is not None:
        path.write_text(content)
    result = _check(path)
    assert result.returncode == 1
    assert "Cannot read pytest JUnit report" in result.stderr
    assert "Traceback" not in result.stderr


def test_case_order_and_irrelevant_cases_cannot_change_module_gate(
    tmp_path: Path,
) -> None:
    """Seeded reports preserve the gate under ordering and unrelated noise."""
    rng = random.Random(173)
    path = tmp_path / "junit.xml"
    for iteration in range(2 * len(MODULES)):
        missing = MODULES[iteration % len(MODULES)]
        passing = iteration < len(MODULES)
        cases = [
            (module, None) for module in MODULES if passing or module != missing
        ]
        cases += [(module, "skipped") for module in MODULES]
        cases += [(missing + "_unrelated", None)] * rng.randrange(1, 5)
        rng.shuffle(cases)
        _report(path, cases)
        result = _check(path)
        assert result.returncode == (0 if passing else 1), (
            173,
            iteration,
            cases,
        )


@pytest.mark.parametrize("outcome", ["failure", "error"])
@pytest.mark.parametrize("module", MODULES)
def test_passing_sibling_does_not_conceal_protected_error(
    tmp_path: Path, module: str, outcome: str
) -> None:
    """An executed protected error fails even if another case passed."""
    path = tmp_path / "junit.xml"
    _report(path, [(item, None) for item in MODULES] + [(module, outcome)])
    result = _check(path)
    assert result.returncode == 1
    assert module in result.stderr


def test_empty_report_cannot_prove_any_module(tmp_path: Path) -> None:
    """A syntactically valid report with zero cases is a failed gate."""
    path = tmp_path / "junit.xml"
    _report(path, [])
    result = _check(path)
    assert result.returncode == 1
    assert all(module in result.stderr for module in MODULES)


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


def test_artifact_scope_accepts_only_its_complete_inventory(tmp_path):
    """The focused matrix proves all sixteen files without rerunning the repo."""
    path = tmp_path / "junit.xml"
    _report(path, [(module, None) for module in ARTIFACT_MODULES])
    result = _check(path, "artifacts")
    assert result.returncode == 0, result.stderr
    assert "16 required modules" in result.stdout


@pytest.mark.parametrize("module", ARTIFACT_MODULES)
@pytest.mark.parametrize(
    "outcome", ["missing", "zero", "skipped", "failure", "error"]
)
def test_artifact_scope_rejects_each_unexecuted_module(
    tmp_path, module, outcome
):
    """Every focused inventory member must supply its own passing witness."""
    path = tmp_path / "junit.xml"
    cases = [(m, None) for m in ARTIFACT_MODULES if m != module]
    if outcome not in {"missing", "zero"}:
        cases.append((module, outcome))
    _report(path, cases)
    if outcome == "zero":
        tree = ET.parse(path)
        ET.SubElement(tree.getroot(), "testsuite", name=module, tests="0")
        tree.write(path)
    result = _check(path, "artifacts")
    assert result.returncode == 1
    assert module in result.stderr


@pytest.mark.parametrize("module", ARTIFACT_MODULES)
def test_artifact_scope_rejects_partial_optional_skips(tmp_path, module):
    """A passing sibling cannot hide an optional-runtime skip in this matrix."""
    path = tmp_path / "junit.xml"
    _report(path, [(m, None) for m in ARTIFACT_MODULES] + [(module, "skipped")])
    result = _check(path, "artifacts")
    assert result.returncode == 1
    assert module in result.stderr
    assert "skipped" in result.stderr


def test_unknown_scope_cannot_silently_select_a_partial_gate(tmp_path):
    """CLI inventory selection is closed rather than an arbitrary prefix filter."""
    path = tmp_path / "junit.xml"
    _report(path, [(m, None) for m in MODULES])
    result = _check(path, "unknown")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
