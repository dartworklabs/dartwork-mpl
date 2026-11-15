"""The MCP lint tools' replies over ``dartwork_mpl.guide.lint``."""

from typing import Any

from dartwork_mpl import guide


def lint_text(code: str) -> str:
    """One ``[severity] rule-id (line n): message → fix`` line per finding."""
    findings = guide.lint(code)
    return "\n".join(map(str, findings)) if findings else "No issues found."


def lint_records(code: str) -> list[dict[str, Any]]:
    """One dict per finding of ``code`` (``lint_dartwork_mpl_code_json``); empty when clean."""
    return [
        {
            "rule_id": f.rule_id,
            "severity": str(f.severity),
            "line": f.line,
            "message": f.message,
            "fix_suggestion": f.fix,
        }
        for f in guide.lint(code)
    ]
