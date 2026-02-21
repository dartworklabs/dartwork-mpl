"""MCP Tools for dartwork-mpl.

This module defines tools that provide additional functionality
for accessing dartwork-mpl documentation and resources.
"""

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """
    Register all tools with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register tools with.
    """

    # Register GitHub document fetch tool
    @mcp.tool()
    def fetch_github_document(url: str) -> str:
        """
        Fetch document content from a GitHub Raw URL.

        This tool retrieves the content of a document from GitHub's
        raw content URL. The URL should point to a raw file on GitHub,
        typically in the format:
        https://raw.githubusercontent.com/owner/repo/branch/path/to/file

        Parameters
        ----------
        url : str
            GitHub Raw URL to fetch the document from.
            Example: https://raw.githubusercontent.com/dartworklabs/
            dartwork-mpl/main/README.md

        Returns
        ----------
        str
            The content of the document as a string.

        Raises
        ----------
        ValueError
            If the URL is invalid or the request fails.
        """
        try:
            import httpx

            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            return response.text
        except ImportError:
            # Fallback to urllib if httpx is not available
            from urllib.request import urlopen

            try:
                with urlopen(url, timeout=10) as response:
                    return response.read().decode("utf-8")
            except Exception as e:
                raise ValueError(f"Failed to fetch document: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to fetch document: {e}") from e
