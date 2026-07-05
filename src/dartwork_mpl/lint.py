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
from collections.abc import Callable, Iterable
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
            # Populate ``snippet`` symmetrically with the regex branch —
            # it used to be regex-only, so substring issues rendered
            # without their offending line.
            snippet = code.splitlines()[line - 1].strip() if code else None
            matches.append(
                Issue(
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=rule.message,
                    line=line,
                    snippet=snippet,
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
    (
        re.compile(r"\bdm\.auto_layout\s*\("),
        "dm.auto_layout removed in 0.5.4; use "
        "dm.simple_layout(fig, margin=...) (legacy padding maps to "
        "margin; max_iter/tolerance are obsolete).",
    ),
    (
        re.compile(
            r"\bdm\.(?:install_llm_txt|uninstall_llm_txt|INSTALL_TARGETS)\b"
        ),
        "install_llm_txt family removed in 0.5; use "
        "dm.get_agent_doc(name) / dm.agent_doc_path(name) or the MCP "
        "dartwork-mpl://guide/* resources.",
    ),
    (
        re.compile(r"\bdm\.(?:style_spines|add_grid|minimal_axes)\b"),
        "dm.style_spines/add_grid/minimal_axes removed in 0.4.1; inline "
        "the raw matplotlib calls (see docs/usage_guide/recipes.md).",
    ),
    (
        re.compile(r"\bdm\.format_axis_percent\s*\("),
        "dm.format_axis_percent removed in 0.4.1; use "
        "ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0)) "
        "(from matplotlib import ticker).",
    ),
    (
        re.compile(r"\bdm\.format_axis_labels\s*\("),
        "dm.format_axis_labels removed in 0.4.1; use "
        'ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}")) '
        "(from matplotlib import ticker).",
    ),
    (
        re.compile(r"\bdm\.format_axis_thousands\s*\("),
        "dm.format_axis_thousands removed in 0.4.1; use "
        'ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{x:,.0f}")) '
        "(from matplotlib import ticker).",
    ),
    (
        re.compile(r"\bdm\.add_frame\s*\("),
        "dm.add_frame removed in 0.4.1; use "
        "fig.patches.append(plt.Rectangle((0, 0), 1, 1, fill=False, "
        "transform=fig.transFigure)).",
    ),
    (
        re.compile(r"\bdm\.add_value_labels\s*\("),
        "dm.add_value_labels removed in 0.4.1; use a plain loop of "
        "ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), "
        'f"{bar.get_height():.0f}", ha="center", va="bottom").',
    ),
    (
        re.compile(r"\bdm\.set_xmargin\s*\("),
        "dm.set_xmargin removed in 0.4.1; use ax.set_xmargin(...) "
        "(the matplotlib Axes method).",
    ),
    (
        re.compile(r"\bdm\.set_ymargin\s*\("),
        "dm.set_ymargin removed in 0.4.1; use ax.set_ymargin(...) "
        "(the matplotlib Axes method).",
    ),
    (
        re.compile(r"\bdm\.hide_spines\s*\("),
        "dm.hide_spines removed in 0.4.1; use "
        'for s in ("top", "right"): ax.spines[s].set_visible(False).',
    ),
    (
        re.compile(r"\bdm\.hide_all_spines\s*\("),
        "dm.hide_all_spines removed in 0.4.1; use "
        "for s in ax.spines: ax.spines[s].set_visible(False).",
    ),
    (
        re.compile(r"\bdm\.show_only_spines\s*\("),
        "dm.show_only_spines removed in 0.4.1; use "
        'for s in ax.spines: ax.spines[s].set_visible(s in ("left", "bottom")).',
    ),
    (
        re.compile(r"\bdm\.remove_grid\s*\("),
        "dm.remove_grid removed in 0.4.1; use ax.grid(False).",
    ),
    (
        re.compile(r"\bdm\.save_figure\s*\("),
        "dm.save_figure removed in 0.4.1; use fig.savefig(...) "
        "(or dm.save_formats(fig, path) for multi-format).",
    ),
    (
        re.compile(r"\bdm\.create_figure_with_style\s*\("),
        "dm.create_figure_with_style removed in 0.4.1; use "
        'dm.style.use(style); plt.subplots(figsize=dm.figsize("<n>cm", '
        '"<aspect>")).',
    ),
    (
        re.compile(r"\bdm\.auto_select_colors\b"),
        "dm.auto_select_colors renamed in 0.4.1; use "
        "dm.make_palette(n, kind=..., highlight=...).",
    ),
    (
        re.compile(r"\bdm\.named\s*\("),
        "dm.named removed in 0.4.1; use dm.color(...) (accepts token "
        "names, hex, rgb()/oklch()/oklab()).",
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


def _rewrite_tight_layout(match: re.Match[str]) -> str:
    """Rewrite ``<recv>.tight_layout()`` preserving the receiver name."""
    receiver = match.group(1)
    figure = "fig" if receiver == "plt" else receiver
    return f"dm.simple_layout({figure})"


def _protected_spans(code: str) -> list[tuple[int, int]]:
    """Absolute ``(start, end)`` offsets of string / comment tokens.

    Auto-fix substitutions must not rewrite text inside string literals
    or comments (e.g. a docstring mentioning ``plt.tight_layout()``), so
    those regions are masked out. Returns ``[]`` if the source can't be
    tokenized (malformed snippet) — the caller then falls back to a
    plain whole-source substitution.
    """
    import io
    import tokenize

    # Map 1-based line number → absolute offset of that line's start.
    line_starts = [0]
    for line in code.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    def _abs(row: int, col: int) -> int:
        return line_starts[row - 1] + col

    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    return [
        (_abs(*tok.start), _abs(*tok.end))
        for tok in toks
        # FSTRING_* tokens exist on 3.12+; guard by name.
        if tok.type in (tokenize.STRING, tokenize.COMMENT)
        or tokenize.tok_name.get(tok.type, "").startswith("FSTRING")
    ]


def _sub_outside_strings(
    pattern: re.Pattern[str],
    repl: str | Callable[[re.Match[str]], str],
    code: str,
) -> str:
    """``pattern.sub`` applied only outside string / comment regions."""
    protected = _protected_spans(code)
    if not protected:
        return pattern.sub(repl, code)

    def _guarded(match: re.Match[str]) -> str:
        s, e = match.span()
        for ps, pe in protected:
            if s < pe and e > ps:  # overlaps a protected span
                return match.group(0)
        return repl(match) if callable(repl) else match.expand(repl)

    return pattern.sub(_guarded, code)


_AUTO_FIX_TABLE: tuple[
    tuple[str, re.Pattern[str], str | Callable[[re.Match[str]], str]], ...
] = (
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
    # plt.tight_layout() / <fig>.tight_layout() → dm.simple_layout(<fig>).
    # The receiver is preserved so ``myfig.tight_layout()`` rewrites to
    # ``dm.simple_layout(myfig)`` rather than the canonical-but-wrong
    # ``dm.simple_layout(fig)`` (which would reference an undefined name).
    # A ``plt`` receiver has no figure handle, so it falls back to the
    # canonical ``fig`` used across every template and recipe.
    (
        "tight-layout",
        re.compile(r"\b(plt|[A-Za-z_][A-Za-z0-9_]*)\.tight_layout\s*\(\s*\)"),
        _rewrite_tight_layout,
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

    fixable_ids = {rule_id for rule_id, _, _ in _AUTO_FIX_TABLE}
    for _rule_id, pattern, replacement in _AUTO_FIX_TABLE:
        code = _sub_outside_strings(pattern, replacement, code)

    after = lint(code)
    after_signatures = {(i.rule_id, i.line, i.column) for i in after}
    # An issue is "applied" only if this function could fix its rule and
    # the issue is gone. Restricting to ``fixable_ids`` prevents a
    # non-fixable issue (e.g. ``figsize-direct``) whose column merely
    # shifted after a same-line rewrite from being falsely reported as
    # both applied and still-unfixed.
    applied = [
        i
        for i in before
        if i.rule_id in fixable_ids
        and (i.rule_id, i.line, i.column) not in after_signatures
    ]
    return code, applied, after
