"""Text rendering of lint issues.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``format_report``.
"""

from __future__ import annotations

from .catalog import Issue


def format_report(issues: list[Issue]) -> str:
    """Render issues as a multi-line ``[SEV] rule-id: message`` report.

    The full message is preserved (including any subsequent lines from
    a YAML ``|`` block scalar) and indented under the header line so
    reports stay readable in plain-text MCP/CLI output.

    If a rule provides a ``fix_suggestion``, it is emitted on its own
    line directly after the message as ``→ fix: <suggestion>`` so AI
    agents can lift the replacement directly without a second
    round-trip.
    """
    if not issues:
        return "✅ No issues found."
    lines: list[str] = []
    for issue in issues:
        line_part = f" (line {issue.line})" if issue.line else ""
        msg_lines = [ln.rstrip() for ln in issue.message.splitlines()]
        # Drop trailing blank lines but keep internal structure.
        while msg_lines and not msg_lines[-1]:
            msg_lines.pop()
        if not msg_lines:
            msg_lines = [""]
        lines.append(
            f"[{issue.severity.upper()}] {issue.rule_id}"
            f"{line_part}: {msg_lines[0]}"
        )
        lines.extend(f"    {tail}" if tail else "" for tail in msg_lines[1:])
        if issue.fix_suggestion:
            lines.append(f"  → fix: {issue.fix_suggestion}")
    return "\n".join(lines)
