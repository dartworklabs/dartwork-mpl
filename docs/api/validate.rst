Visual Validation
=================

Automatic detection of common rendering issues that are invisible in
stdout-only environments (e.g. AI agent pipelines).  Every check emits
structured ``[VISUAL]`` log lines so agents can grep and auto-correct.

``validate_figure`` runs all checks by default and is integrated into
``save_formats()`` (enabled via ``validate=True``).

``validate_figure(fig, *, checks=None, quiet=False)``
   - Parameters:
     - ``fig``: matplotlib ``Figure`` to validate.
     - ``checks``: tuple of check IDs to run; ``None`` runs all five.
     - ``quiet``: if ``True``, suppress printed output.
   - Returns:
     - ``list[VisualWarning]`` — all detected issues.

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

Data Structures
---------------

``VisualWarning``
   A dataclass representing a single detected issue:
   ``severity`` (``Severity.WARNING`` or ``Severity.INFO``),
   ``check_id`` (string matching the check names above),
   ``message`` (human-readable description),
   ``detail`` (dict with check-specific metadata).

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
       print(w)  # ⚠️  [overflow] Title extends beyond figure canvas

   # Run specific checks only
   warnings = dm.validate_figure(fig, checks=('overlap', 'tick_crowding'))

   # Integrated in save_formats (on by default)
   dm.save_formats(fig, 'output/fig', validate=True)

.. autofunction:: dartwork_mpl.validate_figure
