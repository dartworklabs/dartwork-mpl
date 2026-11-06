"""Legacy-code migration: rewrite proven styles and annotate removed APIs.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``migrate_legacy_code``.
The removed-name hints, their names and how each name is used come from
``dartwork_mpl._compat``, the one registry of removed names; this module
only compiles them and adds its two native-call hints.
"""

from __future__ import annotations

import ast
import re

from .._compat import _CODEMOD_HINTS
from .detect import lint
from .fix import _apply_edits, _Edit, _planned_fixes
from .syntax import SourceRejected, _OwnerKind, _parse_source, _Syntax

# Two hints for native calls that are not removed names. Hint comments over
# one statement are written in catalog order; these two have always followed
# the hint for the removed figure constructors, whose replacement they
# complete. Every other hint comes from the removed-name registry.
_FIGSIZE_TUPLE_HINT = (
    re.compile(r"\bfigsize\s*=\s*\("),
    "raw figsize=(w, h) tuple bypasses physical-width contract; "
    "use figsize=dm.figsize(<width>, <aspect>).",
)
_TIGHT_LAYOUT_HINT = (
    re.compile(r"\btight_layout\s*\("),
    "tight_layout() collides with dm spines; use dm.simple_layout(fig).",
)
_AFTER_CONSTRUCTORS = 1 + next(
    index
    for index, hint in enumerate(_CODEMOD_HINTS)
    if "subplots" in hint.names
)
_REGISTRY_HINTS = tuple(
    (re.compile(hint.pattern), hint.text) for hint in _CODEMOD_HINTS
)
_MIGRATE_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    *_REGISTRY_HINTS[:_AFTER_CONSTRUCTORS],
    _FIGSIZE_TUPLE_HINT,
    _TIGHT_LAYOUT_HINT,
    *_REGISTRY_HINTS[_AFTER_CONSTRUCTORS:],
)
_FIGSIZE_TUPLE = _MIGRATE_HINTS.index(_FIGSIZE_TUPLE_HINT)
_TIGHT_LAYOUT = _MIGRATE_HINTS.index(_TIGHT_LAYOUT_HINT)
# Catalog index -> the registry hint it was compiled from.
_REGISTRY_AT = {
    _MIGRATE_HINTS.index(compiled): hint
    for hint, compiled in zip(_CODEMOD_HINTS, _REGISTRY_HINTS, strict=True)
}
# ``from dm.<name> import ...`` module prefixes and their hint index.
_IMPORT_HINTS = tuple(
    (f"dm.{name}", index)
    for index, hint in _REGISTRY_AT.items()
    if hint.form == "import"
    for name in hint.names
)
# The hints a ``dm.<path>`` reference, call or subscript can carry.
_DM_HINTS = frozenset(
    index for index, hint in _REGISTRY_AT.items() if hint.form != "import"
)


def _statement_boundary(
    syntax: _Syntax, node: ast.AST
) -> tuple[int, str, str] | None:
    """Find a physical line start before the containing executable logical statement."""
    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, ast.stmt):
            start, _end = syntax.span(current)
            line_start = syntax.starts[current.lineno - 1]
            indent = syntax.code[line_start:start]
            if not indent.strip():
                line = syntax.lines[current.lineno - 1]
                newline = (
                    "\r\n"
                    if line.endswith("\r\n")
                    else "\n"
                    if line.endswith("\n")
                    else "\r\n"
                    if "\r\n" in syntax.code
                    else "\n"
                )
                return line_start, indent, newline
        current = syntax.parents.get(id(current))
    # A later semicolon-separated statement shares the earlier statement's
    # physical boundary even though that earlier statement is not its parent.
    for statement in ast.walk(syntax.tree):
        if not isinstance(statement, ast.stmt) or statement.lineno != getattr(
            node, "lineno", None
        ):
            continue
        start, _end = syntax.span(statement)
        line_start = syntax.starts[statement.lineno - 1]
        indent = syntax.code[line_start:start]
        if not indent.strip() and start <= syntax.span(node)[0]:
            line = syntax.lines[statement.lineno - 1]
            newline = (
                "\r\n"
                if line.endswith("\r\n")
                else "\n"
                if line.endswith("\n")
                else "\r\n"
                if "\r\n" in syntax.code
                else "\n"
            )
            return line_start, indent, newline
    return None


def _migration_hints(syntax: _Syntax) -> list[_Edit]:
    """Add legacy hints only at executable logical boundaries, outside literals."""
    insertions: dict[int, tuple[str, str, set[int]]] = {}
    for node in ast.walk(syntax.tree):
        start: int | None = None
        kind: _OwnerKind | None = None
        text = ""
        allowed: set[int] = set()
        if isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
            expression = (
                node.func
                if isinstance(node, ast.Call)
                else node.value
                if isinstance(node, ast.Subscript)
                else node
            )
            owner, path, kind = syntax.owner(expression, conventional=True)
            if kind == "dm" and path:
                start, end = syntax.span(node)
                owner_end = syntax.span(owner)[1]
                text = "dm" + syntax.code[owner_end:end]
                allowed = set(_DM_HINTS)
            elif isinstance(node, ast.Call) and kind in {"figure", "pyplot"}:
                if path == ["tight_layout"]:
                    start, end = syntax.span(node.func)
                    text = syntax.code[start:end] + "("
                    allowed = {_TIGHT_LAYOUT}
                if path in (["figure"], ["subplots"]):
                    for keyword in node.keywords:
                        if keyword.arg == "figsize" and isinstance(
                            keyword.value, ast.Tuple
                        ):
                            boundary = _statement_boundary(syntax, node)
                            if boundary:
                                offset, indent, newline = boundary
                                entry = insertions.setdefault(
                                    offset, (indent, newline, set())
                                )
                                entry[2].add(_FIGSIZE_TUPLE)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
            allowed = {
                index
                for prefix, index in _IMPORT_HINTS
                if module.startswith(prefix)
            }
            if allowed:
                start, end = syntax.span(node)
                text = syntax.code[start:end]
        if start is None or any(
            left <= start < right for left, right in syntax.protected
        ):
            continue
        for index in allowed:
            pattern, _hint = _MIGRATE_HINTS[index]
            match = pattern.search(text)
            # A dm-owned path must start with the removed name; an import
            # statement's module follows its ``from``.
            if match is None or (kind == "dm" and match.start() != 0):
                continue
            boundary = _statement_boundary(syntax, node)
            if boundary:
                offset, indent, newline = boundary
                entry = insertions.setdefault(offset, (indent, newline, set()))
                entry[2].add(index)
    edits: list[_Edit] = []
    for offset, (indent, newline, indexes) in sorted(insertions.items()):
        existing: set[str] = set()
        for line in reversed(syntax.code[:offset].splitlines()):
            if line.lstrip().startswith("# TODO(dm-migrate):"):
                existing.add(line.strip())
            else:
                break
        comments = [
            f"{indent}# TODO(dm-migrate): {_MIGRATE_HINTS[index][1]}{newline}"
            for index in sorted(indexes)
            if f"# TODO(dm-migrate): {_MIGRATE_HINTS[index][1]}" not in existing
        ]
        if comments:
            edits.append(_Edit(offset, offset, "".join(comments)))
    return edits


def migrate_legacy_code(code: str) -> str:
    """Rewrite proven supported styles and annotate executable legacy statements.

    Comments, literal values and all bytes outside explicit edits are preserved.
    Unsafe style calls and malformed AST/token streams are returned unchanged.
    Hints never split continuations, inline suites or multiline literal contents.
    """
    syntax = _parse_source(code)
    if isinstance(syntax, SourceRejected):
        return code
    fixes = _planned_fixes(syntax, lint(code), layout=False)
    edits = [edit for fix in fixes for edit in fix.edits] + _migration_hints(
        syntax
    )
    result = _apply_edits(code, edits)
    return result if isinstance(result, str) else code
