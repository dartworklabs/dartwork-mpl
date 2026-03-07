MCP Server
==========

**dartwork-mpl** includes a built-in `Model Context Protocol (MCP) <https://modelcontextprotocol.io>`_
server that lets AI coding assistants — such as Claude Code, Cursor,
Windsurf, and any MCP-compatible client — access library documentation,
style guides, and helper tools **inside the chat context**.

.. contents:: On this page
   :local:
   :depth: 2

----

What can MCP do?
----------------

When the ``dartwork-mpl`` MCP server is connected, your AI assistant
gains access to the following **resources** and **tools** without you
having to copy-paste documentation:

Resources
^^^^^^^^^

========================== ================================================
URI                        Description
========================== ================================================
``dartwork-mpl://guide/general-guide``   Complete usage guide — styles, colors, layout,
                                         fonts, save/export, workflow, and full examples.
``dartwork-mpl://guide/layout-guide``    Deep-dive into ``simple_layout``, GridSpec
                                         strategies, hardcoded-element conflicts, and
                                         combined-layout solutions (1 100+ lines).
========================== ================================================

These are read-only text resources that the AI assistant can retrieve
on demand. They contain the same content as the Markdown files under
``dartwork_mpl/asset/prompt/``.

Tools
^^^^^

=============================== ===================================================
Tool                            Description
=============================== ===================================================
``fetch_github_document(url)``  Fetch any raw file from GitHub.  Useful for pulling
                                the latest README, CHANGELOG, or example scripts
                                from the dartwork-mpl repo at runtime.
=============================== ===================================================

Practical use-cases
^^^^^^^^^^^^^^^^^^^

1. **Style selection** — Ask the assistant *"Which dartwork-mpl preset
   should I use for a Korean-language investment chart?"* and it can
   look up the ``general-guide`` resource to answer accurately.

2. **Layout debugging** — Paste your figure code and ask *"My title
   overlaps the axes after simple_layout — how do I fix it?"*.  The
   assistant reads the ``layout-guide`` resource and proposes one of
   the five documented solutions.

3. **Color palette lookup** — *"Give me a warm OC palette for a bar
   chart"* — the assistant can reference the color section in the
   general guide.

4. **Remote doc retrieval** — The ``fetch_github_document`` tool lets
   the assistant pull the latest docs from GitHub when local resources
   are outdated.

----

Installation
------------

Prerequisites
^^^^^^^^^^^^^

* Python ≥ 3.10
* ``dartwork-mpl`` installed (see :doc:`/installation/index`)
* The ``[mcp]`` optional dependencies:

  .. code-block:: bash

     # uv (recommended)
     uv pip install -e ".[mcp]"

     # pip
     pip install "dartwork-mpl[mcp]"

  This pulls in ``fastmcp ≥ 2.13`` and ``httpx ≥ 0.27``.


Client configuration
^^^^^^^^^^^^^^^^^^^^

Every MCP-capable client has its own config format.  Below are
copy-paste-ready snippets for the most popular ones.

.. tab-set::

   .. tab-item:: Claude Code
      :sync: claude

      Add to ``~/.claude.json`` (global) or
      ``<project>/.claude/mcp_servers.json``:

      .. code-block:: json

         {
           "mcpServers": {
             "dartwork-mpl": {
               "command": "uv",
               "args": [
                 "run",
                 "--directory", "/absolute/path/to/dartwork-mpl",
                 "dartwork-mpl-mcp"
               ]
             }
           }
         }

   .. tab-item:: Cursor / Windsurf
      :sync: cursor

      Add to ``~/.cursor/mcp.json`` (or the Windsurf equivalent):

      .. code-block:: json

         {
           "mcpServers": {
             "dartwork-mpl": {
               "command": "uv",
               "args": [
                 "run",
                 "--directory", "/absolute/path/to/dartwork-mpl",
                 "dartwork-mpl-mcp"
               ]
             }
           }
         }

   .. tab-item:: Antigravity (Gemini)
      :sync: antigravity

      Add to ``~/.gemini/antigravity/mcp_config.json``:

      .. code-block:: json

         {
           "mcpServers": {
             "dartwork-mpl": {
               "command": "uv",
               "args": [
                 "run",
                 "--directory", "/absolute/path/to/dartwork-mpl",
                 "dartwork-mpl-mcp"
               ],
               "env": {}
             }
           }
         }

      After saving the config, **restart Antigravity** (or start a new
      conversation) for the server to be picked up.  You can verify the
      connection by asking the assistant to list its available MCP
      resources.

   .. tab-item:: Generic stdio
      :sync: generic

      Any client that supports the MCP stdio transport can launch the
      server directly:

      .. code-block:: bash

         uv run --directory /path/to/dartwork-mpl dartwork-mpl-mcp

      Or via the Python module:

      .. code-block:: bash

         uv run python -m dartwork_mpl.mcp.server

.. important::

   Replace ``/absolute/path/to/dartwork-mpl`` with the actual path
   where the package source lives on your machine.  If you installed
   ``dartwork-mpl`` from PyPI (once published), the
   ``--directory`` flag can be dropped and the ``command`` can simply
   be ``dartwork-mpl-mcp``.


----

Verification
------------

After configuring your client, verify the server is reachable.

Quick smoke test (terminal)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Send a JSON-RPC initialize request via stdin
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' \
     | uv run dartwork-mpl-mcp

Expected output (key fields):

.. code-block:: json

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

If you see this response, the server is working correctly. ✅

Python import test
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from dartwork_mpl.mcp.server import mcp

   print(mcp.name)   # → "dartwork-mpl"
   print(mcp)        # FastMCP instance info

Unit tests
^^^^^^^^^^

.. code-block:: bash

   uv run pytest tests/test_mcp.py -v

All 7 tests should pass:

.. code-block:: text

   tests/test_mcp.py::TestMcpServer::test_mcp_instance_is_fastmcp      PASSED
   tests/test_mcp.py::TestMcpServer::test_mcp_server_name               PASSED
   tests/test_mcp.py::TestMcpResources::test_register_resources_no_error PASSED
   tests/test_mcp.py::TestMcpResources::test_register_resources_calls_resource_decorator PASSED
   tests/test_mcp.py::TestMcpTools::test_register_tools_no_error         PASSED
   tests/test_mcp.py::TestMcpTools::test_register_tools_calls_tool_decorator PASSED
   tests/test_mcp.py::TestMcpPackage::test_mcp_package_exports           PASSED

----

Architecture
------------

.. code-block:: text

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

* **server.py** instantiates ``FastMCP("dartwork-mpl")`` and calls
  ``register_resources()`` / ``register_tools()``.
* **resources.py** reads bundled Markdown guides via
  ``dartwork_mpl.prompt.get_prompt()`` and exposes them as MCP
  resources under the ``dartwork-mpl://guide/`` URI scheme.
* **tools.py** registers callable tools (currently
  ``fetch_github_document``).
* **cli.py** simply calls ``mcp.run()`` — used by the
  ``dartwork-mpl-mcp`` console script.

----

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Symptom
     - Fix
   * - ``ModuleNotFoundError: fastmcp``
     - Install the MCP extras: ``uv pip install -e ".[mcp]"``
   * - ``uv run mcp`` launches the wrong CLI
     - The ``mcp`` Python package ships its own ``mcp`` script.
       Use ``dartwork-mpl-mcp`` instead.
   * - Server starts but client shows no resources
     - Verify the ``--directory`` flag points to the package root.
       Check your client's MCP log for connection errors.
   * - ``ValueError: Prompt guide not found``
     - The ``asset/prompt/`` directory is missing.
       Reinstall the package or check the source tree.
