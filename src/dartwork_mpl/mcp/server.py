"""FastMCP server for dartwork-mpl.

This module provides the main MCP server instance that exposes
dartwork-mpl usage guides and documentation through the Model
Context Protocol.
"""

import os
import sys

from fastmcp import FastMCP

from .artifacts import (
    ArtifactRuntime,
    ConfigurationError,
    configure_store,
    register_artifacts,
)
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
# stdout carries only MCP messages; the operator's reason goes to stderr, and
# artifact calls still answer with the fixed configuration_error message.
# `python -m dartwork_mpl.mcp.server` runs this body twice (imported by the
# package, then as __main__); only the first run reports.
if isinstance(_store, ConfigurationError) and not (
    __name__ == "__main__" and "dartwork_mpl.mcp.server" in sys.modules
):
    print(
        "dartwork-mpl: artifact storage disabled: "
        f"{_store.reason or _store.message}",
        file=sys.stderr,
        flush=True,
    )
_runtime = ArtifactRuntime(_store, os.environ.get("DARTWORK_MPL_INPUT_POLICY"))
register_artifacts(mcp, _store, runtime=_runtime)

# Server entry point
if __name__ == "__main__":
    mcp.run(show_banner=False)
