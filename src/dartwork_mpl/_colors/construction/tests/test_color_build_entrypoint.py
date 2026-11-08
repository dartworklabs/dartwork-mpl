"""Subprocess contracts for bootstrapping the generated color artifact."""

import os
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import pytest

from dartwork_mpl._build_entry import is_color_build_invocation
from tests.support.approved_inputs import read_approved_bytes

_REPO_ROOT = Path(__file__).resolve().parents[5]
_PACKAGE_SOURCE = _REPO_ROOT / "src" / "dartwork_mpl"
# The two frozen baselines the real build reads (``_build.py``): nothing else
# from their folder is copied.
_BASELINE_INPUTS = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_compatibility.json",
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_quality.json",
)
_GENERATED_RELATIVE = Path("src/dartwork_mpl/_colors/_generated.py")
_BROKEN_SOURCE = "def syntax_broken(:\n"
_BuildArtifactState = Literal["missing", "syntax-broken"]


def _link_or_copy(source: str, target: str) -> str:
    """Hard-link one fixture file, falling back to an ordinary copy."""
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)
    return target


def _isolated_checkout(tmp_path: Path) -> Path:
    """Copy only the source and the two frozen baselines the real build reads.

    Each baseline is written from bytes the approved-input reader returned
    after its existing pin check, so the copy is a file this test owns, never
    a hard link back to the checked-in input.
    """
    checkout = tmp_path / "checkout"
    shutil.copytree(
        _PACKAGE_SOURCE,
        checkout / "src" / "dartwork_mpl",
        copy_function=_link_or_copy,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    for relative in _BASELINE_INPUTS:
        target = checkout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(read_approved_bytes(relative))
    return checkout


@pytest.fixture
def checkout(tmp_path: Path) -> Iterator[Path]:
    """Yield an isolated checkout and delete its copied baselines afterwards.

    The copies are removed even when the copy or the test fails; pytest's own
    temporary-directory retention would otherwise keep them.
    """
    copied = tmp_path / "checkout" / "docs"
    try:
        yield _isolated_checkout(tmp_path)
    finally:
        if copied.exists():
            shutil.rmtree(copied)


def _set_generated_state(
    generated: Path, state: _BuildArtifactState
) -> bytes | None:
    """Replace the copied generated artifact with one bootstrap state."""
    generated.unlink()
    if state == "missing":
        return None
    generated.write_text(_BROKEN_SOURCE, encoding="utf-8")
    return generated.read_bytes()


@pytest.fixture(scope="module")
def mpl_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Share one private Matplotlib config/font cache across this module.

    Every subprocess here imports Matplotlib; a fresh directory per test made
    each one rebuild the font cache first. The checkouts stay per test.
    """
    return tmp_path_factory.mktemp("mpl-cache")


def _subprocess_environment(checkout: Path, mpl_cache: Path) -> dict[str, str]:
    """Return an isolated source and Matplotlib environment for one test."""
    environment = os.environ.copy()
    environment["MPLCONFIGDIR"] = str(mpl_cache)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(checkout / "src")
    return environment


def _run_build(
    checkout: Path, mpl_cache: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run the documented module entry point against an isolated source tree."""
    return subprocess.run(
        [sys.executable, "-m", "dartwork_mpl._colors._build", *arguments],
        cwd=checkout,
        env=_subprocess_environment(checkout, mpl_cache),
        capture_output=True,
        check=False,
        text=True,
    )


@pytest.mark.approved_input
def test_isolated_checkout_holds_owned_copies_of_only_the_two_baselines(
    checkout: Path,
) -> None:
    """Copy exactly the build's two baselines, byte for byte, never linked."""
    copied = sorted(
        path.relative_to(checkout).as_posix()
        for path in (checkout / "docs").rglob("*")
        if path.is_file()
    )

    assert copied == sorted(_BASELINE_INPUTS)
    for relative in _BASELINE_INPUTS:
        copy = checkout / relative
        assert copy.read_bytes() == read_approved_bytes(relative)
        assert copy.stat().st_ino != (_REPO_ROOT / relative).stat().st_ino


@pytest.mark.parametrize("state", ["missing", "syntax-broken"])
@pytest.mark.color_pipeline
@pytest.mark.approved_input
def test_module_build_check_reaches_coordinator_without_repairing_default(
    state: _BuildArtifactState, checkout: Path, mpl_cache: Path
) -> None:
    """Report valid drift as 2 without importing or changing bad output."""
    generated = checkout / _GENERATED_RELATIVE
    before = _set_generated_state(generated, state)
    before_siblings = tuple(sorted(generated.parent.iterdir()))

    result = _run_build(checkout, mpl_cache, "--check")

    assert result.returncode == 2, result.stderr
    after = generated.read_bytes() if generated.exists() else None
    assert after == before
    assert tuple(sorted(generated.parent.iterdir())) == before_siblings


@pytest.mark.parametrize("state", ["missing", "syntax-broken"])
@pytest.mark.color_pipeline
@pytest.mark.approved_input
def test_module_build_regenerates_default_before_normal_eager_import(
    state: _BuildArtifactState, checkout: Path, mpl_cache: Path
) -> None:
    """Repair either bootstrap state and restore the eager public API."""
    generated = checkout / _GENERATED_RELATIVE
    before = _set_generated_state(generated, state)

    result = _run_build(checkout, mpl_cache)

    assert result.returncode == 0, result.stderr
    assert generated.is_file()
    assert generated.read_bytes() != before
    compile(generated.read_bytes(), str(generated), "exec")
    smoke = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import matplotlib as mpl; import dartwork_mpl as dm; "
                "assert dm.Color; assert dm.font; "
                "assert 'dc.aurora' in mpl.colormaps; "
                "assert dm.colors('blue', n=1)"
            ),
        ],
        cwd=checkout,
        env=_subprocess_environment(checkout, mpl_cache),
        capture_output=True,
        check=False,
        text=True,
    )
    assert smoke.returncode == 0, smoke.stderr


@pytest.mark.color_pipeline
@pytest.mark.approved_input
def test_module_build_honors_custom_output_while_default_is_missing(
    checkout: Path, mpl_cache: Path
) -> None:
    """Forward CLI arguments without importing or repairing default output."""
    generated = checkout / _GENERATED_RELATIVE
    _set_generated_state(generated, "missing")
    custom_output = checkout / "build" / "custom_generated.py"

    result = _run_build(checkout, mpl_cache, "--output", str(custom_output))

    assert result.returncode == 0, result.stderr
    assert not generated.exists()
    assert custom_output.is_file()
    compile(custom_output.read_bytes(), str(custom_output), "exec")


@pytest.mark.parametrize(
    ("original_argv", "active_argv"),
    [
        (["python", "-m", "dartwork_mpl._colors._build_extra"], ["-m"]),
        (["python", "-m", "dartwork_mpl.cli"], ["-m"]),
        (
            ["python", "script.py", "-m", "dartwork_mpl._colors._build"],
            ["script.py", "-m", "dartwork_mpl._colors._build"],
        ),
        (["python", "dartwork_mpl._colors._build"], ["-m"]),
    ],
)
def test_build_guard_fails_closed_for_non_entrypoint_arguments(
    original_argv: list[str], active_argv: list[str]
) -> None:
    """Do not weaken normal eager imports for similar arbitrary arguments."""
    assert not is_color_build_invocation(original_argv, active_argv)


def test_build_guard_accepts_only_exact_module_mode() -> None:
    """Recognize the one source-isolated invocation documented to users."""
    assert is_color_build_invocation(
        ["python", "-X", "dev", "-m", "dartwork_mpl._colors._build"],
        ["-m", "--check"],
    )


@pytest.mark.approved_input
def test_ordinary_import_preserves_eager_inventory_and_reload(
    checkout: Path, mpl_cache: Path
) -> None:
    """Keep the bootstrap guard transparent outside the exact build command."""
    program = textwrap.dedent(
        """
        import importlib

        import matplotlib as mpl

        import dartwork_mpl as dm
        from dartwork_mpl._colors import _generated

        public = {
            "Color",
            "color",
            "colors",
            "figsize",
            "simple_layout",
            "style",
        }
        modules = {
            "font",
            "helpers",
            "icon",
            "lint",
            "templates",
            "tokens",
            "validate_fixes",
        }
        compat = {"_REMOVED_NAMES"}
        assert public <= set(dm.__all__)
        assert all(hasattr(dm, name) for name in modules | {"__getattr__"})
        assert all(hasattr(dm._compat, name) for name in compat)
        assert dm.__version__
        assert mpl.colors.get_named_colors_mapping()["dc.blue0"] == (
            _generated.PALETTE["blue"][0]
        )
        assert "dc.aurora" in mpl.colormaps

        native_twinx = mpl.axes.Axes.twinx
        importlib.reload(dm)
        importlib.reload(dm)

        # Import and reload leave matplotlib's own twinx in place (D7).
        assert mpl.axes.Axes.twinx is native_twinx
        assert "twinx" not in vars(mpl.axes.Axes)
        assert public <= set(dm.__all__)
        assert all(hasattr(dm, name) for name in modules | {"__getattr__"})
        assert "dc.aurora" in mpl.colormaps
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=checkout,
        env=_subprocess_environment(checkout, mpl_cache),
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
