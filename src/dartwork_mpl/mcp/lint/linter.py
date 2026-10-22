"""The MCP lint tools' replies over the anti-pattern linter ``dartwork_mpl.lint``.

The linter is imported at call time, so a patched ``dartwork_mpl.lint``
attribute is what runs.
"""

from typing import Any


def lint_text(code: str) -> str:
    """The text report of ``dm.lint(code)`` (``lint_dartwork_mpl_code``)."""
    from dartwork_mpl.lint import format_report
    from dartwork_mpl.lint import lint as _lint

    return format_report(_lint(code))


def lint_records(code: str) -> list[dict[str, Any]]:
    """One dict per lint issue of ``code`` (``lint_dartwork_mpl_code_json``); empty when clean."""
    from dartwork_mpl.lint import lint as _lint

    return [
        {
            "rule_id": i.rule_id,
            "severity": i.severity,
            "line": i.line,
            "column": i.column,
            "message": i.message,
            "fix_suggestion": i.fix_suggestion,
        }
        for i in _lint(code)
    ]


def fix_code(code: str) -> dict[str, Any]:
    """Safe automatic fixes of ``code`` with the applied and still-unfixed issues (``apply_lint_fixes``)."""
    from dartwork_mpl.lint import apply_lint_fixes as _apply

    fixed_code, applied, unfixed = _apply(code)

    def _serialise(issue: Any) -> dict[str, Any]:
        return {
            "rule_id": issue.rule_id,
            "severity": issue.severity,
            "line": issue.line,
            "column": issue.column,
            "message": issue.message,
            "fix_suggestion": issue.fix_suggestion,
        }

    return {
        "fixed_code": fixed_code,
        "applied": [_serialise(i) for i in applied],
        "unfixed": [_serialise(i) for i in unfixed],
    }


def migrate_code(code: str) -> str:
    """``code`` rewritten toward the 0.4 idioms with hint comments (``migrate_legacy_code``); never raises."""
    from dartwork_mpl.lint import migrate_legacy_code as _migrate

    return _migrate(code)
