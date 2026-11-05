"""Fresh wheel requirements reject the captured vulnerable runtime dependencies."""

import random
import subprocess
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest
import tomllib
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def wheel_metadata(tmp_path_factory):
    """Read actual built-wheel metadata, the requirements installers receive."""
    out = tmp_path_factory.mktemp("dependency-wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--quiet", "--out-dir", str(out)],
        cwd=_ROOT,
        check=True,
    )
    (wheel,) = out.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        (metadata,) = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        ]
        return Parser().parsestr(archive.read(metadata).decode())


def _requirements(metadata, extra):
    """Select requirements active for a fresh core or optional-extra install."""
    return [
        req
        for raw in metadata.get_all("Requires-Dist", [])
        if (req := Requirement(raw)).marker is None
        or req.marker.evaluate({"extra": extra})
    ]


def _accepts(requirements, package, version):
    """Report whether every active requirement permits the proposed version."""
    selected = [req for req in requirements if req.name.lower() == package]
    return bool(selected) and all(version in req.specifier for req in selected)


def test_wheel_python_boundary_excludes_310_and_supports_311_to_313(
    wheel_metadata,
):
    """The installer refuses unsupported 3.10 but retains every approved runtime."""
    supported = SpecifierSet(wheel_metadata["Requires-Python"])
    assert "3.10.99" not in supported
    for version in ("3.11.0", "3.12.0", "3.13.0"):
        assert version in supported
    assert (
        "Programming Language :: Python :: 3.10"
        not in wheel_metadata.get_all("Classifier", [])
    )


@pytest.mark.parametrize("extra", ("", "notebook", "mcp", "ui"))
def test_fresh_wheel_requires_the_matplotlib_series_of_the_baselines(
    wheel_metadata, extra
):
    """Fresh installs resolve Matplotlib 3.11+, the series the baselines are made on."""
    requirements = _requirements(wheel_metadata, extra)
    for version in ("3.11.0", "3.11.2", "3.12.0"):
        assert _accepts(requirements, "matplotlib", version), version
    for version in ("3.10.1", "3.10.9", "3.10.99"):
        assert not _accepts(requirements, "matplotlib", version), version


@pytest.mark.parametrize("extra", ("", "notebook", "mcp", "ui"))
def test_fresh_wheel_accepts_numpy_25_with_the_matplotlib_311_floor(
    wheel_metadata, extra
):
    """Only Matplotlib 3.10's dates.py tripped NumPy 2.5, so 2.5 is allowed."""
    requirements = _requirements(wheel_metadata, extra)
    for version in ("1.26.4", "2.4.6", "2.5.0", "2.5.4"):
        assert _accepts(requirements, "numpy", version), version
    assert not _accepts(requirements, "numpy", "1.25.2")


def test_fresh_ui_wheel_accepts_fastapi_with_included_router_wrapper(
    wheel_metadata,
):
    """The UI policy matches built routers, so FastAPI >=0.137 is allowed."""
    requirements = _requirements(wheel_metadata, "ui")
    for version in ("0.110.0", "0.136.3", "0.137.0", "0.162.0"):
        assert _accepts(requirements, "fastapi", version), version
    assert not _accepts(requirements, "fastapi", "0.109.0")


@pytest.mark.parametrize(
    ("extra", "package", "vulnerable", "patched"),
    [
        ("", "pillow", "12.3.0", "13.0.0"),
        ("mcp", "anyio", "4.14.1", "4.14.2"),
        ("mcp", "authlib", "1.9.0", "1.9.1"),
        ("mcp", "cryptography", "49.0.0", "50.0.0"),
        ("mcp", "dnspython", "2.8.0", "2.9.0"),
        ("mcp", "joserfc", "1.7.5", "1.7.6"),
        ("mcp", "mcp", "1.29.0", "1.30.0"),
        ("mcp", "opentelemetry-api", "1.45.0", "1.45.1"),
        ("mcp", "pydantic-settings", "2.14.1", "2.14.2"),
        ("mcp", "pyjwt", "2.13.0", "2.15.1"),
        ("mcp", "starlette", "1.3.0", "1.3.1"),
        ("mcp", "urllib3", "2.7.0", "2.8.0"),
        ("ui", "anyio", "4.14.1", "4.14.2"),
        ("ui", "starlette", "1.3.0", "1.3.1"),
    ],
)
def test_fresh_wheel_rejects_vulnerable_and_accepts_patched_runtime(
    wheel_metadata, extra, package, vulnerable, patched
):
    """Security floors survive wheel publication instead of existing only in uv.lock."""
    requirements = _requirements(wheel_metadata, extra)
    assert not _accepts(requirements, package, vulnerable)
    assert _accepts(requirements, package, patched)


def test_fastmcp_range_preserves_2x_and_patched_3x_with_generated_boundaries(
    wheel_metadata,
):
    """PEP 440 exclusions cover vulnerable 3.x including post releases without losing 2.x."""
    requirements = _requirements(wheel_metadata, "mcp")
    for version in ("2.14.7", "2.99.0", "3.4.10", "3.5.0", "3.99.0"):
        assert _accepts(requirements, "fastmcp", version), version
    for version in ("2.13.3", "2.14.6", "4.0.0"):
        assert not _accepts(requirements, "fastmcp", version), version
    rng = random.Random(7311)
    versions = [
        f"3.{minor}.{patch}" for minor in range(4) for patch in range(50)
    ]
    versions.extend(f"3.4.{patch}" for patch in range(20))
    rng.shuffle(versions)
    for raw in versions:
        for suffix in ("", ".post1"):
            version = raw + suffix
            expected = Version(raw) >= Version("3.4.10")
            assert _accepts(requirements, "fastmcp", version) == expected, (
                version
            )


def test_jupyter_development_stack_is_absent_from_every_published_extra(
    wheel_metadata,
):
    """Patching developer tooling must not move Jupyter into consumer installations."""
    development = {
        "notebook",
        "jupyterlab",
        "jupyter-server",
        "virtualenv",
        "mistune",
        "filelock",
    }
    for extra in ("", "notebook", "mcp", "ui"):
        names = {
            req.name.lower() for req in _requirements(wheel_metadata, extra)
        }
        assert not names & development


@pytest.mark.parametrize(
    ("package", "vulnerable", "patched"),
    [
        # GHSA-6m44-fpc8-c3rq: Markdown emphasis recursion denial of service.
        ("mistune", ("3.3.0", "3.3.2"), "3.3.3"),
        # GHSA-4f8h-vr72-p32c and GHSA-cx6f-vjhg-g3cc: seed links and
        # unescaped Bash prompt expansion, including the 21.14.9 regression.
        ("virtualenv", ("21.14.8", "21.14.9", "21.14.12"), "21.14.13"),
    ],
)
def test_development_requirements_and_lock_exclude_captured_vulnerabilities(
    package, vulnerable, patched
):
    """Reject the captured vulnerable ranges both on fresh sync and in CI's lock."""
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text())
    requirements = [
        Requirement(raw) for raw in project["dependency-groups"]["dev"]
    ]
    for version in vulnerable:
        assert not _accepts(requirements, package, version), (package, version)
    assert _accepts(requirements, package, patched)
    lock = tomllib.loads((_ROOT / "uv.lock").read_text())
    versions = [
        entry["version"]
        for entry in lock["package"]
        if entry["name"] == package
    ]
    assert versions
    assert all(Version(version) >= Version(patched) for version in versions)
