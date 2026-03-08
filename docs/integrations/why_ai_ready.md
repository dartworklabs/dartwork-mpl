# Why AI-Ready?

dartwork-mpl is designed from the ground up to work **with** AI coding assistants, not just alongside them. This page explains the specific design decisions that make AI-assisted plotting dramatically more reliable.

```{contents} On this page
:local:
:depth: 2
```

---

## The Problem with Raw matplotlib

When an AI assistant generates matplotlib code from scratch, it faces several challenges:

- **Hundreds of API choices** — `tight_layout` vs `constrained_layout` vs manual `subplots_adjust`? AI picks inconsistently.
- **Magic hex codes** — `color='#1f77b4'` is impossible to reason about. Did the AI hallucinate that value?
- **Layout fragility** — Code that looks fine in `plt.show()` breaks when saved to file at publication DPI.
- **No self-verification** — The AI generates code, you run it, and discover clipped labels only after visual inspection.

dartwork-mpl solves each of these problems with a deliberately AI-friendly API surface.

---

## 1. One Right Way to Do Things

The most common source of AI errors is **ambiguity**. When there are multiple ways to achieve the same result, LLMs pick different approaches across conversations — leading to inconsistent, often broken output.

dartwork-mpl eliminates ambiguity by providing **one canonical function** for each task:

| Task | Raw matplotlib (many ways) | dartwork-mpl (one way) |
| --- | --- | --- |
| Apply a style | `plt.style.use()`, `rcParams`, `with plt.style.context()` | `dm.style.use('scientific')` |
| Set layout | `tight_layout()`, `constrained_layout`, `subplots_adjust()` | `dm.simple_layout(fig)` |
| Save figures | `savefig()` with many kwargs | `dm.save_formats(fig, path)` |
| Preview in notebook | `plt.show()` | `dm.save_and_show(fig)` |
| Set font size | `fontsize=12`, `fontsize='large'` | `fontsize=dm.fs(2)` |

When AI assistants see this predictable, narrow API, they produce correct code **on the first try** — no iteration needed.

```python
# AI can reliably produce this pattern every time
import dartwork_mpl as dm

dm.style.use('scientific')
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)
ax.plot(x, y, color='oc.blue5', linewidth=0.7)
dm.simple_layout(fig)
dm.save_and_show(fig)
```

---

## 2. Semantic Color Names

AI assistants are terrible at remembering hex codes. Ask for "a nice blue" and you'll get a different `#hex` every time.

dartwork-mpl solves this with **human-readable, deterministic color names**:

```python
# AI can describe these naturally
ax.plot(x, y1, color='oc.red5')       # Open Color red, weight 5
ax.plot(x, y2, color='tw.blue:500')   # Tailwind blue 500
ax.fill_between(x, y1, y2, color='oc.gray2', alpha=0.3)

# Compare with raw matplotlib
ax.plot(x, y1, color='#e03131')       # What color is this? 🤷
ax.plot(x, y2, color='#3b82f6')       # AI might hallucinate this
```

The AI can say *"change the color to `oc.green6`"* and both the human and the code understand exactly what that means. No guessing, no hallucination.

---

## 3. Built-in Knowledge Base

Most plotting libraries rely on external documentation that AI assistants may not have access to, or may have outdated versions of. dartwork-mpl bundles its own knowledge base **inside the package**:

```python
import dartwork_mpl as dm

# See what guides are available
dm.list_prompts()
# ['general-guide', 'layout-guide']

# Read a guide programmatically
content = dm.get_prompt('general-guide')

# Copy a guide to your project
dm.copy_prompt('layout-guide', './docs/')
```

This means AI assistants can **read the official documentation at runtime** — even in air-gapped environments or when web search is unavailable.

---

## 4. Automatic Validation

AI-generated plots often have subtle issues that are invisible in text-only environments: clipped labels, overlapping legends, missing tick marks. dartwork-mpl includes a validation pipeline that catches these automatically:

```python
# After creating your figure
issues = dm.validate_figure(fig)

# Returns a list of detected problems:
# - Clipped text outside figure bounds
# - Overlapping elements
# - Missing labels or titles
# - Inconsistent font sizes
```

This is especially powerful in **autonomous AI pipelines** where there's no human to visually inspect every plot. The validation step acts as a quality gate.

---

## 5. MCP Protocol: Real-Time AI Access

The **Model Context Protocol (MCP)** is the most advanced integration layer. Instead of relying on training data or static files, dartwork-mpl ships a built-in MCP server that gives AI assistants **live access** to:

| Resource | What the AI gets |
| --- | --- |
| `dartwork-mpl://guide/general-guide` | Complete usage guide — styles, colors, layout, fonts, save/export |
| `dartwork-mpl://guide/layout-guide` | Deep-dive into `simple_layout`, GridSpec strategies, edge cases |
| `fetch_github_document(url)` | Any raw file from the dartwork-mpl GitHub repo, on demand |

This means the AI assistant always has **the latest, most accurate documentation** — no copy-paste, no stale caches, no hallucinated APIs.

→ For setup instructions, see **[MCP Server](mcp_server.md)**.

---

## Putting It All Together

Here's what an AI-assisted workflow looks like with dartwork-mpl:

```
┌─────────────────────────────────────────────────────┐
│  You say: "Plot the signal response with a red line │
│  and save it as SVG for my paper."                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  AI reads dartwork-mpl guide via MCP                │
│  → Knows to use dm.style.use('scientific')          │
│  → Knows to use dm.simple_layout(), not tight_layout│
│  → Knows color syntax: 'oc.red5'                    │
│  → Knows to save with dm.save_formats()             │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  AI generates correct code on first attempt         │
│  → dm.validate_figure() confirms no issues          │
│  → Paper-ready SVG saved                            │
└─────────────────────────────────────────────────────┘
```

No iteration. No debugging. No "sorry, let me try again."

→ Ready to set this up? See **[AI-Assisted Development](ai_assisted.md)** for the workflow guide, or jump straight to **[MCP Server](mcp_server.md)** for configuration.
