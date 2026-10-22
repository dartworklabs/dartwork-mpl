"""Proven local autofixes for lint issues.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``apply_lint_fixes``.
The edit planning here is shared with :mod:`.migrate`.
"""

from __future__ import annotations

import ast
import tokenize
from dataclasses import dataclass

from .catalog import Issue
from .detect import _call_owner, _method_offset, lint
from .syntax import _parse_source, _Syntax

# The table declares the supported actions and their catalog identities.
# Public Issue fields remain independent of this private dispatch metadata.
_AUTO_FIX_TABLE = (
    ("plt-style-use", "style", "style.use"),
    ("tight-layout", "layout", "simple_layout"),
)


@dataclass(frozen=True)
class _Edit:
    """A bounded source replacement expressed in original character offsets."""

    start: int
    end: int
    text: str


@dataclass(frozen=True)
class _Fix:
    """One original occurrence and the nonoverlapping edits that remove it."""

    issue: Issue
    identity: tuple[str, int, int, int]
    edits: tuple[_Edit, ...]


def _dm_owner(syntax: _Syntax, node: ast.expr) -> str | None:
    """Choose an existing direct dm import from this exact expression's scope."""
    return next(
        (
            name
            for name, kind in syntax.facts.get(id(node), {}).items()
            if kind == "dm" and "." not in name
        ),
        None,
    )


def _supported_preset(value: ast.expr) -> bool:
    """Whether ``value`` is a string literal naming a shipped preset.

    Reads the style slice's preset registry; submitted code is never
    imported or executed.
    """
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return False
    from ..style import style as shipped_style

    return value.value in shipped_style.presets_dict()


def _planned_fixes(
    syntax: _Syntax, before: list[Issue], *, layout: bool = True
) -> list[_Fix]:
    """Plan only complete locally proven calls; never infer missing imports or figures."""
    by_key = {(issue.rule_id, issue.column): issue for issue in before}
    fixes: list[_Fix] = []
    ids = {rule_id for rule_id, _action, _method in _AUTO_FIX_TABLE}
    for node in ast.walk(syntax.tree):
        if not isinstance(node, ast.Call):
            continue
        owner, path, kind = _call_owner(syntax, node)
        package = _dm_owner(syntax, node.func)
        if package is None:
            continue
        rule_id = ""
        edits: tuple[_Edit, ...] = ()
        if (
            kind == "pyplot"
            and path == ["style", "use"]
            and len(node.args) == 1
            and not node.keywords
            and _supported_preset(node.args[0])
        ):
            rule_id = "plt-style-use"
            start, end = syntax.span(owner)
            offset = start
            edits = (_Edit(start, end, package),)
        elif (
            layout
            and isinstance(owner, ast.Name)
            and kind == "figure"
            and syntax.facts.get(id(owner), {}).get(owner.id) == "figure"
            and path == ["tight_layout"]
            and isinstance(node.func, ast.Attribute)
            and not node.args
            and not node.keywords
        ):
            rule_id = "tight-layout"
            start, end = syntax.span(node)
            offset = _method_offset(syntax, node.func)
            comments = [
                token
                for token in syntax.tokens
                if token.type == tokenize.COMMENT
                and start <= syntax.token_offset(token.start) < end
            ]
            if comments:
                function_start, function_end = syntax.span(node.func)
                opening = syntax.code.index("(", function_end, end)
                edits = (
                    _Edit(
                        function_start, function_end, f"{package}.simple_layout"
                    ),
                    _Edit(opening + 1, opening + 1, owner.id),
                )
            else:
                edits = (
                    _Edit(start, end, f"{package}.simple_layout({owner.id})"),
                )
        if rule_id not in ids:
            continue
        issue = by_key.get((rule_id, offset))
        if issue is not None:
            span = syntax.span(node)
            fixes.append(_Fix(issue, (rule_id, *span, len(fixes)), edits))
    return sorted(fixes, key=lambda fix: fix.identity[1])


def _apply_edits(code: str, edits: list[_Edit]) -> str | None:
    """Apply original-span edits once, refusing overlaps or invalid complete output."""
    ordered = sorted(edits, key=lambda edit: (edit.start, edit.end))
    end = -1
    for edit in ordered:
        if edit.start < end:
            return None
        end = edit.end
    result = code
    for edit in reversed(ordered):
        result = result[: edit.start] + edit.text + result[edit.end :]
    return result if _parse_source(result) is not None else None


def _original_offset(offset: int, edits: list[_Edit]) -> int | None:
    """Map a surviving result occurrence back to its original character position."""
    delta = 0
    for edit in sorted(edits, key=lambda item: (item.start, item.end)):
        start = edit.start + delta
        end = start + len(edit.text)
        if offset < start:
            break
        if start <= offset < end:
            return None
        delta += len(edit.text) - (edit.end - edit.start)
    return offset - delta


def apply_lint_fixes(code: str) -> tuple[str, list[Issue], list[Issue]]:
    """Fix proven local calls while preserving refused source and occurrence identity.

    Applied Issue locations refer to the original source. Unfixed locations refer
    to the returned source. Malformed input is returned exactly with no applied
    issues; neither parsing nor rewriting executes supplied Python.
    """
    before = lint(code)
    syntax = _parse_source(code)
    if syntax is None:
        return code, [], before
    fixes = _planned_fixes(syntax, before)
    edits = [edit for fix in fixes for edit in fix.edits]
    result = _apply_edits(code, edits)
    if result is None:
        return code, [], before
    after = lint(result)
    survivors = {
        (issue.rule_id, _original_offset(issue.column, edits))
        for issue in after
        if issue.column is not None
    }
    applied = [
        fix.issue
        for fix in fixes
        if (fix.issue.rule_id, fix.issue.column) not in survivors
    ]
    # Preserve the catalog's public declaration order within original locations.
    applied_keys = {(issue.rule_id, issue.column) for issue in applied}
    return (
        result,
        [
            issue
            for issue in before
            if (issue.rule_id, issue.column) in applied_keys
        ],
        after,
    )
