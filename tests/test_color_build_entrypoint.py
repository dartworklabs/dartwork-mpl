"""Subprocess contracts for bootstrapping the generated color artifact."""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Literal

import pytest

from dartwork_mpl._build_entry import is_color_build_invocation

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE_SOURCE = _REPO_ROOT / "src" / "dartwork_mpl"
_BASELINE_ASSETS = (
    _REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
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
    """Copy only the source and frozen baselines needed by the real build."""
    checkout = tmp_path / "checkout"
    shutil.copytree(
        _PACKAGE_SOURCE,
        checkout / "src" / "dartwork_mpl",
        copy_function=_link_or_copy,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copytree(
        _BASELINE_ASSETS,
        checkout
        / "docs"
        / "superpowers"
        / "specs"
        / "assets"
        / _BASELINE_ASSETS.name,
        copy_function=_link_or_copy,
    )
    return checkout


def _set_generated_state(
    generated: Path, state: _BuildArtifactState
) -> bytes | None:
    """Replace the copied generated artifact with one bootstrap state."""
    generated.unlink()
    if state == "missing":
        return None
    generated.write_text(_BROKEN_SOURCE, encoding="utf-8")
    return generated.read_bytes()


def _subprocess_environment(checkout: Path) -> dict[str, str]:
    """Return an isolated source and Matplotlib environment for one test."""
    environment = os.environ.copy()
    environment["MPLCONFIGDIR"] = str(checkout.parent / "mpl-cache")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(checkout / "src")
    return environment


def _run_build(
    checkout: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run the documented module entry point against an isolated source tree."""
    return subprocess.run(
        [sys.executable, "-m", "dartwork_mpl._colors._build", *arguments],
        cwd=checkout,
        env=_subprocess_environment(checkout),
        capture_output=True,
        check=False,
        text=True,
    )


@pytest.mark.parametrize("state", ["missing", "syntax-broken"])
def test_module_build_check_reaches_coordinator_without_repairing_default(
    state: _BuildArtifactState, tmp_path: Path
) -> None:
    """Report valid drift as 2 without importing or changing bad output."""
    checkout = _isolated_checkout(tmp_path)
    generated = checkout / _GENERATED_RELATIVE
    before = _set_generated_state(generated, state)
    before_siblings = tuple(sorted(generated.parent.iterdir()))

    result = _run_build(checkout, "--check")

    assert result.returncode == 2, result.stderr
    after = generated.read_bytes() if generated.exists() else None
    assert after == before
    assert tuple(sorted(generated.parent.iterdir())) == before_siblings


@pytest.mark.parametrize("state", ["missing", "syntax-broken"])
def test_module_build_regenerates_default_before_normal_eager_import(
    state: _BuildArtifactState, tmp_path: Path
) -> None:
    """Repair either bootstrap state and restore the eager public API."""
    checkout = _isolated_checkout(tmp_path)
    generated = checkout / _GENERATED_RELATIVE
    before = _set_generated_state(generated, state)

    result = _run_build(checkout)

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
        env=_subprocess_environment(checkout),
        capture_output=True,
        check=False,
        text=True,
    )
    assert smoke.returncode == 0, smoke.stderr


def test_module_build_honors_custom_output_while_default_is_missing(
    tmp_path: Path,
) -> None:
    """Forward CLI arguments without importing or repairing default output."""
    checkout = _isolated_checkout(tmp_path)
    generated = checkout / _GENERATED_RELATIVE
    _set_generated_state(generated, "missing")
    custom_output = checkout / "build" / "custom_generated.py"

    result = _run_build(checkout, "--output", str(custom_output))

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


def test_ordinary_import_preserves_eager_inventory_and_reload(
    tmp_path: Path,
) -> None:
    """Keep the bootstrap guard transparent outside the exact build command."""
    checkout = _isolated_checkout(tmp_path)
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
        private = {
            "_Deprecation",
            "_DEPRECATED_NAMES",
            "_REMOVED_NAMES",
            "__getattr__",
        }
        assert public <= set(dm.__all__)
        assert all(hasattr(dm, name) for name in modules | private)
        assert dm.__version__
        assert mpl.colors.get_named_colors_mapping()["dc.blue0"] == (
            _generated.PALETTE["blue"][0]
        )
        assert "dc.aurora" in mpl.colormaps

        patched_twinx = mpl.axes.Axes.twinx
        importlib.reload(dm)
        importlib.reload(dm)

        assert mpl.axes.Axes.twinx is patched_twinx
        assert getattr(patched_twinx, "__dm_patched__", False)
        assert public <= set(dm.__all__)
        assert all(hasattr(dm, name) for name in modules | private)
        assert "dc.aurora" in mpl.colormaps
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=checkout,
        env=_subprocess_environment(checkout),
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
