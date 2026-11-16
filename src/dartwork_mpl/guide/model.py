"""The guide slice's types, and the one place text becomes them.

A :class:`Rule` from the anti-pattern catalog, the :class:`Code` it is
checked against (the source, its quoted spans and the literal colour and
colormap names it passes) and the :class:`Finding` a match makes. The
reading side is in ``reference``. Everything parses here once; the
decisions only see these types.
"""

from __future__ import annotations

import ast
import re
import token
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import accumulate
from typing import ClassVar, Protocol, runtime_checkable

import yaml

# Larger sources are refused: a plotting script is a few hundred lines.
MAX_SOURCE = 500_000
# Keywords whose literal value is one matplotlib colour.
COLOR_KEYWORDS = frozenset(
    {"c", "color", "ec", "edgecolor", "facecolor", "fc"}
    | {"markeredgecolor", "markerfacecolor", "mec", "mfc"}
)
# dartwork-mpl's own helpers take colour words of their own
# (``dm.label_bars(ax, color="series")``), so their calls are not checked.
OWN_ROOTS = frozenset({"dm", "dartwork_mpl"})


@dataclass(frozen=True)
class Critical:
    """A finding that blocks a run: fix it."""

    word: ClassVar[str] = "critical"

    def __str__(self) -> str:
        """The catalog's word for it."""
        return self.word


@dataclass(frozen=True)
class Warn:
    """A finding to fix unless the user asked for the value."""

    word: ClassVar[str] = "warning"

    def __str__(self) -> str:
        """The catalog's word for it."""
        return self.word


@dataclass(frozen=True)
class Info:
    """A hint."""

    word: ClassVar[str] = "info"

    def __str__(self) -> str:
        """The catalog's word for it."""
        return self.word


#: How much a finding matters: ``critical`` blocks a run, ``info`` hints.
Severity = Critical | Warn | Info


def parse_severity(text: object) -> Severity:
    """A catalog severity; ``ValueError`` for anything else."""
    for severity in (Critical(), Warn(), Info()):
        if severity.word == text:
            return severity
    raise ValueError(f"{text!r} is not a severity")


@dataclass(frozen=True)
class ColormapName:
    """A literal colormap name (``cmap="..."``) must be registered."""

    value: ClassVar[str] = "colormap-name"
    rule: ClassVar[str] = "invalid-colormap-name"


@dataclass(frozen=True)
class ColorName:
    """A literal colour (``color="..."``) must be one matplotlib reads."""

    value: ClassVar[str] = "color-name"
    rule: ClassVar[str] = "invalid-color-name"


#: A catalog rule detected from literal names instead of a pattern; ``rule``
#: is the id of the catalog rule it backs.
Check = ColormapName | ColorName


def parse_check(text: object) -> Check:
    """A catalog check; ``ValueError`` for anything else."""
    for check in (ColormapName(), ColorName()):
        if check.value == text:
            return check
    raise ValueError(f"{text!r} is not a check")


@runtime_checkable
class Table(Protocol):
    """A YAML mapping, read by key."""

    def get(self, key: str, /) -> object:
        """The value at ``key``, ``None`` if absent."""
        ...

    def __getitem__(self, key: str, /) -> object:
        """The value at ``key``."""
        ...


@runtime_checkable
class Items(Protocol):
    """A YAML sequence, read for its items."""

    def __iter__(self) -> Iterator[object]:
        """The items."""
        ...


@dataclass(frozen=True)
class Rule:
    """One catalog rule: a pattern over the source, or a literal-name check."""

    id: str
    severity: Severity
    message: str
    fix: str | None
    pattern: re.Pattern[str] | None
    check: Check | None

    @classmethod
    def parse(cls, entry: object) -> Rule:
        """One catalog entry; it gives exactly one of ``pattern`` / ``check``."""
        if not isinstance(entry, Table):
            raise ValueError(f"a catalog rule must be a mapping: {entry!r}")
        pattern, check, fix = (
            entry.get("pattern"),
            entry.get("check"),
            entry.get("fix"),
        )
        if (pattern is None) == (check is None):
            raise ValueError(f"{entry.get('id')}: give a pattern or a check")
        return cls(
            id=str(entry["id"]),
            severity=parse_severity(str(entry["severity"])),
            message=str(entry["message"]).strip(),
            fix=None if fix is None else str(fix),
            pattern=None if pattern is None else re.compile(str(pattern), re.M),
            check=None if check is None else parse_check(str(check)),
        )


@dataclass(frozen=True)
class Rules:
    """The anti-pattern catalog, in file order."""

    items: tuple[Rule, ...]

    @classmethod
    def parse(cls, text: str) -> Rules:
        """Parse the YAML catalog; a malformed one raises ``ValueError``."""
        data: object = yaml.safe_load(text)
        entries = data.get("rules") if isinstance(data, Table) else None
        if isinstance(entries, str | Table) or not isinstance(entries, Items):
            raise ValueError("the catalog must be a mapping with a rules list")
        rules = tuple(Rule.parse(e) for e in entries)
        if len({r.id for r in rules}) != len(rules):
            raise ValueError("rule ids must be unique")
        return cls(rules)


@dataclass(frozen=True)
class Spot:
    """Where a rule matched, and the literal name it matched, if any."""

    offset: int
    name: str | None = None


@dataclass(frozen=True)
class Literal:
    """A literal colour or colormap name, at the offset of its keyword."""

    check: Check
    value: str
    offset: int


@dataclass(frozen=True)
class Registered:
    """Names a source registers itself; ``dynamic`` when one is not a literal."""

    names: frozenset[str] = frozenset()
    dynamic: bool = False


@dataclass(frozen=True)
class Code:
    """A source with what the lint needs to know about it.

    ``quoted`` holds the ``(start, end)`` spans of strings and comments: text
    there is prose, not code. The literal names, the twin axes and the
    registrations come from the syntax tree; a source that does not parse
    has none of them.
    """

    text: str
    quoted: tuple[tuple[int, int], ...]
    literals: tuple[Literal, ...] = ()
    twins: bool = False
    colormaps: Registered = Registered()
    colors: Registered = Registered()

    @classmethod
    def parse(cls, text: object) -> Code:
        """Read a source; more than :data:`MAX_SOURCE` characters raise ``ValueError``."""
        if not isinstance(text, str):
            raise TypeError(f"code must be a str (got {type(text).__name__})")
        if len(text) > MAX_SOURCE:
            raise ValueError(
                f"code is {len(text):,} characters; the lint reads at most {MAX_SOURCE:,}"
            )
        lines = text.splitlines(keepends=True)
        starts = [0, *accumulate(len(line) for line in lines)]
        quoted = _quoted(lines, starts)
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            return cls(text, quoted)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        return cls(
            text=text,
            quoted=quoted,
            literals=tuple(_literals(calls, lines, starts)),
            twins=any(_called(c) in {"twinx", "twiny"} for c in calls),
            colormaps=_colormap_registrations(calls),
            colors=_color_registrations(tree),
        )

    def line_of(self, offset: int) -> int:
        """The 1-based line an offset falls on."""
        return self.text.count("\n", 0, offset) + 1

    def is_quoted(self, offset: int) -> bool:
        """Whether an offset falls inside a string or a comment."""
        return any(start <= offset < end for start, end in self.quoted)


# A colour matplotlib parses without a name: hex (#rgb, #rgba, #rrggbb,
# #rrggbbaa), a cycle entry (C0) or a grey level in [0, 1].
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
_CYCLE = re.compile(r"C\d+")
_GREY = re.compile(r"(?:0(?:\.\d*)?|1(?:\.0*)?|\.\d+)")


@dataclass(frozen=True)
class Known:
    """What matplotlib has registered: colour names (lower case) and colormaps."""

    colors: frozenset[str]
    colormaps: frozenset[str]

    def is_color(self, value: str) -> bool:
        """Whether matplotlib reads ``value`` as a colour: a registered
        name, ``"none"``, hex, a cycle entry (``C0``) or a grey level."""
        text = value.strip()
        return bool(
            text.lower() in self.colors
            or text.lower() == "none"
            or _HEX.fullmatch(text)
            or _CYCLE.fullmatch(text)
            or _GREY.fullmatch(text)
        )


@dataclass(frozen=True)
class LintFacts:
    """A source and the registries its literal names are checked against."""

    code: Code
    known: Known


@dataclass(frozen=True)
class Finding:
    """One rule match: where it is, what it means and how to fix it."""

    rule_id: str
    severity: Severity
    line: int
    message: str
    fix: str | None
    offset: int
    name: str | None = None

    def __str__(self) -> str:
        """``[severity] rule-id (line n): message → fix``."""
        fix = f" → {self.fix}" if self.fix else ""
        return f"[{self.severity}] {self.rule_id} (line {self.line}): {self.message}{fix}"


Findings = tuple[Finding, ...]


# -- reading a source -------------------------------------------------------

# Strings and comments; on Python 3.12+ also the text of an f-string.
_QUOTED = frozenset(
    kind
    for kind, name in token.tok_name.items()
    if name in {"STRING", "COMMENT", "FSTRING_MIDDLE"}
)


def _quoted(lines: list[str], starts: list[int]) -> tuple[tuple[int, int], ...]:
    """Spans of string and comment tokens, up to where tokenizing fails."""
    spans: list[tuple[int, int]] = []
    try:
        for tok in tokenize.generate_tokens(iter(lines).__next__):
            if tok.type in _QUOTED:
                (r0, c0), (r1, c1) = tok.start, tok.end
                spans.append((starts[r0 - 1] + c0, starts[r1 - 1] + c1))
    except (tokenize.TokenError, SyntaxError):
        pass
    return tuple(spans)


def _offset(
    node: ast.expr | ast.keyword, lines: list[str], starts: list[int]
) -> int:
    """A node's character offset (``col_offset`` counts UTF-8 bytes)."""
    line = lines[node.lineno - 1].encode("utf-8")
    return starts[node.lineno - 1] + len(
        line[: node.col_offset].decode("utf-8", "ignore")
    )


def _called(node: ast.AST) -> str:
    """The name a call calls (``ax.twinx()`` → ``twinx``), else ``""``."""
    if not isinstance(node, ast.Call):
        return ""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _root(node: ast.expr) -> str:
    """The name an attribute chain starts from (``dm.label_bars`` → ``dm``)."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ""


def _string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literals(
    calls: list[ast.Call], lines: list[str], starts: list[int]
) -> list[Literal]:
    """Literal ``cmap=``, colour keywords and ``get_cmap("...")`` on matplotlib calls."""
    found: list[Literal] = []
    for call in calls:
        if _root(call.func) in OWN_ROOTS:
            continue
        for kw in call.keywords:
            value = _string(kw.value)
            check = ColormapName() if kw.arg == "cmap" else ColorName()
            if value is not None and (
                kw.arg == "cmap" or kw.arg in COLOR_KEYWORDS
            ):
                found.append(Literal(check, value, _offset(kw, lines, starts)))
        first = call.args[0] if call.args else None
        if _called(call) == "get_cmap" and (value := _string(first)):
            found.append(
                Literal(ColormapName(), value, _offset(call, lines, starts))
            )
    return found


def _colormap_registrations(calls: list[ast.Call]) -> Registered:
    """``colormaps.register(cmap, name="x")``: literal names, or dynamic."""
    names: set[str] = set()
    dynamic = False
    for call in calls:
        func = call.func
        if not (isinstance(func, ast.Attribute) and func.attr == "register"):
            continue
        receiver = ast.unparse(func.value)
        if "colormaps" not in receiver and not receiver.endswith("cm"):
            continue
        name = next(
            (kw.value for kw in call.keywords if kw.arg == "name"), None
        )
        if (value := _string(name)) is None:
            dynamic = True
        else:
            names.add(value)
    return Registered(frozenset(names), dynamic)


def _color_registrations(tree: ast.AST) -> Registered:
    """``get_named_colors_mapping()["x"] = ...``; ``.update(...)`` is dynamic."""
    names: set[str] = set()
    dynamic = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and (
                    _called(target.value) == "get_named_colors_mapping"
                ):
                    if (value := _string(target.slice)) is None:
                        dynamic = True
                    else:
                        names.add(value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and _called(node.func.value) == "get_named_colors_mapping"
        ):
            dynamic = True
    return Registered(frozenset(names), dynamic)
