"""Rule detection: apply catalog rules to a source string.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``lint``. Bundled rules
use the static detectors here; custom rules use their regex or substring.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable

from matplotlib import colormaps
from matplotlib.colors import is_color_like

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


def _builtin_matches(syntax: _Syntax, rule: Rule) -> list[Issue]:
    """Apply catalog rules to executable syntax while retaining actual literal rules."""
    detector = _rule_detector(rule)
    if isinstance(detector, _AstNameDetector):
        return _scan_literal_names(syntax, rule, detector.check)
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
    syntax: _Syntax, rule: Rule, check: _AstCheck
) -> list[Issue]:
    """Check actual literal arguments on proven or conventional plotting receivers."""
    code = syntax.code
    registrations = _source_registrations(syntax.tree, check)
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
                matches.append(_issue(code, rule, syntax.span(value)[0]))
    return sorted(matches, key=lambda issue: issue.column or 0)


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
        if rule == bundled.get(rule.id) and rule.detector_kind != "substring":
            matches = (
                []
                if isinstance(syntax, SourceRejected)
                else _builtin_matches(syntax, rule)
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
