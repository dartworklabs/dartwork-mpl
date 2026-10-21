"""Check the package's slice boundaries from source, without importing it (ADR 0005).

Every production module under ``src/dartwork_mpl`` belongs to one unit: a
slice (a capability), a platform unit (mechanism with no business), or an
entry point module that only wires. Ownership is by the longest unit prefix,
so a sub-slice can be declared inside a slice later. A unit's surface is its
own module (the package ``__init__`` or the single file) and the names in its
literal ``__all__``; everything else is private.

Reported violations, one stable line each (no line numbers, so a debt entry
survives unrelated edits):

  missing __all__        a unit whose surface module declares no literal __all__
  private import         an import of another unit's module below its surface,
                         or of a name its __all__ does not list
  entry point import     a non-entry module importing an entry point (the package
                         root reaches every slice)
  undeclared dependency  a slice importing another slice's surface without an
                         ALLOWED entry naming the business reason
  platform reaches slice a platform unit reaching a slice by any import path,
                         through other platform units included
  cycle                  units that reach each other, lazy and TYPE_CHECKING
                         imports and package initializers included
  decision import        a module listed in DECISIONS importing another unit
  unowned module         a production module no unit or entry point owns
  unused allowance       an ALLOWED entry no import backs
  stale debt             a DEBT entry that no longer occurs (delete it)

Violations listed in DEBT are known and pass; the list only shrinks. Run:
``uv run python scripts/check_boundaries.py`` (exit 1 on any violation).
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "dartwork_mpl"

# Modules that only wire: they may import any unit's surface. The package
# root runs on every `import dartwork_mpl`, so no unit may import it.
ENTRY_POINTS = frozenset(
    {
        "dartwork_mpl",
        "dartwork_mpl._build_entry",
        "dartwork_mpl.cli",
        # `python -m dartwork_mpl.mcp.server` / `dartwork-mpl-ui`
        "dartwork_mpl.mcp.server",
        "dartwork_mpl.ui.__main__",
    }
)

# Units holding business-agnostic mechanism. They import no slice.
PLATFORM = frozenset({"dartwork_mpl._figure_geometry", "dartwork_mpl._rc"})

# Units holding one capability each.
SLICES = frozenset(
    {
        "dartwork_mpl._colors",
        "dartwork_mpl._luminance",
        "dartwork_mpl.agent",
        "dartwork_mpl.annotation",
        "dartwork_mpl.config",
        "dartwork_mpl.diagnostics",
        "dartwork_mpl.explore",
        "dartwork_mpl.font",
        "dartwork_mpl.formatting",
        "dartwork_mpl.helpers",
        "dartwork_mpl.icon",
        "dartwork_mpl.io",
        "dartwork_mpl.layout",
        "dartwork_mpl.lint",
        "dartwork_mpl.mcp",
        "dartwork_mpl.prompt",
        "dartwork_mpl.scale",
        "dartwork_mpl.style",
        "dartwork_mpl.templates",
        "dartwork_mpl.tokens",
        "dartwork_mpl.ui",
        "dartwork_mpl.units",
        "dartwork_mpl.util",
        "dartwork_mpl.validate",
        "dartwork_mpl.validate_fixes",
    }
)

# (from slice, to slice) -> the business fact that requires the dependency.
# A slice may import another slice's surface only with an entry here.
ALLOWED: Mapping[tuple[str, str], str] = {
    ("dartwork_mpl._colors", "dartwork_mpl.units"): (
        "show_colors sizes its swatch figure with the physical-width API"
    ),
    ("dartwork_mpl.annotation", "dartwork_mpl.scale"): (
        "annotation text defaults to a size relative to the active preset"
    ),
    ("dartwork_mpl.diagnostics", "dartwork_mpl.font"): (
        "the font diagnostic draws the bundled font files"
    ),
    ("dartwork_mpl.explore", "dartwork_mpl._colors"): (
        "the explorer browses the shipped colour families"
    ),
    ("dartwork_mpl.explore", "dartwork_mpl.diagnostics"): (
        "the explorer draws the colour and font diagnostics it lists"
    ),
    ("dartwork_mpl.io", "dartwork_mpl.config"): (
        "saving applies the user's export defaults from dm.config"
    ),
    ("dartwork_mpl.io", "dartwork_mpl.layout"): (
        "saving finalises axis-label typography before writing files"
    ),
    ("dartwork_mpl.io", "dartwork_mpl.validate"): (
        "saving runs the visual validation the user asked for"
    ),
    ("dartwork_mpl.layout", "dartwork_mpl.config"): (
        "layout follows the user's tick-label font adoption setting"
    ),
    ("dartwork_mpl.layout", "dartwork_mpl.units"): (
        "margins are given as physical lengths"
    ),
    ("dartwork_mpl.mcp", "dartwork_mpl.lint"): (
        "the MCP server exposes the anti-pattern linter as tools"
    ),
    ("dartwork_mpl.mcp", "dartwork_mpl.prompt"): (
        "the MCP server serves the bundled prompt corpus"
    ),
    ("dartwork_mpl.templates", "dartwork_mpl.scale"): (
        "a template sizes its text relative to the active preset"
    ),
    ("dartwork_mpl.templates", "dartwork_mpl.units"): (
        "a template's default figure size is a physical width and aspect"
    ),
    ("dartwork_mpl.validate", "dartwork_mpl.formatting"): (
        "the tick-decimal check recommends the precision the formatter uses"
    ),
    ("dartwork_mpl.style", "dartwork_mpl.font"): (
        "a preset may name bundled fonts, which must be registered first"
    ),
}

# Modules holding pure decisions: they import no other unit, surfaces included.
DECISIONS: Mapping[str, str] = {
    "dartwork_mpl.mcp.artifacts.policy": (
        "artifact admission, expiry and request parsing decide from values"
    ),
    "dartwork_mpl.mcp.artifacts.input_policy": (
        "retained-input revision rules decide from parsed values"
    ),
}

# Known violations at the start of the refactor (ADR 0005), each with the
# plan step that removes it. The list only shrinks.
DEBT: Mapping[str, str] = {
    "cycle: dartwork_mpl, dartwork_mpl.validate_fixes": "L2",
    "cycle: dartwork_mpl._colors, dartwork_mpl._luminance": "K1",
    "entry point import: dartwork_mpl.mcp.resources -> dartwork_mpl": "M6",
    "entry point import: dartwork_mpl.mcp.tools -> dartwork_mpl": "M4",
    "entry point import: dartwork_mpl.validate_fixes -> dartwork_mpl": "L2",
    "missing __all__: dartwork_mpl._luminance": "K1",
    "missing __all__: dartwork_mpl.validate_fixes": "L2",
    "private import: dartwork_mpl -> dartwork_mpl.validate_fixes.validate_with_fixes": "L2",
    "private import: dartwork_mpl._colors._contrast -> dartwork_mpl._luminance._contrast_ratio": "K1",
    "private import: dartwork_mpl._luminance -> dartwork_mpl._colors._conversion": "K1",
    "private import: dartwork_mpl.diagnostics._colormaps -> dartwork_mpl._colors._families.CYCLIC": "K5",
    "private import: dartwork_mpl.diagnostics._colormaps -> dartwork_mpl._colors._families.DIVERGING": "K5",
    "private import: dartwork_mpl.diagnostics._colormaps -> dartwork_mpl._colors._families.MULTI_HUE": "K5",
    "private import: dartwork_mpl.diagnostics._colormaps -> dartwork_mpl._colors._families.QUALITATIVE": "K5",
    "private import: dartwork_mpl.diagnostics._colormaps -> dartwork_mpl._colors._families.SEQUENTIAL": "K5",
    "private import: dartwork_mpl.diagnostics._colors -> dartwork_mpl._colors._loader.COLOR_LIBRARIES": "K5",
    "private import: dartwork_mpl.helpers.labels -> dartwork_mpl._colors._loader.ensure_loaded": "K4",
    "private import: dartwork_mpl.mcp.resources -> dartwork_mpl._colors._loader.COLOR_LIBRARIES": "K4",
    "private import: dartwork_mpl.mcp.tools -> dartwork_mpl._colors._loader.COLOR_LIBRARIES": "K4",
    "private import: dartwork_mpl.style -> dartwork_mpl._colors._semantic.SEMANTIC_TOKEN_NAMES": "K4",
    "private import: dartwork_mpl.style -> dartwork_mpl._colors._semantic.apply_semantic": "K4",
    "private import: dartwork_mpl.validate._checks._luminance -> dartwork_mpl._luminance._contrast_ratio": "K1",
    "private import: dartwork_mpl.validate._checks._luminance -> dartwork_mpl._luminance._linearized": "K1",
    "private import: dartwork_mpl.validate._checks._luminance -> dartwork_mpl._luminance._rel_lum": "K1",
    "private import: dartwork_mpl.validate._checks.grayscale_safety -> dartwork_mpl._colors._conversion._srgb_to_oklab": "K3",
    "private import: dartwork_mpl.validate._checks.grayscale_safety -> dartwork_mpl._colors._conversion.relative_y_srgb_d65": "K3",
    "private import: dartwork_mpl.validate._checks.text_contrast -> dartwork_mpl._luminance._contrast_ratio": "K1",
    "private import: dartwork_mpl.validate_fixes -> dartwork_mpl.helpers.quality._MIN_RECOMMENDED_DPI": "L2",
    "undeclared dependency: dartwork_mpl.helpers -> dartwork_mpl.scale": "C11",
    "undeclared dependency: dartwork_mpl.mcp -> dartwork_mpl.util": "C9",
    "undeclared dependency: dartwork_mpl.ui -> dartwork_mpl.util": "C9",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl._colors": "C10",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl.annotation": "C10",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl.formatting": "C10",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl.io": "C10",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl.layout": "C10",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl.prompt": "C10",
    "undeclared dependency: dartwork_mpl.util -> dartwork_mpl.scale": "C10",
    "undeclared dependency: dartwork_mpl.validate_fixes -> dartwork_mpl.validate": "L2",
}

# Package paths that hold user-facing sample code, not package source: the
# bundled prompt templates and the UI scaffold templates copied into user
# projects (they import `dartwork_mpl` as any user would).
EXCLUDED_DIRS = (("asset",), ("ui", "templates"))


@dataclass(frozen=True)
class Layout:
    """The unit classification the checker judges a tree against."""

    entry_points: frozenset[str]
    platform: frozenset[str]
    slices: frozenset[str]
    allowed: Mapping[tuple[str, str], str]
    decisions: Mapping[str, str]

    @property
    def units(self) -> frozenset[str]:
        """Every unit name, platform and slice."""
        return self.platform | self.slices


REPOSITORY_LAYOUT = Layout(ENTRY_POINTS, PLATFORM, SLICES, ALLOWED, DECISIONS)


def is_test(rel: Path) -> bool:
    """Whether a path below the package root is a colocated test file."""
    return (
        "tests" in rel.parts
        or rel.name.startswith("test_")
        or rel.name == "conftest.py"
    )


def read_sources(root: Path) -> tuple[dict[str, str], set[str]]:
    """Read the production modules under the package root ``root``.

    Returns the module sources keyed by dotted name and the set of names that
    are packages. Colocated tests and ``EXCLUDED_DIRS`` are skipped.
    """
    code: dict[str, str] = {}
    packages: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if is_test(rel) or any(rel.parts[: len(d)] == d for d in EXCLUDED_DIRS):
            continue
        parts = rel.with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
            packages.add(".".join((PACKAGE, *parts)))
        code[".".join((PACKAGE, *parts))] = path.read_text(encoding="utf-8")
    return code, packages


def owner(module: str, layout: Layout) -> str | None:
    """The unit owning ``module`` by longest dotted prefix, or None."""
    best = None
    for unit in layout.units:
        if (module == unit or module.startswith(unit + ".")) and (
            best is None or len(unit) > len(best)
        ):
            best = unit
    return best


def imports(
    module: str, tree: ast.Module, packages: set[str]
) -> list[tuple[str, str | None]]:
    """Every import in ``tree`` as (absolute module, imported name or None).

    Walks the whole tree, so imports inside functions and ``TYPE_CHECKING``
    blocks count. Relative imports resolve against the module's package.
    """
    result: list[tuple[str, str | None]] = []
    package = module if module in packages else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend((alias.name, None) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                parent = parts[: len(parts) - node.level + 1]
                base = ".".join((*parent, *base.split("."))).rstrip(".")
            result.extend((base, alias.name) for alias in node.names)
    return result


def exports(tree: ast.Module) -> set[str] | None:
    """The literal ``__all__`` of a module, or None when absent or dynamic."""
    for node in tree.body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign) and node.value is not None
            else []
        )
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            value = node.value
            try:
                literal = ast.literal_eval(value) if value is not None else None
            except ValueError:
                return None
            if isinstance(literal, list | tuple) and all(
                isinstance(item, str) for item in literal
            ):
                return set(literal)
            return None
    return None


def _cycles(graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Strongly connected components of more than one node (Tarjan)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    found: list[list[str]] = []
    counter = 0

    def visit(node: str) -> None:
        nonlocal counter
        index[node] = low[node] = counter
        counter += 1
        stack.append(node)
        on_stack.add(node)
        for nxt in sorted(graph.get(node, ())):
            if nxt not in index:
                visit(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], index[nxt])
        if low[node] == index[node]:
            component = []
            while True:
                top = stack.pop()
                on_stack.discard(top)
                component.append(top)
                if top == node:
                    break
            if len(component) > 1:
                found.append(sorted(component))

    for node in sorted(graph):
        if node not in index:
            visit(node)
    return sorted(found)


def violations(
    code: Mapping[str, str], packages: set[str], layout: Layout
) -> list[str]:
    """Every boundary violation in ``code`` (module name -> source), sorted, unique.

    ``packages`` names the modules that are packages. Debt is not applied
    here; see ``check``.
    """
    trees = {name: ast.parse(src, filename=name) for name, src in code.items()}
    errors: set[str] = set()
    surfaces: dict[str, set[str] | None] = {}
    for unit in sorted(layout.units):
        if unit in trees:
            surfaces[unit] = exports(trees[unit])
            if surfaces[unit] is None:
                errors.add(f"missing __all__: {unit}")
    for name in code:
        if name not in layout.entry_points and owner(name, layout) is None:
            errors.add(f"unowned module: {name}")

    def node_of(module: str) -> str | None:
        """The graph node for a module: its unit, or itself for an entry point no unit owns."""
        unit = owner(module, layout)
        if unit is None and module in layout.entry_points:
            return module
        return unit

    graph: dict[str, set[str]] = {}
    used: set[tuple[str, str]] = set()
    for name, tree in trees.items():
        source_unit = owner(name, layout)
        source_node = node_of(name)
        for base, symbol in imports(name, tree, packages):
            if base != PACKAGE and not base.startswith(PACKAGE + "."):
                continue
            submodule = f"{base}.{symbol}" if symbol else None
            target = submodule if submodule in code else base
            # Python runs every parent package's initializer before the
            # module; the root initializer is the entry point and is judged
            # by the explicit import rule below, not as a graph edge.
            parts = target.split(".")
            touched = {target}
            touched.update(
                ".".join(parts[:end]) for end in range(2, len(parts))
            )
            if source_node is not None:
                for module in touched:
                    node = node_of(module)
                    if node is not None and node != source_node:
                        graph.setdefault(source_node, set()).add(node)
            if target in layout.entry_points:
                # An entry point inside a slice (its runnable module) may be
                # imported by that slice; anything else reaching an entry
                # point would reach everything it wires.
                target_owner = owner(target, layout)
                if name not in layout.entry_points and (
                    target_owner is None or target_owner != source_unit
                ):
                    errors.add(f"entry point import: {name} -> {target}")
                continue
            target_unit = owner(target, layout)
            if target_unit is None or target_unit == source_unit:
                continue
            surface = surfaces.get(target_unit) or set()
            is_surface = target == target_unit and (
                symbol is None or symbol in surface or submodule == target
            )
            if submodule == target and target != target_unit:
                is_surface = False
            shown = submodule if submodule else base
            if not is_surface:
                errors.add(f"private import: {name} -> {shown}")
            if name in layout.decisions:
                errors.add(f"decision import: {name} -> {target_unit}")
            if source_unit in layout.platform:
                continue
            if (
                source_unit in layout.slices
                and target_unit in layout.slices
                and is_surface
            ):
                pair = (source_unit, target_unit)
                if pair in layout.allowed:
                    used.add(pair)
                else:
                    errors.add(
                        f"undeclared dependency: {source_unit} -> {target_unit}"
                    )
    for platform in sorted(layout.platform):
        reached = {platform: (platform,)}
        pending = [platform]
        while pending:
            node = pending.pop()
            for nxt in sorted(graph.get(node, ())):
                if nxt not in reached:
                    reached[nxt] = (*reached[node], nxt)
                    pending.append(nxt)
                    if nxt not in layout.slices:
                        continue
                    errors.add(
                        "platform reaches slice: " + " -> ".join(reached[nxt])
                    )
    errors.update(
        "cycle: " + ", ".join(component) for component in _cycles(graph)
    )
    errors.update(
        f"unused allowance: {a} -> {b}"
        for a, b in layout.allowed
        if (a, b) not in used
    )
    return sorted(errors)


def check(
    root: Path,
    layout: Layout = REPOSITORY_LAYOUT,
    debt: Mapping[str, str] = DEBT,
) -> list[str]:
    """The violations under package root ``root`` that DEBT does not list, plus stale debt.

    An empty discovery fails closed.
    """
    code, packages = read_sources(root)
    if not code:
        return [f"no production modules found under {root}"]
    found = violations(code, packages, layout)
    return sorted(
        [v for v in found if v not in debt]
        + [f"stale debt: {d}" for d in debt if d not in found]
    )


def main() -> int:
    """Print violations; exit 1 when there are any, 0 otherwise."""
    root = Path(__file__).resolve().parents[1] / "src" / PACKAGE
    errors = check(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Slice boundaries passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
