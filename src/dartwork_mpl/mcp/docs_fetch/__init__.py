"""GitHub Raw document fetch for the MCP ``fetch_github_document`` tool.

``fetch_raw_github(url)`` returns the document text or raises ``ValueError``
for a refused URL, redirect, encoding, size, deadline or HTTP failure.
"""

from .raw_github import fetch_raw_github

__all__ = ["fetch_raw_github"]
