"""Tests for ui/__main__.py CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestMainCli:
    """Tests for the main() CLI dispatcher."""

    def test_no_command_exits_with_error(self) -> None:
        """Running without a subcommand exits with code 1."""
        from dartwork_mpl.ui.__main__ import main

        with patch.object(sys, "argv", ["ui"]):
            with pytest.raises(SystemExit, match="1"):
                main()

    def test_init_non_interactive(self, tmp_path: Path) -> None:
        """'init' with target + --example runs scaffold directly."""
        from dartwork_mpl.ui.__main__ import main

        dest = tmp_path / "proj"
        with patch.object(
            sys, "argv", ["ui", "init", str(dest), "--example", "simple"]
        ):
            main()

        assert (dest / "app.py").exists()
        assert (dest / "README.md").exists()

    def test_init_without_example_triggers_interactive(self) -> None:
        """'init' with target but no --example triggers interactive."""
        from dartwork_mpl.ui.__main__ import main

        with (
            patch.object(sys, "argv", ["ui", "init", "/tmp/dummy"]),
            patch(
                "dartwork_mpl.ui.__main__._interactive_init"
            ) as mock_interactive,
        ):
            main()
            mock_interactive.assert_called_once()

    def test_init_without_target_triggers_interactive(self) -> None:
        """'init' without target triggers interactive."""
        from dartwork_mpl.ui.__main__ import main

        with (
            patch.object(sys, "argv", ["ui", "init"]),
            patch(
                "dartwork_mpl.ui.__main__._interactive_init"
            ) as mock_interactive,
        ):
            main()
            mock_interactive.assert_called_once()


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run ``python -m dartwork_mpl.ui`` in a child process.

    Returns the finished process with captured text output, so a test can
    observe the exit status and messages exactly as a shell user would.
    """
    return subprocess.run(
        [sys.executable, "-m", "dartwork_mpl.ui", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


class TestInitRefusals:
    """``init`` refuses requests it cannot honour with a message and non-zero exit."""

    def test_removed_complex_example_is_rejected_before_any_write(
        self, tmp_path: Path
    ) -> None:
        """``--example complex`` (template deleted in dc750a27) exits 2 and creates nothing."""
        dest = tmp_path / "proj"

        result = _run_cli("init", str(dest), "--example", "complex")

        assert result.returncode == 2
        assert "invalid choice: 'complex'" in result.stderr
        assert "Traceback" not in result.stderr
        assert not dest.exists()

    def test_non_empty_target_exits_non_zero_and_leaves_it_unchanged(
        self, tmp_path: Path
    ) -> None:
        """A non-empty target is refused with exit 1, a message, and no new files."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "keep.txt").write_text("x", encoding="utf-8")

        result = _run_cli("init", str(dest), "--example", "simple")

        assert result.returncode == 1
        assert "already exists and is not empty" in result.stderr
        assert sorted(p.name for p in dest.iterdir()) == ["keep.txt"]
