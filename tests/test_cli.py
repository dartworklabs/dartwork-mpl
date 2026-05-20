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


class TestStdioEndToEnd:
    """End-to-end stdio handshake. Launches the real
    ``dartwork-mpl-mcp`` subprocess and verifies the JSON-RPC
    ``initialize`` response is well-formed. Catches packaging
    regressions (missing entry point, broken ``__init__``, FastMCP
    incompatibility) that unit tests miss.
    """

    def test_initialize_handshake(self) -> None:
        pytest.importorskip("fastmcp")
        import json
        import shutil
        import subprocess
        import sys

        # The console-script lives on the venv's PATH when installed
        # in editable mode. Fall back to ``python -m`` if missing.
        cli_path = shutil.which("dartwork-mpl-mcp")
        cmd = (
            [cli_path]
            if cli_path
            else [sys.executable, "-m", "dartwork_mpl.cli"]
        )

        request = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "dartwork-mpl-pytest",
                            "version": "0.1",
                        },
                    },
                }
            )
            + "\n"
        )

        # FastMCP prints a banner to stderr and the JSON-RPC response
        # to stdout. Capture both, parse only stdout.
        proc = subprocess.run(
            cmd, input=request, capture_output=True, text=True, timeout=30.0
        )

        # The server returns one JSON-RPC envelope on stdout. It may
        # be followed by a newline; ``json.loads`` on the first line
        # is what we want.
        first_line = next(
            (ln for ln in proc.stdout.splitlines() if ln.strip()), ""
        )
        assert first_line, f"empty stdout; stderr was:\n{proc.stderr[:1000]}"

        envelope = json.loads(first_line)
        assert envelope["jsonrpc"] == "2.0"
        assert envelope["id"] == 1
        result = envelope["result"]
        assert result["serverInfo"]["name"] == "dartwork-mpl"
        # The MCP server must advertise tools, resources, and prompts.
        caps = result["capabilities"]
        assert "tools" in caps
        assert "resources" in caps
        assert "prompts" in caps
