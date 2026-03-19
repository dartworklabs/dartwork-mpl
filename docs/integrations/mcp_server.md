# MCP Server

**dartwork-mpl** includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that lets AI coding assistants — such as Claude Code, Cursor, Windsurf, and any MCP-compatible client — access library documentation, style guides, and helper tools **inside the chat context**.

```{contents} On this page
:local:
:depth: 2
```

---

## What can MCP do?

When the `dartwork-mpl` MCP server is connected, your AI assistant gains access to **resources**, **tools**, and **prompts** without you having to copy-paste documentation.

### Resources

Read-only data that the AI assistant can retrieve on demand.

| URI                                       | Description                                                                 |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| `dartwork-mpl://guide/general-guide`      | Complete usage guide — styles, colors, layout, fonts, save/export, workflow |
| `dartwork-mpl://guide/layout-guide`       | Deep-dive into `simple_layout`, GridSpec strategies, and layout solutions   |
| `dartwork-mpl://palette/colors`           | Full list of registered colors with hex codes (`dc.*`, `tw.*`, `oc.*`, …)  |
| `dartwork-mpl://palette/fonts`            | Sorted list of all fonts available to matplotlib                            |
| `dartwork-mpl://styles/list`              | Available mplstyle preset names                                             |
| `dartwork-mpl://styles/{preset}`          | Content of a specific mplstyle preset file                                  |
| `dartwork-mpl://templates/list`           | Available plot template types                                               |
| `dartwork-mpl://templates/{plot_type}`    | Boilerplate Python script for a specific plot type                          |

### Tools

Callable functions the AI assistant can invoke during a conversation.

| Tool                                        | Description                                                                     |
| ------------------------------------------- | ------------------------------------------------------------------------------- |
| `fetch_github_document(url)`                | Fetch any raw file from GitHub (README, CHANGELOG, examples, etc.)              |
| `get_color_value(name)`                     | Get the hex code for a dartwork-mpl or matplotlib color name                    |
| `mix_colors(color1, color2, ratio)`         | Blend two colors and return the resulting hex code                              |
| `list_color_families()`                     | List color families (`dc.*`, `tw.*`, `oc.*`, …) with counts and samples        |
| `lint_dartwork_mpl_code(code)`              | Analyze Python code for dartwork-mpl best practices and antipatterns            |
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
   - **MCP in action:** The assistant reads the `general-guide` resource and immediately outputs correct code using `dm.subplots(style=['lang-kr'])`.

2. **Automated layout debugging**
   - **You ask:** _"I used simple_layout but my legend is overlapping the plot."_
   - **MCP in action:** The assistant reads the `layout-guide` resource, understands the library's specific constraints, and provides the exact code to fix the issue.

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

---

## Installation

### Prerequisites

- Python ≥ 3.10
- `dartwork-mpl` installed (see {doc}`/installation/index`)
- The `[mcp]` optional dependencies:

  ```bash
  # uv (recommended)
  uv pip install -e ".[mcp]"

  # pip
  pip install "dartwork-mpl[mcp]"
  ```

  This pulls in `fastmcp ≥ 2.13` and `httpx ≥ 0.27`.

### Client configuration

Every MCP-capable client has its own config format. Below are copy-paste-ready snippets for the most popular ones.

::::{tab-set}

:::{tab-item} Claude Code
:sync: claude

Add to `~/.claude.json` (global) or `<project>/.claude/mcp_servers.json`:

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

:::

:::{tab-item} Cursor / Windsurf
:sync: cursor

Add to `~/.cursor/mcp.json` (or the Windsurf equivalent):

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

:::

:::{tab-item} Antigravity (Gemini)
:sync: antigravity

Add to `~/.gemini/antigravity/mcp_config.json`:

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
      ],
      "env": {}
    }
  }
}
```

After saving the config, **restart Antigravity** (or start a new conversation) for the server to be picked up. You can verify the connection by asking the assistant to list its available MCP resources.
:::

:::{tab-item} Generic stdio
:sync: generic

Any client that supports the MCP stdio transport can launch the server directly:

```bash
uv run --directory /path/to/dartwork-mpl dartwork-mpl-mcp
```

Or via the Python module:

```bash
uv run python -m dartwork_mpl.mcp.server
```

:::

::::

> **Important:** Replace `/absolute/path/to/dartwork-mpl` with the actual path where the package source lives on your machine. If you installed `dartwork-mpl` from PyPI (once published), the `--directory` flag can be dropped and the `command` can simply be `dartwork-mpl-mcp`.

---

## Verification

After configuring your client, verify the server is reachable.

### Quick smoke test (terminal)

```bash
# Send a JSON-RPC initialize request via stdin
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' \
  | uv run dartwork-mpl-mcp
```

Expected output (key fields):

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

If you see this response, the server is working correctly. ✅

### Python import test

```python
from dartwork_mpl.mcp.server import mcp

print(mcp.name)   # → "dartwork-mpl"
print(mcp)        # FastMCP instance info
```

## Troubleshooting

| Symptom                                     | Fix                                                                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `ModuleNotFoundError: fastmcp`              | Install the MCP extras: `uv pip install -e ".[mcp]"`                                                         |
| `uv run mcp` launches the wrong CLI         | The `mcp` Python package ships its own `mcp` script. Use `dartwork-mpl-mcp` instead.                         |
| Server starts but client shows no resources | Verify the `--directory` flag points to the package root. Check your client's MCP log for connection errors. |
| `ValueError: Prompt guide not found`        | The `asset/prompt/` directory is missing. Reinstall the package or check the source tree.                    |
