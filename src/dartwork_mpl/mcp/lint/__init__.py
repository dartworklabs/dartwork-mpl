"""Anti-pattern lint for the MCP lint tools.

``lint_text`` and ``lint_records`` report ``dm.lint_code`` findings as text
or dicts. Each returns the tool's reply.
"""

from .linter import lint_records, lint_text

__all__ = ["lint_records", "lint_text"]
