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

    graph_attr = {
        "bgcolor": "transparent",
        "pad": "0.3",
        "nodesep": "0.45",
        "ranksep": "0.65",
        "splines": "spline",
        "fontname": "Inter, system-ui, sans-serif",
        "fontsize": "11",
        "fontcolor": "#60646c",
    }
    node_attr = {
        "fontname": "Inter, system-ui, sans-serif",
        "fontsize": "11",
        "fontcolor": "#1c2024",
    }
    edge_attr = {
        "color": "#9498a3",
        "penwidth": "0.9",
        "arrowsize": "0.7",
        "fontname": "Inter, system-ui, sans-serif",
        "fontsize": "9.5",
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

            with Cluster("Authoring surface"):
                script = Python("Analysis script\n(plt + dm.figsize + dm.fs)")

            with Cluster("dartwork-mpl runtime"):
                style_engine = Python("style.use(preset)")
                with Cluster("Design tokens (read-only)"):
                    colors = Storage("colors / cmap")
                    fonts = Storage("font / asset")
                    presets = Storage("dmpl.mplstyle\npresets")
                layout = Python("simple_layout()")
                save = Python("save_formats()")

            with Cluster("Validation & AI"):
                lint = Python("lint engine\n(anti-pattern catalog)")
                validate = Python("validate_figure()")
                mcp = Fastapi("MCP server\n(13 tools)")
                agent = Python("agent helpers")

            artifact = Storage("PNG / PDF / SVG\n+ provenance")

            # Authoring flow ------------------------------------------------
            analyst >> Edge(label="write code") >> script
            script >> Edge(label="dm.style.use") >> style_engine
            style_engine >> Edge(style="dashed") >> presets
            style_engine >> Edge(style="dashed") >> colors
            style_engine >> Edge(style="dashed") >> fonts
            script >> Edge(label="plt.subplots\n(figsize=dm.figsize)") >> layout
            layout >> Edge(label="save_formats") >> save
            save >> Edge(label="emit") >> artifact

            # AI-side observers --------------------------------------------
            (
                script
                >> Edge(style="dotted", label="lint_dartwork_mpl_code")
                >> lint
            )
            save >> Edge(style="dotted", label="validate_plot_data") >> validate
            mcp >> Edge(style="dashed") >> lint
            mcp >> Edge(style="dashed") >> validate
            (
                analyst
                >> Edge(style="dotted", color="#0d8ee8", label="MCP tools")
                >> mcp
            )
            (
                agent
                << Edge(
                    style="dotted", color="#9750c1", label="docs / templates"
                )
                << mcp
            )
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
