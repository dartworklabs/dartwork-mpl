"""Tests for ui/__main__.py CLI entry point."""

from __future__ import annotations

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
