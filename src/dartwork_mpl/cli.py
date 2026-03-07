#!/usr/bin/env python3
"""Command Line Interface for dartwork-mpl MCP server.

This module provides a command-line entry point for running the
dartwork-mpl Model Context Protocol server.
"""

__all__ = ["main"]

from .mcp.server import mcp


def main() -> None:
    """
    Run the dartwork-mpl MCP server.

    This function starts the FastMCP server that exposes dartwork-mpl
    usage guides and documentation through the Model Context Protocol.
    """
    mcp.run()


if __name__ == "__main__":
    main()
