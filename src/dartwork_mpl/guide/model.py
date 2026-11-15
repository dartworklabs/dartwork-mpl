"""The guide slice's types, and the one place text becomes them.

The lint side: a :class:`Rule` from the anti-pattern catalog, the
:class:`Code` it is checked against (the source, its quoted spans and the
literal colour and colormap names it passes) and the :class:`Finding` a match
makes. The reading side: a :class:`Reference` (a guide page or a template)
with the words a :class:`Query` is ranked against. Everything parses here
once; the decisions only see these types.
"""

from __future__ import annotations

import ast
import re
import tokenize
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import accumulate
from typing import TypeGuard

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


class Severity(StrEnum):
    """How much a finding matters: ``critical`` blocks a run, ``info`` hints."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Check(StrEnum):
    """A catalog rule detected from literal names instead of a pattern."""

    COLORMAP = "colormap-name"
    COLOR = "color-name"


def _mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, dict)


def _listed(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


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
        if not _mapping(entry):
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
            severity=Severity(str(entry["severity"])),
            message=str(entry["message"]).strip(),
            fix=None if fix is None else str(fix),
            pattern=None if pattern is None else re.compile(str(pattern), re.M),
            check=None if check is None else Check(str(check)),
        )


@dataclass(frozen=True)
class Rules:
    """The anti-pattern catalog, in file order."""

    items: tuple[Rule, ...]

    @classmethod
    def parse(cls, text: str) -> Rules:
        """Parse the YAML catalog; a malformed one raises ``ValueError``."""
        data: object = yaml.safe_load(text)
        entries = data.get("rules") if _mapping(data) else None
        if not _listed(entries):
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


# -- reading ----------------------------------------------------------------


class Kind(StrEnum):
    """A guide page (prose) or a plot template (a runnable script)."""

    GUIDE = "guide"
    TEMPLATE = "template"


_REF_ID = re.compile(r"guide/[a-z0-9-]+|template/(?:advanced/)?[a-z0-9_]+")
_WORD = re.compile(r"[a-z0-9]+")


def ref_id(text: object) -> str:
    """``text`` as a reference id; anything else raises ``ValueError``.

    An id (``guide/layout``, ``template/bar``, ``template/advanced/bar``)
    never names a path.
    """
    if not isinstance(text, str) or not _REF_ID.fullmatch(text):
        raise ValueError(
            f"{text!r} is not a reference id like 'guide/layout', 'template/bar'"
            " or 'template/advanced/bar'; dm.guide.references() lists them"
        )
    return text


def words(text: str) -> frozenset[str]:
    """The lower-case words of ``text``, a plural ``s`` dropped (bars → bar)."""
    return frozenset(
        w[:-1] if len(w) > 3 and w.endswith("s") else w
        for w in _WORD.findall(text.lower())
    )


@dataclass(frozen=True)
class Reference:
    """A guide page or template: its id, a title and summary, and its words."""

    id: str
    kind: Kind
    title: str
    summary: str
    tags: frozenset[str]
    words: frozenset[str]

    @classmethod
    def guide(cls, id: str, text: str) -> Reference:
        """A Markdown page: its first heading, first paragraph and every heading."""
        headings = [
            ln.lstrip("#").strip()
            for ln in text.splitlines()
            if ln.startswith("#")
        ]
        title = headings[0] if headings else id
        prose = [
            " ".join(p.split())
            for p in text.split("\n\n")
            if p.strip()
            and not p.lstrip().startswith(("#", "```", "|", "---", "-"))
        ]
        summary = prose[0] if prose else title
        tags = words(id.removeprefix("guide/"))
        return cls(
            id,
            Kind.GUIDE,
            title,
            summary,
            tags,
            words(" ".join([*headings, summary])),
        )

    @classmethod
    def template(cls, id: str, text: str) -> Reference:
        """A template script: its docstring's first line and its meta block."""
        meta = template_meta(text)
        docstring = text.lstrip().removeprefix('"""').split('"""', 1)[0].strip()
        title = docstring.splitlines()[0] if docstring else id
        summary = meta.get("use_case", title)
        if "data_shape" in meta:
            summary += f". Data: {meta['data_shape']}"
        tags = words(meta.get("tags", ""))
        return cls(
            id,
            Kind.TEMPLATE,
            title,
            summary,
            tags,
            words(" ".join([title, *meta.values()])),
        )


def template_meta(text: str) -> dict[str, str]:
    """The ``key: value`` lines between ``# ai-template-meta-start`` and ``-end``."""
    block = text.partition("# ai-template-meta-start")[2]
    block = block.partition("# ai-template-meta-end")[0]
    pairs = (
        line.removeprefix("#").partition(":") for line in block.splitlines()
    )
    return {k.strip(): v.strip() for k, sep, v in pairs if sep and k.strip()}


@dataclass(frozen=True)
class Query:
    """What a search asks for, and how many references to return."""

    words: frozenset[str]
    limit: int

    @classmethod
    def parse(cls, text: object, limit: object = 5) -> Query:
        """A free-text query and a positive ``limit``."""
        if not isinstance(text, str):
            raise TypeError(f"query must be a str (got {type(text).__name__})")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError(f"limit must be a positive int (got {limit!r})")
        return cls(words(text), limit)


# -- reading a source -------------------------------------------------------

# Strings and comments; on Python 3.12+ also the text of an f-string.
_QUOTED = frozenset(
    {
        tokenize.STRING,
        tokenize.COMMENT,
        getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING),
    }
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
    return (
        func.attr
        if isinstance(func, ast.Attribute)
        else getattr(func, "id", "")
    )


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
            check = Check.COLORMAP if kw.arg == "cmap" else Check.COLOR
            if value is not None and (
                kw.arg == "cmap" or kw.arg in COLOR_KEYWORDS
            ):
                found.append(Literal(check, value, _offset(kw, lines, starts)))
        first = call.args[0] if call.args else None
        if _called(call) == "get_cmap" and (value := _string(first)):
            found.append(
                Literal(Check.COLORMAP, value, _offset(call, lines, starts))
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
