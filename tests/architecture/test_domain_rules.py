"""Rules for a slice's domain files, by file name. Hard failures, no baseline.

A core slice keeps its domain in three files (see docs/handbook/architecture.md):

``model.py``   the slice's types; the one place a primitive gets wrapped
``decide.py``  pure decisions for the ordinary figure: facts in, plan out
``edges.py``   named special cases, appended to ``EDGES``

D1  ``decide.py`` and ``edges.py`` speak in domain types. A parameter or return
    annotated ``str``, ``int``, ``float``, ``dict``, ``Any`` ... is an error, as
    is a missing annotation. ``bool`` and ``None`` are allowed.
D2  The three files are pure: no matplotlib, no I/O.
D3  ``edges.py`` defines ``EDGES`` as a tuple of ``EdgeCase(...)`` with literal,
    unique ``name`` and a literal ``why``.
D4  Every edge-case name appears in a test under the slice's ``tests/``.

Source is read with ``ast`` only.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dartwork_mpl.edgecase import EdgeCase, settle

PKG_DIR = Path(__file__).resolve().parents[2] / "src" / "dartwork_mpl"
DOMAIN_FILES = frozenset({"model.py", "decide.py", "edges.py"})
TYPED_FILES = frozenset({"decide.py", "edges.py"})
PRIMITIVES = frozenset(
    {"str", "int", "float", "bytes", "complex", "dict", "Any", "object"}
)
BARE_CONTAINERS = frozenset({"list", "tuple", "set", "frozenset"})
IMPURE = frozenset(
    {
        "matplotlib",
        "mpl_toolkits",
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "shutil",
        "tempfile",
        "io",
        "sys",
        "urllib",
        "httpx",
    }
)


def domain_files(root: Path, names: frozenset[str]) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*.py")
        if p.name in names and "tests" not in p.relative_to(root).parts
    )


def _primitive_in(annotation: ast.expr) -> str | None:
    """The first primitive an annotation names, or None."""
    if isinstance(annotation, ast.Constant) and isinstance(
        annotation.value, str
    ):
        annotation = ast.parse(annotation.value, mode="eval").body
    if isinstance(annotation, ast.Name) and annotation.id in BARE_CONTAINERS:
        return annotation.id
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id in PRIMITIVES:
            return node.id
        if isinstance(node, ast.Attribute) and node.attr in PRIMITIVES:
            return node.attr
    return None


def primitive_offences(source: str) -> list[str]:
    """D1: functions whose signature uses a primitive or lacks an annotation."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        args = node.args
        params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        params += [a for a in (args.vararg, args.kwarg) if a is not None]
        for arg in params:
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                found.append(f"{node.name}({arg.arg}): no annotation")
            elif bad := _primitive_in(arg.annotation):
                found.append(f"{node.name}({arg.arg}): primitive {bad}")
        if node.returns is None:
            found.append(f"{node.name} -> : no annotation")
        elif bad := _primitive_in(node.returns):
            found.append(f"{node.name} -> : primitive {bad}")
    return found


def purity_offences(source: str) -> list[str]:
    """D2: impure imports and ``open()`` calls."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names} & IMPURE
        elif isinstance(node, ast.ImportFrom) and not node.level:
            found |= {(node.module or "").split(".")[0]} & IMPURE
        elif isinstance(node, ast.Call) and (
            getattr(node.func, "id", "") == "open"
        ):
            found.add("open()")
    return sorted(found)


def edge_names(source: str) -> tuple[list[str], list[str]]:
    """D3: the literal edge names in ``EDGES`` and what is malformed."""
    names: list[str] = []
    errors: list[str] = []
    value = None
    for node in ast.parse(source).body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign)
            else []
        )
        if any(getattr(t, "id", "") == "EDGES" for t in targets):
            value = node.value
    if not isinstance(value, ast.Tuple):
        return names, ["EDGES must be a module-level tuple literal"]
    for item in value.elts:
        if not (
            isinstance(item, ast.Call)
            and getattr(item.func, "id", "") == "EdgeCase"
        ):
            errors.append("every EDGES item must be an EdgeCase(...) call")
            continue
        kw = {k.arg: k.value for k in item.keywords}
        for field in ("name", "why"):
            v = kw.get(field)
            if not (
                isinstance(v, ast.Constant)
                and isinstance(v.value, str)
                and v.value.strip()
            ):
                errors.append(f"EdgeCase needs a literal {field}=")
        name = kw.get("name")
        if isinstance(name, ast.Constant) and isinstance(name.value, str):
            names.append(name.value)
    errors += [
        f"duplicate edge name {n!r}" for n in set(names) if names.count(n) > 1
    ]
    return names, errors


def untested_edges(edges_file: Path) -> list[str]:
    """D4: edge names no test under the slice's ``tests/`` mentions."""
    names, _ = edge_names(edges_file.read_text(encoding="utf-8"))
    tests = edges_file.parent / "tests"
    text = "".join(
        p.read_text(encoding="utf-8") for p in sorted(tests.rglob("*.py"))
    )
    return [n for n in names if n not in text]


def violations(root: Path = PKG_DIR) -> list[str]:
    found = []
    for path in domain_files(root, DOMAIN_FILES):
        rel = path.relative_to(root)
        source = path.read_text(encoding="utf-8")
        found += [f"{rel}: D2 impure {x}" for x in purity_offences(source)]
        if path.name in TYPED_FILES:
            found += [f"{rel}: D1 {x}" for x in primitive_offences(source)]
        if path.name == "edges.py":
            found += [f"{rel}: D3 {x}" for x in edge_names(source)[1]]
            found += [
                f"{rel}: D4 edge {n!r} has no test naming it"
                for n in untested_edges(path)
            ]
    return found


def test_domain_files_follow_the_rules():
    found = violations()
    assert not found, "\n".join(found)


# -- the rules fail on injected violations -----------------------------------

GOOD_EDGES = """
from dartwork_mpl.edgecase import EdgeCase
from .model import Facts, Plan

def empty(facts: Facts, plan: Plan) -> bool:
    return facts.empty

def keep(facts: Facts, plan: Plan) -> Plan:
    return plan

EDGES: tuple[EdgeCase[Facts, Plan], ...] = (
    EdgeCase(name="empty-panel", why="nothing to fit", applies=empty, adjust=keep),
)
"""


def _slice(tmp_path: Path, **files: str) -> Path:
    slice_dir = tmp_path / "s"
    (slice_dir / "tests").mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        target = slice_dir / name.replace("__", "/")
        target.write_text(text, encoding="utf-8")
    return tmp_path


def test_a_clean_slice_passes(tmp_path):
    root = _slice(
        tmp_path,
        **{
            "edges.py": GOOD_EDGES,
            "decide.py": "def plan(facts: Facts) -> Plan: ...",
            "tests__test_edges.py": "'empty-panel'",
        },
    )
    assert violations(root) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def f(width: float) -> Plan: ...", "primitive float"),
        ("def f(x: Facts) -> dict[str, Any]: ...", "primitive dict"),
        ("def f(x: Facts) -> list: ...", "primitive list"),
        ("def f(x) -> Plan: ...", "no annotation"),
        ("def f(x: Facts): ...", "no annotation"),
        ("def f(x: 'str') -> Plan: ...", "primitive str"),
    ],
)
def test_primitive_signatures_are_errors(tmp_path, source, expected):
    found = violations(_slice(tmp_path, **{"decide.py": source}))
    assert any("D1" in v and expected in v for v in found), found


def test_domain_types_and_bool_are_allowed():
    ok = "def f(a: Facts, b: tuple[Box, ...], c: Length | None) -> bool: ..."
    assert primitive_offences(ok) == []


def test_impure_domain_file_is_an_error(tmp_path):
    root = _slice(tmp_path, **{"model.py": "import matplotlib.pyplot as plt"})
    assert violations(root) == ["s/model.py: D2 impure matplotlib"]


def test_malformed_or_untested_edges_are_errors(tmp_path):
    unnamed = GOOD_EDGES.replace('name="empty-panel", ', "")
    assert any(
        "D3" in v for v in violations(_slice(tmp_path, **{"edges.py": unnamed}))
    )
    untested = violations(_slice(tmp_path, **{"edges.py": GOOD_EDGES}))
    assert untested == [
        "s/edges.py: D4 edge 'empty-panel' has no test naming it"
    ]


def test_settle_applies_edges_in_order_and_reports_them():
    double = EdgeCase(
        name="double",
        why="test",
        applies=lambda facts, plan: facts,
        adjust=lambda facts, plan: plan * 2,
    )
    never = EdgeCase(
        name="never",
        why="test",
        applies=lambda facts, plan: False,
        adjust=lambda facts, plan: plan + 100,
    )
    settled = settle(True, 3, (double, never, double))
    assert settled.plan == 12
    assert settled.fired == ("double", "double")
