#!/usr/bin/env python3
"""CLI module for the dartwork-mpl MCP server.

This module provides the command-line entry point for running the
dartwork-mpl Model Context Protocol (MCP) server.
"""

from __future__ import annotations

import sys

__all__ = ["main"]


def main() -> None:
    """Run the dartwork-mpl MCP server.

    Starts a FastMCP server that exposes dartwork-mpl's usage guides
    and documentation to agent environments via the Model Context
    Protocol (MCP).

    The MCP server depends on the optional ``[mcp]`` extra (fastmcp,
    httpx). If those imports fail (e.g. plain ``pip install dartwork-mpl``
    with no extras), exit ``1`` after printing a friendly install hint
    rather than dumping an opaque ModuleNotFoundError traceback.
    """
    try:
        from .mcp.server import mcp
    except ImportError as exc:
        sys.stderr.write(
            "dartwork-mpl-mcp requires the [mcp] extra "
            "(fastmcp, httpx).\n"
            "  Install with:  pip install 'dartwork-mpl[mcp]'\n"
            "                 uv add 'dartwork-mpl[mcp]'\n"
            f"\nUnderlying error: {exc}\n"
        )
        sys.exit(1)
    mcp.run()


if __name__ == "__main__":
    main()
