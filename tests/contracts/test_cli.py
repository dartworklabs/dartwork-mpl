"""Tests for the ``dartwork-mpl-mcp`` CLI entry point.

The CLI is a thin shim around ``mcp.server.mcp.run()`` plus a graceful
fallback when the ``[mcp]`` extra is not installed.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.support.child_deadline import HANG_GUARD_S


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

    @pytest.mark.parametrize(
        "module", ["console", "dartwork_mpl.cli", "dartwork_mpl.mcp.server"]
    )
    def test_initialize_handshake(self, module: str) -> None:
        """Both real entrypoints keep JSON-RPC usable without promotional banners."""
        pytest.importorskip("fastmcp")
        import json
        import subprocess
        import sys
        import sysconfig
        from pathlib import Path

        if module == "console":
            # The console script of the environment running this suite, not
            # the first one on PATH: a user-site ``~/.local/bin`` install
            # with another interpreter would test that install instead
            # (2026-11-06: ``#!/usr/bin/python3``, no fastmcp). A missing
            # script is a broken install, not a reason to test ``-m``.
            console = Path(sysconfig.get_path("scripts")) / "dartwork-mpl-mcp"
            assert console.is_file(), f"no console script at {console}"
            cmd = [str(console)]
        else:
            cmd = [sys.executable, "-m", module]

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

        # Runtime diagnostics stay on stderr; protocol envelopes stay on stdout.
        # ``run`` returns when the server exits after its stdin closes. The
        # timeout is a hang guard, not an expectation of start-up speed: a
        # loaded runner took longer than 30 s to import and start the server.
        proc = subprocess.run(
            cmd,
            input=request,
            capture_output=True,
            text=True,
            timeout=HANG_GUARD_S,
        )

        # The server returns one JSON-RPC envelope on stdout. It may
        # be followed by a newline; ``json.loads`` on the first line
        # is what we want.
        first_line = next(
            (ln for ln in proc.stdout.splitlines() if ln.strip()), ""
        )
        assert first_line, f"empty stdout; stderr was:\n{proc.stderr[:1000]}"

        assert "gofastmcp.com" not in proc.stderr
        assert "Update available" not in proc.stderr
        assert "Starting MCP server" in proc.stderr

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
