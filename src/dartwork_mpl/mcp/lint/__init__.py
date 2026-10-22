"""Anti-pattern lint for the MCP lint tools.

``lint_text`` and ``lint_records`` report issues as text or dicts,
``fix_code`` applies the safe automatic fixes and ``migrate_code`` rewrites
0.3-era source. Each returns the tool's reply.
"""

from .linter import fix_code, lint_records, lint_text, migrate_code

__all__ = ["fix_code", "lint_records", "lint_text", "migrate_code"]
