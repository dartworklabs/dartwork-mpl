"""FastMCP server for dartwork-mpl.

This module provides the main MCP server instance that exposes
dartwork-mpl usage guides and documentation through the Model
Context Protocol.
"""

from fastmcp import FastMCP

from .resources import register_resources
from .tools import register_tools

__all__ = ["mcp"]

# Create the MCP server instance
mcp = FastMCP("dartwork-mpl")

# Register resources and tools
register_resources(mcp)
register_tools(mcp)

# Server entry point
if __name__ == "__main__":
    mcp.run()
