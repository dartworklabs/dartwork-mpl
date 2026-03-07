Interactive Viewer (UI)
======================

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
     - ``copy_to``: path(s) to auto-copy saved images to.
     - ``host``: server host.  Default ``"127.0.0.1"``.
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

Example
-------

.. code-block:: python

   from dartwork_mpl.ui import ParamModel, run
   from pydantic import Field
   import matplotlib.pyplot as plt
   import numpy as np

   class Params(ParamModel):
       n: int = Field(default=100, ge=10, le=1000, description="Number of points")
       alpha: float = Field(default=0.5, ge=0, le=1, description="Opacity")

   def scatter_plot(params: Params):
       fig, ax = plt.subplots()
       ax.scatter(range(params.n), np.random.randn(params.n), alpha=params.alpha)
       return fig

   run(scatter_plot)  # opens http://127.0.0.1:8501

.. automodule:: dartwork_mpl.ui
   :members:
   :undoc-members:
   :show-inheritance:
