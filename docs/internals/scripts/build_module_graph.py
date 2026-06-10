"""Extract the in-package dependency graph of ``dartwork_mpl`` and emit a
Graphviz DOT file rendered to SVG.

Walks ``src/dartwork_mpl/`` with :mod:`ast`, parses every ``from
dartwork_mpl(.sub) import …`` / ``import dartwork_mpl.sub`` statement, and
collapses everything to *top-level submodule granularity* (e.g. the
internal helpers under ``dartwork_mpl/colors/`` all roll up to a single
``colors`` node). The resulting DOT is checked in as a static asset, so
docs builds without the ``dot`` binary still show the rendered graph via
the committed SVG fallback.

Usage
-----
    uv run python docs/internals/scripts/build_module_graph.py

Outputs (both deterministic — no timestamps, sorted edges):
    docs/_static/diagrams/module_graph.dot
    docs/_static/diagrams/module_graph.svg   (only if ``dot`` is on PATH)

The DOT file is what the ``.. graphviz:: ../_static/diagrams/module_graph.dot``
directive on the PoC page reads at build time; the committed SVG mirrors it
for environments without graphviz installed.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "dartwork_mpl"
OUT_DIR = ROOT / "docs" / "_static" / "diagrams"
DOT_OUT = OUT_DIR / "module_graph.dot"
SVG_OUT = OUT_DIR / "module_graph.svg"

# Submodules that should not appear as separate nodes — collapse into
# their owning umbrella module instead. ``mcp.server`` and friends are
# implementation detail of the ``mcp`` package and would otherwise
# explode into a 12-node subtree that drowns out the architecture.
EXCLUDE_NODES: frozenset[str] = frozenset()


def _toplevel(mod: str) -> str:
    """Return the first dotted segment of an import path.

    ``colors.palette`` -> ``colors``; ``mcp.server.tools`` -> ``mcp``.
    """
    return mod.split(".", 1)[0]


def _walk_imports(pkg_root: Path):
    """Yield ``(source_top, target_top)`` pairs for every in-package import."""
    pkg_name = pkg_root.name  # "dartwork_mpl"

    for py_path in sorted(pkg_root.rglob("*.py")):
        rel = py_path.relative_to(pkg_root)
        # Source module = first segment of the file's path relative to the
        # package root. ``cmap.py`` -> "cmap"; ``colors/palette.py`` ->
        # "colors"; ``__init__.py`` -> "" (skipped, no self-edges).
        parts = rel.parts
        if not parts or parts[0] == "__init__.py":
            continue
        source = parts[0] if (pkg_root / parts[0]).is_dir() else parts[0][:-3]

        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                # relative ``from . import X``
                if node.level and node.level >= 1:
                    target = _toplevel(node.module) if node.module else None
                    if target is None or target == source:
                        continue
                    yield source, target
                    continue
                if not node.module.startswith(pkg_name):
                    continue
                tail = node.module[len(pkg_name) + 1 :]  # strip "dartwork_mpl."
                if not tail:
                    continue
                target = _toplevel(tail)
                if target != source:
                    yield source, target
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if not alias.name.startswith(f"{pkg_name}."):
                        continue
                    tail = alias.name[len(pkg_name) + 1 :]
                    target = _toplevel(tail)
                    if target != source:
                        yield source, target


def _build_dot(edges: dict[tuple[str, str], int]) -> str:
    """Render the edge dict to a hand-formatted DOT string.

    Hand-formatting (instead of going through pydot/graphviz Python
    bindings) keeps the output byte-identical across runs — every edge
    is sorted alphabetically and no metadata is stamped in.
    """
    nodes = sorted({n for edge in edges for n in edge} - EXCLUDE_NODES)

    # Group nodes into rough architectural clusters for layout. The
    # mapping below is *static and intentional* — Graphviz can't infer
    # what the user-facing API surface looks like from imports alone.
    clusters = {
        "api": [
            "style",
            "layout",
            "io",
            "annotation",
            "formatting",
            "scale",
            "units",
            "icon",
        ],
        "data": ["colors", "cmap", "font", "asset", "asset_viz"],
        "support": [
            "agent",
            "mcp",
            "ui",
            "validate",
            "validate_fixes",
            "lint",
            "diagnostics",
            "explore",
            "helpers",
            "_helpers",
            "templates",
            "prompt",
            "util",
            "cli",
            "config",
        ],
    }
    cluster_color = {"api": "#0d8ee8", "data": "#0090a8", "support": "#9750c1"}
    cluster_label = {
        "api": "Plotting API (the part you import)",
        "data": "Design tokens & assets",
        "support": "Tooling, agent, validation",
    }

    placed = set()
    lines = [
        "digraph dartwork_mpl {",
        '  rankdir="LR";',
        '  bgcolor="transparent";',
        '  node [shape=box, style="rounded,filled", fillcolor="#ffffff",',
        '        color="#cdced6", fontsize=11, margin="0.18,0.10",',
        '        fontname="Inter, system-ui, sans-serif"];',
        '  edge [color="#9498a3", arrowsize=0.6, penwidth=0.9];',
    ]

    for cname, members in clusters.items():
        present = [m for m in members if m in nodes]
        if not present:
            continue
        lines.append(f"  subgraph cluster_{cname} {{")
        lines.append(f'    label="{cluster_label[cname]}";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#fafafb";')
        lines.append('    color="#dfe0e6";')
        lines.append("    fontsize=10;")
        lines.append('    fontcolor="#60646c";')
        lines.append(
            f'    node [color="{cluster_color[cname]}", penwidth=1.2];'
        )
        for m in present:
            lines.append(f'    "{m}";')
            placed.add(m)
        lines.append("  }")

    # Catch-all for anything not pre-clustered.
    leftover = [n for n in nodes if n not in placed]
    lines.extend(f'  "{m}";' for m in leftover)

    # Deterministic edge order — sort by (src, dst).
    for (src, dst), weight in sorted(edges.items()):
        if src in EXCLUDE_NODES or dst in EXCLUDE_NODES:
            continue
        # Edge thickness scales weakly with import count — a faint signal
        # that's still readable in print.
        penwidth = 0.7 + min(0.05 * weight, 1.0)
        lines.append(f'  "{src}" -> "{dst}" [penwidth={penwidth:.2f}];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not SRC.is_dir():
        sys.exit(f"package root not found: {SRC}")

    edges: dict[tuple[str, str], int] = defaultdict(int)
    for src, dst in _walk_imports(SRC):
        edges[(src, dst)] += 1

    dot_text = _build_dot(dict(edges))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOT_OUT.write_text(dot_text, encoding="utf-8")
    print(f"wrote {DOT_OUT.relative_to(ROOT)}  ({len(edges)} edges)")

    dot_bin = shutil.which("dot")
    if dot_bin is None:
        print(
            "`dot` binary not found — skipping SVG render. "
            "Install with `brew install graphviz` / `apt install graphviz`."
        )
        return 0

    subprocess.run(
        [dot_bin, "-Tsvg", str(DOT_OUT), "-o", str(SVG_OUT)], check=True
    )
    print(f"wrote {SVG_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
