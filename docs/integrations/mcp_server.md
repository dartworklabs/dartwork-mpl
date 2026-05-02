# MCP Server

**dartwork-mpl** includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that lets AI coding assistants — such as Claude Code, Cursor, Windsurf, and any MCP-compatible client — access library documentation, style guides, and helper tools **inside the chat context**.

```{contents} On this page
:local:
:depth: 2
```

---

## Quick setup

A typical install-and-wire-up takes under a minute. The flow is:

1. Install `dartwork-mpl` with the `[mcp]` extra.
2. Drop a small JSON config into your AI client.
3. Restart the client (or start a fresh chat).

### 1. Install the package with MCP extras

The `[mcp]` extra pulls in `fastmcp` (>=2.13.3,<4) and `httpx`. After install, the
console script `dartwork-mpl-mcp` is on your `PATH`.

```bash
# pip
pip install "dartwork-mpl[mcp]"

# uv (project-scoped)
uv add "dartwork-mpl[mcp]"

# uv pip (env-scoped)
uv pip install "dartwork-mpl[mcp]"
```

Confirm the entry point is wired up:

```bash
which dartwork-mpl-mcp
# → /…/site-packages/bin/dartwork-mpl-mcp  (or similar)
```

### 2. Configure your AI client

::::{tab-set}

:::{tab-item} Claude Code
:sync: claude

Add to `~/.claude.json` (global) **or** `<project>/.claude/mcp_servers.json`
(per-project; takes precedence for that workspace):

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "dartwork-mpl-mcp"
    }
  }
}
```

That's the entire config when `dartwork-mpl-mcp` is on `PATH`. If you want
to pin to a specific virtualenv, use the absolute path to the script:

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "/abs/path/to/.venv/bin/dartwork-mpl-mcp"
    }
  }
}
```

:::

:::{tab-item} Cursor
:sync: cursor

Add to `~/.cursor/mcp.json` (global) **or** `<project>/.cursor/mcp.json`
(per-project):

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "dartwork-mpl-mcp"
    }
  }
}
```

:::

:::{tab-item} Windsurf
:sync: windsurf

Windsurf uses the same JSON shape as Cursor. Add to
`~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "dartwork-mpl-mcp"
    }
  }
}
```

:::

:::{tab-item} Antigravity (Gemini)
:sync: antigravity

Add to `~/.gemini/antigravity/mcp_config.json`:

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "dartwork-mpl-mcp",
      "env": {}
    }
  }
}
```

:::

:::{tab-item} Local clone (no PyPI)
:sync: clone

If you are hacking on `dartwork-mpl` from a checkout instead of installing
from PyPI, run the entry point through `uv run --directory`:

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/dartwork-mpl",
        "dartwork-mpl-mcp"
      ]
    }
  }
}
```

This works for every client above — only the file location of the JSON
changes.

:::

:::{tab-item} Generic stdio
:sync: generic

Any client that speaks the MCP stdio transport can launch the server
directly:

```bash
dartwork-mpl-mcp
# or, when working from a checkout:
uv run --directory /path/to/dartwork-mpl dartwork-mpl-mcp
# or via the module:
python -m dartwork_mpl.mcp.server
```

:::

::::

### 3. Restart the client

Most clients only re-read MCP config on startup. Quit and relaunch (or start a fresh chat) before running the verification steps below.

---

## Verify the setup

Once configured, you should be able to confirm the server from inside your client **and** from the terminal.

### Inside the client

Ask the assistant something only the server can answer, for example:

- _"List the MCP resources you can read from `dartwork-mpl`."_ → it should mention `dartwork-mpl://guide/agent-entry`, `…/policy`, palette/style URIs, etc.
- _"Use the `dartwork-mpl` MCP server to give me the hex code for `oc.blue5`."_ → triggers `get_color_value`.

If the assistant says it has no MCP server named `dartwork-mpl`, see [Troubleshooting](#troubleshooting).

#### Claude Code specifics

Claude Code exposes connected MCP servers in its UI and in chat metadata. After a successful connection you should see `dartwork-mpl` listed as an available MCP server in the session header.

#### Cursor specifics

Cursor surfaces MCP servers under **Settings → Cursor Settings → MCP**. The entry should show a green "connected" indicator.

### From the terminal (smoke test)

You can hand-roll an `initialize` JSON-RPC request to the server over stdio:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' \
  | dartwork-mpl-mcp
```

Expected response (key fields):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "resources": { "subscribe": false, "listChanged": false },
      "tools": { "listChanged": true },
      "prompts": { "listChanged": false }
    },
    "serverInfo": { "name": "dartwork-mpl", "version": "..." }
  }
}
```

### From Python

```python
from dartwork_mpl.mcp.server import mcp

print(mcp.name)   # → "dartwork-mpl"
print(mcp)        # FastMCP instance info
```

---

## First use

Now that the server is reachable, here are the highest-value calls to try first. Each one is a tiny smoke test that also doubles as a useful real-world action.

1. **Pull the agent entry point.** Ask the assistant to fetch the `dartwork-mpl://guide/agent-entry` resource. This is the 0.4 SSOT decision tree — once it is in context, the assistant will write 0.4-compliant code (width/aspect, no `figsize`, etc.) by default.

2. **Lint a code snippet.** Paste a small matplotlib script and ask:

   > _"Use the `lint_dartwork_mpl_code` MCP tool on this snippet."_

   You should get back a structured list of antipatterns (`figsize=`, `tight_layout()`, raw hex colors, …) with suggested fixes.

3. **Resolve a color.** Ask:

   > _"What's the hex for `tw.emerald500`? Use the `get_color_value` MCP tool."_

   The tool round-trips through the live palette registry — no guessing or hallucinated hex codes.

4. **Generate a plot from a description.** Try the `create_plot` prompt:

   > _"Use the `create_plot` MCP prompt: a tornado chart comparing energy savings across five buildings, Korean labels."_

   The prompt steers the assistant to read the relevant template, palette, and policy resources before emitting code.

If all four work, the integration is fully operational.

---

## Troubleshooting

| Symptom                                                | Likely cause                                                                                  | Fix                                                                                                                                       |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `command not found: dartwork-mpl-mcp`                  | The `[mcp]` extra wasn't installed, or the venv that has it isn't on `PATH`.                  | Reinstall with the extra (`pip install "dartwork-mpl[mcp]"`) and/or use the absolute venv path in the JSON config.                        |
| `ModuleNotFoundError: fastmcp`                         | `dartwork-mpl` was installed, but without the `[mcp]` extra.                                  | `pip install "dartwork-mpl[mcp]"` (or `uv pip install -e ".[mcp]"` for an editable checkout).                                             |
| Server starts but client shows no resources / tools    | Client picked up an older config, or `--directory` points at the wrong checkout.              | Restart the client. Double-check the absolute path. Inspect the client's MCP log for connection errors.                                   |
| `uv run mcp …` launches the wrong CLI                  | The unrelated `mcp` PyPI package ships its own `mcp` console script that takes precedence.    | Always invoke `dartwork-mpl-mcp` (not `mcp`) in your config.                                                                               |
| `ValueError: Prompt guide not found`                   | The bundled `asset/prompt/` tree is missing (e.g., a partial install or stripped package).    | Reinstall the package; verify `dartwork_mpl/asset/prompt/` exists in your `site-packages`.                                                |
| `fastmcp` import errors after upgrading                | A breaking `fastmcp` major release. dartwork-mpl is pinned to `>=2.13.3,<4`.                  | Pin `fastmcp<4` in your environment (or reinstall the `[mcp]` extra so the constraint is re-applied).                                     |
| Works in terminal but not in the client                | The client launches the command in a different shell / `PATH` than your interactive terminal. | Use the absolute path to `dartwork-mpl-mcp` (e.g., `/Users/you/.venv/bin/dartwork-mpl-mcp`) in the JSON, or wire it via `uv run` instead. |

---

## What can MCP do?

When the `dartwork-mpl` MCP server is connected, your AI assistant gains access to **resources**, **tools**, and **prompts** without you having to copy-paste documentation.

### Resources

Read-only data that the AI assistant can retrieve on demand.

| URI                                       | Description                                                                 |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| `dartwork-mpl://guide/agent-entry`        | 0.4 entry point — decision tree + always-true facts (start here)            |
| `dartwork-mpl://guide/policy`             | 0.4 policy: width, aspect, layout, color, font, save                        |
| `dartwork-mpl://guide/anti-patterns`      | Machine-readable lint catalog (the lint engine source)                      |
| `dartwork-mpl://guide/recipes`            | Intent → function-call cookbook (per plot type)                             |
| `dartwork-mpl://api/index`                | List of public dartwork-mpl callables (from `__all__`)                      |
| `dartwork-mpl://api/{name}`               | Signature + first paragraph of docstring for a given public name            |
| `dartwork-mpl://palette/colors`           | Full list of registered colors with hex codes (`dc.*`, `tw.*`, `oc.*`, …)  |
| `dartwork-mpl://palette/fonts`            | Sorted list of all fonts available to matplotlib                            |
| `dartwork-mpl://styles/list`              | Available mplstyle preset names                                             |
| `dartwork-mpl://styles/{preset}`          | Content of a specific mplstyle preset file                                  |
| `dartwork-mpl://templates/list`           | Available plot template types                                               |
| `dartwork-mpl://templates/{plot_type}`    | Boilerplate Python script for a specific plot type                          |
| `dartwork-mpl://guide/general-guide`      | _Deprecated alias_ for `guide/agent-entry` (kept for 0.3 clients)           |
| `dartwork-mpl://guide/layout-guide`       | _Deprecated alias_ for `guide/policy` (kept for 0.3 clients)                |

### Tools

Callable functions the AI assistant can invoke during a conversation.

| Tool                                        | Description                                                                     |
| ------------------------------------------- | ------------------------------------------------------------------------------- |
| `fetch_github_document(url)`                | Fetch any raw file from GitHub (README, CHANGELOG, examples, etc.)              |
| `get_color_value(name)`                     | Get the hex code for a dartwork-mpl or matplotlib color name                    |
| `mix_colors(color1, color2, ratio)`         | Blend two colors and return the resulting hex code                              |
| `list_color_families()`                     | List color families (`dc.*`, `tw.*`, `oc.*`, …) with counts and samples        |
| `lint_dartwork_mpl_code(code)`              | Analyze Python code for dartwork-mpl best practices and antipatterns            |
| `lint_dartwork_mpl_code_json(code)`         | Same as above, returning structured JSON for programmatic consumption           |
| `migrate_legacy_code(code)`                 | Rewrite 0.3-era source toward 0.4 idioms (safe substitutions + TODO hints)      |
| `validate_plot_data(plot_type, data_json)`  | Validate whether a data structure matches a plot type's requirements            |
| `dartwork_mpl_info()`                       | Get a structured summary of all capabilities, presets, and templates            |

### Prompts

Interactive prompt templates that guide the AI through multi-step tasks.

| Prompt                              | Description                                                                 |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `create_plot(description, data)`    | Generate a complete dartwork-mpl script from a natural language description  |
| `style_review(code)`               | Review and fix a script for dartwork-mpl style compliance                   |

### Practical use-cases

Here are specific examples of how an AI assistant behaves differently when the `dartwork-mpl` MCP server is connected:

1. **Zero-shot accurate coding**
   - **You ask:** _"I need a bar chart for a Korean research paper."_
   - **MCP in action:** The assistant reads the `agent-entry` resource and immediately outputs correct code using `dm.subplots(style=['lang-kr'])`.

2. **Automated layout debugging**
   - **You ask:** _"I used simple_layout but my legend is overlapping the plot."_
   - **MCP in action:** The assistant reads the `policy` resource, understands the library's specific constraints, and provides the exact code to fix the issue.

3. **Live color lookup**
   - **You ask:** _"What's the hex code for dc.blue500?"_
   - **MCP in action:** The assistant calls `get_color_value("dc.blue500")` and returns the exact hex code — no guessing.

4. **Code quality check**
   - **You ask:** _"Review my plotting script for dartwork-mpl best practices."_
   - **MCP in action:** The assistant uses the `lint_dartwork_mpl_code` tool to check for antipatterns (e.g., `figsize=`, `tight_layout()`, `plt.subplots()`) and suggests fixes.

5. **Guided plot creation**
   - **You ask:** _"Create a tornado chart comparing energy savings."_
   - **MCP in action:** The assistant uses the `create_plot` prompt with the `tornado` template from `dartwork-mpl://templates/tornado` to generate a complete, standards-compliant script.

6. **Data validation before plotting**
   - **You ask:** _"Plot this data as a heatmap."_
   - **MCP in action:** The assistant calls `validate_plot_data("heatmap", ...)` to verify the data structure is correct before generating the plot code.
