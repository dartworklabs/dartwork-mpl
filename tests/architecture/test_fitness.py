"""Architecture fitness rules over all product code, as one-way ratchets (ADR 0005).

``boundaries.py`` judges slice-to-slice imports. These rules judge
the shape of the whole package: module and function size, slice size, naming,
import cycles and the purity of decision code. The T rules (``escapes.py``)
count the ways code slips past the type checker; the C rules
(``composition.py``) keep slices apart and ``compose/`` free of decisions. They read source with ``ast``
only; nothing is imported.

The contract, shared by every rule: ``fitness_baseline.json`` records today's
violations. A measurement worse than its baseline entry, or a violator the
baseline does not list, fails. A baseline entry that is stale (the value
improved or the violator is gone) also fails, so the baseline can only shrink.

Line-count rules (``ADVISORY``: module, slice, function and entry-point
function size) only warn. A hard line cap invites contrived splits made to
satisfy the number, so size is a signal for the reader, not a gate.

After improving something, lower the baseline with::

    uv run python tests/architecture/test_fitness.py --update

``--update`` refuses (exit 1) if any number would rise or any violator would be
added (advisory rules never block it). ``--allow-increase`` overrides that and is for the owner only: it records
a regression as accepted. A missing baseline file is created without the check.

Product code excludes colocated tests, ``conftest.py`` and generated modules.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import warnings
from collections.abc import Callable, Mapping
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG_DIR = ROOT / "src" / "dartwork_mpl"
BASELINE = Path(__file__).with_name("fitness_baseline.json")
_SPEC = importlib.util.spec_from_file_location(
    "check_boundaries", Path(__file__).with_name("boundaries.py")
)
assert _SPEC is not None and _SPEC.loader is not None
cb = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = cb  # dataclasses look their module up
_SPEC.loader.exec_module(cb)
_ESC = importlib.util.spec_from_file_location(
    "escapes", Path(__file__).with_name("escapes.py")
)
assert _ESC is not None and _ESC.loader is not None
escapes = importlib.util.module_from_spec(_ESC)
_ESC.loader.exec_module(escapes)
_COMP = importlib.util.spec_from_file_location(
    "composition", Path(__file__).with_name("composition.py")
)
assert _COMP is not None and _COMP.loader is not None
composition = importlib.util.module_from_spec(_COMP)
_COMP.loader.exec_module(composition)

P = "dartwork_mpl"
MODULE_CAP = 500  # lines; the well-factored modules already fit
SLICE_CAP = 4000  # lines per top-level slice
SUBPACKAGE_CAP = 2000  # lines per sub-package one level down
FUNCTION_CAP = 80  # lines per function or method
ENTRY_FUNCTION_CAP = 30  # entry points only wire
GENERATED: frozenset[str] = frozenset()
DUMPING = frozenset(
    ["utils", "util", "common", "helpers", "misc", "shared", "base"]
)
IMPURE = frozenset(
    [
        "matplotlib",
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "shutil",
        "tempfile",
        "urllib",
        "http",
        "requests",
        "httpx",
        "sqlite3",
    ]
)

# Kinds: "ceil" maps (bigger is worse), "floor" maps (smaller is worse),
# "set" lists (a member is a violator).
KIND = {
    "R1_module_lines": "ceil",
    "R2_slice_lines": "ceil",
    "R3_underscore_toplevel": "set",
    "R3_underscore_modules": "ceil",
    "R4_cycles": "set",
    "R4_lazy_cycle_edges": "ceil",
    "R5_dumping_ground": "set",
    "R6_impure_decisions": "set",
    "R6_matplotlib_free": "floor",
    "R7_function_lines": "ceil",
    "R8_missing_all": "set",
    "R8_entry_function_lines": "ceil",
}
WHY = {
    "R1_module_lines": f"a module over {MODULE_CAP} lines holds several ideas; split by capability",
    "R2_slice_lines": f"a slice over {SLICE_CAP} lines or sub-package over {SUBPACKAGE_CAP} is a mega slice; split it",
    "R3_underscore_toplevel": "a top-level name starting with _ hides a capability; give it a plain name",
    "R3_underscore_modules": "underscore modules inside a slice are unnamed parts; rename or fold them",
    "R4_cycles": "a package import cycle makes the packages one unit; invert or extract",
    "R4_lazy_cycle_edges": "a function-level import hiding a cycle is still a cycle; remove it",
    "R5_dumping_ground": "a utils/common/helpers module has no capability; move code to its owner",
    "R6_impure_decisions": "decision code must stay pure: no matplotlib, no I/O",
    "R6_matplotlib_free": "the matplotlib-free modules are the functional core; they may only grow",
    "R7_function_lines": f"a function over {FUNCTION_CAP} lines needs extracting",
    "R8_missing_all": "a top-level slice without a literal __all__ has no declared surface",
    "R8_entry_function_lines": f"an entry point function over {ENTRY_FUNCTION_CAP} lines does work instead of wiring",
}
KIND.update(dict.fromkeys(escapes.MEASURES, "ceil"))
WHY.update(escapes.WHY)
KIND.update(composition.KIND)
WHY.update(composition.WHY)
RULES = tuple(KIND)
# Size rules warn instead of failing: a hard line cap breeds contrived code.
ADVISORY = frozenset(
    {
        "R1_module_lines",
        "R2_slice_lines",
        "R7_function_lines",
        "R8_entry_function_lines",
    }
)


class FitnessAdvisory(UserWarning):
    """A size signal worth a look; never a failure."""


Tree = tuple[Mapping[str, str], set[str]]  # module -> source, package names


@cache
def load_tree(root: Path = PKG_DIR) -> Tree:
    """Product sources keyed by dotted module name, and the package names."""
    code, packages = cb.read_sources(root)
    return {m: s for m, s in code.items() if m not in GENERATED}, packages


def path_of(module: str, packages: set[str]) -> str:
    """Repo-relative path of a module, for messages and baseline keys."""
    rel = module.replace(".", "/")
    return f"src/{rel}/__init__.py" if module in packages else f"src/{rel}.py"


def is_underscored(name: str) -> bool:
    return name.startswith("_") and not (
        name.startswith("__") and name.endswith("__")
    )


def r1_module_lines(tree: Tree) -> dict[str, int]:
    code, packages = tree
    lines = {path_of(m, packages): s.count("\n") + 1 for m, s in code.items()}
    return {p: n for p, n in sorted(lines.items()) if n > MODULE_CAP}


def r2_slice_lines(tree: Tree) -> dict[str, int]:
    code, _ = tree
    totals: dict[str, int] = {}
    subs: dict[str, int] = {}
    for module, source in code.items():
        parts = module.split(".")
        if len(parts) < 2:
            continue
        n = source.count("\n") + 1
        totals[parts[1]] = totals.get(parts[1], 0) + n
        if len(parts) > 3 or (len(parts) == 3 and module in tree[1]):
            key = "/".join(parts[1:3])
            subs[key] = subs.get(key, 0) + n
    out = {k: v for k, v in totals.items() if v > SLICE_CAP}
    out.update({k: v for k, v in subs.items() if v > SUBPACKAGE_CAP})
    return dict(sorted(out.items()))


def r3_underscore_toplevel(tree: Tree) -> list[str]:
    code, _ = tree
    return sorted(
        {
            m.split(".")[1]
            for m in code
            if len(m.split(".")) > 1 and is_underscored(m.split(".")[1])
        }
    )


def r3_underscore_modules(tree: Tree) -> dict[str, int]:
    """Underscore-prefixed modules and packages below each top-level slice."""
    code, _ = tree
    seen: dict[str, set[str]] = {}
    for module in code:
        parts = module.split(".")
        for i in range(2, len(parts) + 1):
            if is_underscored(parts[i - 1]):
                seen.setdefault(parts[1], set()).add(".".join(parts[:i]))
    return {k: len(v) for k, v in sorted(seen.items())}


def edges(tree: Tree) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Module-level and lazy (in function or TYPE_CHECKING) import edges."""
    code, packages = tree
    hard: set[tuple[str, str]] = set()
    lazy: set[tuple[str, str]] = set()

    def resolve(module: str, base: str, name: str | None) -> str | None:
        for cand in (f"{base}.{name}" if name else None, base):
            if cand and cand in code:
                return cand
        return None

    def visit(module: str, node: ast.AST, is_lazy: bool) -> None:
        for child in ast.iter_child_nodes(node):
            deferred = is_lazy or isinstance(
                child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
            )
            if isinstance(child, ast.If) and "TYPE_CHECKING" in ast.unparse(
                child.test
            ):
                deferred = True
            pairs: list[tuple[str, str | None]] = []
            if isinstance(child, ast.Import):
                pairs = [(a.name, None) for a in child.names]
            elif isinstance(child, ast.ImportFrom):
                one = ast.Module(body=[child], type_ignores=[])
                pairs = cb.imports(module, one, packages)
            for base, name in pairs:
                target = resolve(module, base, name)
                if target and target != module:
                    (lazy if deferred else hard).add((module, target))
            visit(module, child, deferred)

    for module, source in code.items():
        visit(module, ast.parse(source), False)
    return hard, lazy


def _node(module: str, packages: set[str], depth: int | None) -> str:
    """Collapse a module to its top ``depth`` components, or its own package."""
    if depth is None:
        return module if module in packages else module.rpartition(".")[0]
    return ".".join(module.split(".")[: depth + 1])


def _graph(
    es: set[tuple[str, str]], packages: set[str], depth: int | None
) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for a, b in es:
        na, nb = _node(a, packages, depth), _node(b, packages, depth)
        # a package initializer a child imports is not a dependency (ADR 0005)
        if na != nb and not (b in packages and a.startswith(b + ".")):
            graph.setdefault(na, set()).add(nb)
    return graph


def r4_cycles(tree: Tree) -> list[str]:
    """Package-level SCCs of module-level imports, at depth 1, 2 and innermost."""
    hard, _ = edges(tree)
    out = []
    for label, depth in (("top", 1), ("depth2", 2), ("pkg", None)):
        for comp in cb._cycles(_graph(hard, tree[1], depth)):
            out.append(f"{label}: {', '.join(comp)}")
    return sorted(out)


def r4_lazy_cycle_edges(tree: Tree) -> dict[str, int]:
    """Top-level edges that lie on a cycle only because of lazy imports."""
    hard, lazy = edges(tree)
    full = _graph(hard | lazy, tree[1], 1)
    strict = _graph(hard, tree[1], 1)

    def comp(graph: Mapping[str, set[str]]) -> dict[str, int]:
        return {n: i for i, c in enumerate(cb._cycles(graph)) for n in c}

    cf, ch = comp(full), comp(strict)
    count = sum(
        1
        for a, bs in full.items()
        for b in bs
        if a in cf
        and cf.get(a) == cf.get(b)
        and not (a in ch and ch.get(a) == ch.get(b))
    )
    return {"top_level_edges": count}


def r5_dumping_ground(tree: Tree) -> list[str]:
    return sorted(m for m in tree[0] if m.rpartition(".")[2] in DUMPING)


def purity_offences(source: str) -> list[str]:
    """Impure imports and ``open()`` calls in one module's source."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names} & IMPURE
        elif isinstance(node, ast.ImportFrom) and not node.level:
            found |= {(node.module or "").split(".")[0]} & IMPURE
        elif (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == "open"
        ):
            found.add("open()")
    return sorted(found)


def r6_impure_decisions(
    tree: Tree, decisions: Mapping[str, str] | None = None
) -> list[str]:
    code, packages = tree
    decisions = cb.DECISIONS if decisions is None else decisions
    return sorted(
        f"{path_of(m, packages)}: {', '.join(purity_offences(code[m]))}"
        for m in decisions
        if m in code and purity_offences(code[m])
    )


def r6_matplotlib_free(tree: Tree) -> dict[str, int]:
    free = sum(
        1 for s in tree[0].values() if "matplotlib" not in purity_offences(s)
    )
    return {"modules": free}


def functions(source: str):
    """Yield (qualname, lines) for outermost functions and methods."""

    def walk(node: ast.AST, prefix: str):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                yield (
                    f"{prefix}{child.name}",
                    child.end_lineno - child.lineno + 1,
                )
            elif isinstance(child, ast.ClassDef):
                yield from walk(child, f"{prefix}{child.name}.")
            else:
                yield from walk(child, prefix)

    yield from walk(ast.parse(source), "")


def r7_function_lines(tree: Tree) -> dict[str, int]:
    code, packages = tree
    return {
        f"{path_of(m, packages)}::{q}": n
        for m, s in sorted(code.items())
        for q, n in functions(s)
        if n > FUNCTION_CAP
    }


def r8_missing_all(tree: Tree) -> list[str]:
    code, packages = tree
    tops = {m for m in packages if len(m.split(".")) == 2}
    return sorted(m for m in tops if cb.exports(ast.parse(code[m])) is None)


def r8_entry_function_lines(
    tree: Tree, entries: frozenset[str] | None = None
) -> dict[str, int]:
    code, packages = tree
    entries = cb.ENTRY_POINTS if entries is None else entries
    return {
        f"{path_of(m, packages)}::{q}": n
        for m in sorted(entries)
        if m in code
        for q, n in functions(code[m])
        if n > ENTRY_FUNCTION_CAP
    }


MEASURES: Mapping[str, Callable[[Tree], object]] = {
    "R1_module_lines": r1_module_lines,
    "R2_slice_lines": r2_slice_lines,
    "R3_underscore_toplevel": r3_underscore_toplevel,
    "R3_underscore_modules": r3_underscore_modules,
    "R4_cycles": r4_cycles,
    "R4_lazy_cycle_edges": r4_lazy_cycle_edges,
    "R5_dumping_ground": r5_dumping_ground,
    "R6_impure_decisions": r6_impure_decisions,
    "R6_matplotlib_free": r6_matplotlib_free,
    "R7_function_lines": r7_function_lines,
    "R8_missing_all": r8_missing_all,
    "R8_entry_function_lines": r8_entry_function_lines,
}


def _escape(fn: Callable[[Mapping[str, str]], dict[str, int]]):
    def measure(tree: Tree) -> dict[str, int]:
        code, packages = tree
        return fn({path_of(m, packages): s for m, s in code.items()})

    return measure


MEASURES = {**MEASURES, **{k: _escape(f) for k, f in escapes.MEASURES.items()}}


def _composition(fn: Callable[..., object]):
    def measure(tree: Tree) -> object:
        hard, lazy = edges(tree)
        return fn(tree[0], hard | lazy, cb.SLICES)

    return measure


MEASURES = {
    **MEASURES,
    **{k: _composition(f) for k, f in composition.MEASURES.items()},
}


def compare(
    rule: str, measured: object, baseline: object
) -> tuple[list[str], list[str]]:
    """(regressions, stale entries) of one rule against its baseline."""
    kind = KIND[rule]
    worse: list[str] = []
    stale: list[str] = []
    if kind == "set":
        new, old = set(measured), set(baseline or [])  # type: ignore[arg-type]
        worse = [f"new violator: {x}" for x in sorted(new - old)]
        stale = [f"gone, remove from baseline: {x}" for x in sorted(old - new)]
        return worse, stale
    now, base = dict(measured), dict(baseline or {})  # type: ignore[arg-type]
    for key in sorted(set(now) | set(base)):
        a, b = now.get(key), base.get(key)
        if kind == "floor":
            a, b = (a if a is not None else 0), (b if b is not None else 0)
            if a < b:
                worse.append(f"{key}: {a}, baseline {b}")
            elif a > b:
                stale.append(f"{key}: {a}, baseline {b} (raise the floor)")
        elif b is None:
            worse.append(f"{key}: {a}, not in baseline (new violator)")
        elif a is None:
            stale.append(f"{key}: fixed, baseline {b} (remove the entry)")
        elif a > b:
            worse.append(f"{key}: {a}, baseline {b}")
        elif a < b:
            stale.append(f"{key}: {a}, baseline {b} (lower the entry)")
    return worse, stale


def problems(
    rule: str, tree: Tree, baseline: Mapping[str, object]
) -> list[str]:
    worse, stale = compare(rule, MEASURES[rule](tree), baseline.get(rule))
    why = WHY[rule]
    head = [f"{rule}: {why}"] if worse or stale else []
    update = (
        "lower it: uv run python tests/architecture/test_fitness.py --update"
    )
    return (
        head + [f"  {w}" for w in worse] + [f"  {s} -- {update}" for s in stale]
    )


@pytest.mark.parametrize("rule", KIND)
def test_rule_matches_baseline(rule):
    """One test case per rule (R1 ... R8); the id names the rule that failed."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    found = problems(rule, load_tree(), baseline)
    if rule in ADVISORY:
        if found:
            warnings.warn("\n".join(found), FitnessAdvisory, stacklevel=1)
        return
    assert not found, "\n".join(found)


def test_baseline_has_exactly_the_rules():
    assert set(json.loads(BASELINE.read_text(encoding="utf-8"))) == set(KIND)


if __name__ == "__main__":
    tree = load_tree()
    old = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    if "--update" not in sys.argv:
        found = {r: problems(r, tree, old) for r in KIND}
        for r, lines in found.items():
            tag = "warning" if r in ADVISORY else "FAIL"
            print("\n".join(f"[{tag}] {line}" for line in lines), end="")
            print("" if not lines else "\n", end="")
        failed = any(lines for r, lines in found.items() if r not in ADVISORY)
        print("fitness: " + ("FAILED" if failed else "ok"))
        sys.exit(1 if failed else 0)
    new = {r: fn(tree) for r, fn in MEASURES.items()}
    worse = [
        f"{r}: {w}"
        for r in KIND
        if r not in ADVISORY
        for w in compare(r, new[r], old.get(r))[0]
    ]
    if old and worse and "--allow-increase" not in sys.argv:
        print("refusing to raise the baseline; fix the code instead.")
        print(
            "Only the owner may pass --allow-increase to accept a regression."
        )
        sys.exit("\n".join(worse))
    BASELINE.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n")
    print(f"wrote {BASELINE.name}")
