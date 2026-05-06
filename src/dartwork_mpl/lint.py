"""dartwork-mpl lint engine.

Loads the anti-pattern catalog from
``asset/prompt/02-anti-patterns.yaml`` and applies it to a Python
source string. Used by the MCP ``lint_dartwork_mpl_code`` tool, the
``dartwork-mpl lint`` CLI, and CI drift tests.

The catalog is the single source of truth: code never inlines rule
text. Add or change rules in the YAML file; this module loads them
verbatim.
"""

from __future__ import annotations

__all__ = [
    "Issue",
    "Rule",
    "format_report",
    "lint",
    "load_rules",
    "migrate_legacy_code",
]

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

_RULES_PATH: Path = (
    Path(__file__).parent / "asset" / "prompt" / "02-anti-patterns.yaml"
)


@dataclass(frozen=True)
class Rule:
    """A single anti-pattern definition."""

    id: str
    severity: str  # "critical" | "warning" | "info"
    detector_kind: str  # "regex" | "substring"
    detector_value: str  # pattern or literal
    message: str
    why: str | None = None
    fix_suggestion: str | None = None


@dataclass(frozen=True)
class Issue:
    """A detected violation.

    ``column`` is the absolute byte offset of the match in the source
    string (0-indexed). It is included to disambiguate multiple
    violations on the same line — ``(rule_id, line)`` alone collapses
    them and hides the second occurrence from auto-fixers.

    ``fix_suggestion`` mirrors the YAML field of the same name and is
    surfaced inline by :func:`format_report` so AI agents can apply a
    fix without a second round-trip.
    """

    rule_id: str
    severity: str
    message: str
    line: int | None = None
    snippet: str | None = None
    column: int | None = None
    fix_suggestion: str | None = None


def load_rules(path: Path | None = None) -> list[Rule]:
    """Load and parse the anti-pattern catalog.

    Parameters
    ----------
    path : Path | None, optional
        Override path for testing. Defaults to the bundled
        ``02-anti-patterns.yaml``.

    Returns
    -------
    list[Rule]
        Parsed rule objects in declaration order.
    """
    yaml_path = path or _RULES_PATH
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    rules: list[Rule] = []
    for entry in data.get("rules", []):
        detector = entry.get("detector", {})
        kind = detector.get("kind", "regex")
        if kind == "regex":
            value = detector["pattern"]
        elif kind == "substring":
            value = detector["literal"]
        else:
            raise ValueError(
                f"Unsupported detector kind {kind!r} in rule "
                f"{entry.get('id')!r}"
            )
        rules.append(
            Rule(
                id=entry["id"],
                severity=entry["severity"],
                detector_kind=kind,
                detector_value=value,
                message=entry["message"].rstrip(),
                why=(entry.get("why") or None),
                fix_suggestion=entry.get("fix_suggestion"),
            )
        )
    return rules


def _scan_one(code: str, rule: Rule) -> list[Issue]:
    matches: list[Issue] = []
    if rule.detector_kind == "regex":
        pattern = re.compile(rule.detector_value, re.MULTILINE)
        for m in pattern.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            snippet = code.splitlines()[line - 1].strip() if code else None
            matches.append(
                Issue(
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=rule.message,
                    line=line,
                    snippet=snippet,
                    column=m.start(),
                    fix_suggestion=rule.fix_suggestion,
                )
            )
    elif rule.detector_kind == "substring":
        idx = 0
        while True:
            found = code.find(rule.detector_value, idx)
            if found < 0:
                break
            line = code.count("\n", 0, found) + 1
            matches.append(
                Issue(
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=rule.message,
                    line=line,
                    column=found,
                    fix_suggestion=rule.fix_suggestion,
                )
            )
            idx = found + len(rule.detector_value)
    return matches


def lint(code: str, *, rules: Iterable[Rule] | None = None) -> list[Issue]:
    """Apply anti-pattern rules to a Python source string.

    .. note::

        ``code`` must be **Python source**, not YAML/Markdown/JSON. The
        rules are regex-based, so feeding non-Python content (e.g. the
        anti-patterns YAML itself) will produce false positives.

    Parameters
    ----------
    code : str
        Python source to scan.
    rules : Iterable[Rule] | None, optional
        Override the rule set (e.g. for tests). Defaults to
        :func:`load_rules` output.

    Returns
    -------
    list[Issue]
        Issues in declaration order, deduplicated by
        ``(rule_id, column)`` so multiple violations on the same line
        are reported separately.
    """
    rule_list = list(rules) if rules is not None else load_rules()
    issues: list[Issue] = []
    # Dedupe by (rule_id, absolute match offset). ``column`` is the
    # absolute character offset of the match, which is unique per
    # occurrence even when several violations share a line. Using
    # ``(rule_id, line)`` (the previous key) collapsed them and hid
    # the second match from agents trying to auto-fix.
    seen: set[tuple[str, int | None]] = set()
    for rule in rule_list:
        for issue in _scan_one(code, rule):
            key = (issue.rule_id, issue.column)
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)
    return issues


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


# ---------------------------------------------------------------------------
# 0.3 → 0.4 source rewriter (T4 in 0.5+ AI-readiness roadmap).
#
# Splits its job into two passes:
#   1. Safe textual substitutions that the agent can rely on
#      mechanically (``dm.cm2in`` → ``dm.cm``, ``plt.style.use`` →
#      ``dm.style.use``, ``plt.subplots`` → ``dm.subplots``).
#   2. Patterns whose 0.4 replacement depends on context — the
#      width tokens, ``figsize=`` tuples, ``tight_layout()`` calls,
#      and the removed ``dm.agent_utils`` / ``dm.xplot`` namespaces.
#      Those get a one-line ``# TODO(dm-migrate): …`` comment
#      inserted directly above the offending line.
#
# The function is intentionally regex-only. AST-based migration is in
# the spec's "Out of Scope" list.
# ---------------------------------------------------------------------------

_MIGRATE_SAFE_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bdm\.cm2in\b"), "dm.cm"),
    (re.compile(r"\bplt\.style\.use\b"), "dm.style.use"),
    (re.compile(r"\bplt\.subplots\b"), "dm.subplots"),
)

_MIGRATE_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bdm\.(?:SW|MW|TW|DW)\b"),
        "dm.SW/MW/TW/DW removed in 0.4; use dm.col1, dm.col2, or dm.cm(<num>).",
    ),
    (
        re.compile(r"\bdm\.FS_[A-Z_]+\b"),
        "dm.FS_* tuples removed; use dm.subplots(width=..., aspect=...).",
    ),
    (
        re.compile(r"\bdm\.WIDTHS\["),
        'dm.WIDTHS removed; pick a width string (e.g. "9cm") instead.',
    ),
    (
        re.compile(r"\bfigsize\s*=\s*\("),
        "figsize= forbidden; use dm.subplots(width=..., aspect=...).",
    ),
    (
        re.compile(r"\btight_layout\s*\("),
        "tight_layout() collides with dm spines; use dm.auto_layout(fig).",
    ),
    (
        re.compile(r"\bdm\.agent_utils\b"),
        "dm.agent_utils removed; surfaces moved to dm.lint, "
        "dm.validate_figure, dm.helpers, etc.",
    ),
    (
        re.compile(r"\bdm\.xplot\b"),
        "dm.xplot removed; templates now live in dm.templates / "
        "dm.helpers (see docs/migration.md).",
    ),
)


def migrate_legacy_code(code: str) -> str:
    """Best-effort regex rewrite from 0.3-era to 0.4 dartwork-mpl idioms.

    Two passes:

    1. **Safe substitutions** are applied in place
       (``dm.cm2in`` → ``dm.cm``, ``plt.style.use`` → ``dm.style.use``,
       ``plt.subplots`` → ``dm.subplots``).
    2. **Context-dependent patterns** (the deprecated width tokens,
       ``figsize=`` literals, ``tight_layout()`` calls, and the removed
       ``dm.agent_utils`` / ``dm.xplot`` namespaces) get a
       ``# TODO(dm-migrate): …`` comment inserted above the offending
       line so the agent can see what to change without losing the
       original code.

    Parameters
    ----------
    code : str
        0.3-era Python source.

    Returns
    -------
    str
        Rewritten source. Always returned (never raises). Use
        :func:`lint` on the result to confirm no critical issues
        remain after the agent applies the manual hints.

    Notes
    -----
    AST-based migration is intentionally out of scope (see
    ``docs/superpowers/specs/2026-05-01-ai-readiness-0.5-roadmap.md``,
    "Out of Scope"). Inputs that don't match any pattern are returned
    unchanged.
    """
    # Pass 1: safe in-place substitutions.
    for pattern, replacement in _MIGRATE_SAFE_REWRITES:
        code = pattern.sub(replacement, code)

    # Pass 2: emit hint comments above any line containing a context-
    # dependent pattern. Multiple matches on one line produce multiple
    # hints (one per pattern, in declaration order). Indentation is
    # copied from the matched line so the comments align.
    output_lines: list[str] = []
    for line in code.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        line_terminator = line[len(body) :]
        # Files that don't end with a newline produce an empty
        # `line_terminator` for their final line. Without forcing a
        # newline below, the inserted "# TODO(dm-migrate): ..." comment
        # would concatenate directly with the original code on join,
        # effectively turning that statement into part of the comment
        # text. Force `\n` whenever the source had no trailing newline.
        comment_terminator = line_terminator or "\n"
        leading_ws_match = re.match(r"\s*", body)
        indent = leading_ws_match.group(0) if leading_ws_match else ""
        for pattern, hint in _MIGRATE_HINTS:
            if pattern.search(body):
                output_lines.append(
                    f"{indent}# TODO(dm-migrate): {hint}{comment_terminator}"
                )
        output_lines.append(line)
    return "".join(output_lines)
