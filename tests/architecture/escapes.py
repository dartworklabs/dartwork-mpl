"""Ways product code slips past the type checker, counted per file.

Each measure returns ``{repo-relative path: count}`` for files with at least
one offence. ``test_fitness.py`` ratchets them: a count may only fall and a
new file may not appear. They read source with ``ast`` and ``tokenize`` only.

T1  ``cast(...)``. A cast tells the checker a type it cannot verify.
T2  ``# type: ignore`` and ``# pyright: ignore``, except a pyright ignore that
    names only matplotlib's untyped members (``STUB_GAPS``).
T3  ``isinstance`` in ``decide.py`` and ``edges.py``. A domain function that
    asks what it was given has a parameter type that is too wide.
T4  A ``_dm_`` attribute on a matplotlib object. State hidden there has no
    type and couples slices where no import shows it.
T5  An enum member in any comparison (``x is Kind.DATES``, ``x in (Kind.A,
    Kind.B)``), in a condition or a returned predicate alike. A new member
    falls through silently; ``match`` with ``assert_never`` does not.
T6  A string literal compared (``side == "above"``, ``loc in ("left",
    "right")``) or a ``Literal["..."]`` annotation, anywhere but ``model.py``.
    A string is parsed once in ``model.py`` into a type, then never compared.
T7  A ``match`` whose ``case _`` does anything but ``assert_never``. A
    catch-all hides the variant nobody handled.
T9  A function returning ``TypeGuard`` / ``TypeIs``. It narrows on the
    author's word, like a cast; a parser returns the type or raises.
T10 ``getattr`` / ``hasattr`` / ``setattr`` / ``delattr``. An attribute
    reached by name is one the checker cannot follow.
T11 ``Any`` in an annotation, ``vars()`` and ``__dict__``. Each switches the
    checker off for the value it touches.
T12 An enum in a costume: a class holding two or more constants of its own
    type, or two or more module-level instances of one class told apart by a
    string argument. Nothing can check that every one is handled.
T8  ``Enum`` classes. A flag that picks behaviour in several places wants a
    variant type carrying its own data; each enum left is a place to look.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Callable, Iterator, Mapping

Sources = Mapping[str, str]  # repo-relative path -> source

STUB_GAPS = frozenset(
    {
        "reportUnknownMemberType",
        "reportUnknownVariableType",
        "reportUnknownArgumentType",
    }
)
DOMAIN = ("decide.py", "edges.py")
PARSERS = ("model.py",)  # the one place a string becomes a type
IGNORE = re.compile(r"#\s*(type|pyright):\s*ignore(?:\[([^\]]*)\])?")
ENUM_BASES = frozenset({"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"})
SMUGGLED = "_dm_"
REFLECT = frozenset({"getattr", "setattr", "hasattr", "delattr"})


def _count(sources: Sources, one: Callable[[str, str], int]) -> dict[str, int]:
    found = {path: one(path, text) for path, text in sorted(sources.items())}
    return {path: n for path, n in found.items() if n}


def _name(node: ast.AST) -> str:
    return (
        node.id
        if isinstance(node, ast.Name)
        else node.attr
        if isinstance(node, ast.Attribute)
        else ""
    )


def _comments(text: str) -> Iterator[str]:
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            yield token.string


def casts(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        return sum(
            isinstance(n, ast.Call) and _name(n.func) == "cast"
            for n in ast.walk(ast.parse(text))
        )

    return _count(sources, one)


def ignores(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        count = 0
        for comment in _comments(text):
            found = IGNORE.search(comment)
            if found is None:
                continue
            codes = {
                c.strip() for c in (found[2] or "").split(",") if c.strip()
            }
            if found[1] == "pyright" and codes and codes <= STUB_GAPS:
                continue
            count += 1
        return count

    return _count(sources, one)


def domain_isinstance(sources: Sources) -> dict[str, int]:
    def one(path: str, text: str) -> int:
        if not path.endswith(DOMAIN):
            return 0
        return sum(
            isinstance(n, ast.Call) and _name(n.func) == "isinstance"
            for n in ast.walk(ast.parse(text))
        )

    return _count(sources, one)


def smuggled_attributes(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        count = 0
        for n in ast.walk(ast.parse(text)):
            if (
                isinstance(n, ast.Attribute) and n.attr.startswith(SMUGGLED)
            ) or (
                isinstance(n, ast.Constant)
                and isinstance(n.value, str)
                and n.value.startswith(SMUGGLED)
            ):
                count += 1
        return count

    return _count(sources, one)


def _is_member(node: ast.expr) -> bool:
    """``Kind.DATES``: an upper-case attribute of a capitalised name."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr.isupper()
        and isinstance(node.value, ast.Name)
        and node.value.id[:1].isupper()
    )


def enum_branches(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        return sum(
            isinstance(c, ast.Compare)
            and any(
                _is_member(e)
                for side in (c.left, *c.comparators)
                for e in ast.walk(side)
                if isinstance(e, ast.expr)
            )
            for c in ast.walk(ast.parse(text))
        )

    return _count(sources, one)


def _is_text(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    return isinstance(node, ast.Tuple | ast.Set | ast.List) and any(
        _is_text(e) for e in node.elts
    )


def string_branches(sources: Sources) -> dict[str, int]:
    def one(path: str, text: str) -> int:
        if path.endswith(PARSERS):
            return 0
        count = 0
        for n in ast.walk(ast.parse(text)):
            if (
                isinstance(n, ast.Compare)
                and any(_is_text(side) for side in (n.left, *n.comparators))
                and _name(n.left) != "__name__"
            ):
                count += 1
            elif isinstance(n, ast.Subscript) and _name(n.value) == "Literal":
                count += any(
                    _is_text(e)
                    for e in ast.walk(n.slice)
                    if isinstance(e, ast.expr)
                )
        return count

    return _count(sources, one)


def _asserts_never(case: ast.match_case) -> bool:
    return any(
        isinstance(n, ast.Call) and _name(n.func) == "assert_never"
        for stmt in case.body
        for n in ast.walk(stmt)
    )


def swallowing_matches(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        count = 0
        for n in ast.walk(ast.parse(text)):
            if not isinstance(n, ast.Match):
                continue
            for case in n.cases:
                catch_all = (
                    isinstance(case.pattern, ast.MatchAs)
                    and case.pattern.pattern is None
                    and case.guard is None
                )
                count += catch_all and not _asserts_never(case)
        return count

    return _count(sources, one)


def enums(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        return sum(
            isinstance(n, ast.ClassDef)
            and any(_name(b) in ENUM_BASES for b in n.bases)
            for n in ast.walk(ast.parse(text))
        )

    return _count(sources, one)


def guards(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        return sum(
            isinstance(n, ast.Name | ast.Attribute)
            and _name(n) in {"TypeGuard", "TypeIs"}
            and isinstance(getattr(n, "ctx", None), ast.Load)
            for f in ast.walk(ast.parse(text))
            if isinstance(f, ast.FunctionDef) and f.returns is not None
            for n in ast.walk(f.returns)
        )

    return _count(sources, one)


def reflection(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        return sum(
            isinstance(n, ast.Call) and _name(n.func) in REFLECT
            for n in ast.walk(ast.parse(text))
        )

    return _count(sources, one)


def untyped(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        count = 0
        for n in ast.walk(ast.parse(text)):
            if isinstance(n, ast.Name) and n.id == "Any":
                count += isinstance(n.ctx, ast.Load)
            elif (isinstance(n, ast.Call) and _name(n.func) == "vars") or (
                isinstance(n, ast.Attribute) and n.attr == "__dict__"
            ):
                count += 1
        return count

    return _count(sources, one)


def _own_constants(cls: ast.ClassDef) -> int:
    """Class attributes typed ``ClassVar[<the class itself>]``."""
    return sum(
        isinstance(n, ast.AnnAssign)
        and isinstance(n.annotation, ast.Subscript)
        and _name(n.annotation.value) == "ClassVar"
        and cls.name in ast.unparse(n.annotation.slice)
        for n in cls.body
    )


def costumed_enums(sources: Sources) -> dict[str, int]:
    def one(_: str, text: str) -> int:
        tree = ast.parse(text)
        classes = {
            n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
        }
        by_class = sum(
            _own_constants(n) >= 2
            for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef)
        )
        # NAME = Cls("word") / Cls(value="word"): instances told apart by a string
        tagged: dict[str, int] = {}
        for n in tree.body:
            value = getattr(n, "value", None)
            if (
                isinstance(n, ast.Assign | ast.AnnAssign)
                and isinstance(value, ast.Call)
                and _name(value.func) in classes
                and any(
                    isinstance(a, ast.Constant) and isinstance(a.value, str)
                    for a in (*value.args, *(k.value for k in value.keywords))
                )
            ):
                tagged[_name(value.func)] = tagged.get(_name(value.func), 0) + 1
        return by_class + sum(n >= 2 for n in tagged.values())

    return _count(sources, one)


MEASURES: Mapping[str, Callable[[Sources], dict[str, int]]] = {
    "T1_casts": casts,
    "T2_ignores": ignores,
    "T3_domain_isinstance": domain_isinstance,
    "T4_smuggled_attributes": smuggled_attributes,
    "T5_enum_branches": enum_branches,
    "T6_string_branches": string_branches,
    "T7_swallowing_matches": swallowing_matches,
    "T8_enums": enums,
    "T9_guards": guards,
    "T10_reflection": reflection,
    "T11_untyped": untyped,
    "T12_costumed_enums": costumed_enums,
}
WHY = {
    "T1_casts": "a cast asserts a type nobody checked; parse into the type instead",
    "T2_ignores": "an ignore silences the checker; only matplotlib's untyped members may be ignored, by a pyright ignore naming reportUnknown*",
    "T3_domain_isinstance": "a decision asking what it was given has too wide a parameter; give each facts/plan pair its own function and registry",
    "T4_smuggled_attributes": "a _dm_ attribute on a matplotlib object is untyped state and a hidden dependency between slices; keep it in a typed registry behind the owning slice's surface",
    "T5_enum_branches": "an if on an enum member lets a new member fall through; use match with assert_never, or a variant type",
    "T6_string_branches": "code compares strings; parse the string once in model.py into a type",
    "T7_swallowing_matches": "a catch-all case hides the unhandled variant; end with case _: assert_never(x)",
    "T9_guards": "a TypeGuard is a cast with a function around it; parse into the type and return it",
    "T10_reflection": "getattr/hasattr/setattr reach an attribute the checker cannot see; name the type that has it",
    "T11_untyped": "Any, vars() and __dict__ switch the checker off for whatever they touch; give the value its type",
    "T12_costumed_enums": "one class whose instances differ by a string, or that holds constants of its own type, is an enum in a costume; make one class per variant",
    "T8_enums": "an enum is a status flag; a variant type carries its own data and is matched exhaustively. Adding one is the owner's decision",
}
