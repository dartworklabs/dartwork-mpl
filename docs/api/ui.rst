Interactive Viewer (UI)
=======================

A FastAPI-powered web UI that auto-generates parameter controls from
function signatures or Pydantic models and renders matplotlib figures
in real-time.  Install the optional ``ui`` extra to use this module:

.. code-block:: bash

   uv add "dartwork-mpl[ui]"

``run(figure_fn, param_model=None, *, title, copy_to, host, port)``

   Launch the interactive figure viewer in the browser.

   - Parameters:

     - ``figure_fn``: callable accepting a single ``ParamModel`` instance, returns a ``Figure``.
     - ``param_model``: optional explicit ``ParamModel`` subclass (auto-detected from type hints if omitted).
     - ``title``: browser tab title.  Default ``"Dartwork Viewer"``.
     - ``copy_to``: one ``str`` / ``os.PathLike[str]``, a list of those,
       or ``None``. Image saves also create copies in these directories;
       script saves stay in the script directory. ``~`` expands, relative
       roots use the working directory at startup, and duplicate directory
       objects are deduplicated.
     - ``host``: loopback IP literal, or ``"localhost"`` (mapped directly to
       ``"127.0.0.1"``). Default ``"127.0.0.1"``. Wildcard, non-loopback,
       and other hostname binds are rejected before server startup or writes.
     - ``port``: server port.  Default ``8501``.

   - Returns:

     - ``None`` — runs the server until interrupted.

``ParamModel``

   Base Pydantic model for declaring plot parameters.  Subclass it and
   add typed fields with ``pydantic.Field`` for validation, ranges, and
   default values.  The UI auto-generates sliders, dropdowns, and text
   fields from the field metadata.

Features
--------

- **Auto-generated controls**: sliders, dropdowns, and text inputs created from type annotations.
- **Real-time preview**: figure re-renders on every parameter change.
- **Export**: download PNG/SVG/PDF or generate a standalone Python script.
- **Presets**: save and restore parameter combinations.
- **Server-side save**: save images and scripts to the project directory.
- **Hot reload**: restart the server to pick up code changes.

Local access and saves
----------------------

The viewer is a local development tool with trusted Python callbacks.
Loopback access establishes network locality, not a person's identity;
local processes are trusted. Every route checks Host, and effects check
each supplied Origin and Referer against it. Forwarded headers do not
grant access. Hosted access and reverse proxies are outside this contract.

Server image and script saves are **create-only** below the script directory.
Use a new relative filename for every save, including every ``copy_to``
destination. Safe nested subdirectories are allowed; absolute paths,
traversal, symlinks and non-directory parents are refused. An existing
target at any destination returns 409: **file exists; choose a new name**.
There is no overwrite action. Generated names also use exclusive creation.

The viewer pins directory handles and uses no-follow, handle-relative
operations. Multi-root saves use best-effort rollback, not a cross-root
transaction: readers can observe provisional files, cleanup can fail, and
a crash may leave new files. A partial-save 503 identifies affected relative
paths. A retry needs a new name. This does not protect against a malicious
same-owner process moving already-authorized directories or racing cleanup.

State and recovery
------------------

Only ``.dartwork_ui_config.json`` and ``.dartwork_ui_presets.json`` use
bounded atomic replacement. Malformed or oversized existing state returns
409 (``invalid_stored_state``); reads, updates and deletes preserve its
bytes. The UI reports the failure and keeps defaults, controls and Reset
usable. Reset changes active parameters; it does not repair stored files.

Renamed or removed model fields are projected out on reads and reported
through ``dropped_fields`` on config and individual presets. Reads do not
rewrite the files. Retained values are not checked against the current
model until used; an obsolete type or range can return 422. Use Reset to
restore current defaults. Preset-list success responses remain JSON lists.
Updates serialize within one process; separate viewer processes sharing a
directory can lose updates because the last replacement wins.

Input limits and failures
-------------------------

JSON-bearing requests require ``application/json`` with an absent or UTF-8
charset and no Content-Encoding. Limits count UTF-8 bytes where applicable:

- Request body and config file: 1 MiB each; preset file: 8 MiB.
- JSON depth: 16; total values: 65,536; entries per container: 4,096.
- String: 64 KiB; integer token: 640 digits.
- Tabs: 64, with unique integer IDs; presets: 1,000; label: 256 bytes.
- Relative output path: 1,024 bytes, plus platform component limits.
- Active figure width: integer 30..100; out-of-range stored widths use
  the UI default. Unknown active fields, including nested model fields,
  are rejected; declared open dictionaries remain open within these bounds.

Controlled API failures include ``detail`` and a stable ``code``. Statuses:

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Status
     - Meaning
   * - 400
     - Malformed, duplicate-key or non-finite JSON; unsafe output path.
   * - 403
     - Local access policy or unclassified effect refusal.
   * - 404
     - Requested preset or route does not exist.
   * - 409
     - Existing output, changed root/target, or invalid stored state.
   * - 413
     - Request or next serialized state exceeds a limit.
   * - 415
     - Unsupported media type, charset or content encoding.
   * - 422
     - Wrong schema, unknown field, or invalid active parameter value.
   * - 500
     - Trusted callback failed (``callback_failed``), without traceback details.
   * - 501
     - Safe filesystem primitives unavailable (``unsupported_filesystem_capability``).
   * - 503
     - Filesystem I/O or partial-save failure.

The package's general OS-independent support does not guarantee these
filesystem primitives. A scoped 501 leaves rendering and downloads usable;
it does not fall back to unsafe writes. Callbacks execute serially and
are trusted arbitrary Python: there is no hard CPU, memory or deadline
guarantee, and the viewer is not a hostile-code sandbox.

Example
-------

.. snippet: no-run
.. code-block:: python

   from dartwork_mpl.ui import ParamModel, run
   from pydantic import Field
   import matplotlib.pyplot as plt
   import numpy as np
   import dartwork_mpl as dm

   class Params(ParamModel):
       n: int = Field(default=100, ge=10, le=1000, description="Number of points")
       alpha: float = Field(default=0.5, ge=0, le=1, description="Opacity")

   def scatter_plot(params: Params):
       dm.style.use("scientific")
       fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
       ax.scatter(range(params.n), np.random.randn(params.n), alpha=params.alpha)
       dm.simple_layout(fig)
       return fig

   run(scatter_plot)  # opens the local viewer

.. automodule:: dartwork_mpl.ui
   :members:
   :undoc-members:
   :show-inheritance:
