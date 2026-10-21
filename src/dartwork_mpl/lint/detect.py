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

from .catalog import Issue, Rule, load_rules
from .syntax import (
    _CMAP_CALLS,
    _COLOR_CALLS,
    _COLOR_KEYWORDS,
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
