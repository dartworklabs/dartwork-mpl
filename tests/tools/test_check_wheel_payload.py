"""The release shell accepts the built payload and rejects omissions or leaks."""

import random
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_wheel_payload.py"
PAYLOAD = (
    "dartwork_mpl/__init__.py",
    "dartwork_mpl/probe/rules.py",
    "dartwork_mpl/asset/color/probe.csv",
    "dartwork_mpl/asset/font/probe.ttf",
    "dartwork_mpl/skills/dartwork-mpl/SKILL.md",
    "dartwork_mpl/asset/agent/AGENTS.md",
    "dartwork_mpl/asset/agent/CLAUDE.md",
    "dartwork_mpl/asset/agent/llms.txt",
    "dartwork_mpl/asset/agent/llms-full.txt",
)


@pytest.fixture
def package_project(tmp_path: Path) -> Path:
    """Track a small real package with runtime data, consumer docs and excluded tests."""
    project = tmp_path / "project"
    project.mkdir()
    for name in (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "AGENTS.md",
        "CLAUDE.md",
        "llms.txt",
        "llms-full.txt",
    ):
        shutil.copy2(ROOT / name, project / name)
    for member in PAYLOAD[:-2]:
        path = project / "src" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# packaged probe\n", encoding="utf-8")
    for name in (
        "probe/tests/test_rules.py",
        "probe/tests/__init__.py",
        "probe/test_loose.py",
        "probe/conftest.py",
    ):
        path = project / "src/dartwork_mpl" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# excluded test\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet", str(project)], check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    return project


def _check(
    project: Path, members: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    """Run the public checker against a real ZIP and git index, without imports."""
    wheel = project / "candidate.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for member in members:
            archive.writestr(member, "probe")
        archive.writestr("dartwork_mpl-0.5.6.dist-info/METADATA", "metadata")
    return subprocess.run(
        [sys.executable, str(CHECKER), str(wheel)],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


def test_actual_release_shell_accepts_legitimate_built_payload(
    package_project: Path,
) -> None:
    """The unchanged build policy can ship all runtime members while excluding tests."""
    project = package_project
    subprocess.run(
        ["uv", "build", "--wheel", "--quiet", "--out-dir", "dist"],
        cwd=project,
        check=True,
    )
    if CHECKER.exists():
        (project / "scripts").mkdir()
        shutil.copy2(CHECKER, project / "scripts" / CHECKER.name)
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/release.yml").read_text()
    )
    step = next(
        step
        for step in workflow["jobs"]["build"]["steps"]
        if step.get("name") == "Wheel ↔ git-tracked tree parity"
    )
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=project,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_complete_payload_is_accepted(package_project: Path) -> None:
    """Positive parity includes forced indexes and both bundled consumer entries."""
    result = _check(package_project, PAYLOAD)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("missing", PAYLOAD)
def test_each_runtime_member_is_required(
    package_project: Path, missing: str
) -> None:
    """Dropping a module, CSV, font, skill or any agent document fails closed."""
    result = _check(
        package_project, tuple(name for name in PAYLOAD if name != missing)
    )
    assert result.returncode == 1
    assert missing in result.stderr


@pytest.mark.parametrize(
    "extra",
    (
        "dartwork_mpl/probe/tests/test_rules.py",
        "dartwork_mpl/probe/test_loose.py",
        "dartwork_mpl/probe/conftest.py",
        "dartwork_mpl/extra.py",
        "dartwork_mpl/asset/agent/untracked.md",
    ),
)
def test_extra_package_member_is_rejected(
    package_project: Path, extra: str
) -> None:
    """Tests and other untracked files cannot leak into an otherwise complete wheel."""
    result = _check(package_project, (*PAYLOAD, extra))
    assert result.returncode == 1
    assert extra in result.stderr


def test_duplicate_member_is_rejected(package_project: Path) -> None:
    """A duplicate ZIP entry cannot conceal a second package member with the same name."""
    with pytest.warns(UserWarning, match="Duplicate name"):
        result = _check(package_project, (*PAYLOAD, PAYLOAD[0]))
    assert result.returncode == 1
    assert "Duplicate package members" in result.stderr
    assert PAYLOAD[0] in result.stderr


@pytest.mark.parametrize("contents", [None, b"not a ZIP"])
def test_missing_or_invalid_wheel_fails_closed(
    package_project: Path, contents: bytes | None
) -> None:
    """Missing or invalid release artifacts are rejected with a useful error."""
    wheel = package_project / "broken.whl"
    if contents is not None:
        wheel.write_bytes(contents)
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(wheel)],
        cwd=package_project,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Cannot check wheel payload" in result.stderr


def test_member_order_is_irrelevant_and_unknown_members_fail(
    package_project: Path,
) -> None:
    """Seeded permutations retain parity, while each generated extra path breaks it."""
    generator = random.Random(5128)
    for index in range(12):
        shuffled = tuple(generator.sample(PAYLOAD, len(PAYLOAD)))
        result = _check(package_project, shuffled)
        assert result.returncode == 0, (index, result.stderr)
        extra = f"dartwork_mpl/extra-{generator.getrandbits(64)}.csv"
        result = _check(package_project, (*shuffled, extra))
        assert result.returncode == 1 and extra in result.stderr, (index, extra)
