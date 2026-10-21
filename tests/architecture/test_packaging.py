"""The wheel never ships tests, although slice-owned tests live inside the package tree (ADR 0005)."""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Files the wheel build reads besides the package (readme, license, and the
# agent docs that `force-include` copies into the package).
_BUILD_INPUTS = (
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "CLAUDE.md",
    "AGENTS.md",
    "llms.txt",
    "llms-full.txt",
)


def _wheel_members(project: Path, out: Path) -> list[str]:
    """Build the wheel of ``project`` into ``out`` with uv and return its member names."""
    subprocess.run(
        ["uv", "build", "--wheel", "--quiet", "--out-dir", str(out)],
        cwd=project,
        check=True,
    )
    (wheel,) = out.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs the uv CLI")
def test_wheel_excludes_colocated_tests_and_keeps_package_modules(tmp_path):
    """This repository's build config, on a probe package, drops every test file and keeps the rest.

    The probe holds one ordinary module, a slice ``tests/`` package with a test
    and a ``conftest.py``, and a ``test_*.py`` outside any ``tests/`` folder;
    only the ordinary module and the package ``__init__`` may ship.
    """
    project = tmp_path / "project"
    project.mkdir()
    for name in _BUILD_INPUTS:
        shutil.copy2(ROOT / name, project / name)
    package = project / "src" / "dartwork_mpl"
    tests = package / "probe" / "tests"
    tests.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "probe" / "__init__.py").write_text("", encoding="utf-8")
    (package / "probe" / "rules.py").write_text("X = 1\n", encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_rules.py").write_text(
        "def test_x(): ...\n", encoding="utf-8"
    )
    (tests / "conftest.py").write_text("", encoding="utf-8")
    (package / "probe" / "test_loose.py").write_text("", encoding="utf-8")

    members = _wheel_members(project, tmp_path / "dist")

    package_files = sorted(
        m
        for m in members
        if m.startswith("dartwork_mpl/") and m.endswith(".py")
    )
    assert package_files == [
        "dartwork_mpl/__init__.py",
        "dartwork_mpl/probe/__init__.py",
        "dartwork_mpl/probe/rules.py",
    ]
