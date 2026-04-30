"""Tests for the ``dartwork-mpl-mcp`` CLI entry point.

The CLI is a thin shim around ``mcp.server.mcp.run()`` plus a graceful
fallback when the ``[mcp]`` extra is not installed.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestCliMainGracefulFallback:
    """``main()`` must not raise ``ModuleNotFoundError`` to the caller
    when fastmcp is missing — it should print a friendly install hint
    and ``sys.exit(1)``.
    """

    def test_missing_mcp_extra_exits_one_with_hint(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Force the ``from .mcp.server import mcp`` line in ``main()``
        # to raise ImportError, regardless of whether fastmcp is
        # installed in the dev env.
        from dartwork_mpl import cli

        importlib.reload(cli)

        def raise_import_error(*args: object, **kwargs: object) -> None:
            raise ImportError("simulated missing fastmcp")

        with patch.dict(sys.modules, {}, clear=False):
            # Drop cached import so the lazy import inside main() runs
            # fresh.
            sys.modules.pop("dartwork_mpl.mcp.server", None)
            with patch(
                "builtins.__import__", side_effect=raise_import_error
            ) as _imp:
                _ = _imp  # silence linter
                with pytest.raises(SystemExit) as exc_info:
                    cli.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "[mcp] extra" in err or "fastmcp" in err
        assert "pip install" in err

    def test_main_runs_when_mcp_available(self) -> None:
        """When fastmcp is installed, ``main()`` should call
        ``mcp.run()`` exactly once."""
        pytest.importorskip("fastmcp")

        from dartwork_mpl import cli

        importlib.reload(cli)
        mock_mcp = MagicMock()

        with patch("dartwork_mpl.mcp.server.mcp", mock_mcp):
            cli.main()

        mock_mcp.run.assert_called_once()
