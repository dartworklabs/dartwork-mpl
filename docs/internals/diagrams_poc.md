---
orphan: true
---

# Diagrams PoC — five libraries, three deliverables

This page is a proof-of-concept catalog for the docs diagramming layer.
It exists to answer two questions:

1. **Which diagram library do we standardize on?** PR #337 wired in
   Mermaid as the first choice. This page renders the *same* content
   through five different libraries so the tradeoffs are visible at a
   glance.
2. **What does the rest of dartwork-mpl actually look like?** §B and §C
   below ship the first two architecture-level diagrams the docs site
   has ever had — a system overview (curated) and a module-dependency
   graph (auto-extracted from `src/dartwork_mpl/`).

The page is `:orphan:` — it lives off the sidebar so casual visitors
don't trip on it, but the URL is stable
(`/internals/diagrams_poc.html`) so reviewers can link to it.

---

## §A — same diagram, five libraries

Each tile renders the **dartwork-mpl config-precedence chain** — the
exact same "per-call keyword → `dm.config` field → hard-coded default"
ladder you see on the [Layout config](../usage_guide/config.md) page.
Identical content means visual differences are *aesthetic*, not
informational.

### 1. Mermaid (current default)

Source: live `mermaid` directive — parsed by `mermaid.js` in the
browser. Authored in plain text inside the `.md` file, so `git diff`
shows the diagram edits as-is. **No build step. No binary dep.**

```{mermaid}
flowchart TD
    A["<b>per-call keyword</b><br/><code>simple_layout(fig, …)</code><br/><i>always wins</i>"]
    B["<b>dm.config field</b><br/><code>dm.config.adopt_orphan_tick_font&nbsp;=&nbsp;False</code><br/><i>project default</i>"]
    C["<b>hard-coded Config default</b><br/>(True / False)<br/><i>library default</i>"]
    A -->|"None? fall through"| B
    B -->|"no field? fall through"| C

    style A fill:#fef3c7,stroke:#cdced6,stroke-width:1px
    style B fill:#ecfeff,stroke:#cdced6,stroke-width:1px
    style C fill:#f3e8ff,stroke:#cdced6,stroke-width:1px
```

```{admonition} Verdict
:class: tip

**Strengths.** Diff-friendly (text), zero install (CDN-hosted JS),
themable via `mermaid_init_js`, supports flowchart / sequence / class /
state / gantt / git in one directive. **Weaknesses.** Layout is
auto-computed and not always fixable; complex graphs degrade quickly;
no per-node positioning. **Use for:** flowcharts, sequence diagrams,
state machines — anything where the layout solver does an adequate job.
```

### 2. Graphviz (auto-extracted graphs)

Source: hand-written `.dot` syntax. Rendered at *Sphinx build time* by
the `dot` binary (added to CI via `apt install graphviz`).

```{graphviz}
digraph config_chain {
    rankdir="TB";
    bgcolor="transparent";
    node [shape=box, style="rounded,filled", fontname="Inter, system-ui, sans-serif",
          fontsize=11, margin="0.22,0.13", color="#cdced6"];
    edge [fontname="Inter, system-ui, sans-serif", fontsize=10, color="#60646c"];

    A [label="per-call keyword\nsimple_layout(fig, …)\n★ always wins", fillcolor="#fef3c7"];
    B [label="dm.config field\ndm.config.adopt_orphan_tick_font = False\nproject default", fillcolor="#ecfeff"];
    C [label="hard-coded Config default\n(True / False)\nlibrary default", fillcolor="#f3e8ff"];

    A -> B [label="None? fall through"];
    B -> C [label="no field? fall through"];
}
```

```{admonition} Verdict
:class: tip

**Strengths.** Best-in-class layout engine — handles 100+ node graphs
gracefully; deterministic output; SVG is a single static file with no
runtime JS. **Weaknesses.** No theming language beyond per-node
attributes; curved edges look stiff next to Mermaid; needs `dot` on
the build host. **Use for:** dependency graphs, call graphs,
relationships — anything Graphviz's `dot` / `neato` algorithms are
designed to solve.
```

### 3. Mingrammer Diagrams (curated system architecture)

Source: Python script (`docs/internals/scripts/build_architecture_diagram.py`).
Wraps Graphviz internally but renders **with named icons** for cloud
primitives — useful for system-level diagrams where "a User" or "a
FastAPI service" is a recognizable shape, not a labeled box.

```{image} ../_static/diagrams/architecture_overview.svg
:alt: dartwork-mpl system architecture overview rendered by Mingrammer Diagrams
:width: 100%
```

```{admonition} Verdict
:class: tip

**Strengths.** Iconography is the headline — AWS/GCP/K8s/Generic
nodes render as actual brand glyphs, which is irreplaceable for cloud
architecture diagrams; Python-as-source means programmatic
construction (loops, conditionals). **Weaknesses.** Still Graphviz
underneath, so the same `dot` binary dependency applies; the icon
library is opinionated (~700 nodes, not all relevant). **Use for:**
system-level architecture (the diagram above), AI/ML pipelines,
"how this product fits together" overviews.
```

### 4. Excalidraw aesthetic (hand-drawn)

Source: hand-authored SVG with an `feTurbulence` + `feDisplacementMap`
filter applied (`docs/_static/diagrams/mental_model_excalidraw.svg`).
Mimics Excalidraw's wobbly-line look without dragging in the full
Excalidraw runtime.

```{image} ../_static/diagrams/mental_model_excalidraw.svg
:alt: dartwork-mpl config resolution chain in Excalidraw aesthetic
:width: 100%
```

```{admonition} Verdict
:class: tip

**Strengths.** Conveys "this is informal / approachable" instantly —
ideal for blog posts, README hero shots, or design rationale notes
where a precise diagram would feel over-engineered. **Weaknesses.**
Custom-authored per diagram (no source language); the wobble filter
is decorative, not informational. **Use for:** philosophy pages,
explanatory blog posts, "rough draft" architecture sketches.
```

### 5. D3.js (interactive force-directed)

Source: inline data + a 200-line vanilla-JS script
(`docs/_static/diagram_d3.js`). Renders a draggable force-directed
graph of the same module dependency data §C extracts statically.
Hover a node for its cluster; drag to rearrange.

```{raw} html
<div id="dm-d3-modgraph"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"
        integrity="sha384-K9d61t+vfcfV3wL+nlNqzx5HwRBP8VsBlAR3eYHbKzgkdJyHnsq6vC2vTu7ULNqM"
        crossorigin="anonymous"></script>
<script src="../_static/diagram_d3.js"></script>
```

```{admonition} Verdict
:class: tip

**Strengths.** The only library here that's *interactive* — drag,
hover, tooltip; perfect for graphs the reader wants to explore (peer
networks, supply chains, citation graphs). **Weaknesses.** Most code
(D3 has no high-level diagram API — you compose forces and shapes
yourself); requires a CDN script tag or vendored `d3.min.js`; doesn't
print well. **Use for:** anything where the value is *exploration*,
not viewing.
```

```{admonition} Picking a default
:class: important

**Mermaid stays the default** — diff-friendly text, no build dep, good
for 80% of flowchart / sequence / state needs.

The other four are **escalation paths**:

- **Graphviz** when the graph has > 15 nodes or auto-layout matters.
- **Mingrammer Diagrams** for system architecture with iconography.
- **Excalidraw aesthetic** for informal / philosophical pages.
- **D3** for interactive exploration of a relationship graph.

There is no single "best" library — each occupies a niche the others
can't fill cleanly.
```

---

## §B — system architecture overview

Curated picture of how an analyst's script flows through dartwork-mpl
and where each subsystem attaches. Rendered with Mingrammer Diagrams.

```{image} ../_static/diagrams/architecture_overview.svg
:alt: dartwork-mpl system architecture — Mingrammer Diagrams
:width: 100%
```

**How to read it.** The analyst (left) writes a script that calls
`dm.style.use(...)`, `plt.subplots(figsize=dm.figsize(...))`, and
`dm.simple_layout(fig)`. Each call resolves design tokens *read-only*
from the `colors / cmap / font / asset` data layer (dashed = read).
`save_formats` emits the artifact. The AI tooling layer (lint,
validate, MCP, agent helpers) *observes* the script and the artifact
(dotted) but never mutates them — it's a one-way critic.

To regenerate after a structural change:

```bash
uv run python docs/internals/scripts/build_architecture_diagram.py
```

The script is idempotent. The committed SVG is the source of truth;
re-running locally and seeing no `git diff` means the architecture
hasn't drifted.

---

## §C — module dependency graph (auto-extracted)

`docs/internals/scripts/build_module_graph.py` walks
`src/dartwork_mpl/` with `ast`, extracts every in-package
`from dartwork_mpl.X import …` statement, collapses to top-level
submodule granularity, and clusters by role (API / data / support).

```{graphviz} ../_static/diagrams/module_graph.dot
```

**Reading the layout.** Left-to-right = "depends on flows left." The
blue API cluster (style, layout, io, …) is what users import directly;
the teal data cluster (colors, cmap, font, asset) holds design tokens;
the lilac support cluster is the agent / validation / MCP scaffolding
that exists *for* the API but isn't usually imported manually. Edges
are weighted faintly by import count.

To regenerate after refactoring:

```bash
uv run python docs/internals/scripts/build_module_graph.py
```

The script is fully deterministic — alphabetically sorted node and
edge order, no timestamps. A clean `git diff` after rerunning means
no module-level dependencies changed.

---

## Engineering notes for the next iteration

- **CI installs Graphviz.** Both `ci.yml` and `docs.yml` now run
  `sudo apt-get install -y graphviz` before `sphinx-build`. Local
  builds need `brew install graphviz` (macOS) or the equivalent.
- **The `.dot` file is the source.** §C reads the committed `.dot`
  at Sphinx build time and re-renders it with the project font.
  This means the docs HTML stays text-diff-friendly (`.dot` is the
  diff target, not the SVG).
- **Mermaid theming** lives in `docs/conf.py → mermaid_init_js`.
  PR #337 added the radix-design palette there; this PR widened
  the SVG to fill the container (`useMaxWidth: false`) so labels
  stop wrapping at 64rem body width.
- **No `sphinxcontrib-plantuml`.** Considered, declined: PlantUML
  ships a Java jar that adds 80 MB to CI and a startup cost on
  every build. The five libraries here cover its use cases
  (Graphviz for class diagrams, Mermaid for sequence).
