# MCP Server

**dartwork-mpl** includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that lets AI coding assistants — such as Claude Code, Cursor, Windsurf, and any MCP-compatible client — access library documentation, style guides, and helper tools **inside the chat context**.

```{contents} On this page
:local:
:depth: 2
```

---

## What can MCP do?

When the `dartwork-mpl` MCP server is connected, your AI assistant gains access to the following **resources** and **tools** without you having to copy-paste documentation:

### Resources

| URI                                  | Description                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| `dartwork-mpl://guide/general-guide` | Complete usage guide — styles, colors, layout, fonts, save/export, workflow, and full examples.                                 |
| `dartwork-mpl://guide/layout-guide`  | Deep-dive into `simple_layout`, GridSpec strategies, hardcoded-element conflicts, and combined-layout solutions (1 100+ lines). |

These are read-only text resources that the AI assistant can retrieve on demand. They contain the same content as the Markdown files under `dartwork_mpl/asset/prompt/`.

### Tools

| Tool                         | Description                                                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `fetch_github_document(url)` | Fetch any raw file from GitHub. Useful for pulling the latest README, CHANGELOG, or example scripts from the dartwork-mpl repo at runtime. |

### Practical use-cases

Here are specific examples of how an AI assistant behaves differently when the `dartwork-mpl` MCP server is connected:

1. **Zero-shot accurate coding**
   - **You ask:** _"I need a bar chart for a Korean investment report. How do I set the style using dartwork-mpl?"_
   - **MCP in action:** The assistant reads the `general-guide` resource and immediately outputs:

     ```python
     import dartwork_mpl as dm
     dm.style.use('investment-kr')
     ```

2. **Automated layout debugging**
   - **You ask:** _"I used simple_layout but my legend is overlapping the plot. Fix it using bbox techniques."_
   - **MCP in action:** The assistant reads the `layout-guide` resource, understands the library's specific constraints regarding hardcoded `bbox_to_anchor`, and provides the exact code to move the legend cleanly using the prescribed methods.

3. **Style and Color lookup without browsing docs**
   - **You ask:** _"Give me the hex codes for the 'warm' OC color palette for a pie chart."_
   - **MCP in action:** The assistant extracts the exact hex codes from the color section of the built-in guide without guessing or hallucinating standard hex values.

4. **Pulling remote examples**
   - **You ask:** _"Can you check the dartwork-mpl GitHub repo for the latest example of a waterfall chart and adapt it for my code?"_
   - **MCP in action:** Using the `fetch_github_document` tool, the assistant downloads the raw file directly from GitHub and writes the adapted code for you.

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
      "tools": { "listChanged": true }
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

### Unit tests

```bash
uv run pytest tests/test_mcp.py -v
```

All 7 tests should pass:

```text
tests/test_mcp.py::TestMcpServer::test_mcp_instance_is_fastmcp      PASSED
tests/test_mcp.py::TestMcpServer::test_mcp_server_name               PASSED
tests/test_mcp.py::TestMcpResources::test_register_resources_no_error PASSED
tests/test_mcp.py::TestMcpResources::test_register_resources_calls_resource_decorator PASSED
tests/test_mcp.py::TestMcpTools::test_register_tools_no_error         PASSED
tests/test_mcp.py::TestMcpTools::test_register_tools_calls_tool_decorator PASSED
tests/test_mcp.py::TestMcpPackage::test_mcp_package_exports           PASSED
```

---

## Architecture

```text
dartwork_mpl/
├── mcp/
│   ├── __init__.py      # Exports the ``mcp`` FastMCP instance
│   ├── server.py        # Creates + wires the FastMCP server
│   ├── resources.py     # Registers guide resources
│   └── tools.py         # Registers helper tools
├── cli.py               # ``dartwork-mpl-mcp`` entry point
└── asset/prompt/
    ├── general-guide.md  # General usage guide (~390 lines)
    └── layout-guide.md   # Layout deep-dive (~1 150 lines)
```

- **server.py** instantiates `FastMCP("dartwork-mpl")` and calls `register_resources()` / `register_tools()`.
- **resources.py** reads bundled Markdown guides via `dartwork_mpl.prompt.get_prompt()` and exposes them as MCP resources under the `dartwork-mpl://guide/` URI scheme.
- **tools.py** registers callable tools (currently `fetch_github_document`).
- **cli.py** simply calls `mcp.run()` — used by the `dartwork-mpl-mcp` console script.

---

## Troubleshooting

| Symptom                                     | Fix                                                                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `ModuleNotFoundError: fastmcp`              | Install the MCP extras: `uv pip install -e ".[mcp]"`                                                         |
| `uv run mcp` launches the wrong CLI         | The `mcp` Python package ships its own `mcp` script. Use `dartwork-mpl-mcp` instead.                         |
| Server starts but client shows no resources | Verify the `--directory` flag points to the package root. Check your client's MCP log for connection errors. |
| `ValueError: Prompt guide not found`        | The `asset/prompt/` directory is missing. Reinstall the package or check the source tree.                    |
