"""MCP Resources for dartwork-mpl guides.

This module defines resources that expose dartwork-mpl usage guides
through the Model Context Protocol.
"""

from fastmcp import FastMCP

from ..util import get_prompt


def register_resources(mcp: FastMCP) -> None:
    """
    Register all resources with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register resources with.
    """

    # Register general-guide resource
    @mcp.resource("dartwork-mpl://guide/general-guide")
    def general_guide() -> str:
        """
        Get the general usage guide for dartwork-mpl.

        Returns
        ----------
        str
            The content of the general-guide markdown file.
        """
        return get_prompt("general-guide")

    # Register layout-guide resource
    @mcp.resource("dartwork-mpl://guide/layout-guide")
    def layout_guide() -> str:
        """
        Get the layout guide for dartwork-mpl.

        Returns
        ----------
        str
            The content of the layout-guide markdown file.
        """
        return get_prompt("layout-guide")
