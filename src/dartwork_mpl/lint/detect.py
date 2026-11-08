"""Rule detection: apply catalog rules to a source string.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``lint``. Bundled rules
use the static detectors here, one per rule id in ``_BUILTIN_DETECTORS``;
the ``_TEXT_ONLY_RULES`` and custom rules use their regex or substring.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from matplotlib import colormaps
from matplotlib.colors import is_color_like

from .._compat import _LINT_RULES, LintRule
from .catalog import (
    Issue,
    Rule,
    _AstCheck,
    _AstNameDetector,
    _RegexDetector,
    _rule_detector,
    _SubstringDetector,
    _UnsupportedDetector,
    load_rules,
)
from .syntax import (
    _CMAP_CALLS,
    _COLOR_CALLS,
    _COLOR_KEYWORDS,
    SourceRejected,
    _OwnerKind,
    _parse_source,
    _source_registrations,
    _Syntax,
)

_Detect: TypeAlias = Callable[[_Syntax, Rule], Iterable[int]]
"""A bundled rule's static detector: source offsets of its violations."""


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
) -> tuple[ast.expr, list[str], _OwnerKind | None]:
    """Read only recognized owners of an actual call expression."""
    return syntax.owner(call.func, conventional=conventional)


@dataclass(frozen=True)
class _CallSite:
    """One call expression with the owner facts every call rule reads.

    ``direct`` means the method is called on the owner itself
    (``plt.savefig``, not ``plt.style.use``); ``constructors`` means the
    call builds a Figure (``plt.figure`` / ``plt.subplots`` /
    ``Figure()``).
    """

    node: ast.Call
    path: list[str]
    kind: _OwnerKind | None
    method: str
    start: int
    native: bool
    constructors: bool


def _call_sites(syntax: _Syntax) -> Iterator[_CallSite]:
    """Every call in the source with its conventional owner resolved."""
    for node in ast.walk(syntax.tree):
        if not isinstance(node, ast.Call):
            continue
        owner, path, kind = _call_owner(syntax, node, conventional=True)
        native = kind in {"pyplot", "axes", "figure"} and len(path) == 1
        constructors = (
            kind == "pyplot" and path in (["figure"], ["subplots"])
        ) or (kind == "figure-class" and not path)
        yield _CallSite(
            node,
            path,
            kind,
            path[-1] if path else "",
            syntax.span(owner)[0],
            native,
            constructors,
        )


def _tight_layout(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``plt.tight_layout()`` / ``fig.tight_layout()``, at the method name."""
    for site in _call_sites(syntax):
        if (
            site.native
            and site.kind in {"pyplot", "figure"}
            and site.method == "tight_layout"
            and isinstance(site.node.func, ast.Attribute)
        ):
            yield _method_offset(syntax, site.node.func)


def _is_concatenation(node: ast.expr) -> bool:
    """``a + b``, or a list or tuple that unpacks sequences (``[*a, *b]``)."""
    if isinstance(node, ast.BinOp):
        return isinstance(node.op, ast.Add)
    return isinstance(node, (ast.List, ast.Tuple)) and any(
        isinstance(item, ast.Starred) for item in node.elts
    )


def _twin_legend_hand_merge(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """An Axes legend call that merges a twin pair's entries by hand.

    Only in a source that makes a ``twinx`` / ``twiny``, and only on an
    Axes (or pyplot's current Axes): ``ax.legend(h1 + h2, l1 + l2)`` after
    two ``get_legend_handles_labels`` reads, or ``ax.legend(lns, labs)``
    whose handles are, or name a variable bound to, a concatenation
    (``lns = l1 + l2``). That is the merge ``dm.place_legend`` does for a
    twin pair. One legend for two panels, or a figure legend, is the
    caller's layout: ``dm.place_legend(ax)`` would drop entries there.
    """
    figure_legends = {
        id(site.node)
        for site in _call_sites(syntax)
        if site.kind == "figure" and site.method == "legend"
    }
    reads = twins = 0
    concatenated: set[str] = set()
    for node in ast.walk(syntax.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            reads += node.func.attr == "get_legend_handles_labels"
            twins += node.func.attr in {"twinx", "twiny"}
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and _is_concatenation(node.value)
        ):
            concatenated.add(node.targets[0].id)

    def merged(node: ast.expr | None) -> bool:
        return node is not None and (
            _is_concatenation(node)
            or (isinstance(node, ast.Name) and node.id in concatenated)
        )

    if not twins:
        return
    for node in ast.walk(syntax.tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "legend"
            and id(node) not in figure_legends
        ):
            continue
        given = {
            keyword.arg: keyword.value
            for keyword in node.keywords
            if keyword.arg in {"handles", "labels"}
        }
        positional = list(node.args)
        handles = positional[0] if positional else given.get("handles")
        labels = positional[1] if len(positional) > 1 else given.get("labels")
        both = (
            reads >= 2
            and handles is not None
            and labels is not None
            and _is_concatenation(handles)
            and _is_concatenation(labels)
        )
        if both or merged(handles):
            yield _method_offset(syntax, node.func)


def _plt_style_use(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``plt.style.use(...)``."""
    for site in _call_sites(syntax):
        if site.kind == "pyplot" and site.path == ["style", "use"]:
            yield site.start


def _plt_show_only(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """A bare ``plt.show()``."""
    for site in _call_sites(syntax):
        if (
            site.kind == "pyplot"
            and site.path == ["show"]
            and not site.node.args
            and not site.node.keywords
        ):
            yield site.start


def _savefig_direct(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``plt.savefig(...)`` / ``fig.savefig(...)``."""
    for site in _call_sites(syntax):
        if (
            site.native
            and site.kind in {"pyplot", "figure"}
            and site.method == "savefig"
        ):
            yield site.start


def _dpi_arg(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``dpi=`` passed to ``plt.figure`` / ``plt.subplots``."""
    for site in _call_sites(syntax):
        if (
            site.constructors
            and site.kind == "pyplot"
            and any(keyword.arg == "dpi" for keyword in site.node.keywords)
        ):
            yield site.start


def _multirow_subplots(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``plt.subplots`` with a literal 2+ rows and no gridspec/share keywords."""
    for site in _call_sites(syntax):
        if not (site.kind == "pyplot" and site.path == ["subplots"]):
            continue
        node = site.node
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
            yield site.start


def _figsize_tuples(syntax: _Syntax) -> Iterator[ast.keyword]:
    """``figsize=(...)`` tuple keywords on Figure constructors."""
    for site in _call_sites(syntax):
        if not site.constructors:
            continue
        for keyword in site.node.keywords:
            if keyword.arg == "figsize" and isinstance(
                keyword.value, ast.Tuple
            ):
                yield keyword


def _figsize_direct(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """Any ``figsize=(w, h)`` tuple on a Figure constructor."""
    for keyword in _figsize_tuples(syntax):
        yield syntax.span(keyword)[0]


def _dm_in_figsize(names: frozenset[str]) -> _Detect:
    """A ``figsize=(...)`` tuple that uses one of the ``dm`` ``names``."""

    def detect(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
        for keyword in _figsize_tuples(syntax):
            if any(
                isinstance(item, ast.Attribute)
                and item.attr in names
                and syntax.kind(item.value, conventional=True) == "dm"
                for item in ast.walk(keyword.value)
            ):
                yield syntax.span(keyword)[0]

    return detect


def _raw_width_number(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``dm.figsize(<bare number>, ...)``."""
    for site in _call_sites(syntax):
        if site.kind == "dm" and site.path == ["figsize"] and site.node.args:
            argument = syntax.code[slice(*syntax.span(site.node.args[0]))]
            if re.fullmatch(r"-?\d+(?:\.\d+)?", argument):
                yield site.start


def _oversize_width(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """A literal ``"<n>cm"`` width above 17 cm in ``dm.figsize`` or ``width=``."""
    for site in _call_sites(syntax):
        node = site.node
        values = (
            [(node.args[0], site.start)]
            if site.kind == "dm" and site.path == ["figsize"] and node.args
            else []
        )
        if site.kind in {"dm", "pyplot", "figure", "axes"}:
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
                yield offset


def _keyword_pattern(syntax: _Syntax, rule: Rule) -> Iterator[int]:
    """The rule's regex matched at the start of a keyword on a native call."""
    pattern = re.compile(rule.detector_value)
    for site in _call_sites(syntax):
        if not site.native:
            continue
        for keyword in site.node.keywords:
            text = syntax.code[slice(*syntax.span(keyword))]
            match = pattern.match(text)
            if match:
                yield syntax.span(keyword)[0] + match.start()


def _dm_names(syntax: _Syntax, rule: Rule, *, called: bool) -> Iterator[int]:
    """A ``dm.<path>`` load matching the rule's regex, at its ``dm`` owner.

    With ``called`` the name must be the function of a call and is matched
    with a trailing ``(``, as the catalog pattern spells it.
    """
    for node in ast.walk(syntax.tree):
        if not (
            isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)
        ):
            continue
        owner, path, kind = syntax.owner(node, conventional=True)
        if not (kind == "dm" and path):
            continue
        text = "dm." + ".".join(path)
        if called:
            parent = syntax.parents.get(id(node))
            if not isinstance(parent, ast.Call) or parent.func is not node:
                continue
            text += "("
        if re.fullmatch(rule.detector_value, text) or (
            re.match(rule.detector_value, text)
            and not isinstance(syntax.parents.get(id(node)), ast.Attribute)
        ):
            yield syntax.span(owner)[0]


def _dm_called(syntax: _Syntax, rule: Rule) -> Iterator[int]:
    """A removed or renamed ``dm`` function that is called."""
    return _dm_names(syntax, rule, called=True)


def _dm_referenced(syntax: _Syntax, rule: Rule) -> Iterator[int]:
    """A removed ``dm`` name that is referenced at all."""
    return _dm_names(syntax, rule, called=False)


def _removed_name_detector(rule: LintRule) -> _Detect:
    """The static detector of a registry rule's form."""
    match rule.form:
        case "call":
            return _dm_called
        case "reference":
            return _dm_referenced
        case "figsize":
            return _dm_in_figsize(frozenset(rule.names))


def _literal_names(syntax: _Syntax, rule: Rule) -> Iterator[int]:
    """A literal colormap or colour name matplotlib does not know."""
    detector = _rule_detector(rule)
    if isinstance(detector, _AstNameDetector):
        yield from _literal_name_offsets(syntax, detector.check)


_MPL_DEFAULT_REQUEST: Mapping[str, tuple[object, ...]] = MappingProxyType(
    {
        "style": ("sci", "scientific"),
        "useOffset": (True,),
        "scilimits": ((-5, 6),),
        "useMathText": (False,),
        "useLocale": (False,),
    }
)
"""``ticklabel_format`` values a fresh ``ScalarFormatter`` already holds
(matplotlib's rc defaults): asking for them changes no attribute."""


def _asks_only_defaults(call: ast.Call) -> bool:
    """Every keyword but ``axis`` a literal default, and at least one."""
    asked = False
    for keyword in call.keywords:
        if keyword.arg is None:  # **kwargs: the source cannot tell
            return False
        if keyword.arg == "axis":
            continue
        try:
            value = ast.literal_eval(keyword.value)
        except (ValueError, TypeError, SyntaxError):
            return False
        if isinstance(value, list):
            value = tuple(value)
        if value not in _MPL_DEFAULT_REQUEST.get(keyword.arg, ()):
            return False
        asked = True
    return asked and not call.args


def _callee_name(func: ast.expr) -> str:
    """The called name: ``f`` for ``f(...)``, ``attr`` for ``x.attr(...)``."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _literal_axis(call: ast.Call, position: int, default: str) -> str | None:
    """The ``axis`` a call targets (``"x"``, ``"y"`` or ``"both"``), from its
    keyword or its ``position``-th argument; ``None`` when the source cannot
    tell."""
    node: ast.expr | None = None
    for keyword in call.keywords:
        if keyword.arg == "axis":
            node = keyword.value
        elif keyword.arg is None:
            return None
    if node is None and len(call.args) > position:
        node = call.args[position]
    if node is None:
        return default
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None
    return value if value in ("x", "y", "both") else None


def _directions(axis: str) -> tuple[str, ...]:
    return ("x", "y") if axis == "both" else (axis,)


def _prepared_axes(syntax: _Syntax) -> dict[tuple[str, str], int]:
    """Axis directions given an order-independent formatter, keyed by the
    Axes' source text and ``"x"``/``"y"``, at the earliest offset.

    ``ax.yaxis.set_major_formatter(ScalarFormatter(...))`` prepares ``y``;
    ``dm.format_axis_year(ax, axis=...)`` prepares its axis (``"x"`` by
    default). A later default ``ticklabel_format`` request on a prepared
    direction holds through the layout, so the advisory must not repeat
    its own cure; another direction of the same Axes is not covered.
    """
    prepared: dict[tuple[str, str], int] = {}

    def mark(receiver: ast.expr, directions: tuple[str, ...], at: int) -> None:
        for direction in directions:
            key = (ast.unparse(receiver), direction)
            prepared[key] = min(at, prepared.get(key, at))

    for node in ast.walk(syntax.tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        at = syntax.span(node)[0]
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "set_major_formatter"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr in {"xaxis", "yaxis"}
            and node.args
            and isinstance(node.args[0], ast.Call)
            and _callee_name(node.args[0].func) == "ScalarFormatter"
        ):
            mark(func.value.value, (func.value.attr[0],), at)
        elif _callee_name(func) == "format_axis_year" and node.args:
            axis = _literal_axis(node, 1, "x")
            if axis is not None:
                mark(node.args[0], _directions(axis), at)
    return prepared


def _ticklabel_format_default(syntax: _Syntax, _rule: Rule) -> Iterator[int]:
    """``ax.ticklabel_format(style="sci")`` asking only for defaults before
    any ``dm.simple_layout`` in the source (source order, not run order).

    Quiet when every direction the request targets was given an explicit
    ``ScalarFormatter`` or ``dm.format_axis_year`` earlier on the same Axes,
    and for a request made after a layout (matplotlib applies it; running
    the layout again, as the guide says, keeps its multiplier on the
    canvas)."""
    sites = list(_call_sites(syntax))
    layouts = [
        site.start
        for site in sites
        if site.kind == "dm" and site.method == "simple_layout"
    ]
    if not layouts:
        return
    first = min(layouts)
    prepared = _prepared_axes(syntax)
    for site in sites:
        if (
            site.native
            and site.kind in {"axes", "pyplot"}
            and site.method == "ticklabel_format"
            and isinstance(site.node.func, ast.Attribute)
            and site.start < first
            and _asks_only_defaults(site.node)
        ):
            if site.kind == "axes":
                axis = _literal_axis(site.node, len(site.node.args), "both")
                receiver = ast.unparse(site.node.func.value)
                if axis is not None and all(
                    prepared.get((receiver, d), site.start) < site.start
                    for d in _directions(axis)
                ):
                    continue
            yield _method_offset(syntax, site.node.func)


_BUILTIN_DETECTORS: Mapping[str, _Detect] = MappingProxyType(
    {
        "invalid-colormap-name": _literal_names,
        "invalid-color-name": _literal_names,
        "figsize-direct": _figsize_direct,
        "tight-layout": _tight_layout,
        "twin-legend-hand-merge": _twin_legend_hand_merge,
        "multirow-subplots-no-gridspec-kw": _multirow_subplots,
        "ticklabel-format-default-before-layout": _ticklabel_format_default,
        "plt-style-use": _plt_style_use,
        "plt-show-only": _plt_show_only,
        **{rule.id: _removed_name_detector(rule) for rule in _LINT_RULES},
        "raw-width-number": _raw_width_number,
        "dpi-arg": _dpi_arg,
        "raw-hex-color": _keyword_pattern,
        "fontsize-literal": _keyword_pattern,
        "linewidth-literal": _keyword_pattern,
        "savefig-direct": _savefig_direct,
        "jet-cmap": _keyword_pattern,
        "oversize-width": _oversize_width,
    }
)
"""Bundled rule id -> the static detector that replaces its catalog regex.

A bundled rule is matched on the parsed syntax, so strings, comments and
look-alike names do not trip it. The catalog regex stays the rule's
documentation and the detector for edited copies of the rule. The
removed-name rules take the detector of their form in the registry
(``dartwork_mpl._compat._LINT_RULES``).
"""

_TEXT_ONLY_RULES = frozenset({"zero-resize-mention"})
"""Bundled rules deliberately scanned as raw text with their catalog detector."""


def _builtin_matches(
    syntax: _Syntax, rule: Rule, detect: _Detect
) -> list[Issue]:
    """Report a bundled rule's static matches once each, in source order."""
    offsets = set(detect(syntax, rule))
    return [_issue(syntax.code, rule, offset) for offset in sorted(offsets)]


def _literal_name_offsets(syntax: _Syntax, check: _AstCheck) -> list[int]:
    """Check actual literal arguments on proven or conventional plotting receivers."""
    registrations = _source_registrations(syntax.tree, check)
    if registrations is None:
        return []
    offsets: list[int] = []
    for node in ast.walk(syntax.tree):
        if not isinstance(node, ast.Call):
            continue
        _owner, path, kind = _call_owner(syntax, node, conventional=True)
        if kind not in {"pyplot", "axes"} or len(path) != 1:
            continue
        method = path[0]
        candidates: list[ast.expr] = []
        if check == "colormap-name":
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
        elif check == "color-name" and method in _COLOR_CALLS:
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
                    if check == "colormap-name"
                    else is_color_like(value.value)
                )
            )
            if not valid:
                offsets.append(syntax.span(value)[0])
    return sorted(offsets)


def _scan_literal_names(
    syntax: _Syntax, rule: Rule, check: _AstCheck
) -> list[Issue]:
    """Report a literal-name rule's matches in source order."""
    return [
        _issue(syntax.code, rule, offset)
        for offset in _literal_name_offsets(syntax, check)
    ]


def _scan_one(code: str, rule: Rule) -> list[Issue]:
    """Apply one catalog-selected detector and preserve source locations.

    A rule whose detector this engine does not implement matches nothing.
    """
    match _rule_detector(rule):
        case _AstNameDetector(check):
            syntax = _parse_source(code)
            if isinstance(syntax, SourceRejected):
                return []
            return _scan_literal_names(syntax, rule, check)
        case _RegexDetector(pattern):
            compiled = re.compile(pattern, re.MULTILINE)
            return [
                _text_issue(code, rule, m.start())
                for m in compiled.finditer(code)
            ]
        case _SubstringDetector(literal):
            matches: list[Issue] = []
            idx = 0
            while True:
                found = code.find(literal, idx)
                if found < 0:
                    break
                matches.append(_text_issue(code, rule, found))
                idx = found + len(literal)
            return matches
        case _UnsupportedDetector():
            return []


def _text_issue(code: str, rule: Rule, offset: int) -> Issue:
    """Build a raw-text match; regex and substring rules share this shape.

    Unlike ``_issue`` the snippet is ``None`` for empty source.
    """
    line = code.count("\n", 0, offset) + 1
    snippet = code.splitlines()[line - 1].strip() if code else None
    return Issue(
        rule_id=rule.id,
        severity=rule.severity,
        message=rule.message,
        line=line,
        snippet=snippet,
        column=offset,
        fix_suggestion=rule.fix_suggestion,
    )


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
        detect = _BUILTIN_DETECTORS.get(rule.id)
        if rule == bundled.get(rule.id) and detect is not None:
            matches = (
                []
                if isinstance(syntax, SourceRejected)
                else _builtin_matches(syntax, rule, detect)
            )
        else:
            matches = _scan_one(code, rule)
        for issue in matches:
            key = (issue.rule_id, issue.column)
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)
    return issues
