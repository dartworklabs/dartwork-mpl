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
)


def _check(path: Path) -> subprocess.CompletedProcess[str]:
    """Run the public CLI against a real report without any project imports."""
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
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
    assert "4 required modules" in result.stdout


@pytest.mark.parametrize("outcome", ["missing", "skipped", "failure", "error"])
@pytest.mark.parametrize("module", MODULES)
def test_rejects_each_module_without_a_passed_case(
    tmp_path: Path, module: str, outcome: str
) -> None:
    """Passing siblings cannot conceal one missing, skipped, or failed file."""
    cases = [(sibling, None) for sibling in MODULES if sibling != module]
    if outcome != "missing":
        cases.append((module + ".TestPublicAPI", outcome))
    path = tmp_path / "junit.xml"
    _report(path, cases)
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
    for iteration in range(12):
        missing = MODULES[iteration % len(MODULES)]
        passing = iteration % 2 == 0
        cases = [
            (module, None) for module in MODULES if passing or module != missing
        ]
        cases += [(module, "skipped") for module in MODULES]
        cases += [(missing + "_unrelated", None)] * rng.randrange(1, 5)
        rng.shuffle(cases)
        _report(path, cases)
        result = _check(path)
        assert result.returncode == (0 if passing else 1), iteration
