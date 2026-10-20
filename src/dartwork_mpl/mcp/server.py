"""FastMCP server for dartwork-mpl.

This module provides the main MCP server instance that exposes
dartwork-mpl usage guides and documentation through the Model
Context Protocol.
"""

import os

from fastmcp import FastMCP

from .artifacts import ArtifactRuntime, configure_store, register_artifacts
from .prompts import register_prompts
from .resources import register_resources
from .tools import register_tools

__all__ = ["mcp"]

# Create the MCP server instance
mcp = FastMCP("dartwork-mpl")

# Register resources, tools, and prompts
register_resources(mcp)
register_tools(mcp)
register_prompts(mcp)
_store = configure_store(os.environ.get("DARTWORK_MPL_ARTIFACT_DIR"))
_runtime = ArtifactRuntime(_store, os.environ.get("DARTWORK_MPL_INPUT_POLICY"))
register_artifacts(mcp, _store, runtime=_runtime)

# Server entry point
if __name__ == "__main__":
    mcp.run()
