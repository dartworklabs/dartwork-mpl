Visual Validation
=================

Automatic detection of common rendering issues that are invisible in
stdout-only environments (e.g. AI agent pipelines).  Every check emits
structured ``[VISUAL]`` log lines so agents can grep and auto-correct.

``validate_figure`` runs all checks by default and is integrated into
``save_formats()`` (enabled via ``validate=True``).

Available Checks
----------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 20

   * - Check ID
     - Description
     - Severity
   * - ``overflow``
     - Artists whose bounding box exceeds the figure canvas
     - WARNING
   * - ``overlap``
     - Overlapping text labels within each axes
     - WARNING
   * - ``legend_overflow``
     - Legends occupying too much of the axes area
     - WARNING
   * - ``tick_crowding``
     - Overcrowded tick labels on either axis
     - WARNING
   * - ``empty_axes``
     - Axes with no visible data
     - INFO

Example
-------

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   fig, ax = plt.subplots()
   ax.plot([0, 1], [0, 1])

   # Run all checks
   warnings = dm.validate_figure(fig)
   for w in warnings:
       print(w)

   # Run specific checks only
   warnings = dm.validate_figure(fig, checks=('overlap', 'tick_crowding'))

   # Integrated in save_formats (on by default)
   dm.save_formats(fig, 'output/fig', validate=True)

API
---

.. autofunction:: dartwork_mpl.validate_figure
