---
orphan: true
---

# Diagrams PoC — four libraries, real examples

This page is a proof-of-concept catalog for the docs diagramming layer.
It answers two questions:

1. **Which diagram library do we standardize on?** PR #337 wired in
   Mermaid first. Rather than draw one trivial box-chart four ways, §A
   below shows each library doing **the thing it's actually good at**,
   on real dartwork-mpl content — so the comparison reflects how each
   tool behaves on a non-toy diagram.
2. **What does dartwork-mpl actually look like?** §B and §C ship the
   first two architecture-level diagrams the docs site has had — a
   curated system overview and a module-dependency graph
   auto-extracted from `src/dartwork_mpl/`.

The page is `:orphan:` — off the sidebar so casual visitors don't trip
on it, but the URL is stable (`/internals/diagrams_poc.html`) for
linking.

```{admonition} TL;DR — which to reach for
:class: important

| Need | Library | Why |
|---|---|---|
| Flow / sequence / state, edited inline as text | **Mermaid** | no build step, diff-friendly, six diagram types |
| Auto-laid-out graph with branches / clusters | **Graphviz** | the `dot` solver handles 15–100 nodes that Mermaid can't |
| System architecture with recognizable shapes | **Mingrammer Diagrams** | Python-as-source + cloud/service iconography |
| A relationship graph the reader should *explore* | **D3.js** | the only interactive option — drag, hover, degree-sized nodes |

Mermaid stays the default; the other three are escalation paths.
```

---

## §A — each library on its strongest example

### 1. Mermaid — a sequence diagram

Mermaid's reach is the selling point: one directive does flowchart,
**sequence**, class, state, gantt, and git graphs. A sequence diagram
is where it clearly beats Graphviz, so that's the fair example. This
one traces **what actually happens in one plotting session** — the
agent lints a draft, applies a preset, draws, lays out, and saves,
with the AI layer observing.

Source: plain text in the `.md` file — `git diff` shows the diagram
edits verbatim. No build step, no binary.

```{mermaid}
sequenceDiagram
    autonumber
    actor A as Agent / analyst
    participant S as dm.style
    participant P as plt · Figure
    participant L as simple_layout
    participant IO as save_formats
    participant V as lint + validate

    A->>V: lint_dartwork_mpl_code(draft)
    V-->>A: 0 anti-patterns ✓
    A->>S: dm.style.use("scientific")
    S-->>A: rcParams applied (fonts · dpi · palette)
    A->>P: plt.subplots(figsize=dm.figsize("13cm","wide"))
    P-->>A: fig, ax — physical width honored
    A->>P: ax.plot(x, y, lw=dm.lw(0))
    A->>L: dm.simple_layout(fig)
    L->>P: measure tick & label extents
    L-->>A: deterministic margins set
    A->>IO: dm.save_formats(fig, "out", ("png","pdf"))
    IO->>V: validate_figure(fig)
    V-->>IO: no overflow / clipping
    IO-->>A: out.png + out.pdf written
```

```{admonition} Verdict
:class: tip

**Strengths.** Six diagram types from one text directive; sequence and
state machines render well; zero install (CDN JS); themable via
`mermaid_init_js`. **Weaknesses.** Auto-layout you can't fully steer;
flowcharts with many cross-edges get tangled (that's Graphviz's job
below). **Use for:** flows, **sequences**, state machines — the 80%
case.
```

### 2. Graphviz — an auto-laid-out decision graph

Graphviz's `dot` solver is the reason to escalate: it routes a graph
with **clusters and many branches** that Mermaid's layout would
tangle. The example is the real `dm.figsize(width, aspect)` argument
contract from `CLAUDE.md` — two argument families, each with several
accepted forms, all converging on one inch-tuple.

Source: inline DOT, rendered at Sphinx build time by the `dot` binary
(CI installs it via `apt install graphviz`).

```{graphviz}
digraph figsize_contract {
    rankdir="TB";
    bgcolor="transparent";
    node [shape=box, style="rounded,filled", fillcolor="#ffffff",
          color="#cdced6", fontsize=11, margin="0.18,0.10",
          fontname="Inter, system-ui, sans-serif"];
    edge [color="#9498a3", fontsize=10, arrowsize=0.7,
          fontname="Inter, system-ui, sans-serif"];

    call [label="dm.figsize(width, aspect)", fillcolor="#eef6ff",
          color="#0d8ee8", penwidth=1.4];

    subgraph cluster_w {
        label="width — physical, never bare numbers";
        style="rounded,filled"; fillcolor="#fafafb"; color="#dfe0e6";
        fontsize=10; fontcolor="#60646c";
        w_str  [label="unit string\n'13cm' · '5in' · '170mm' · '24pt'"];
        w_len  [label="Length value\ndm.cm(13) · dm.col1 · dm.col2"];
        w_bad  [label="bare int / float\n→ TypeError", fillcolor="#fff0f0",
                color="#e5484d"];
    }

    subgraph cluster_a {
        label="aspect — four interchangeable forms";
        style="rounded,filled"; fillcolor="#fafafb"; color="#dfe0e6";
        fontsize=10; fontcolor="#60646c";
        a_tok  [label="aspect token\n'wide' · 'standard' · 'golden'"];
        a_num  [label="ratio float\n0.6"];
        a_hstr [label="height string\n'12cm'"];
        a_hlen [label="height Length\ndm.cm(12)"];
    }

    out [label="(w_inches, h_inches)\n→ plt.subplots(figsize=…)",
         fillcolor="#effaf1", color="#30a46c", penwidth=1.4];

    call -> w_str  [label="width="];
    call -> w_len;
    call -> w_bad  [color="#e5484d", style=dashed];
    call -> a_tok  [label="aspect="];
    call -> a_num;
    call -> a_hstr;
    call -> a_hlen;

    w_str  -> out;
    w_len  -> out;
    a_tok  -> out;
    a_num  -> out;
    a_hstr -> out;
    a_hlen -> out;
}
```

```{admonition} Verdict
:class: tip

**Strengths.** Best-in-class layout — clusters, ranks, and 15–100-node
graphs stay legible; deterministic; SVG is one static file, no runtime
JS. **Weaknesses.** Theming is per-node attributes only; curved edges
look stiffer than Mermaid's. **Use for:** decision graphs, dependency
graphs (see §C), call graphs — anything `dot`/`neato` is built to
solve.
```

### 3. Mingrammer Diagrams — system architecture with iconography

When the nodes are *kinds of things* — a user, a service, a store —
named icons read faster than labeled boxes. Mingrammer Diagrams builds
the graph from a Python script and renders branded glyphs through
Graphviz. The full diagram is §B; here's the same asset inline so you
can judge the aesthetic next to the others.

```{image} ../_static/diagrams/architecture_overview.svg
:alt: dartwork-mpl system architecture (Mingrammer Diagrams)
:class: dm-diag-architecture
```

```{admonition} Verdict
:class: tip

**Strengths.** Iconography is irreplaceable for cloud / service
architecture (AWS · GCP · K8s · generic glyphs); Python source means
loops and conditionals build the graph. **Weaknesses.** Graphviz
underneath (same `dot` dependency); the icon set is opinionated.
**Use for:** system overviews (§B), ML pipelines, "how it fits
together" pictures.
```

### 4. D3.js — an interactive force graph

The only library here that's *interactive*. This renders the same
module dependency data §C extracts statically, but you can **drag a
node, hover for its degree, and watch the force layout settle**. Node
radius scales with edge count, so hub modules (`config`, `asset`,
`lint`) read as bigger.

```{raw} html
<div id="dm-d3-modgraph"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="../_static/diagram_d3.js"></script>
```

```{admonition} Verdict
:class: tip

**Strengths.** Interactivity — drag, hover, degree-sized nodes; ideal
for graphs the reader should *explore* (peer networks, supply chains,
citation graphs). **Weaknesses.** Most code by far (D3 has no
high-level diagram API — you compose forces and shapes); needs a CDN
or vendored `d3.min.js`; doesn't print. **Use for:** exploration, not
static viewing.
```

---

## §B — system architecture overview

Curated picture of how a script flows through dartwork-mpl. The runtime
is a one-way pipeline (`style.use → simple_layout → save_formats`); the
design tokens are read-only (dashed); the AI layer observes but never
mutates (dotted).

```{image} ../_static/diagrams/architecture_overview.svg
:alt: dartwork-mpl system architecture — Mingrammer Diagrams
:class: dm-diag-architecture
```

Regenerate after a structural change (idempotent — a clean `git diff`
means the architecture hasn't drifted):

```bash
uv run python docs/internals/scripts/build_architecture_diagram.py
```

---

## §C — module dependency graph (auto-extracted)

`docs/internals/scripts/build_module_graph.py` walks
`src/dartwork_mpl/` with `ast`, captures every in-package import,
collapses to top-level submodule granularity, clusters by role
(API / data / support), and emits hand-formatted DOT — alphabetical
node and edge order, no timestamps, so it's byte-stable across runs.
**This is the §A.2 Graphviz example at production scale: 20 nodes,
70 edges, laid out automatically.**

```{graphviz} ../_static/diagrams/module_graph.dot
```

**Reading the layout.** Left-to-right = "depends-on flows left." Blue
API cluster (style, layout, io, …) is what users import; teal data
cluster (colors, cmap, font, asset) holds design tokens; lilac support
cluster is the agent / validation / MCP scaffolding. Edge thickness
tracks import count.

Regenerate after refactoring:

```bash
uv run python docs/internals/scripts/build_module_graph.py
```

---

## Engineering notes

- **CI installs Graphviz.** Both `ci.yml` and `docs.yml` run
  `sudo apt-get install -y graphviz` before `sphinx-build`. Local
  builds need `brew install graphviz` (macOS) / `apt install graphviz`.
- **Mermaid widths.** `conf.py → mermaid_init_js` injects a `themeCSS`
  `nowrap` rule so Mermaid *measures* each node at its full label width
  — the viewBox grows to the real content size instead of the CSS
  having to stretch a too-narrow SVG (which only blurs it). The
  `.mermaid > svg` rule then caps at `max-width: 100%` without force-
  scaling.
- **The `.dot` files are the source.** §C reads the committed `.dot` at
  build time and re-renders it with the project font, so the docs stay
  text-diff-friendly (the `.dot` is the diff target, not the SVG).
- **No `sphinxcontrib-plantuml`.** Declined: PlantUML ships a Java jar
  that adds ~80 MB to CI. The four libraries here cover its use cases
  (Graphviz for class diagrams, Mermaid for sequence).
- **Excalidraw was prototyped and dropped.** A hand-wobbled SVG looked
  charming but had no source language (every diagram authored by hand)
  and the filter blurred at the sizes we needed — not worth a slot.
