"""Legacy-code migration: rewrite proven styles and annotate removed APIs.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``migrate_legacy_code``.
The hint table changes together with the package root's removed-name
registry.
"""

from __future__ import annotations

import ast
import re

from .detect import lint
from .fix import _apply_edits, _Edit, _planned_fixes
from .syntax import _parse_source, _Syntax

# Legacy migration hint wording remains owned by the existing catalog below.
_MODEL_B_REMOVED_COLOR_NAMES: tuple[str, ...] = (
    "get_\u0070alette",
    "set_\u0063ycle",
    "cycle",
    "cycle_\u0063ycler",
    "list_\u0070alettes",
    "list_\u0063olormaps",
    "plot_\u0063olors",
    "plot_\u0063olormaps",
    "show_\u0070alette",
    "classify_\u0063olormap",
    "Dartwork\u0043olor",
    "Dartwork\u0043olormap",
)
_MODEL_B_REMOVED_COLOR_PATTERN = "|".join(
    re.escape(name) for name in _MODEL_B_REMOVED_COLOR_NAMES
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
    (
        re.compile(r"\bdm\.(?:" + _MODEL_B_REMOVED_COLOR_PATTERN + r")\b"),
        "Model B removed this color API vocabulary; use dm.colors(...), "
        "dm.set_colors(...), dm.list_colors(), or dm.show_colors().",
    ),
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
        kind: str | None = None
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
                allowed = set(range(len(_MIGRATE_HINTS))) - {5, 6, 7}
            elif isinstance(node, ast.Call) and kind in {"figure", "pyplot"}:
                if path == ["tight_layout"]:
                    start, end = syntax.span(node.func)
                    text = syntax.code[start:end] + "("
                    allowed = {6}
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
                                entry[2].add(5)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("dm.agent_utils")
        ):
            start, end = syntax.span(node)
            text = syntax.code[start:end]
            allowed = {7}
        if start is None or any(
            left <= start < right for left, right in syntax.protected
        ):
            continue
        for index in allowed:
            pattern, _hint = _MIGRATE_HINTS[index]
            match = pattern.search(text)
            if match is None or (
                index != 7 and kind == "dm" and match.start() != 0
            ):
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
    if syntax is None:
        return code
    fixes = _planned_fixes(syntax, lint(code), layout=False)
    edits = [edit for fix in fixes for edit in fix.edits] + _migration_hints(
        syntax
    )
    result = _apply_edits(code, edits)
    return code if result is None else result
