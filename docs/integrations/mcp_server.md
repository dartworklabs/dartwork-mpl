# MCP Server

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

> Part of [AI & Agent-Assisted Plotting](../ai/index.md) — the hub covering the
> 30-second setup, IDE compatibility matrix, prompt corpus, and plot templates.

**dartwork-mpl** includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that lets AI coding assistants — such as Claude Code, Cursor, Windsurf, and any MCP-compatible client — access library documentation, style guides, and helper tools **inside the chat context**.

For the measured CSV → render → image/report review → style revision → fresh
retrieval loop, see [Agent Plot Evaluation](agent_plot_evaluation.md). It separates
stored delivery, declared validation, independent data/visual checks and model
review, with retained commands and known limitations.

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

The `[mcp]` extra pulls in FastMCP 2.14.7+ or patched 3.x below 4, excluding
3.0–3.4.9, plus HTTPX and the patched MCP SDK (>=1.30,<2). FastMCP 2.13.3's
older SDK pin cannot satisfy these security requirements. After install, the
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

That's the entire config when `dartwork-mpl-mcp` is on `PATH`. Prefer the
CLI? Running `claude mcp add dartwork-mpl dartwork-mpl-mcp` writes exactly
this config for you. If you want to pin to a specific virtualenv, use the
absolute path to the script:

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
        "--extra",
        "mcp",
        "dartwork-mpl-mcp"
      ]
    }
  }
}
```

> `--extra mcp` pulls in `fastmcp`/`httpx` from the optional `[mcp]`
> dependency set. Without it, `dartwork-mpl-mcp` exits early with a
> `ModuleNotFoundError: fastmcp` even though the directory is correct.

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
uv run --directory /path/to/dartwork-mpl --extra mcp dartwork-mpl-mcp
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

- _"List the tools of the `dartwork-mpl` MCP server."_ → `guide`, `search_reference`, `get_reference`, `lint`, `render`.
- _"Use the `dartwork-mpl` MCP server to give me the hex code for `dc.teal2`."_ → triggers `get_reference(kind="color", id="dc.teal2")`.

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
    "capabilities": { "tools": { "listChanged": true }, "...": {} },
    "serverInfo": { "name": "dartwork-mpl", "version": "..." }
  }
}
```

### From Python

```python
from dartwork_mpl.mcp.server import server

print(server.name)   # → "dartwork-mpl"
```

---

## First use

Now that the server is reachable, here are the highest-value calls to try first. Each one is a tiny smoke test that also doubles as a useful real-world action.

1. **Read the rules.** Ask the assistant to call `guide()`. It returns the
   bundled skill (presets by purpose, sizing, layout, saving, data rules, the
   review loop) and the list of topics `guide(topic)` reads.

2. **Find a starting point.** _"Use `search_reference` for a grouped bar
   chart, then `get_reference` for the top hit."_ You get the template's
   runnable source.

3. **Lint a code snippet.** _"Run the `lint` tool on this snippet."_ You get
   each anti-pattern (`figsize=(w, h)`, `tight_layout()`, unknown colour
   names, …) with its line and fix. Nothing is executed.

4. **Render it.** _"Render that script with the `render` tool."_ You get the
   PNG inline plus the check report, and a bundle directory on disk.

If all four work, the integration is fully operational.

---

## Troubleshooting

| Symptom                                                | Likely cause                                                                                  | Fix                                                                                                                                       |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `command not found: dartwork-mpl-mcp`                  | The `[mcp]` extra wasn't installed, or the venv that has it isn't on `PATH`.                  | Reinstall with the extra (`pip install "dartwork-mpl[mcp]"`) and/or use the absolute venv path in the JSON config.                        |
| `ModuleNotFoundError: fastmcp`                         | `dartwork-mpl` was installed, but without the `[mcp]` extra.                                  | `pip install "dartwork-mpl[mcp]"` (or `uv add "dartwork-mpl[mcp]"`). From a local checkout: `uv pip install -e ".[mcp]"`.                  |
| Server starts but client shows no tools                | Client picked up an older config, or `--directory` points at the wrong checkout.              | Restart the client. Double-check the absolute path. Inspect the client's MCP log for connection errors.                                   |
| `uv run mcp …` launches the wrong CLI                  | The unrelated `mcp` PyPI package ships its own `mcp` console script that takes precedence.    | Always invoke `dartwork-mpl-mcp` (not `mcp`) in your config.                                                                               |
| `fastmcp` import errors after upgrading                | An unsupported FastMCP/SDK combination: 2.13.3 requires an older SDK, and 3.0–3.4.9 are excluded. | Reinstall the `[mcp]` extra to resolve FastMCP 2.14.7+ or patched 3.x below 4 with MCP SDK >=1.30,<2.                                      |
| Works in terminal but not in the client                | The client launches the command in a different shell / `PATH` than your interactive terminal. | Use the absolute path to `dartwork-mpl-mcp` (e.g., `/Users/you/.venv/bin/dartwork-mpl-mcp`) in the JSON, or wire it via `uv run` instead. |

---

## Tools

The server exposes exactly five tools over stdio, and no resources or
prompts. Search a reference, get it, read the guidance, render, check:

| Tool | Arguments | Returns |
|---|---|---|
| `guide` | `topic?` | No topic: the bundled skill with the topic list. A topic (`layout`, `colors`, `editing`, `korean`, `recipes`, `review`, `anti-patterns`): that page. |
| `search_reference` | `query`, `kind?` | Ranked hits `{kind, id, summary}`, at most five per kind. `kind` is `template`, `preset`, `color` or `rule`. |
| `get_reference` | `kind`, `id` | A template's source (`bar_grouped`, `advanced/bar_grouped`); a preset's style stack and rcParams; a colour family's designed steps (`dc.teal`) or one colour's hex (`dc.teal4`); a lint rule's message and fix. |
| `lint` | `code` | Anti-pattern findings `{rule_id, severity, line, message, fix}`. Executes nothing. |
| `render` | `code`, `figure_var="fig"`, `timeout=20`, `out_dir?`, `inputs?` | The PNG as image content plus `{out_dir, report, manifest, source}`. |

### `render` and the bundle

`render` lints first (a critical finding stops the run), then runs the code
once in a fresh Python process and saves the figure bound to `figure_var`
(else pyplot's current figure, with a note) through `dm.save_formats`. It
writes into `out_dir` (default: a new temporary directory):

| File | Contents |
|---|---|
| `figure.png`, `figure.pdf` | The figure, when the run rendered |
| `source.py` | The exact source that ran |
| `report.json` | `status` (`rendered`, `lint_blocked`, `no_figure`, `raised`, `timed_out`, `crashed`), the figure check's `findings`, `notes`, `lint`, the first 64 KiB of `stdout`/`stderr`, the rlimits that took |
| `manifest.json` | Schema `dartwork-mpl.bundle` version 1: `status`, `created`, `seconds`, `versions`, `files` and `inputs` as `{path, sha256, bytes}`, `canvas` (inches and pixels) |

`inputs` lists data files the code reads (absolute paths); they are hashed
into the manifest, never copied. There is no artifact id, store or expiry:
the directory is the hand-off.

```{warning}
`render` is **not a sandbox**. The code runs with the server user's rights.
What it gets: an empty temporary working directory, an allow-listed
environment (no API keys or tokens are passed on), the Agg backend, its own
process group killed whole on timeout (at most 120 s), CPU, address-space and
file-size rlimits where the OS enforces them, and a 256 KiB source limit.
Run only code you would run yourself, and keep the transport on stdio.
```
