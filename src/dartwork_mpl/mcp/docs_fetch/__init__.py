"""GitHub Raw document fetch for the MCP ``fetch_github_document`` tool.

``fetch(url)`` returns ``Fetched`` (the text) or ``Refused`` (a refused URL,
redirect, encoding, size, deadline or HTTP failure, with its message).
``fetch_raw_github(url)`` is the tool's edge: the text, or ``ValueError``
carrying that message.
"""

from .raw_github import Fetched, Refused, fetch, fetch_raw_github

__all__ = ["Fetched", "Refused", "fetch", "fetch_raw_github"]
