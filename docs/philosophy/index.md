# Design Philosophy

Our goal is simple: matplotlib knowledge combined with minimal dartwork-mpl familiarity should be enough to create publication-quality visualizations with efficient AI assistance.

dartwork-mpl takes a fundamentally different approach from typical visualization libraries. Instead of wrapping matplotlib with a new API layer, we provide **thin utilities** that enhance matplotlib's native capabilities while keeping you in full control.

Explore the three core pillars of our design philosophy:

```{toctree}
:maxdepth: 1
:titlesonly:

Utilities, Not Wrappers <utilities_not_wrappers>
Designed for AI Agents <ai_native>
Ownable & Transparent Code <ownable_code>
```

## AI integration in practice

The philosophy above translates into concrete integration paths — an MCP
server, prompt-corpus resources, lint and validation helpers, and pre-built
plot templates. See the dedicated section:

```{toctree}
:maxdepth: 1
:titlesonly:

AI Integration <../integrations/index>
```
