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
    "apply_lint_fixes",
    "format_report",
    "lint",
    "load_rules",
    "migrate_legacy_code",
]

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

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
#      mechanically (``plt.style.use`` → ``dm.style.use``).
#   2. Patterns whose replacement depends on context — the ``dm.cm2in``
#      helper (returned inches; the correct rewrite depends on whether
#      it sits inside a ``figsize=``), the deprecated width tokens, the
#      removed ``dm.subplots`` / ``dm.figure``, ``figsize=(w, h)`` raw
#      tuples, ``tight_layout()`` calls, and the removed
#      ``dm.agent_utils`` / ``dm.xplot`` namespaces. Those get a
#      one-line ``# TODO(dm-migrate): …`` comment inserted directly
#      above the offending line.
#
# The function is intentionally regex-only. AST-based migration is in
# the spec's "Out of Scope" list.
# ---------------------------------------------------------------------------

# NOTE: ``dm.cm2in`` is deliberately NOT a safe rewrite. ``cm2in``
# returned a float (inches); ``dm.cm`` returns a ``Length``. A blind
# ``dm.cm2in`` → ``dm.cm`` swap produces broken ``figsize=(dm.cm(9), …)``
# code AND erases the token the ``cm2in-figsize`` critical lint rule keys
# on. It is handled as a context-dependent hint below (mirrors the same
# reasoning in ``_AUTO_FIX_TABLE``).
_MIGRATE_SAFE_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bplt\.style\.use\b"), "dm.style.use"),
)

_MIGRATE_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bdm\.cm2in\b"),
        "dm.cm2in removed in 0.4 (it returned inches). Inside a figsize, "
        'use figsize=dm.figsize("<n>cm", "<aspect>"); elsewhere use '
        "dm.cm(<n>), which returns a Length, not a float.",
    ),
    (
        re.compile(r"\bdm\.(?:SW|MW|TW|DW)\b"),
        "dm.SW/MW/TW/DW removed in 0.4; use dm.col1, dm.col2, or dm.cm(<num>).",
    ),
    (
        re.compile(r"\bdm\.FS_[A-Z_]+\b"),
        "dm.FS_* tuples removed; use figsize=dm.figsize(<width>, <aspect>).",
    ),
    (
        re.compile(r"\bdm\.WIDTHS\["),
        'dm.WIDTHS removed; pick a width string (e.g. "9cm") instead.',
    ),
    (
        re.compile(r"\bdm\.(?:subplots|figure)\s*\("),
        "dm.subplots / dm.figure removed; use "
        "plt.subplots(figsize=dm.figsize(<width>, <aspect>)) "
        "(call dm.style.use(...) separately for styling).",
    ),
    (
        re.compile(r"\bfigsize\s*=\s*\("),
        "raw figsize=(w, h) tuple bypasses physical-width contract; "
        "use figsize=dm.figsize(<width>, <aspect>).",
    ),
    (
        re.compile(r"\btight_layout\s*\("),
        "tight_layout() collides with dm spines; use dm.simple_layout(fig).",
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
       (``plt.style.use`` → ``dm.style.use``).
    2. **Context-dependent patterns** (``dm.cm2in``, deprecated width
       tokens, the removed ``dm.subplots`` / ``dm.figure``, raw
       ``figsize=(w,h)`` tuples, ``tight_layout()`` calls, and the
       removed ``dm.agent_utils`` / ``dm.xplot`` namespaces) get a
       ``# TODO(dm-migrate): …`` comment inserted above the offending
       line so the agent can see what to change without losing the
       original code. Re-running on already-migrated output is
       idempotent — existing hint comments are not re-flagged.

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
        # A source's final line may have no trailing newline. The
        # injected ``# TODO(dm-migrate): ...`` comment then concatenates
        # with the original code on join, turning that statement into
        # part of the comment text. Force ``\n`` for the comment line
        # whenever the original had no terminator.
        comment_terminator = line_terminator or "\n"
        # Idempotency guard 1: a hint comment can itself contain a pattern
        # token (the ``dm.cm2in`` / ``dm.SW`` hint text), so never re-flag
        # our own injected comments.
        if body.lstrip().startswith("# TODO(dm-migrate):"):
            output_lines.append(line)
            continue
        leading_ws_match = re.match(r"\s*", body)
        indent = leading_ws_match.group(0) if leading_ws_match else ""
        # Idempotency guard 2: the offending code line is left in place
        # (only annotated), so on a re-run it still matches its pattern.
        # Skip any hint that already sits in the contiguous hint block
        # directly above this line so re-runs don't stack duplicates.
        # Multiple *distinct* hints for one line are still allowed.
        existing_hints: set[str] = set()
        for prev in reversed(output_lines):
            if prev.lstrip().startswith("# TODO(dm-migrate):"):
                existing_hints.add(prev.strip())
            else:
                break
        for pattern, hint in _MIGRATE_HINTS:
            if pattern.search(body):
                hint_line = (
                    f"{indent}# TODO(dm-migrate): {hint}{comment_terminator}"
                )
                if hint_line.strip() not in existing_hints:
                    output_lines.append(hint_line)
        output_lines.append(line)
    return "".join(output_lines)


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------
#
# ``apply_lint_fixes`` performs mechanical, identifier-level rewrites
# for a curated subset of lint rules. Lint detector patterns only catch
# the *start* of a violation (``\bplt\.tight_layout\s*\(``), so they
# can't be used as substitution patterns directly — we'd lose the
# trailing ``)``. Instead each entry below pairs a *bounded* search
# pattern with its replacement.
#
# Anything more invasive (figsize tuple → ``dm.figsize`` choice of
# width and aspect, dpi removal that needs argument-list rebalancing)
# is intentionally left to the caller, who can pair this helper with
# ``migrate_legacy_code`` or the MCP ``apply_lint_fixes`` flow.

_AUTO_FIX_TABLE: tuple[tuple[str, re.Pattern[str], str], ...] = (
    # rule_id, search regex, replacement.
    #
    # Each rule_id MUST be a real id in the anti-pattern SSOT
    # (02-anti-patterns.yaml) — the ``apply_lint_fixes`` diff keys on it,
    # and a label with no matching rule is silently dead. A test
    # (``test_auto_fix_rule_ids_exist_in_ssot``) enforces this.
    #
    # ``dm.cm2in`` is deliberately NOT auto-fixed: the only SSOT rule for
    # it is ``cm2in-figsize`` (the ``figsize=(dm.cm2in(...), ...)`` form),
    # whose correct rewrite is ``figsize=dm.figsize("<n>cm", "<aspect>")``
    # — context-dependent, not a token swap. A bare ``dm.cm2in → dm.cm``
    # substitution would be *wrong* (``cm2in`` returns inches, ``cm``
    # returns a Length), so we leave it to ``migrate_legacy_code``.
    ("plt-style-use", re.compile(r"\bplt\.style\.use\b"), "dm.style.use"),
    # plt.tight_layout() / fig.tight_layout() → dm.simple_layout(fig).
    # The replacement assumes the figure is bound to a name we cannot
    # know, so we conservatively use ``fig`` (the canonical name in
    # every dartwork-mpl template + recipe). Callers passing a
    # differently-named figure can fix that manually after the rewrite.
    (
        "tight-layout",
        re.compile(r"\b(?:plt|[A-Za-z_][A-Za-z0-9_]*)\.tight_layout\s*\(\s*\)"),
        "dm.simple_layout(fig)",
    ),
)


def apply_lint_fixes(code: str) -> tuple[str, list[Issue], list[Issue]]:
    """Apply safe mechanical fixes for a curated subset of lint rules.

    Performs identifier- and call-level rewrites for rules whose
    replacement does not depend on caller-supplied parameters
    (currently ``plt-style-use`` and the no-arg form of
    ``tight-layout``). Each rule is applied as a whole-source
    regex substitution, after which the linter re-runs to compute the
    diff between ``before`` and ``after`` issue sets.

    Parameters
    ----------
    code : str
        Python source.

    Returns
    -------
    tuple[str, list[Issue], list[Issue]]
        ``(fixed_code, applied_issues, unfixed_issues)`` —
        ``applied`` mirrors issues that disappear after the rewrite;
        ``unfixed`` is what still trips the linter (typically
        context-dependent rules like ``figsize-direct``).
    """
    before = lint(code)

    for _rule_id, pattern, replacement in _AUTO_FIX_TABLE:
        code = pattern.sub(replacement, code)

    after = lint(code)
    after_signatures = {(i.rule_id, i.line, i.column) for i in after}
    applied = [
        i
        for i in before
        if (i.rule_id, i.line, i.column) not in after_signatures
    ]
    return code, applied, after
