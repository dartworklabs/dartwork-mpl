Agent Helper Utilities
======================

AI-focused utilities for creating consistent, high-quality visualizations.
This module provides helper functions organized into submodules designed to
assist AI agents and automation tools in generating professional charts.

.. note::

   The ``helpers`` module was previously named ``agent_utils`` in versions before 0.2.0.
   The old name is available as a deprecated alias for backward compatibility.

Overview
--------

The helpers module is organized into specialized submodules:

- **data**: Data validation and cleaning utilities
- **colors**: Automatic color selection and management
- **formatting**: Axis labels, legends, and annotations
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

Color Selection
---------------

Automatic color palette selection based on data characteristics.

.. automodule:: dartwork_mpl.helpers.colors
   :members:
   :undoc-members:
   :show-inheritance:

Example:

.. code-block:: python

   import dartwork_mpl as dm

   # Auto-select colors for 5 data series
   colors = dm.helpers.colors.auto_select_colors(
       n_series=5,
       color_type='qualitative',
       highlight_index=0  # Highlight first series
   )

   # Plot with auto-selected colors
   for i, color in enumerate(colors):
       ax.plot(x, data[i], color=color, label=f"Series {i+1}")

Label, Legend, and Annotation Helpers
-------------------------------------

Functions for composing axis labels, placing legends, and adding
value annotations.

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

   # Format axis labels automatically
   dm.helpers.labels.format_axis_labels(
       ax,
       xlabel="Time",
       ylabel="Value",
       use_latex=False
   )

   # Optimize legend placement
   dm.helpers.labels.optimize_legend(
       ax,
       loc='best',
       frameon=False
   )

   # Add value labels to data points
   dm.helpers.labels.add_value_labels(
       ax,
       x, y,
       format_str="{:.1f}",
       offset=(0, 5)
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
       x_data=x,
       y_data=y,
       data_type='continuous'
   )
   print(f"Suggested chart type: {suggested_type}")

I/O Utilities
-------------

Functions for creating and saving figures with proper settings.

.. automodule:: dartwork_mpl.helpers.io
   :members:
   :undoc-members:
   :show-inheritance:

Example:

.. code-block:: python

   import dartwork_mpl as dm

   # Create figure with style applied
   fig, ax = dm.helpers.io.create_figure_with_style(
       style='scientific',
       figsize=(8, 6),
       dpi=100
   )

   # Plot your data
   ax.plot(x, y)

   # Save with optimal settings
   dm.helpers.io.save_figure(
       fig,
       filename='output.png',
       dpi=300,
       transparent=False,
       optimize=True
   )

Integration with AI Agents
--------------------------

The helpers module is designed to be easily used by AI agents and automation tools:

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt

   def ai_create_chart(data, chart_type=None):
       """Example function an AI agent might use."""

       # Validate input data
       x, y = dm.helpers.data.validate_data(data['x'], data['y'])

       # Suggest chart type if not specified
       if chart_type is None:
           chart_type = dm.helpers.quality.suggest_chart_type(x, y)

       # Create figure with appropriate style
       fig, ax = dm.helpers.io.create_figure_with_style(
           style='scientific' if chart_type == 'scatter' else 'web'
       )

       # Auto-select colors
       colors = dm.helpers.colors.auto_select_colors(
           n_series=1,
           color_type='sequential' if chart_type == 'line' else 'qualitative'
       )

       # Create the plot
       if chart_type == 'line':
           ax.plot(x, y, color=colors[0])
       elif chart_type == 'scatter':
           ax.scatter(x, y, color=colors[0])

       # Format and optimize
       dm.helpers.labels.format_axis_labels(ax)
       dm.helpers.labels.optimize_legend(ax)

       # Check quality
       issues = dm.helpers.quality.check_figure_quality(fig)

       return fig, issues

See Also
--------

- :doc:`../integrations/ai_assisted` - Guide for using dartwork-mpl with AI tools
- :doc:`../integrations/mcp_server` - MCP server for AI integration
- :doc:`../usage_guide/quickstart` - Getting started with dartwork-mpl