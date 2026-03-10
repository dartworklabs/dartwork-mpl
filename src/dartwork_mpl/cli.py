#!/usr/bin/env python3
"""CLI module for the dartwork-mpl MCP server.

This module provides the command-line entry point for running the
dartwork-mpl Model Context Protocol (MCP) server.
"""

__all__ = ["main"]

from .mcp.server import mcp


def main() -> None:
    """Run the dartwork-mpl MCP server.

    Starts a FastMCP server that exposes dartwork-mpl's usage guides
    and documentation to agent environments via the Model Context
    Protocol (MCP).
    """
    mcp.run()


if __name__ == "__main__":
    main()
