"""Render the dartwork-mpl system architecture overview using
``mingrammer/diagrams``.

Mingrammer's library renders a Python AST description of cloud / system
architecture into an SVG via Graphviz under the hood. Unlike the
auto-extracted module graph, this diagram is *hand-curated*: it shows
the user-facing mental model — how an analyst writes a script, where
the design tokens flow in, and where the agent / validation / MCP
layers attach.

Usage
-----
    uv run python docs/internals/scripts/build_architecture_diagram.py

Outputs (deterministic — Diagrams stamps no timestamps):
    docs/_static/diagrams/architecture_overview.svg

Requires the ``dot`` binary on $PATH (same as build_module_graph.py).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "docs" / "_static" / "diagrams"
OUT_BASENAME = "architecture_overview"

# Set BEFORE importing diagrams — the library reads outformat at import time
# when assembling default attrs in some versions.
os.environ.setdefault("DIAGRAMS_GRAPH_ATTR_FONTNAME", "Inter")


def main() -> int:
    if shutil.which("dot") is None:
        print("`dot` binary not found — skipping. Install graphviz first.")
        return 0

    from diagrams import Cluster, Diagram, Edge
    from diagrams.generic.storage import Storage
    from diagrams.onprem.client import User
    from diagrams.programming.framework import Fastapi
    from diagrams.programming.language import Python

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Diagrams insists on writing into the *current* working directory; chdir
    # to the static dir so the artifact lands next to the other diagrams.
    cwd_before = Path.cwd()
    os.chdir(OUT_DIR)

    # Compact layout: fewer nodes, larger fonts. The earlier 13-node
    # version exported at ~1636px and shrank its labels below readability
    # once capped to the body width. Grouping the three token stores into
    # one node and the four AI nodes into two keeps the diagram a clean
    # left-to-right pipeline that stays legible at 100% body width.
    graph_attr = {
        "bgcolor": "transparent",
        "pad": "0.25",
        "nodesep": "0.55",
        "ranksep": "0.85",
        "splines": "spline",
        "fontname": "Inter, system-ui, sans-serif",
        "fontsize": "13",
        "fontcolor": "#60646c",
    }
    node_attr = {
        "fontname": "Inter, system-ui, sans-serif",
        "fontsize": "12.5",
        "fontcolor": "#1c2024",
    }
    edge_attr = {
        "color": "#9498a3",
        "penwidth": "1.0",
        "arrowsize": "0.8",
        "fontname": "Inter, system-ui, sans-serif",
        "fontsize": "11",
        "fontcolor": "#60646c",
    }

    try:
        with Diagram(
            "dartwork-mpl — system overview",
            filename=OUT_BASENAME,
            outformat="svg",
            show=False,
            direction="LR",
            graph_attr=graph_attr,
            node_attr=node_attr,
            edge_attr=edge_attr,
        ):
            analyst = User("Analyst / agent")

            with Cluster("dartwork-mpl runtime (one-way pipeline)"):
                style_engine = Python("dm.style.use(preset)")
                layout = Python("dm.simple_layout(fig)")
                save = Python("dm.save_formats(fig)")
                style_engine >> Edge(label="figsize · fs · lw") >> layout
                layout >> Edge(label="content-aware margins") >> save

            tokens = Storage("Design tokens\ncolors · cmap · font · asset")

            with Cluster("AI / validation layer (read-only observers)"):
                checks = Python("lint engine +\nvalidate_figure()")
                mcp = Fastapi("MCP server\n(13 tools · 12 resources)")

            artifact = Storage("PNG · PDF · SVG\n+ provenance")

            # Authoring pipeline (solid = data flow) -----------------------
            analyst >> Edge(label="writes plot code") >> style_engine
            save >> Edge(label="emits") >> artifact

            # Token reads (dashed = read-only) -----------------------------
            style_engine >> Edge(style="dashed", label="reads") >> tokens

            # AI observers (dotted = inspect, never mutate) ----------------
            style_engine >> Edge(style="dotted", label="lint") >> checks
            save >> Edge(style="dotted", label="validate") >> checks
            (
                analyst
                >> Edge(style="dotted", color="#0d8ee8", label="MCP tools")
                >> mcp
            )
            mcp >> Edge(style="dashed", color="#9750c1") >> checks
    finally:
        os.chdir(cwd_before)

    out_path = OUT_DIR / f"{OUT_BASENAME}.svg"
    if not out_path.exists():
        print(f"warning: expected {out_path} not produced")
        return 1
    print(
        f"wrote {out_path.relative_to(ROOT)}  ({out_path.stat().st_size:,} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
