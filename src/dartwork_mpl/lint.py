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

__all__ = ["Rule", "Issue", "load_rules", "lint", "format_report"]

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
    """A detected violation."""

    rule_id: str
    severity: str
    message: str
    line: int | None = None
    snippet: str | None = None


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
                )
            )
            idx = found + len(rule.detector_value)
    return matches


def lint(code: str, *, rules: Iterable[Rule] | None = None) -> list[Issue]:
    """Apply anti-pattern rules to a Python source string.

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
        Issues in declaration order, deduplicated by (rule_id, line).
    """
    rule_list = list(rules) if rules is not None else load_rules()
    issues: list[Issue] = []
    seen: set[tuple[str, int | None]] = set()
    for rule in rule_list:
        for issue in _scan_one(code, rule):
            key = (issue.rule_id, issue.line)
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)
    return issues


def format_report(issues: list[Issue]) -> str:
    """Render issues as newline-separated `[SEV] rule-id: message` lines."""
    if not issues:
        return "✅ No issues found."
    lines: list[str] = []
    for issue in issues:
        line_part = f" (line {issue.line})" if issue.line else ""
        lines.append(
            f"[{issue.severity.upper()}] {issue.rule_id}{line_part}: "
            f"{issue.message.splitlines()[0]}"
        )
    return "\n".join(lines)
