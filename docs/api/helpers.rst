Helper Utilities (``dm.helpers``)
=================================

General-purpose helpers for building consistent, high-quality
visualizations. They cover the small ergonomic gaps that show up
between matplotlib and a polished figure — data validation, color
picking, label/legend formatting, quality checks, and figure I/O.

These helpers compose well with the rest of dartwork-mpl, but they
also work as a standalone toolkit on top of plain matplotlib.

.. note::

   Upgrading from an older alias? See the :doc:`Migration Guide
   <../migration>` for the full list of renamed paths and one-shot
   migration scripts.

Overview
--------

The helpers module is organized into specialized submodules:

- **data**: Data validation and cleaning utilities
- **colors**: Automatic color selection and management
- **labels**: Legend placement and formatting
- **quality**: Quality checks and chart suggestions
- **io**: Figure creation and saving utilities

Main Module
-----------

.. automodule:: dartwork_mpl.helpers
   :members:
   :undoc-members:
   :show-inheritance:

Data Validation
---------------

Utilities for validating and cleaning data before plotting.

.. automodule:: dartwork_mpl.helpers.data
   :members:
   :undoc-members:
   :show-inheritance:

Example:

.. code-block:: python

   import dartwork_mpl as dm
   import numpy as np

   # Validate data before plotting
   x = np.array([1, 2, np.nan, 4, 5])
   y = np.array([2, 4, 6, 8, 10])

   x_clean, y_clean = dm.helpers.data.validate_data(
       x, y,
       require_same_length=True,
       allow_nan=False,
       min_points=3
   )

Palette Lookup
--------------

Curated dartwork palette sized to the data series count and kind.

.. automodule:: dartwork_mpl.helpers.colors
   :members:
   :undoc-members:
   :show-inheritance:

Example:

.. code-block:: python

   import dartwork_mpl as dm

   # Curated palette for 5 categorical series, item 0 highlighted.
   colors = dm.make_palette(5, kind="categorical", highlight=0)

   # Plot with the palette
   for i, color in enumerate(colors):
       ax.plot(x, data[i], color=color, label=f"Series {i+1}")

Label and Legend Helpers
------------------------

Functions for placing and formatting legends. Axis labels use
matplotlib's native ``ax.set_xlabel`` / ``ax.set_ylabel`` calls; value
annotations use ``ax.text`` or ``ax.bar_label`` directly.

.. automodule:: dartwork_mpl.helpers.labels
   :members:
   :undoc-members:
   :show-inheritance:

Example:

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt

   fig, ax = plt.subplots()
   ax.plot(x, y)

   ax.set_xlabel("Time", fontsize=dm.fs(0))
   ax.set_ylabel("Value", fontsize=dm.fs(0))

   # Optimize legend placement
   dm.helpers.labels.optimize_legend(
       ax,
       preferred_loc="best",
       outside=False,
   )

Quality Checks
--------------

Functions for checking figure quality and suggesting improvements.

.. automodule:: dartwork_mpl.helpers.quality
   :members:
   :undoc-members:
   :show-inheritance:

Example:

.. code-block:: python

   import dartwork_mpl as dm

   # Check figure quality
   issues = dm.helpers.quality.check_figure_quality(fig)
   if issues:
       print("Quality issues found:")
       for issue in issues:
           print(f"  - {issue}")

   # Get chart type suggestions
   suggested_type = dm.helpers.quality.suggest_chart_type(
       x_type="continuous",
       y_type="continuous",
       n_points=len(x),
       n_series=1,
   )
   print(f"Suggested chart type: {suggested_type}")

I/O Utilities
-------------

.. note::

   The ``dartwork_mpl.helpers.io`` submodule was retired in 0.4. The
   single remaining entry point for multi-format saves is
   ``dm.save_formats`` (canonical) — pick the file types you want and
   the function handles the rest.

``dm.save_formats`` is the canonical multi-format save helper (see
:doc:`io` for its signature).

Example:

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   dm.style.use("scientific")
   fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
   ax.plot(x, y)
   dm.simple_layout(fig)

   # Save in multiple formats at once
   dm.save_formats(fig, "output", formats=("png", "pdf", "svg"))

End-to-end Example: Automated Visualization
-------------------------------------------

The helpers module composes naturally with the rest of dartwork-mpl
when you want a single function to take raw data and return a
finished, quality-checked figure — useful for batch reporting,
automated dashboards, or letting an LLM agent produce charts
without hand-tuning every call.

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   def automated_visualization(data, chart_type=None):
       """Take raw ``{'x': ..., 'y': ...}`` data and return a polished figure."""

       # 1. Validate input data
       x, y = dm.helpers.data.validate_data(data["x"], data["y"])

       # 2. Suggest a chart type if not specified
       if chart_type is None:
           chart_type = dm.helpers.quality.suggest_chart_type(
               x_type="continuous",
               y_type="continuous",
               n_points=len(x),
               n_series=1,
           )

       # 3. Create the figure with an appropriate style
       dm.style.use("scientific" if chart_type == "scatter" else "web")
       fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))

       # 4. Pick a curated palette
       colors = dm.make_palette(
           1,
           kind="sequential" if chart_type == "line" else "categorical",
       )

       # 5. Render
       if chart_type == "line":
           ax.plot(x, y, color=colors[0])
       elif chart_type == "scatter":
           ax.scatter(x, y, color=colors[0])

       # 6. Format and quality-check
       ax.set_xlabel("X", fontsize=dm.fs(0))
       ax.set_ylabel("Y", fontsize=dm.fs(0))
       dm.helpers.labels.optimize_legend(ax)
       issues = dm.helpers.quality.check_figure_quality(fig)

       return fig, issues

See Also
--------

- :doc:`../integrations/ai_assisted` — using dartwork-mpl from AI assistants
- :doc:`../integrations/mcp_server` — MCP server for AI integration
- :doc:`../usage_guide/quickstart` — getting started
