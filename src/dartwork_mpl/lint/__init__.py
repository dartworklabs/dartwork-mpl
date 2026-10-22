"""dartwork-mpl lint engine.

Loads the anti-pattern catalog from
``asset/prompt/02-anti-patterns.yaml`` and applies it to a Python
source string. Used by the MCP ``lint_dartwork_mpl_code`` tool, the
Python ``dm.lint_code(code)`` API, and CI drift tests. No lint CLI is provided.

The catalog owns rule text and selects regex, substring, or static AST
detectors. AST name checks consult the live public matplotlib registries;
supplied source is never executed or imported.
"""

from __future__ import annotations

__all__ = [
    "Issue",
    "Rule",
    "apply_lint_fixes",
    "format_report",
    "lint",
    "load_rules",
    "migrate_legacy_code",
]

from .catalog import Issue, Rule, load_rules
from .detect import lint
from .fix import apply_lint_fixes
from .migrate import migrate_legacy_code
from .report import format_report
