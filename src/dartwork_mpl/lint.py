"""dartwork-mpl lint engine.

Loads the anti-pattern catalog from
``asset/prompt/02-anti-patterns.yaml`` and applies it to a Python
source string. Used by the MCP ``lint_dartwork_mpl_code`` tool, the
Python ``dm.lint_code(code)`` API, and CI drift tests. No lint CLI is provided.

The catalog owns rule text and selects regex, substring, or static AST
detectors. AST name checks consult the live public matplotlib registries;
supplied source is never executed or imported.
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

import ast
import io
import json
import re
import tokenize
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml
from matplotlib import colormaps
from matplotlib.colors import is_color_like

_RULES_PATH: Path = (
    Path(__file__).parent / "asset" / "prompt" / "02-anti-patterns.yaml"
)


@dataclass(frozen=True)
class Rule:
    """A single anti-pattern definition."""

    id: str
    severity: str  # "critical" | "warning" | "info"
    detector_kind: str  # "regex" | "substring" | "ast"
    detector_value: str  # pattern, literal, or AST check name
    message: str
    why: str | None = None
    fix_suggestion: str | None = None


@dataclass(frozen=True)
class Issue:
    """A detected violation.

    ``column`` is the absolute character offset of the match in the source
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
        elif kind == "ast" and detector.get("check") in {
            "colormap-name",
            "color-name",
        }:
            value = detector["check"]
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


_CMAP_CALLS = frozenset(
    {
        "imshow",
        "matshow",
        "scatter",
        "pcolor",
        "pcolormesh",
        "contour",
        "contourf",
        "tripcolor",
        "tricontour",
        "tricontourf",
        "hist2d",
        "hexbin",
    }
)
_COLOR_CALLS = frozenset(
    {
        "plot",
        "scatter",
        "bar",
        "barh",
        "hist",
        "text",
        "annotate",
        "step",
        "stairs",
        "errorbar",
        "fill",
        "fill_between",
        "fill_betweenx",
        "axhline",
        "axvline",
        "axhspan",
        "axvspan",
    }
)
_COLOR_KEYWORDS = frozenset(
    {"color", "facecolor", "edgecolor", "markerfacecolor", "markeredgecolor"}
)


def _dotted_name(node: ast.expr) -> str:
    """Read only a simple name/attribute chain, without evaluating an expression."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    return ".".join([node.id, *reversed(parts)])


def _source_registrations(tree: ast.AST, check: str) -> set[str] | None:
    """Exempt explicit registrations; unresolved mutations defer their name check.

    Matplotlib import aliases are read as syntax only. Literal map names
    passed with ``register(name=...)`` and direct named-color mapping
    assignments are understood. Other map registrations may obtain their
    names from arbitrary code, so map-name checking conservatively defers.
    Direct named-color mapping updates and dynamic assignment keys likewise
    defer color-name checking without evaluating the supplied mutation.
    """
    mpl_names = {"mpl", "matplotlib"}
    cmap_names: set[str] = set()
    color_modules = {"mcolors", "matplotlib.colors"}
    color_mappings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "matplotlib":
                    mpl_names.add(alias.asname or alias.name)
                elif alias.name == "matplotlib.colors":
                    color_modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "matplotlib":
            for alias in node.names:
                if alias.name == "colormaps":
                    cmap_names.add(alias.asname or alias.name)
                elif alias.name == "colors":
                    color_modules.add(alias.asname or alias.name)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module == "matplotlib.colors"
        ):
            color_mappings.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "get_named_colors_mapping"
            )
    registries = cmap_names | {f"{name}.colormaps" for name in mpl_names}
    color_mappings.update(
        f"{name}.get_named_colors_mapping" for name in color_modules
    )
    registrations: set[str] = set()
    for node in ast.walk(tree):
        if (
            check == "colormap-name"
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
            and _dotted_name(node.func.value) in registries
        ):
            name = next(
                (k.value for k in node.keywords if k.arg == "name"), None
            )
            if not isinstance(name, ast.Constant) or not isinstance(
                name.value, str
            ):
                return None
            registrations.add(name.value)
        elif (
            check == "color-name"
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and isinstance(node.func.value, ast.Call)
            and _dotted_name(node.func.value.func) in color_mappings
        ):
            return None
        elif check == "color-name" and isinstance(node, ast.Assign):
            for target in node.targets:
                if not (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Call)
                    and _dotted_name(target.value.func) in color_mappings
                ):
                    continue
                if isinstance(target.slice, ast.Constant) and isinstance(
                    target.slice.value, str
                ):
                    registrations.add(target.slice.value)
                else:
                    return None
    return registrations


_CANONICAL = {"plt": "pyplot", "ax": "axes", "fig": "figure", "dm": "dm"}
_RELEVANT_ATTRIBUTES = {
    "tight_layout",
    "simple_layout",
    "style",
    "figure",
    "subplots",
    "savefig",
    "show",
    "figsize",
    "get_cmap",
    *_CMAP_CALLS,
    *_COLOR_CALLS,
}


def _bound_names(node: ast.AST) -> set[str]:
    """Find writes in this lexical scope without inheriting nested scope bodies."""
    names: set[str] = set()

    def visit(current: ast.AST) -> None:
        """Collect binding syntax only, never evaluate a target or declaration."""
        if isinstance(
            current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            names.add(current.name)
            return
        if isinstance(current, ast.Name) and isinstance(
            current.ctx, (ast.Store, ast.Del)
        ):
            names.add(current.id)
        elif isinstance(current, ast.arg):
            names.add(current.arg)
        elif isinstance(current, (ast.Global, ast.Nonlocal)):
            names.update(current.names)
        elif isinstance(current, ast.Import):
            names.update(
                alias.asname or alias.name.split(".")[0]
                for alias in current.names
            )
        elif isinstance(current, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in current.names)
        elif (
            isinstance(current, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar))
            and current.name
        ):
            names.add(current.name)
        elif isinstance(current, ast.MatchMapping) and current.rest:
            names.add(current.rest)
        for child in ast.iter_child_nodes(current):
            visit(child)

    for child in ast.iter_child_nodes(node):
        visit(child)
    return names


class _Syntax:
    """Parsed source, character spans and conservative per-expression binding facts."""

    def __init__(
        self, code: str, tree: ast.Module, tokens: list[tokenize.TokenInfo]
    ):
        """Read lexical syntax once; each scope starts without inherited proof."""
        self.code = code
        self.tree = tree
        self.tokens = tokens
        self.lines = code.splitlines(keepends=True)
        self.starts = [0]
        for line in self.lines:
            self.starts.append(self.starts[-1] + len(line))
        self.facts: dict[int, dict[str, str | None]] = {}
        self.parents = {
            id(child): node
            for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)
        }
        self.protected = [
            (self.token_offset(token.start), self.token_offset(token.end))
            for token in tokens
            if token.type in (tokenize.STRING, tokenize.COMMENT)
        ]
        self.protected.extend(
            self.span(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.JoinedStr)
        )
        self._statements(tree.body, {})

    def token_offset(self, point: tuple[int, int]) -> int:
        """Convert tokenizer character columns to absolute source offsets."""
        row, column = point
        return self.starts[min(row - 1, len(self.starts) - 1)] + column

    def offset(self, row: int, column: int) -> int:
        """Convert AST UTF-8 byte columns without normalizing source bytes."""
        line = self.lines[row - 1]
        return self.starts[row - 1] + len(
            line.encode("utf-8")[:column].decode("utf-8")
        )

    def span(self, node: ast.AST) -> tuple[int, int]:
        """Return the complete AST node's half-open character span."""
        if not isinstance(node, (ast.expr, ast.stmt, ast.keyword)):
            raise ValueError(
                "A source span requires an expression or statement"
            )
        if node.end_lineno is None or node.end_col_offset is None:
            raise ValueError("The parsed node has no complete source span")
        return (
            self.offset(node.lineno, node.col_offset),
            self.offset(node.end_lineno, node.end_col_offset),
        )

    def kind(self, node: ast.AST, *, conventional: bool = False) -> str | None:
        """Resolve only explicit imported owners or a canonical snippet receiver."""
        name = _dotted_name(node) if isinstance(node, ast.expr) else ""
        env = self.facts.get(id(node), {})
        if name in env:
            kind = env[name]
            # A native constructor proves Figure type, not renderer readiness.
            return "figure" if kind == "bare-figure" else kind
        if conventional and isinstance(node, ast.Name) and node.id not in env:
            return _CANONICAL.get(node.id)
        return None

    def owner(
        self, node: ast.expr, *, conventional: bool = False
    ) -> tuple[ast.expr, list[str], str | None]:
        """Split an attribute chain at an explicitly recognized module/object owner."""
        parts: list[str] = []
        current = node
        while True:
            kind = self.kind(current, conventional=conventional)
            if kind:
                return current, list(reversed(parts)), kind
            if not isinstance(current, ast.Attribute):
                return current, [], None
            parts.append(current.attr)
            current = current.value

    def _invalidate(self, target: ast.AST, env: dict[str, str | None]) -> None:
        """Invalidate explicit writes, including relevant tracked attribute writes."""
        if isinstance(target, ast.Name):
            for key in list(env):
                if key == target.id or key.startswith(target.id + "."):
                    env[key] = None
            env[target.id] = None
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._invalidate(item, env)
        elif isinstance(target, ast.Starred):
            self._invalidate(target.value, env)
        elif isinstance(target, ast.Attribute):
            dotted = _dotted_name(target)
            owners = sorted({*env, *_CANONICAL}, key=len, reverse=True)
            for owner in owners:
                if not dotted.startswith(owner + "."):
                    continue
                attribute = dotted[len(owner) + 1 :].split(".")[0]
                kind = env.get(owner, _CANONICAL.get(owner))
                if attribute in _RELEVANT_ATTRIBUTES or kind == "dm":
                    self._invalidate(ast.Name(id=owner.split(".")[0]), env)
                break

    def _expression(
        self, node: ast.AST | None, env: dict[str, str | None]
    ) -> None:
        """Record facts at each expression without carrying proof into new scopes."""
        if node is None:
            return
        self.facts[id(node)] = dict(env)
        if isinstance(node, ast.Lambda):
            local = dict.fromkeys(_bound_names(node))
            self._expression(node.body, local)
            return
        if isinstance(
            node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            local = dict.fromkeys(_bound_names(node))
            for child in ast.iter_child_nodes(node):
                self._expression(child, local)
            return
        for child in ast.iter_child_nodes(node):
            self._expression(child, env)
        if isinstance(node, ast.NamedExpr):
            self._invalidate(node.target, env)

    def _constructor(self, value: ast.expr | None) -> str | None:
        """Recognize direct Figure and pyplot construction, never arbitrary aliases."""
        if not isinstance(value, ast.Call):
            return None
        if self.kind(value.func) == "figure-class":
            return "bare-figure"
        if (
            isinstance(value.func, ast.Attribute)
            and self.kind(value.func.value) == "pyplot"
            and value.func.attr in {"figure", "subplots"}
        ):
            return value.func.attr
        return None

    def _assign(
        self,
        target: ast.expr,
        value: ast.expr | None,
        env: dict[str, str | None],
    ) -> None:
        """Commit only direct constructor facts after invalidating assignment targets."""
        self._invalidate(target, env)
        kind = self._constructor(value)
        if isinstance(target, ast.Name) and kind in {"figure", "bare-figure"}:
            env[target.id] = kind
        elif (
            kind == "subplots"
            and isinstance(target, (ast.Tuple, ast.List))
            and len(target.elts) == 2
        ):
            figure, axes = target.elts
            if isinstance(figure, ast.Name):
                env[figure.id] = "figure"
            if (
                isinstance(axes, ast.Name)
                and isinstance(value, ast.Call)
                and _single_axes(value)
            ):
                env[axes.id] = "axes"

    def _statements(
        self, statements: list[ast.stmt], env: dict[str, str | None]
    ) -> None:
        """Follow straight-line statements, invalidating ambiguous-flow writes."""
        for statement in statements:
            self.facts[id(statement)] = dict(env)
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    bound = alias.asname or alias.name.split(".")[0]
                    self._invalidate(ast.Name(id=bound), env)
                    if alias.name == "matplotlib.pyplot":
                        env[alias.asname or alias.name] = "pyplot"
                    elif alias.name == "dartwork_mpl":
                        env[bound] = "dm"
            elif isinstance(statement, ast.ImportFrom):
                if any(alias.name == "*" for alias in statement.names):
                    for name in {*env, *_CANONICAL}:
                        env[name] = None
                for alias in statement.names:
                    bound = alias.asname or alias.name
                    self._invalidate(ast.Name(id=bound), env)
                    if (
                        statement.module == "matplotlib"
                        and alias.name == "pyplot"
                    ):
                        env[bound] = "pyplot"
                    elif (
                        statement.module == "matplotlib.figure"
                        and alias.name == "Figure"
                    ):
                        env[bound] = "figure-class"
            elif isinstance(
                statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                for child in ast.iter_child_nodes(statement):
                    if not isinstance(child, ast.stmt):
                        self._expression(child, env)
                self._invalidate(ast.Name(id=statement.name), env)
                local = dict.fromkeys(_bound_names(statement))
                self._statements(statement.body, local)
            elif isinstance(statement, ast.Assign):
                self._expression(statement.value, env)
                for target in statement.targets:
                    self._expression(target, env)
                    self._assign(target, statement.value, env)
            elif isinstance(statement, ast.AnnAssign):
                self._expression(statement.annotation, env)
                self._expression(statement.value, env)
                self._expression(statement.target, env)
                self._assign(statement.target, statement.value, env)
            elif isinstance(statement, (ast.AugAssign, ast.Delete)):
                self._expression(statement, env)
                targets = (
                    statement.targets
                    if isinstance(statement, ast.Delete)
                    else [statement.target]
                )
                for target in targets:
                    self._invalidate(target, env)
            elif isinstance(statement, (ast.Global, ast.Nonlocal)):
                for name in statement.names:
                    self._invalidate(ast.Name(id=name), env)
            elif (
                isinstance(
                    statement,
                    (
                        ast.If,
                        ast.For,
                        ast.AsyncFor,
                        ast.While,
                        ast.Try,
                        ast.With,
                        ast.AsyncWith,
                        ast.Match,
                    ),
                )
                or type(statement).__name__ == "TryStar"
            ):
                names = _bound_names(statement)
                for name in names:
                    self._invalidate(ast.Name(id=name), env)
                for node in ast.walk(statement):
                    if isinstance(node, ast.Attribute) and isinstance(
                        node.ctx, (ast.Store, ast.Del)
                    ):
                        self._invalidate(node, env)
                for child in ast.iter_child_nodes(statement):
                    if isinstance(child, ast.stmt):
                        self._statements([child], dict(env))
                    else:
                        self._flow_child(child, dict(env))
                for name in names:
                    self._invalidate(ast.Name(id=name), env)
            else:
                self._expression(statement, env)

    def _flow_child(self, node: ast.AST, env: dict[str, str | None]) -> None:
        """Read handlers/cases under conservative flow facts without merging proof."""
        self.facts[id(node)] = dict(env)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                self._statements([child], env)
            else:
                self._expression(child, env)


def _single_axes(call: ast.Call) -> bool:
    """Prove only a statically single, squeezed subplots result is scalar Axes."""
    if len(call.args) > 2 or any(
        keyword.arg is None for keyword in call.keywords
    ):
        return False
    values = {
        "nrows": call.args[0] if call.args else None,
        "ncols": call.args[1] if len(call.args) > 1 else None,
    }
    for keyword in call.keywords:
        if keyword.arg in values:
            values[keyword.arg] = keyword.value
        elif keyword.arg == "squeeze" and not (
            isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
        ):
            return False
    return all(
        value is None
        or (
            isinstance(value, ast.Constant)
            and type(value.value) is int
            and value.value == 1
        )
        for value in values.values()
    )


def _parse_source(code: str) -> _Syntax | None:
    """Refuse malformed AST/token streams completely; submitted source stays inert."""
    try:
        tree = ast.parse(code)
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        if any(
            token.type == tokenize.ERRORTOKEN and not token.string.isspace()
            for token in tokens
        ):
            return None
        return _Syntax(code, tree, tokens)
    except (
        SyntaxError,
        ValueError,
        RecursionError,
        UnicodeError,
        tokenize.TokenError,
    ):
        return None


def _issue(code: str, rule: Rule, offset: int) -> Issue:
    """Keep catalog fields and public absolute character locations unchanged."""
    line = code.count("\n", 0, offset) + 1
    return Issue(
        rule.id,
        rule.severity,
        rule.message,
        line,
        code.splitlines()[line - 1].strip(),
        offset,
        rule.fix_suggestion,
    )


def _method_offset(syntax: _Syntax, node: ast.Attribute) -> int:
    """Locate the actual method identifier, even after Unicode or spaced dots."""
    return syntax.span(node)[1] - len(node.attr)


def _call_owner(
    syntax: _Syntax, call: ast.Call, *, conventional: bool = False
) -> tuple[ast.expr, list[str], str | None]:
    """Read only recognized owners of an actual call expression."""
    return syntax.owner(call.func, conventional=conventional)


def _builtin_matches(syntax: _Syntax, rule: Rule) -> list[Issue]:
    """Apply catalog rules to executable syntax while retaining actual literal rules."""
    if rule.detector_kind == "ast":
        return _scan_literal_names(syntax.code, rule, syntax)
    offsets: set[int] = set()
    for node in ast.walk(syntax.tree):
        if isinstance(node, ast.Call):
            owner, path, kind = _call_owner(syntax, node, conventional=True)
            method = path[-1] if path else ""
            start = syntax.span(owner)[0]
            direct = len(path) == 1
            native = kind in {"pyplot", "axes", "figure"} and direct
            constructors = (
                kind == "pyplot" and path in (["figure"], ["subplots"])
            ) or (kind == "figure-class" and not path)
            if (
                rule.id == "tight-layout"
                and native
                and kind in {"pyplot", "figure"}
                and method == "tight_layout"
                and isinstance(node.func, ast.Attribute)
            ):
                offsets.add(_method_offset(syntax, node.func))
            elif (
                (
                    rule.id == "plt-style-use"
                    and kind == "pyplot"
                    and path == ["style", "use"]
                )
                or (
                    rule.id == "plt-show-only"
                    and kind == "pyplot"
                    and path == ["show"]
                    and not node.args
                    and not node.keywords
                )
                or (
                    rule.id == "savefig-direct"
                    and native
                    and kind in {"pyplot", "figure"}
                    and method == "savefig"
                )
                or (
                    rule.id == "dpi-arg"
                    and constructors
                    and kind == "pyplot"
                    and any(keyword.arg == "dpi" for keyword in node.keywords)
                )
            ):
                offsets.add(start)
            elif (
                rule.id == "multirow-subplots-no-gridspec-kw"
                and kind == "pyplot"
                and path == ["subplots"]
            ):
                rows = next(
                    (
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "nrows"
                    ),
                    node.args[0] if node.args else None,
                )
                if (
                    isinstance(rows, ast.Constant)
                    and type(rows.value) is int
                    and rows.value >= 2
                    and not any(
                        keyword.arg in {"gridspec_kw", "sharex", "sharey", None}
                        for keyword in node.keywords
                    )
                ):
                    offsets.add(start)
            elif (
                rule.id in {"figsize-direct", "cm2in-figsize"} and constructors
            ):
                for keyword in node.keywords:
                    if keyword.arg != "figsize" or not isinstance(
                        keyword.value, ast.Tuple
                    ):
                        continue
                    if rule.id == "figsize-direct" or any(
                        isinstance(item, ast.Attribute)
                        and item.attr == "cm2in"
                        and syntax.kind(item.value, conventional=True) == "dm"
                        for item in ast.walk(keyword.value)
                    ):
                        offsets.add(syntax.span(keyword)[0])
            elif (
                rule.id == "raw-width-number"
                and kind == "dm"
                and path == ["figsize"]
                and node.args
            ):
                argument = syntax.code[slice(*syntax.span(node.args[0]))]
                if re.fullmatch(r"-?\d+(?:\.\d+)?", argument):
                    offsets.add(start)
            elif rule.id == "oversize-width":
                values = (
                    [(node.args[0], start)]
                    if kind == "dm" and path == ["figsize"] and node.args
                    else []
                )
                if kind in {"dm", "pyplot", "figure", "axes"}:
                    values += [
                        (keyword.value, syntax.span(keyword)[0])
                        for keyword in node.keywords
                        if keyword.arg == "width"
                    ]
                for value, offset in values:
                    if (
                        isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and re.fullmatch(r"\d+(?:\.\d+)?cm", value.value)
                        and float(value.value[:-2]) > 17
                    ):
                        offsets.add(offset)
            elif (
                rule.id
                in {
                    "raw-hex-color",
                    "fontsize-literal",
                    "linewidth-literal",
                    "jet-cmap",
                }
                and native
            ):
                pattern = re.compile(rule.detector_value)
                for keyword in node.keywords:
                    text = syntax.code[slice(*syntax.span(keyword))]
                    match = pattern.match(text)
                    if match:
                        offsets.add(syntax.span(keyword)[0] + match.start())
        if (
            (rule.id.startswith("dm-") or rule.id == "deprecated-width-token")
            and isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
        ):
            owner, path, kind = syntax.owner(node, conventional=True)
            if kind == "dm" and path:
                text = "dm." + ".".join(path)
                if rule.id in {
                    "dm-subplots-removed",
                    "dm-spines-removed",
                    "dm-legacy-wrappers-removed",
                    "dm-auto-select-colors-renamed",
                    "dm-auto-layout-removed",
                    "dm-named-renamed",
                }:
                    parent = syntax.parents.get(id(node))
                    if (
                        not isinstance(parent, ast.Call)
                        or parent.func is not node
                    ):
                        continue
                    text += "("
                if re.fullmatch(rule.detector_value, text) or (
                    re.match(rule.detector_value, text)
                    and not isinstance(
                        syntax.parents.get(id(node)), ast.Attribute
                    )
                ):
                    offsets.add(syntax.span(owner)[0])
    return [_issue(syntax.code, rule, offset) for offset in sorted(offsets)]


def _scan_literal_names(
    code: str, rule: Rule, syntax: _Syntax | None = None
) -> list[Issue]:
    """Check actual literal arguments on proven or conventional plotting receivers."""
    syntax = syntax or _parse_source(code)
    if syntax is None:
        return []
    registrations = _source_registrations(syntax.tree, rule.detector_value)
    if registrations is None:
        return []
    matches: list[Issue] = []
    for node in ast.walk(syntax.tree):
        if not isinstance(node, ast.Call):
            continue
        _owner, path, kind = _call_owner(syntax, node, conventional=True)
        if kind not in {"pyplot", "axes"} or len(path) != 1:
            continue
        method = path[0]
        candidates: list[ast.expr] = []
        if rule.detector_value == "colormap-name":
            if method in _CMAP_CALLS:
                candidates = [
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg == "cmap"
                ]
            elif method == "get_cmap" and kind == "pyplot":
                candidates = list(node.args[:1]) + [
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg == "name"
                ]
        elif rule.detector_value == "color-name" and method in _COLOR_CALLS:
            candidates = [
                keyword.value
                for keyword in node.keywords
                if keyword.arg in _COLOR_KEYWORDS
            ]
        for value in candidates:
            if not isinstance(value, ast.Constant) or not isinstance(
                value.value, str
            ):
                continue
            keyword = next(
                (
                    keyword.arg
                    for keyword in node.keywords
                    if keyword.value is value
                ),
                None,
            )
            sentinel = (
                keyword in {"markerfacecolor", "markeredgecolor"}
                and value.value.lower() == "auto"
            ) or (
                method == "scatter"
                and keyword == "edgecolor"
                and value.value.lower() == "face"
            )
            valid = (
                value.value in registrations
                or sentinel
                or (
                    value.value in colormaps
                    if rule.detector_value == "colormap-name"
                    else is_color_like(value.value)
                )
            )
            if not valid:
                matches.append(_issue(code, rule, syntax.span(value)[0]))
    return sorted(matches, key=lambda issue: issue.column or 0)


def _scan_one(code: str, rule: Rule) -> list[Issue]:
    """Apply one catalog-selected detector and preserve source locations."""
    if rule.detector_kind == "ast":
        return _scan_literal_names(code, rule)
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

        ``code`` must be **Python source**, not YAML/Markdown/JSON. Most
        built-in executable rules require complete Python syntax. Deliberate
        text-only and custom regex/substring rules still inspect raw text.

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
    catalog = load_rules()
    rule_list = list(rules) if rules is not None else catalog
    bundled = {rule.id: rule for rule in catalog}
    syntax = _parse_source(code)
    issues: list[Issue] = []
    # Dedupe by (rule_id, absolute match offset). ``column`` is the
    # absolute character offset of the match, which is unique per
    # occurrence even when several violations share a line. Using
    # ``(rule_id, line)`` (the previous key) collapsed them and hid
    # the second match from agents trying to auto-fix.
    seen: set[tuple[str, int | None]] = set()
    for rule in rule_list:
        if rule == bundled.get(rule.id) and rule.detector_kind != "substring":
            matches = [] if syntax is None else _builtin_matches(syntax, rule)
        else:
            matches = _scan_one(code, rule)
        for issue in matches:
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
    """Read shipped preset file names without importing or executing submitted code."""
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return False
    with (Path(__file__).parent / "asset/mplstyle/presets.json").open(
        encoding="utf-8"
    ) as handle:
        presets = json.load(handle)
    return value.value in presets


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
