"""Static source analysis for the lint engine: parsing and name-binding facts.

Private to :mod:`dartwork_mpl.lint`. ``_parse_source`` turns submitted
source into a ``_Syntax`` (AST, tokens and per-node binding facts) without
executing or importing it, or returns ``None`` when it cannot.
"""

from __future__ import annotations

import ast
import io
import tokenize

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
        """Track absolute-import facts; local imports and flow invalidate names."""
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
                        statement.level == 0
                        and statement.module == "matplotlib"
                        and alias.name == "pyplot"
                    ):
                        env[bound] = "pyplot"
                    elif (
                        statement.level == 0
                        and statement.module == "matplotlib.figure"
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
