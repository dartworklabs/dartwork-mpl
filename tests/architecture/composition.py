"""Slices do not know each other; ``compose/`` joins them.

A slice imports the platform packages and nothing else of this package. Where
one capability needs another (a layout that settles ticks, labels and legends
before it measures; a preset that registers fonts first), a module in
``dartwork_mpl/compose/`` joins them, and only the package root imports
``compose``. So every cross-slice dependency sits in one folder, by name.

    src/dartwork_mpl/compose/<slice>.py    what <slice> needs from the others

C1  A slice importing another slice. None does: the baseline is empty, so
    any such import is a new violator (``boundaries.py`` fails it too).
C2  A compose module is named after the slice it serves: ``compose/layout.py``
    joins what ``layout`` needs. No other names, no sub-packages.
C3  A compose module only joins. It may import slice and platform surfaces
    (``from dartwork_mpl import layout, ticks``), ``__future__``, ``typing``
    and ``collections.abc``, and other libraries under ``TYPE_CHECKING`` for
    annotations. Nothing else, and never a slice's inner module.
C4  A compose module decides nothing: no ``if``, ``match``, loop, ``try``,
    comprehension, conditional expression, lambda or class. A decision belongs
    to the slice that owns the fact. The count is per file and must be zero.
C5  Only the package root imports ``compose``. A slice that reached for it
    would be depending on every slice it joins.

Each measure returns the offenders; ``test_fitness.py`` ratchets them.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping

P = "dartwork_mpl"
COMPOSE = f"{P}.compose"
FREE_IMPORTS = frozenset({"__future__", "typing", "collections"})
DECIDING = (
    ast.If,
    ast.IfExp,
    ast.Match,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Lambda,
    ast.ClassDef,
)

Code = Mapping[str, str]  # dotted module -> source
Edges = set[tuple[str, str]]  # (importer, imported), dotted modules


def _top(module: str) -> str:
    return ".".join(module.split(".")[:2])


def _in_compose(module: str) -> bool:
    return module == COMPOSE or module.startswith(COMPOSE + ".")


def slice_imports_slice(
    code: Code, edges: Edges, slices: frozenset[str]
) -> list[str]:
    del code
    found = {
        f"{_top(a)} -> {_top(b)}"
        for a, b in edges
        if _top(a) in slices and _top(b) in slices and _top(a) != _top(b)
    }
    return sorted(found)


def compose_names(
    code: Code, edges: Edges, slices: frozenset[str]
) -> list[str]:
    del edges
    served = {s.rpartition(".")[2] for s in slices}
    return sorted(
        m
        for m in code
        if _in_compose(m)
        and m != COMPOSE
        and (m.count(".") != 2 or m.rpartition(".")[2] not in served)
    )


def _type_checking(node: ast.AST) -> bool:
    return isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(
        node.test
    )


def _foreign_imports(tree: ast.Module) -> list[str]:
    """Runtime imports of anything but this package and ``FREE_IMPORTS``."""
    found: list[str] = []
    for node in tree.body:
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names = [node.module or ""]
        found += [n for n in names if n.split(".")[0] not in {P, *FREE_IMPORTS}]
    return found


def compose_reaches(
    code: Code, edges: Edges, slices: frozenset[str]
) -> list[str]:
    del slices
    found: set[str] = set()
    for a, b in edges:
        if _in_compose(a) and not _in_compose(b) and b.count(".") > 1:
            found.add(f"{a} imports the inner module {b}")
    for module, source in code.items():
        if _in_compose(module):
            found |= {
                f"{module} imports {name} at runtime"
                for name in _foreign_imports(ast.parse(source))
            }
    return sorted(found)


def compose_decisions(
    code: Code, edges: Edges, slices: frozenset[str]
) -> dict[str, int]:
    del edges, slices
    out: dict[str, int] = {}
    for module, source in sorted(code.items()):
        if not _in_compose(module):
            continue
        count = sum(
            isinstance(n, DECIDING) and not _type_checking(n)
            for n in ast.walk(ast.parse(source))
        )
        if count:
            out[module] = count
    return out


def compose_importers(
    code: Code, edges: Edges, slices: frozenset[str]
) -> list[str]:
    del code, slices
    return sorted(
        {
            a
            for a, b in edges
            if _in_compose(b) and not _in_compose(a) and a != P
        }
    )


Measure = Callable[[Code, Edges, frozenset[str]], object]
MEASURES: Mapping[str, Measure] = {
    "C1_slice_imports_slice": slice_imports_slice,
    "C2_compose_names": compose_names,
    "C3_compose_reaches": compose_reaches,
    "C4_compose_decisions": compose_decisions,
    "C5_compose_importers": compose_importers,
}
KIND = {
    "C1_slice_imports_slice": "set",
    "C2_compose_names": "set",
    "C3_compose_reaches": "set",
    "C4_compose_decisions": "ceil",
    "C5_compose_importers": "set",
}
WHY = {
    "C1_slice_imports_slice": "a slice imports only the platform; join slices in compose/<slice>.py",
    "C2_compose_names": "a compose module is compose/<slice>.py, named after the slice it serves",
    "C3_compose_reaches": "a compose module imports slice surfaces only, and other libraries only under TYPE_CHECKING",
    "C4_compose_decisions": "a compose module only joins; a branch, loop or class there is a decision that belongs to a slice",
    "C5_compose_importers": "only the package root imports compose",
}
