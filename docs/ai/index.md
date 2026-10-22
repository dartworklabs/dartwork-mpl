---
# H3 questions in the IDE matrix shouldn't crowd the right rail.
tocdepth: 2
---

# AI & Agent-Assisted Plotting

dartwork-mpl is **built for the way Python plots are written in 2026**:
a developer types intent into Cursor / Claude Code / Zed Agent panel,
the agent calls matplotlib through dartwork-mpl, and a
figure can be created, reviewed and revised through the existing tools.
Presets and prompt resources guide that loop; generated plots still need
data checks and visual review. See the [bounded live evaluation](../integrations/agent_plot_evaluation.md)
for measured outcomes and limitations.

This page is the **hub** — the 30-second setup, the IDE compatibility
matrix, and the deep links into agent-specific guides. New to the
library? Start here, then jump to your tool.

---

## Installed Python (core package, no MCP)

Start with the [executable installed Python workflow](installed_python.md):
read bundled guidance and basic/advanced template source, preserve missing-data
gaps, lint code, validate the native Figure, save PNG/PDF, inspect the actual
images and hand off a separate-stem revision with full reports.

## 30-second setup

::::{tab-set}

:::{tab-item} Agent skill (Claude Code, Codex)
:sync: skill

The wheel ships an agent skill, the `SKILL.md` folder format Claude Code
and Codex read: a short router plus reference files on sizing, editing, colours, Korean text,
templates and the render → inspect → revise loop. Link it into the project
once; the agent loads it whenever a task involves a plot.

```bash
pip install dartwork-mpl                 # or:  uv add dartwork-mpl
python -m dartwork_mpl.skills install    # .claude/skills + .agents/skills
```

The command links `.claude/skills/dartwork-mpl` (Claude Code) and
`.agents/skills/dartwork-mpl` (Codex) to the folder inside the installed
package, so the skill always matches the installed version. `--claude` or
`--codex` installs for one agent, `--dest ~` for your user account, and
`--copy` copies instead of linking where symlinks are unavailable (rerun it
after upgrading). It never overwrites a folder it did not create unless you
pass `--force`. `python -m dartwork_mpl.skills path` prints the folder.

Claude Code also ships a general `/dataviz` skill. The dartwork-mpl skill
tells the agent how the two fit: for matplotlib figures the active preset is
the design system and the output is a static, physically sized file.
:::

:::{tab-item} MCP-native client
:sync: mcp

If your agent supports the [Model Context Protocol](https://modelcontextprotocol.io)
— Claude Code, Cursor, Windsurf, Continue, Zed Agent panel, and a
growing list of others do — the agent reads dartwork-mpl docs live,
runs the lint engine on your draft code, and looks up colors and
templates *inside the chat context*.

```bash
# 1. Install with the [mcp] extra
pip install "dartwork-mpl[mcp]"          # or:  uv add "dartwork-mpl[mcp]"

# 2. Verify the console entry point
which dartwork-mpl-mcp
```

Then drop the JSON below into your client's MCP config (paths shown
on the **[MCP Server](../integrations/mcp_server.md)** page for each
client). One restart and the agent has dartwork-mpl context.

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "dartwork-mpl-mcp"
    }
  }
}
```

→ Per-client config snippets: **[MCP Server setup](../integrations/mcp_server.md)**
:::

:::{tab-item} File-based fallback (every other agent)
:sync: file

Agents that don't speak MCP yet (Aider, GitHub Copilot Chat, plain
ChatGPT or Claude.ai) still benefit from dartwork-mpl's bundled
**LLM-readable corpus** — anti-patterns, design rules, and 18 ready-to-use
plot templates concatenated into one paste-able file.

```python
import dartwork_mpl as dm

# Resolve the bundled corpus (also accepts "AGENTS", "CLAUDE", "llms")
path = dm.agent_doc_path("llms-full")   # -> Path to the corpus file
text = dm.get_agent_doc("llms-full")    # -> its contents as a string
```

Copy that file into your IDE's AI-context location (or paste its
contents into a system prompt).

For agents that can read a local file but don't auto-detect a folder:

```bash
# Aider — read the corpus as one big system prompt
aider --read $(python -c "import dartwork_mpl; print(dartwork_mpl.agent_doc_path('llms-full'))")
```

`dm.agent_doc_path("llms-full")` (and the companion `dm.get_agent_doc("llms-full")`)
also accept ``"llms"``, ``"AGENTS"``, and ``"CLAUDE"`` so you can pipe
any of the four onboarding files into any tool that takes a file path
or a system-prompt string.

For chat-only surfaces (web ChatGPT, Claude.ai), paste the contents
of `llms.txt` (≈ 4 KB index) into a system prompt or pinned message.

→ Full instructions: **[AI-Assisted Development](../integrations/ai_assisted.md)**
:::

:::{tab-item} Zero setup
:sync: zero

Even without MCP or file installation, dartwork-mpl's
**one-right-way API** makes any agent's matplotlib output more
reliable. Names like `dm.style.use("scientific")`, `dc.teal2`,
`dm.figsize("13cm", "standard")`, and `dm.simple_layout(fig)` are
concrete patterns an agent can follow. Check the resulting code, values and
image; names alone do not guarantee identical output across conversations.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, y, color="dc.teal2")
dm.simple_layout(fig)
dm.save_formats(fig, "out", formats=("png", "pdf"))
```

→ Design rationale: **[Why AI-Ready?](../integrations/why_ai_ready.md)**
:::

::::

---

(ide-agent-compatibility-2026-q2)=
## IDE & agent compatibility (2026-Q2)

| Tool / Agent | MCP support | Recommended path | File-based fallback |
|---|---|---|---|
| **Claude Code** (Anthropic CLI / VS Code / JetBrains) | ✅ first-class | `python -m dartwork_mpl.skills install --claude`; MCP: `claude mcp add dartwork-mpl dartwork-mpl-mcp` | `.claude/skills/dartwork-mpl` (the skill) |
| **Cursor** (legacy single-file rules) | ✅ Settings → Composer → MCP | Drop JSON in `~/.cursor/mcp.json`, restart | copy `llms-full.txt` into `.cursor/` |
| **Cursor** (2026 `rules/*.mdc` format) | ✅ | — | copy `llms-full.txt` into `.cursor/rules/` |
| **Windsurf** (Cascade) | ✅ JSON config | `~/.codeium/windsurf/mcp_config.json` | copy `llms-full.txt` into `.windsurf/rules/` |
| **Continue** (VS Code / JetBrains) | ✅ `config.yaml` | `mcpServers:` block | copy `llms-full.txt` into `.continue/rules/` |
| **Zed** (Agent panel) | ✅ Settings → Agent → Tools | JSON snippet (`~/.config/zed/settings.json` → `context_servers`) | — |
| **GitHub Copilot Chat** | ✅ since 2025-Q4 (MCP preview) | VS Code → Copilot → MCP settings | copy `llms-full.txt` into `.github/copilot-instructions.md` |
| **Antigravity** (Google Gemini CLI) | ✅ JSON config | `~/.gemini/antigravity/mcp_config.json` | copy `dm.agent_doc_path("AGENTS")` into your project's `GEMINI.md` |
| **OpenAI Codex CLI** | ✅ `codex mcp add` / `~/.codex/config.toml` | `python -m dartwork_mpl.skills install --codex`; MCP: `codex mcp add dartwork-mpl -- dartwork-mpl-mcp` | `.agents/skills/dartwork-mpl` (the skill), or copy `dm.agent_doc_path("AGENTS")` into `AGENTS.md` |
| **JetBrains AI Assistant** | 🟡 partial (MCP in 2026.2 preview) | Settings → Tools → AI → MCP | — |
| **Anthropic API / SDK** (custom agents) | ✅ via `tools=` | Wire `dartwork-mpl-mcp` as a sub-process | — |
| **Aider** | ❌ | `aider --read $(python -c "import dartwork_mpl; print(dartwork_mpl.agent_doc_path('llms-full'))")` | repo-root `CONVENTIONS.md`, or `--read` the corpus |
| **ChatGPT** (web / desktop) | ❌ | Paste `llms.txt` (≈ 4 KB) into system prompt | — |
| **Claude.ai** (web) | ❌ on free tier; ✅ on Teams/Enterprise via Custom MCP | Same JSON as Claude Code | — |
| **Other LLMs** | varies | `dm.get_agent_doc("llms-full")` paste-in works for all | — |

> Updated 2026-10-22. Open a PR on this table if your tool's MCP
> support changed — it moves fast.
>
> The installed package resolves the file-based corpus with
> `dm.agent_doc_path(name)` / `dm.get_agent_doc(name)`: `"AGENTS"` and
> `"CLAUDE"` both return the short consumer entry that points to the skill,
> `"llms"` and `"llms-full"` the index and the full dump. Copy whichever
> file your tool reads into its context location. The repo-root `AGENTS.md`
> and `CLAUDE.md` are for contributors to dartwork-mpl itself.

---

## Why agents work well here

dartwork-mpl is **not an AI wrapper around matplotlib** — it is
matplotlib with the ambiguity removed. The library follows three
rules that compound into reliable AI output:

::::{grid} 1 2 2 4
:gutter: 2

:::{grid-item-card} 🎯 **One canonical call**

For every plotting task, there is one dartwork-mpl function — not
three (`tight_layout` / `constrained_layout` / `subplots_adjust`).
This gives agents a consistent starting point. Reproducibility still depends
on the generated source, inputs and execution environment.
:::

:::{grid-item-card} 🎨 **Semantic names**

Colors are `dc.teal2` and `tw.indigo600`, not `#3b82f6`. Figure
widths are `"13cm"`, not `5.118`. Agents reliably reproduce the
names; they hallucinate the numbers.
:::

:::{grid-item-card} 🔁 **Preset-relative scaling**

Font sizes, line widths, and weights go through `dm.fs(n)`,
`dm.lw(n)`, `dm.fw(n)` — relative offsets from the active style.
Swap `dm.style.use("scientific")` to `"presentation"` and every
size, weight, and stroke re-targets the new preset without an
edit.
:::

:::{grid-item-card} 🧪 **Inline validation**

`dm.validate_figure(fig)` catches overflow, asymmetric margins, and
pie-label cutoffs before the agent hands back a broken plot. The
MCP tool `validate_generated_plot(code)` runs the same check on
agent-generated snippets in an isolated subprocess and returns
structured JSON.
:::

::::

→ Long-form design rationale: **[Designed for AI Agents](../philosophy/ai_native.md)**

---

## Reviewable plot-data suggestions

Call the existing MCP tool `validate_plot_data(plot_type, data_json, report=True)`
to inspect numeric-string suggestions alongside preserved original data and a
separate candidate. The default `report=False` keeps the existing text response;
the opt-in report is JSON encoded inside the returned string and needs another
decode after the MCP envelope.

Coverage is `scatter`, `bar`, `bar_horizontal`, `histogram` and `heatmap`, limited
to their declared fields. Unknown fields stay unchanged and unvalidated; a partial
candidate can remain invalid. The caller reviews before/after and chooses data.
The tool has `effects:"none"` and never applies, renders or stores changes;
templates remain standalone Python examples.

→ [Concrete call, report example, numeric rules and limits](../integrations/mcp_server.md#reviewable-plot-data-suggestions)

## Bundled AI assets

| Asset | Use it for | Entry point |
|---|---|---|
| **Agent skill** | Claude Code / Codex load the rules on demand | `python -m dartwork_mpl.skills install` |
| **MCP server** | Live doc access + lint inside the chat | `dartwork-mpl-mcp` console script ([setup](../integrations/mcp_server.md)) |
| **Prompt corpus** (4 guides + templates) | Anti-patterns, style rules, recipes — paste-able | `dm.list_prompts()` → `["00-index", "01-policy", "02-anti-patterns", "03-recipes"]`; `dm.get_prompt("02-anti-patterns")` |
| **18 plot templates** | Drop-in patterns for bar / line / scatter / heatmap / dashboards | [AI Plot Templates gallery](../examples_gallery/09_ai_templates/index.rst) |
| **Consumer entry** | One-screen onboarding for any LLM; points to the skill | `dm.get_agent_doc("AGENTS")` |
| **`llms.txt`** | Lightweight index (≈ 4 KB) — fits in any system prompt | Repo root, `dm.get_agent_doc("llms")` |
| **`llms-full.txt`** | Concatenated full reference (≈ 76 KB) — for tools that read whole files | Repo root, `dm.get_agent_doc("llms-full")` |

---

## Agent intent → top-level call

For agents that import `dartwork_mpl as dm` directly: every high-value
composition helper is reachable as `dm.<name>`.

| If the agent intends to… | Call |
|---|---|
| Verify input data shape before plotting | `dm.validate_data(...)` |
| Pick a chart type from a data description | `dm.suggest_chart_type(...)` |
| Get a curated palette for N data series | `dm.make_palette(n, kind=...)` |
| Label bar tops with their values | `ax.bar_label(bars, ...)` (matplotlib 3.4+) |
| Place the legend without overlapping data | `dm.optimize_legend(ax, ...)` |
| Run heuristic quality checks on a figure | `dm.check_figure_quality(fig)` |
| Save with hi-res presets in multiple formats | `dm.save_formats(fig, "out")` |
| Lint generated code before returning it | `dm.lint_code(code)` (Python) or `lint_dartwork_mpl_code(code)` (MCP) |

---

## Deep dives

```{toctree}
:maxdepth: 1
:titlesonly:

Installed Python workflow <installed_python>
Why AI-Ready? <../integrations/why_ai_ready>
AI-Assisted Development <../integrations/ai_assisted>
MCP Server <../integrations/mcp_server>
Agent Plot Evaluation <../integrations/agent_plot_evaluation>
Designed for AI Agents (philosophy) <../philosophy/ai_native>
AI Plot Templates (gallery) <../examples_gallery/09_ai_templates/index>
```
