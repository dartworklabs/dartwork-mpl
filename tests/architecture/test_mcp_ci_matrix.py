"""The FastMCP artifact matrix keeps one cell at each floor the range admits.

``test-mcp-artifacts`` is not a "latest versions" list. The locked FastMCP is
exercised by every ``test`` job already, so a cell earns its place by guarding
something the lock does not: the legacy 2.13.3 overlay, and the lowest release
of each major that ``pyproject.toml`` still admits. Moving a cell to the lock
version when the lock moves would silently drop such a floor.
"""

import json
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.version import Version

_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _ROOT / ".github" / "workflows" / "ci.yml"
_GOLDEN = _ROOT / "tests/mcp/data_repair/fixtures/legacy_calls.json"
_CONTRACT = "tests/contracts/test_mcp_data_repair_contract.py"

# Cell versions the range does not admit: legacy source/API coverage only.
_LEGACY = {"2.13.3"}
# major -> (lowest admitted release, the release just below it that the range
# rejects). Raising a floor means changing this, the range and the matrix.
_FLOORS = {2: ("2.14.7", "2.14.6"), 3: ("3.4.10", "3.4.9")}


def _job() -> dict:
    """Return the ``test-mcp-artifacts`` job as decoded from ci.yml."""
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["test-mcp-artifacts"]


def _cells() -> list[str]:
    """Return the FastMCP versions the matrix installs, in file order."""
    return list(_job()["strategy"]["matrix"]["fastmcp"])


def _range():
    """Return the ``fastmcp`` specifier of the ``mcp`` extra."""
    extras = tomllib.loads((_ROOT / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]["optional-dependencies"]["mcp"]
    (req,) = [r for r in map(Requirement, extras) if r.name == "fastmcp"]
    return req.specifier


def test_cells_are_the_legacy_overlay_plus_admitted_releases() -> None:
    """A cell outside the range must be the declared legacy overlay."""
    spec = _range()
    outside = {v for v in _cells() if not spec.contains(v, prereleases=True)}
    assert outside == _LEGACY, outside ^ _LEGACY


@pytest.mark.parametrize("major", sorted(_FLOORS))
def test_each_admitted_major_keeps_its_floor_as_a_cell(major: int) -> None:
    """The lowest admitted release of 2.x and 3.x is a cell, and a true floor."""
    floor, below = _FLOORS[major]
    spec = _range()
    assert spec.contains(floor, prereleases=True)
    assert not spec.contains(below, prereleases=True)
    assert floor in _cells()


def test_every_cell_has_a_golden_entry() -> None:
    """The contract test picks its golden by version; a cell without one fails."""
    captured = json.loads(_GOLDEN.read_text("utf-8"))["runtimes"]
    assert set(_cells()) <= set(captured), sorted(
        set(_cells()) - set(captured), key=Version
    )


def test_cells_run_the_data_repair_contract() -> None:
    """Without this a cell's golden entry is never executed in CI."""
    runs = [
        step["run"]
        for step in _job()["steps"]
        if "pytest tests/mcp/artifacts" in step.get("run", "")
    ]
    assert len(runs) == 1
    assert _CONTRACT in runs[0]
