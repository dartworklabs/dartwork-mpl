"""Check the package's slice boundaries from source, without importing it (ADR 0005).

Every production module under ``src/dartwork_mpl`` belongs to one unit: a
slice (a capability), a platform unit (mechanism with no business), or an
entry point module that only wires. Ownership is by the longest unit prefix,
so a sub-slice can be declared inside a slice; the enclosing package's
initializer is not a dependency of the modules it contains. A unit's surface is its
own module (the package ``__init__`` or the single file) and the names in its
literal ``__all__``; everything else is private.

A compatibility shim (``SHIMS``) keeps a public module path whose contents
moved into a unit. The shim belongs to that owner unit, so its imports of the
owner's private modules are internal, and it is a second surface module of
the owner: importers of the shim are judged against the shim's own literal
``__all__`` (a shim without one is a ``missing __all__``).

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
  decision import        a module listed in DECISIONS importing another slice
  unowned module         a production module no unit or entry point owns
  unused allowance       an ALLOWED entry no import backs
  stale debt             a DEBT entry that no longer occurs (delete it)

Violations listed in DEBT are known and pass; the list only shrinks. Run:
``uv run python tests/architecture/boundaries.py`` (exit 1 on any violation).
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE = "dartwork_mpl"

# Modules that only wire: they may import any unit's surface. The package
# root runs on every `import dartwork_mpl`, so no unit may import it; the
# compose modules join slices for the root (composition.py rules C2..C5).
ENTRY_POINTS = frozenset(
    {
        "dartwork_mpl",
        "dartwork_mpl.compose",
        "dartwork_mpl.compose.size",
        "dartwork_mpl.compose.style",
    }
)

# Units holding business-agnostic mechanism. They import no slice.
PLATFORM = frozenset(
    {
        # Horizontal text alignment (labels and ticks align text to an
        # anchor).
        "dartwork_mpl.align",
        # Colour values and their arithmetic: sRGB, OKLab, compositing,
        # WCAG contrast (color, labels and check compute with them).
        "dartwork_mpl.colorspace",
        # The x/y axis and an axis label's side, as pure types (check,
        # labels, layout, ticks and geometry name them).
        "dartwork_mpl.axis",
        # The scale a number prints in (ticks reports an axis's, labels prints
        # bar values in it).
        "dartwork_mpl.number",
        # An Axes' projection as a pure type (check, layout, labels, ticks
        # and geometry ask it).
        "dartwork_mpl.projection",
        # A physical length and its units (size measures canvases in it,
        # layout margins).
        "dartwork_mpl.length",
        # Whose convention a figure follows (style reads it off a preset,
        # color binds the role colours for it).
        "dartwork_mpl.locale",
        # Figure measurement two or more slices share.
        "dartwork_mpl.geometry",
        # The edge-case registry every slice's edges.py appends to.
        "dartwork_mpl.edgecase",
    }
)

# Units holding one capability each.
SLICES = frozenset(
    {
        "dartwork_mpl.check",
        "dartwork_mpl.color",
        "dartwork_mpl.font",
        "dartwork_mpl.guide",
        "dartwork_mpl.labels",
        "dartwork_mpl.legend",
        "dartwork_mpl.layout",
        "dartwork_mpl.save",
        "dartwork_mpl.size",
        "dartwork_mpl.style",
        "dartwork_mpl.ticks",
    }
)

# (from slice, to slice) -> the business fact that requires the dependency.
# A slice may import another slice's surface only with an entry here.
ALLOWED: Mapping[tuple[str, str], str] = {
    ("dartwork_mpl.labels", "dartwork_mpl.ticks"): (
        "bar value labels print in their axis's tick unit, like the ticks"
    ),
    ("dartwork_mpl.labels", "dartwork_mpl.style"): (
        "label text is sized and weighted relative to the active preset"
    ),
    ("dartwork_mpl.layout", "dartwork_mpl.labels"): (
        "bar labels, line-end names and panel letters settle at the size the "
        "layout fits, before it measures the margins"
    ),
    ("dartwork_mpl.layout", "dartwork_mpl.legend"): (
        "legends settle at the size the layout fits; an outside legend's "
        "side bounds what the margins measure of it"
    ),
    ("dartwork_mpl.layout", "dartwork_mpl.ticks"): (
        "layout writes the library's tick numbers before measuring them and "
        "thins crowded dates at the fitted size"
    ),
}

# Compatibility shims: public module path -> the unit that owns its contents.
SHIMS: Mapping[str, str] = {}

# Modules holding pure decisions: they import no slice, surfaces included.
# The platform's vocabulary (geometry's axis variants) is shared by every
# slice, so a decision may name it.
DECISIONS: Mapping[str, str] = {
    "dartwork_mpl.check.decide": (
        "what is wrong with a figure is decided from its measured facts alone"
    ),
    "dartwork_mpl.check.model": (
        "the facts, findings and label parsing need nothing outside them"
    ),
    "dartwork_mpl.font.decide": (
        "which font-table fixes apply is decided from faces alone"
    ),
    "dartwork_mpl.font.model": (
        "the font table's types need nothing outside it"
    ),
    "dartwork_mpl.color.decide": (
        "colour forms, gradients, mixes and contrast decide from colour values"
    ),
    "dartwork_mpl.color.model": (
        "parsing colour input into colour types needs nothing outside it"
    ),
    "dartwork_mpl.ticks.decide": (
        "tick units, decimals and default formats are decided from tick facts alone"
    ),
    "dartwork_mpl.ticks.model": (
        "the tick types and config parsing need nothing outside them"
    ),
    "dartwork_mpl.legend.decide": (
        "where a legend goes is decided from measured facts and their "
        "measuring functions alone"
    ),
    "dartwork_mpl.legend.model": (
        "the legend's geometry and plan types need nothing outside them"
    ),
    "dartwork_mpl.layout.decide": (
        "grid edges are decided from measured content and margins alone"
    ),
    "dartwork_mpl.size.decide": (
        "the canvas is decided from the parsed request and the page alone"
    ),
    "dartwork_mpl.size.model": (
        "parsing user input into size types needs nothing outside it"
    ),
    "dartwork_mpl.labels.decide": (
        "label placement is decided from measured boxes and parsed options alone"
    ),
    "dartwork_mpl.labels.model": (
        "parsing label_bars' keywords needs nothing outside it"
    ),
    "dartwork_mpl.style.decide": (
        "which layers apply and what a step is worth decide from presets alone"
    ),
    "dartwork_mpl.style.model": (
        "parsing a preset request needs nothing outside it"
    ),
    "dartwork_mpl.save.decide": (
        "which files to write is decided from the parsed request alone"
    ),
    "dartwork_mpl.save.model": (
        "parsing the save arguments needs nothing outside it"
    ),
    "dartwork_mpl.guide.decide": (
        "findings and search ranks are decided from the parsed source, catalog and references"
    ),
    "dartwork_mpl.guide.model": (
        "parsing source, catalog and guidance text needs nothing outside it"
    ),
}

# Modules whose file path is fixed outside their owner's folder, with the
# unit that owns them. Prefix ownership would give them to the enclosing
# package; these paths are pinned elsewhere, so the module cannot move.
PINNED: Mapping[str, str] = {}

# Known violations at the start of the refactor (ADR 0005), each with the
# plan step that removed it. Every one is resolved; the list stays empty
# (tests/architecture/test_boundaries.py) so a new violation fails outright.
DEBT: Mapping[str, str] = {}

# Package paths that hold user-facing sample code, not package source: the
# bundled templates (they import `dartwork_mpl` as any user would).
EXCLUDED_DIRS = (("guide", "assets"),)


@dataclass(frozen=True)
class Layout:
    """The unit classification the checker judges a tree against."""

    entry_points: frozenset[str]
    platform: frozenset[str]
    slices: frozenset[str]
    allowed: Mapping[tuple[str, str], str]
    decisions: Mapping[str, str]
    shims: Mapping[str, str] = field(default_factory=dict)
    pinned: Mapping[str, str] = field(default_factory=dict)

    @property
    def units(self) -> frozenset[str]:
        """Every unit name, platform and slice."""
        return self.platform | self.slices


REPOSITORY_LAYOUT = Layout(
    ENTRY_POINTS, PLATFORM, SLICES, ALLOWED, DECISIONS, SHIMS, PINNED
)


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
    """The unit owning ``module``: a shim's or pinned module's owner, else by longest dotted prefix, or None."""
    if module in layout.shims:
        return layout.shims[module]
    if module in layout.pinned:
        return layout.pinned[module]
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
    for shim in sorted(layout.shims):
        if shim in trees:
            surfaces[shim] = exports(trees[shim])
            if surfaces[shim] is None:
                errors.add(f"missing __all__: {shim}")
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
            # by the explicit import rule below, not as a graph edge. A
            # parent package that also encloses the importing module was
            # initialized before that module ran, so reaching below it adds
            # no dependency (a sub-slice importing inside its own slice).
            parts = target.split(".")
            touched = {target}
            touched.update(
                parent
                for parent in (
                    ".".join(parts[:end]) for end in range(2, len(parts))
                )
                if not name.startswith(parent + ".")
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
            if target in layout.shims:
                # The shim module itself, or a name its __all__ lists.
                shim_surface = surfaces.get(target) or set()
                is_surface = (
                    symbol is None
                    or submodule == target
                    or symbol in shim_surface
                )
            else:
                surface = surfaces.get(target_unit) or set()
                is_surface = target == target_unit and (
                    symbol is None or symbol in surface or submodule == target
                )
                if submodule == target and target != target_unit:
                    is_surface = False
            shown = submodule if submodule else base
            if not is_surface:
                errors.add(f"private import: {name} -> {shown}")
            if name in layout.decisions and target_unit not in layout.platform:
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
    root = Path(__file__).resolve().parents[2] / "src" / PACKAGE
    errors = check(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Slice boundaries passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
