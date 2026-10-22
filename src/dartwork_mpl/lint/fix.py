"""Proven local autofixes for lint issues.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``apply_lint_fixes``.
The edit planning here is shared with :mod:`.migrate`.
"""

from __future__ import annotations

import ast
import tokenize
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from .catalog import Issue
from .detect import _call_owner, _method_offset, lint
from .syntax import SourceRejected, _OwnerKind, _parse_source, _Syntax


@dataclass(frozen=True)
class _Edit:
    """A bounded source replacement expressed in original character offsets."""

    start: int
    end: int
    text: str


@dataclass(frozen=True)
class _Plan:
    """The edits that remove one occurrence, keyed by the issue's column."""

    offset: int
    edits: tuple[_Edit, ...]


@dataclass(frozen=True)
class _Fix:
    """One original occurrence and the nonoverlapping edits that remove it.

    ``start`` is the fixed call's source offset; fixes apply in that order.
    """

    issue: Issue
    start: int
    edits: tuple[_Edit, ...]


@dataclass(frozen=True)
class EditsOverlap:
    """Two planned edits cover the same original characters."""

    first: _Edit
    second: _Edit


@dataclass(frozen=True)
class EditedSourceRejected:
    """The edited source no longer parses, so the edits are refused."""

    rejection: SourceRejected


EditRefused: TypeAlias = EditsOverlap | EditedSourceRejected
"""Why ``_apply_edits`` returned no source; callers keep the original."""


@dataclass(frozen=True)
class InsideEdit:
    """A result offset lies inside inserted text and has no original position."""


@dataclass(frozen=True)
class _Call:
    """A call expression with its recognized owner and the dm name in scope."""

    node: ast.Call
    owner: ast.expr
    path: list[str]
    kind: _OwnerKind | None
    package: str


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


def _plan_style_use(syntax: _Syntax, call: _Call) -> _Plan | None:
    """``plt.style.use("<shipped preset>")`` → ``dm.style.use(...)``."""
    node = call.node
    if not (
        call.kind == "pyplot"
        and call.path == ["style", "use"]
        and len(node.args) == 1
        and not node.keywords
        and _supported_preset(node.args[0])
    ):
        return None
    start, end = syntax.span(call.owner)
    return _Plan(start, (_Edit(start, end, call.package),))


def _plan_tight_layout(syntax: _Syntax, call: _Call) -> _Plan | None:
    """``fig.tight_layout()`` on a proven Figure → ``dm.simple_layout(fig)``."""
    node, owner = call.node, call.owner
    if not (
        isinstance(owner, ast.Name)
        and call.kind == "figure"
        and syntax.facts.get(id(owner), {}).get(owner.id) == "figure"
        and call.path == ["tight_layout"]
        and isinstance(node.func, ast.Attribute)
        and not node.args
        and not node.keywords
    ):
        return None
    package = call.package
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
        return _Plan(
            offset,
            (
                _Edit(function_start, function_end, f"{package}.simple_layout"),
                _Edit(opening + 1, opening + 1, owner.id),
            ),
        )
    return _Plan(
        offset, (_Edit(start, end, f"{package}.simple_layout({owner.id})"),)
    )


# The catalog rules that have a proven local autofix, each with its planner.
# Public Issue fields remain independent of this private dispatch metadata.
_AUTO_FIX_TABLE: Mapping[str, Callable[[_Syntax, _Call], _Plan | None]] = (
    MappingProxyType(
        {"plt-style-use": _plan_style_use, "tight-layout": _plan_tight_layout}
    )
)

_LAYOUT_RULES = frozenset({"tight-layout"})
"""Autofix rules that rewrite layout calls; migration leaves them alone."""


def _planned_fixes(
    syntax: _Syntax, before: list[Issue], *, layout: bool = True
) -> list[_Fix]:
    """Plan only complete locally proven calls; never infer missing imports or figures."""
    by_key = {(issue.rule_id, issue.column): issue for issue in before}
    planners = [
        (rule_id, planner)
        for rule_id, planner in _AUTO_FIX_TABLE.items()
        if layout or rule_id not in _LAYOUT_RULES
    ]
    fixes: list[_Fix] = []
    for node in ast.walk(syntax.tree):
        if not isinstance(node, ast.Call):
            continue
        owner, path, kind = _call_owner(syntax, node)
        package = _dm_owner(syntax, node.func)
        if package is None:
            continue
        call = _Call(node, owner, path, kind, package)
        for rule_id, planner in planners:
            plan = planner(syntax, call)
            if plan is None:
                continue
            issue = by_key.get((rule_id, plan.offset))
            if issue is not None:
                fixes.append(_Fix(issue, syntax.span(node)[0], plan.edits))
            break
    return sorted(fixes, key=lambda fix: fix.start)


def _apply_edits(code: str, edits: list[_Edit]) -> str | EditRefused:
    """Apply original-span edits once, refusing overlaps or invalid complete output."""
    ordered = sorted(edits, key=lambda edit: (edit.start, edit.end))
    previous: _Edit | None = None
    for edit in ordered:
        if previous is not None and edit.start < previous.end:
            return EditsOverlap(previous, edit)
        previous = edit
    result = code
    for edit in reversed(ordered):
        result = result[: edit.start] + edit.text + result[edit.end :]
    parsed = _parse_source(result)
    if isinstance(parsed, SourceRejected):
        return EditedSourceRejected(parsed)
    return result


def _original_offset(offset: int, edits: list[_Edit]) -> int | InsideEdit:
    """Map a surviving result occurrence back to its original character position."""
    delta = 0
    for edit in sorted(edits, key=lambda item: (item.start, item.end)):
        start = edit.start + delta
        end = start + len(edit.text)
        if offset < start:
            break
        if start <= offset < end:
            return InsideEdit()
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
    if isinstance(syntax, SourceRejected):
        return code, [], before
    fixes = _planned_fixes(syntax, before)
    edits = [edit for fix in fixes for edit in fix.edits]
    result = _apply_edits(code, edits)
    if not isinstance(result, str):
        return code, [], before
    after = lint(result)
    survivors = {
        (issue.rule_id, original)
        for issue in after
        if issue.column is not None
        and isinstance(original := _original_offset(issue.column, edits), int)
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
