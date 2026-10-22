"""MCP Prompts for dartwork-mpl.

This module defines interactive prompts that guide users through
creating and reviewing dartwork-mpl plots. The wording is aligned
with the SSOT in ``asset/prompt/`` (00-index, 01-policy,
02-anti-patterns, 03-recipes, 05-templates).

The prompt strings deliberately *describe* forbidden patterns
without spelling out their literal call form, so that the prompt
text itself does not trigger the dartwork-mpl lint engine. Each
rule reference cites the lint rule id from ``02-anti-patterns.yaml``.
"""

from fastmcp import FastMCP

from . import guides

__all__ = ["register_prompts"]


def register_prompts(mcp: FastMCP) -> None:
    """
    Register all prompts with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register prompts with.
    """

    @mcp.prompt()
    def create_plot(description: str, data_sample: str = "") -> str:
        """Guide native Figure creation, data review and artifact delivery.

        Inputs are capped at 8,192 characters each with a truncation marker.
        A data sample describes structure; it does not imply full input access.
        This prompt returns guidance without executing or storing a plot.

        Parameters
        ----------
        description : str
            Natural language description of the desired plot
            (e.g. "tornado chart comparing energy savings across 5 buildings").
        data_sample : str
            Optional JSON or CSV preview, not necessarily the full dataset.
        """
        return guides.create_plot_text(description, data_sample)

    @mcp.prompt()
    def style_review(code: str) -> str:
        """Guide presentation-only edits and review of durable plot artifacts.

        Source is capped at 8,192 characters with a truncation marker; missing
        source must be obtained before claiming a complete review. The prompt
        returns guidance without executing source or changing input data.

        Parameters
        ----------
        code : str
            Python source code to review.
        """
        return guides.style_review_text(code)
