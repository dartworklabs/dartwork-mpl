# MCP Server

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

> Part of [AI & Agent-Assisted Plotting](../ai/index.md) — the hub covering the
> 30-second setup, IDE compatibility matrix, prompt corpus, and plot templates.

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
- _"Use the `dartwork-mpl` MCP server to give me the hex code for `dc.teal2`."_ → triggers `get_color_value`.

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

1. **Pull the agent entry point.** Ask the assistant to fetch the `dartwork-mpl://guide/agent-entry` resource. This is the SSOT decision tree — once it is in context, the assistant will write standards-compliant code (`dm.figsize(width, aspect)`, `simple_layout`, named colors, etc.) by default.

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
| `ModuleNotFoundError: fastmcp`                         | `dartwork-mpl` was installed, but without the `[mcp]` extra.                                  | `pip install "dartwork-mpl[mcp]"` (or `uv add "dartwork-mpl[mcp]"`). From a local checkout: `uv pip install -e ".[mcp]"`.                  |
| Server starts but client shows no resources / tools    | Client picked up an older config, or `--directory` points at the wrong checkout.              | Restart the client. Double-check the absolute path. Inspect the client's MCP log for connection errors.                                   |
| `uv run mcp …` launches the wrong CLI                  | The unrelated `mcp` PyPI package ships its own `mcp` console script that takes precedence.    | Always invoke `dartwork-mpl-mcp` (not `mcp`) in your config.                                                                               |
| `ValueError: Prompt guide not found`                   | The bundled `asset/prompt/` tree is missing (e.g., a partial install or stripped package).    | Reinstall the package; verify `dartwork_mpl/asset/prompt/` exists in your `site-packages`.                                                |
| `fastmcp` import errors after upgrading                | A breaking `fastmcp` major release. dartwork-mpl is pinned to `>=2.13.3,<4`.                  | Pin `fastmcp<4` in your environment (or reinstall the `[mcp]` extra so the constraint is re-applied).                                     |
| Works in terminal but not in the client                | The client launches the command in a different shell / `PATH` than your interactive terminal. | Use the absolute path to `dartwork-mpl-mcp` (e.g., `/Users/you/.venv/bin/dartwork-mpl-mcp`) in the JSON, or wire it via `uv run` instead. |

---

## What can MCP do?

When the `dartwork-mpl` MCP server is connected, your AI assistant gains access to **resources**, **tools**, and **prompts** without you having to copy-paste documentation.

The current public inventory is **18 tools, 10 static resources, 9 resource
templates, and 2 prompts**. Artifact delivery adds two tools and five templates;
existing endpoints retain their names and schemas. In the current color model,
`dc.*` construction uses OKLab L, OKLCH C/h, and ΔEOK. The modeled-relative-Y compatibility lock is an
optional constraint for shipped exact-output compatibility and topology, not
a second authoring space. CIELAB/CIEDE2000 and CVD are model-specific
validation diagnostics; WCAG contrast luminance is a separate pairwise text
contrast metric. A direct OKLCH rule without that output lock is appropriate
only for a new, intentionally incompatible palette whose exact catalog
contract may change.

### Resources

Read-only data that the AI assistant can retrieve on demand.

| URI                                       | Description                                                                 |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| `dartwork-mpl://guide/agent-entry`        | Agent entry point — decision tree + always-true facts (start here)          |
| `dartwork-mpl://guide/policy`             | Policy: width, aspect, layout, color, font, save                            |
| `dartwork-mpl://guide/anti-patterns`      | Machine-readable lint catalog (the lint engine source)                      |
| `dartwork-mpl://guide/recipes`            | Intent → function-call cookbook (per plot type)                             |
| `dartwork-mpl://guide/migration`          | Migration map — removed/renamed names and their replacements                |
| `dartwork-mpl://api/index`                | List of public dartwork-mpl callables (from `__all__`)                      |
| `dartwork-mpl://api/{name}`               | Signature + first paragraph of docstring for a given public name            |
| `dartwork-mpl://palette/colors`           | Full list of registered colors with hex codes (`dc.*`, `tw.*`, `oc.*`, …)  |
| `dartwork-mpl://palette/fonts`            | Sorted list of all fonts available to matplotlib                            |
| `dartwork-mpl://styles/list`              | Available mplstyle preset names                                             |
| `dartwork-mpl://styles/{preset}`          | Content of a specific mplstyle preset file                                  |
| `dartwork-mpl://templates/list`           | Available plot template types                                               |
| `dartwork-mpl://templates/{plot_type}`    | Boilerplate Python script for a specific plot type                          |
| `dartwork-mpl://templates/advanced/{plot_type}` | Tier-2 (advanced) template for a plot type — synthetic data, reference lines, value labels, narrative title; falls back to the basic template |
| `dartwork-mpl://artifacts/{artifact_id}/plot.png` | Verified PNG (`image/png`) |
| `dartwork-mpl://artifacts/{artifact_id}/plot.pdf` | Verified PDF (`application/pdf`) |
| `dartwork-mpl://artifacts/{artifact_id}/source.py` | Exact submitted UTF-8 source (`text/x-python`) |
| `dartwork-mpl://artifacts/{artifact_id}/report.json` | Complete execution/validation report (`application/json`) |
| `dartwork-mpl://artifacts/{artifact_id}/manifest.json` | Version 1 bundle manifest (`application/json`) |

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
| `apply_lint_fixes(code)`                    | Apply safe identifier-level rewrites (`plt.style.use → dm.style.use`, no-arg `tight_layout()` → `dm.simple_layout(fig)`, `dm.cm2in → dm.cm`); returns fixed code + the issues that still need agent attention |
| `migrate_legacy_code(code)`                 | Rewrite 0.3-era source toward 0.4 idioms (safe substitutions + TODO hints)      |
| `suggest_chart_type(x_type, y_type, ...)`   | Recommend a chart type from the data's characteristics, with pointers to the matching basic and advanced templates |
| `find_template(intent, top_k)`              | Rank the 18 bundled AI plot templates against a free-text intent                |
| `render_template(plot_type)`                | Execute a bundled template in a subprocess and return the rendered PNG (base64 or path) for inline preview |
| `render_template_advanced(plot_type)`       | Render the tier-2 (advanced) version of a bundled template — synthetic data, reference lines, value labels, and a narrative title, so it reads like a finished report figure |
| `compose_layered_plot(plot_type, layers)`   | Return a template plus a checklist of annotation/composition layers to apply (guidance for the agent to edit, not a code rewriter) |
| `validate_plot_data(plot_type, data_json, report=False)` | Validate data; opt into a JSON-string report with reviewable suggestions |
| `validate_generated_plot(code)`             | Execute a script in an isolated subprocess and return the `dm.validate_figure` report (overflow, clipped text, asymmetric margins). Lint-critical issues short-circuit before execution. |
| `dartwork_mpl_info()`                       | Get a structured summary of all capabilities, presets, and templates            |
| `render_plot(code, figure_var="fig", timeout_seconds=20.0, chart_type_hint=None)` | Execute trusted code once, validate the selected native Figure and deliver a durable five-file bundle |
| `get_plot_artifact(artifact_id)` | Retrieve that bundle without executing code |

### Reviewable plot-data suggestions

`validate_plot_data(plot_type: str, data_json: str, report: bool = False) -> str`
keeps its existing text response when `report` is omitted or false. With
`report=True`, the same tool returns a version-1 JSON report **inside that
string**. After decoding the MCP envelope, decode the string separately.
For a connected FastMCP Python `client`:

```python
import json
from decimal import Decimal

result = await client.call_tool("validate_plot_data", {
    "plot_type": "bar",
    "data_json": '{"categories":["01","02"],"values":["1","2.5"]}',
    "report": True,
})
report_text = result.content[0].text
report = json.loads(report_text, parse_float=Decimal, parse_int=Decimal)
# With structured content: json.loads(result.structured_content["result"],
#                                    parse_float=Decimal, parse_int=Decimal)
before = report["original"]["data"]
after = report["candidate"]["data"]  # Present only when changes are proposed.
# Inspect before, after, changes and remaining_issues before choosing data.
```

Within `Decimal`'s supported range, this decoding preserves mathematical values
in returned JSON numbers, including originals outside binary64 range. For tokens
whose exponent or precision exceeds your decoder's capacity, retain `report_text`
or use a token-preserving decoder. The exact original `raw_json` remains
authoritative. Selected members of this report:

```json
{
  "status": "proposal",
  "changes": [
    {"path": "/values/0", "before": "1", "after": 1, "reason": "Declared numeric value; JSON type changes, review meaning.", "requires_review": true},
    {"path": "/values/1", "before": "2.5", "after": 2.5, "reason": "Declared numeric value; JSON type changes, review meaning.", "requires_review": true}
  ],
  "candidate": {"data": {"categories": ["01", "02"], "values": [1, 2.5]}, "valid": true, "remaining_issues": []},
  "requires_review": true,
  "effects": "none"
}
```

The original retains the exact admitted `raw_json` and parsed `data`. The caller
compares before/after and chooses what to use; every proposed change requires
review. `effects` is always `"none"`: the tool applies, renders and stores nothing.
Templates remain standalone Python examples, with no JSON-to-renderer adapter.

Reports cover exactly these five names (`plot_type` is lowercased, without trimming):

| Plot type | Declared fields checked |
| --- | --- |
| `scatter` | Nonempty numeric arrays `x`, `y`, with equal lengths |
| `bar`, `bar_horizontal` | Nonempty arrays: string `categories`, numeric `values`, with equal lengths |
| `histogram` | Nonempty numeric `values`; optional `bins`: positive JSON integer token, or at least two nondecreasing numeric edges (duplicates allowed) |
| `heatmap` | Numeric `matrix`, with nonempty rows of equal nonzero length |

The other 13 recognized types return `unsupported`; `recognized` distinguishes
unknown names. `scope.validity` is `"declared_fields_only"`. Unknown top-level
fields are preserved and listed in `scope.unvalidated_paths`, without validation
or conversion. Numeric-looking category labels such as `"01"` stay strings.
Numeric fields require finite binary64 values without overflow or nonzero underflow.

The only proposal converts a whole numeric string at a declared numeric array
element, including bin edges. It accepts strict JSON-number grammar without
whitespace, units or separators, and requires decimal equality after shortest
binary64 serialization, finite conversion, no nonzero underflow, and integer-valued
results within `±(2**53-1)`. Negative-zero strings are refused. Binary64 remains
approximate, and a type change can change meaning; inspect each suggestion.
Scalar `bins` accepts `10`, while `10.0`, `1e1` and `"10"` require manual input.

Missing/type/shape errors, unsafe numbers, bool/null and length mismatches need
manual input. For `scatter` data `{"x":[1,2],"y":[3]}`, `needs_input` identifies
`/x` and related `/y` with lengths `[2,1]` and asks the caller to restore the
intended aligned observations from the source. No values are added or removed.
A mixed input `{"x":["1",2],"y":[3]}` yields a partial `proposal` with
`candidate.valid:false` and the mismatch in `candidate.remaining_issues`.

Limits are 65,536 UTF-8 input bytes, nesting depth 16, 10,000 value/key tokens,
100 issue records **total** across `issues` and `candidate.remaining_issues`,
100 changes, and 1,048,576 serialized report bytes. Exceeding any limit returns
`rejected` / `limit_exceeded`, without payloads or silent truncation. If the plot
name itself cannot fit a bounded refusal, it is returned as `""` with false
membership/coverage and bounded name-size metadata. Duplicate keys, nonstandard
NaN/Infinity tokens and malformed JSON are rejected without repair. Valid UTF-8
syntax errors within the budgets retain exact raw text; Python strings that
cannot encode as UTF-8 return `rejected` / `invalid_json` and omit `original`.

### Plot execution and validation results

`validate_generated_plot(code, figure_var="fig", timeout_seconds=20.0,
chart_type_hint=None)` executes **trusted local snippets** with the Agg backend.
The fresh subprocess isolates Matplotlib state; it is not an OS security
sandbox. It inherits cwd and retains real file-save effects. Hostile code that
mutates the runner is outside this contract.

Every response includes `stdout` and `stderr` strings, `validation_complete`
(boolean), `failed_checks` (original check IDs in run order), `lint`, and
`visual_warnings`. Printed text, JSON-looking logs, low-level stdout writes and
save messages remain logs; invalid UTF-8 log bytes use replacement characters.
The internal JSON result travels through a private,
absolute temporary file that is cleaned up after execution, including timeout.

- `ok`: validation completed (`true`, `[]`); visual warnings may still exist.
- `validation_incomplete`: tolerated check failures prevented completion
  (`false`, original IDs). Each appears as a WARNING `CHECK_FAILED` with
  `detail.check_id`; successful warnings remain in registry order.
- `lint_blocked`, `exec_error`, `no_figure`, `timeout`: validation is incomplete
  (`false`, `[]` unless failures were already acquired). Unexpected validation
  exceptions are visible errors. Captured logs survive errors and timeout.

`semantic_warnings` is present, possibly empty, exactly when `chart_type_hint`
is supplied, including on failure. Native `dm.validate_figure` keeps returning
its warning list; `quiet=True` suppresses printing without removing failures.

### Durable plot artifacts

`render_plot(code: str, figure_var: str = "fig", timeout_seconds: float = 20.0,
chart_type_hint: str | None = None)` uses the same trusted-code execution and
validation contract above. It exports the selected native Figure once through
`dm.save_formats(..., formats=("png", "pdf"), validate=False,
adopt_orphan_tick_font=False)`, preserving the validated Figure without adding
style or layout. Existing template renderers still return base64 PNG or a local
path; they do not publish artifact bundles.

A successful render or `get_plot_artifact(artifact_id: str)` returns, in order,
one PNG image, five MCP resource links in the table's artifact order, and JSON
text. The JSON is identical to `structuredContent`: `schema_version=1`,
`delivery_status="ready"`, `artifact_id`, UTC `created_at`/`expires_at`, `files`,
and `validation`. Each file has `name`, `uri`, `mime_type`, `size_bytes` and
`sha256`; the manifest omits its own digest to avoid recursive self-hashing.
The persisted manifest lists only the four data files. URIs are MCP references,
not HTTP URLs or local paths; use the connected client's resource reader.

Delivery and validation are separate: a ready bundle can have validation status
`ok` with warnings, or `validation_incomplete` with `validation_complete=false`
and original `failed_checks` IDs. `report.json` retains the complete lint,
visual/optional semantic warnings and original stdout/stderr. `source.py` is the
exact submitted string encoded as UTF-8. Retrieval checks expiry, file sizes and
hashes, returns the original timestamps and never runs source or extends expiry.

This runnable example uses a real FastMCP Client and the configured local server.
The snippet sets its own preset/layout and leaves saving to `render_plot`:

```python
import asyncio
import json

from fastmcp import Client
from dartwork_mpl.mcp.server import mcp

code = '''import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
ax.plot([1, 2, 3], [2, 3, 2.8], linewidth=dm.lw(0))
ax.set_xlabel("Iteration", fontsize=dm.fs(0))
ax.set_ylabel("Value", fontsize=dm.fs(0))
dm.simple_layout(fig)
'''


async def main():
    """Render once, reopen metadata and read the original submitted source."""
    async with Client(mcp) as client:
        result = await client.call_tool("render_plot", {"code": code})
        assert not result.is_error
        metadata = result.structured_content
        assert metadata == json.loads(result.content[-1].text)
        print(metadata["artifact_id"], metadata["validation"])
        reopened = await client.call_tool(
            "get_plot_artifact", {"artifact_id": metadata["artifact_id"]}
        )
        assert reopened.structured_content == metadata
        source = next(f for f in metadata["files"] if f["name"] == "source.py")
        contents = await client.read_resource(source["uri"])
        assert contents[0].text == code


asyncio.run(main())
```

Keep the returned ID to reopen with `get_plot_artifact` after server restart;
the server must use the same storage root and local OS user. Set
`DARTWORK_MPL_ARTIFACT_DIR` in the server environment **before startup/import**
to a nonempty absolute path with no symlink components, or use the default
`~/.cache/dartwork-mpl/artifacts`. For a trusted operator-selected directory,
resolve aliases first (for example, `Path(directory).resolve()` for macOS
temporary paths); the server refuses symlinked components. Configuration binds
once; requests cannot choose paths or roots. Directories/files are private (0700/0600). Unsafe roots
and hosts without descriptor-relative no-follow opens and exclusive
no-follow hard-link restoration return `configuration_error` for this capability;
existing tools remain available. Local filesystem validation covers macOS with
Python 3.10, not every OS/filesystem.

Source is limited to 512 KiB UTF-8; timeout must be finite and in `(0, 120]`
seconds. All five files together must fit 32 MiB. Oversize source/report/logs
reject publication instead of truncating them. Bundles expire exactly seven days
after publication; publication occurs after execution/export completes. Expired
valid bundles are cleaned lazily on access. Unknown, corrupt or substituted
objects are retained, including private quarantine when safe restoration
collides. There is no global quota, background sweeper or delete API; the owner
may need disk maintenance. Incomplete crash leftovers are never served.

IDs are lowercase UUID4 hex references, not credentials. All clients of this
server share the same trusted OS user's access. Code inherits that user's OS
permissions and cwd/file-save effects; the subprocess is not an OS sandbox.

Failures return `isError=true`, JSON text and matching structured metadata with
`schema_version=1`, `delivery_status="error"`, `error_code` and a safe `message`.
Execution/export failures also include the available `report`; no failure returns
an artifact ID, image or links. Stable categories are `invalid_request`,
`configuration_error`, `not_found`, `expired`, `corrupt`, `artifact_too_large`,
`publication_error`, `lint_blocked`, `exec_error`, `no_figure`, and `timeout`.
Resource read failures expose these categories through MCP resource errors;
unroutable URIs can be rejected before a resource handler runs. Retrying render
creates a fresh ID. An expired bundle may be `not_found` after lazy cleanup.

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
   - **MCP in action:** The assistant reads the `agent-entry` resource and immediately outputs correct code calling `dm.style.use('scientific-kr')` followed by `plt.subplots(figsize=dm.figsize(...))`.

2. **Automated layout debugging**
   - **You ask:** _"I used simple_layout but my legend is overlapping the plot."_
   - **MCP in action:** The assistant reads the `policy` resource, understands the library's specific constraints, and provides the exact code to fix the issue.

3. **Live color lookup**
   - **You ask:** _"What's the hex code for dc.teal2?"_
   - **MCP in action:** The assistant calls `get_color_value("dc.teal2")` and returns the exact hex code — no guessing.

4. **Code quality check**
   - **You ask:** _"Review my plotting script for dartwork-mpl best practices."_
   - **MCP in action:** The assistant uses the `lint_dartwork_mpl_code` tool to check for antipatterns (e.g., `figsize=`, `tight_layout()`, `plt.subplots()`) and suggests fixes.

5. **Guided plot creation**
   - **You ask:** _"Create a tornado chart comparing energy savings."_
   - **MCP in action:** The assistant uses the `create_plot` prompt with the `tornado` template from `dartwork-mpl://templates/tornado` to generate a complete, standards-compliant script.

6. **Data validation before plotting**
   - **You ask:** _"Plot this data as a heatmap."_
   - **MCP in action:** The assistant calls `validate_plot_data("heatmap", ...)` to verify the data structure is correct before generating the plot code.
