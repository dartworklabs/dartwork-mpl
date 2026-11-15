"""Rules for a slice's domain files, by file name. Hard failures, no baseline.

A core slice keeps its domain in three files (see docs/handbook/architecture.md):

``model.py``   the slice's types; the one place a primitive gets wrapped
``decide.py``  pure decisions for the ordinary figure: facts in, plan out
``edges.py``   named special cases, appended to ``EDGES``

D1  ``decide.py`` and ``edges.py`` speak in domain types. A parameter or return
    annotated ``str``, ``int``, ``float``, ``dict``, ``Any`` ... is an error, as
    is a missing annotation. ``bool`` and ``None`` are allowed.
D2  The three files are pure: no matplotlib, no I/O.
D3  ``edges.py`` defines ``EDGES`` as a tuple of ``EdgeCase(...)`` with a
    literal, unique ``name``; a literal ``why`` of at least five words that is
    not the name (what goes wrong without the edge); and a literal ``example``
    of the form ``test_<file>.py::[Class::]test_<function>``.
D4  The example is a test in the slice's own ``tests/``: the file and the
    function exist, and the function names the edge and asserts. The root
    ``tests/fixtures.py`` runs the other half: while that test runs, the edge must
    fire (``dartwork_mpl.edgecase.tally``).

Source is read with ``ast`` only.
"""

from __future__ import annotations

import ast
import re
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
EXAMPLE = re.compile(r"test_\w+\.py(::[A-Z]\w*)?::test_\w+")
MIN_WHY_WORDS = 5
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


def _literal(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def edge_cases(source: str) -> tuple[list[dict[str, str]], list[str]]:
    """D3: each ``EdgeCase`` in ``EDGES`` as its literal fields, and what is
    malformed."""
    cases: list[dict[str, str]] = []
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
        return cases, ["EDGES must be a module-level tuple literal"]
    for item in value.elts:
        if not (
            isinstance(item, ast.Call)
            and getattr(item.func, "id", "") == "EdgeCase"
        ):
            errors.append("every EDGES item must be an EdgeCase(...) call")
            continue
        kw = {k.arg: _literal(k.value) for k in item.keywords}
        name, why, example = kw.get("name"), kw.get("why"), kw.get("example")
        for field, v in (("name", name), ("why", why), ("example", example)):
            if not (v and v.strip()):
                errors.append(f"EdgeCase needs a literal {field}=")
        if not name:
            continue
        if why and (why.strip() == name or len(why.split()) < MIN_WHY_WORDS):
            errors.append(
                f"edge {name!r}: why= must say what goes wrong without it"
            )
        if example and not EXAMPLE.fullmatch(example):
            errors.append(
                f"edge {name!r}: example= must be "
                "'test_<file>.py::[Class::]test_<function>'"
            )
        cases.append({"name": name, "example": example or ""})
    names = [c["name"] for c in cases]
    errors += [
        f"duplicate edge name {n!r}" for n in set(names) if names.count(n) > 1
    ]
    return cases, errors


def _example_function(tests: Path, example: str) -> ast.FunctionDef | str:
    """The test function ``example`` names, or why it cannot be found."""
    file, *path = example.split("::")
    target = tests / file
    if not target.is_file():
        return f"{file} is not in the slice's tests/"
    body: list[ast.stmt] = ast.parse(target.read_text(encoding="utf-8")).body
    for part in path:
        found = next(
            (
                n
                for n in body
                if isinstance(n, ast.ClassDef | ast.FunctionDef)
                and n.name == part
            ),
            None,
        )
        if found is None:
            return f"{file} has no {part}"
        if isinstance(found, ast.FunctionDef):
            return found
        body = found.body
    return f"{example} is not a function"


def unproven_edges(edges_file: Path) -> list[str]:
    """D4: edges whose example is not a test that names them and asserts."""
    cases, _ = edge_cases(edges_file.read_text(encoding="utf-8"))
    tests = edges_file.parent / "tests"
    found: list[str] = []
    for case in cases:
        name, example = case["name"], case["example"]
        if not EXAMPLE.fullmatch(example):
            continue  # D3 reports it
        func = _example_function(tests, example)
        if isinstance(func, str):
            found.append(f"edge {name!r}: {func}")
            continue
        nodes = list(ast.walk(func))
        if not any(
            _literal(n) == name for n in nodes if isinstance(n, ast.expr)
        ):
            found.append(f"edge {name!r}: {example} does not name it")
        if not any(isinstance(n, ast.Assert) for n in nodes):
            found.append(f"edge {name!r}: {example} asserts nothing")
    return found


def violations(root: Path = PKG_DIR) -> list[str]:
    found = []
    for path in domain_files(root, DOMAIN_FILES):
        rel = path.relative_to(root)
        source = path.read_text(encoding="utf-8")
        found += [f"{rel}: D2 impure {x}" for x in purity_offences(source)]
        if path.name in TYPED_FILES:
            found += [f"{rel}: D1 {x}" for x in primitive_offences(source)]
        if path.name == "edges.py":
            found += [f"{rel}: D3 {x}" for x in edge_cases(source)[1]]
            found += [f"{rel}: D4 {x}" for x in unproven_edges(path)]
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
    EdgeCase(
        name="empty-panel",
        why="an empty panel took margins for text it does not draw",
        example="test_edges.py::test_empty_panel",
        applies=empty,
        adjust=keep,
    ),
)
"""

GOOD_TEST = """
def test_empty_panel():
    assert settle(EMPTY, PLAN, EDGES).fired == ("empty-panel",)
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
            "tests__test_edges.py": GOOD_TEST,
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


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ('name="empty-panel",', "", "literal name="),
        ('example="test_edges.py::test_empty_panel",', "", "literal example="),
        ('"an empty panel took margins for text it does not draw"', '"empty"',
         "what goes wrong"),
        ('"an empty panel took margins for text it does not draw"',
         '"empty-panel"', "what goes wrong"),
        ("test_edges.py::test_empty_panel", "the empty test", "must be"),
        ("test_edges.py::test_empty_panel", "test_edges.py::test_other",
         "has no test_other"),
        ("test_edges.py::test_empty_panel", "test_other.py::test_empty_panel",
         "is not in the slice's tests/"),
    ],
)  # fmt: skip
def test_an_edge_without_a_reason_or_an_example_is_an_error(
    tmp_path, old, new, expected
):
    edges = GOOD_EDGES.replace(old, new)
    root = _slice(
        tmp_path, **{"edges.py": edges, "tests__test_edges.py": GOOD_TEST}
    )
    found = violations(root)
    assert any(expected in v for v in found), found


@pytest.mark.parametrize(
    ("test", "expected"),
    [
        ("def test_empty_panel():\n    assert True\n", "does not name it"),
        ("def test_empty_panel():\n    'empty-panel'\n", "asserts nothing"),
    ],
)
def test_an_example_that_does_not_name_or_assert_is_an_error(
    tmp_path, test, expected
):
    root = _slice(
        tmp_path, **{"edges.py": GOOD_EDGES, "tests__test_edges.py": test}
    )
    found = violations(root)
    assert any("D4" in v and expected in v for v in found), found


def test_settle_applies_edges_in_order_and_reports_them():
    double = EdgeCase(
        name="double",
        why="test",
        example="",
        applies=lambda facts, plan: facts,
        adjust=lambda facts, plan: plan * 2,
    )
    never = EdgeCase(
        name="never",
        why="test",
        example="",
        applies=lambda facts, plan: False,
        adjust=lambda facts, plan: plan + 100,
    )
    settled = settle(True, 3, (double, never, double))
    assert settled.plan == 12
    assert settled.fired == ("double", "double")


def test_the_tally_counts_fired_edges_only_when_switched_on(monkeypatch):
    import dartwork_mpl.edgecase as ec

    double = EdgeCase(
        "double", "doubles", "", lambda f, p: True, lambda f, p: p
    )
    monkeypatch.setattr(ec, "tally", None)
    settle(None, 1, (double,))
    monkeypatch.setattr(ec, "tally", ec.Counter())
    settle(None, 1, (double, double))
    assert ec.tally == {"double": 2}
