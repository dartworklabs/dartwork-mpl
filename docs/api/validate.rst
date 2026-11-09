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
   * - ``OVERFLOW``
     - Text, tick labels, or figure-level text extend past the canvas
     - WARNING
   * - ``OVERLAP``
     - Text labels overlap within a single axes
     - WARNING
   * - ``UNIT_DUP``
     - Axis label declares a unit also shown as a tick affix
     - WARNING
   * - ``CROSS_AXES_OVERLAP``
     - Labels from different axes overlap in multi-panel figures
     - WARNING
   * - ``LEGEND_OVERFLOW``
     - Legends dominate the axes, spill past the figure, or sit outside
       their plot at more than half its size (a figure legend: of the panels)
     - WARNING
   * - ``LEGEND_OVERLAP``
     - A legend covers a title, axis label, tick label or figure-level text
       (suptitle, ``fig.text``)
     - WARNING
   * - ``LEGEND_ON_DATA``
     - A legend (Axes or figure) is drawn over bars, lines or markers of any
       plot box, across the outline of a filled area (``fill_between``,
       ``stackplot``, violin bodies), over a text inside an Axes, over
       another legend, or into another panel
     - WARNING
   * - ``TICK_CROWD``
     - Tick labels consume more space than the axis can comfortably hold
     - INFO
   * - ``TICK_OVERLAP``
     - Neighbouring tick labels of one axis overlap (each label as the
       rectangle its text fills, turned with it); after ``simple_layout``,
       what its wrapping and turning could not clear
     - WARNING
   * - ``TICK_CORNER_OVERLAP``
     - An x tick label overlaps a y tick label of the same plot box at a
       corner (both axes ending on a tick, or a first category name
       reaching under the y labels; a twin's right labels too); after
       ``simple_layout``, what its ``pad`` step could not move (pads set by
       hand)
     - WARNING
   * - ``TICK_ROTATION``
     - X tick labels are rotated needlessly or overlap when horizontal
     - INFO
   * - ``TICK_DECIMAL``
     - Numeric tick labels are mixed or duplicated within a unit, print
       trailing zeros on whole-number ticks, or are over-precise for their step
     - WARNING / INFO
   * - ``VALUE_LABEL_DECIMAL``
     - Every numeric value label in an axes is a whole number, yet some print
       trailing zeros (``120.0``)
     - WARNING
   * - ``VALUE_LABEL_ON_DATA``
     - A value label is drawn over a bar, a line or a marker in its plot box
       (twin Axes included); labels inside their own bar or bubble, boxed,
       slanted and contour labels are left alone
     - WARNING
   * - ``EMPTY_AXES``
     - Axes contain no visible plotted artist or annotation
     - INFO
   * - ``MARGIN_ASYMMETRY``
     - Opposite outer margins differ by more than the threshold
     - WARNING
   * - ``PIE_LABEL_OFFSET``
     - Donut-chart percentage labels are not centered in the ring
     - INFO
   * - ``CLIPPED_TEXT``
     - Text is clipped at an axes or canvas boundary
     - WARNING
   * - ``PRESET_OVERRIDE``
     - Grid, spines or a background differ from the active preset (advisory)
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
   warnings = dm.validate_figure(fig, checks=('OVERLAP', 'TICK_CROWD'))

   # Integrated in save_formats (on by default)
   dm.save_formats(fig, 'output/fig', validate=True)

API
---

Core Validation
^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.validate_figure

Enhanced Validation with Auto-Fix
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``validate_fixes`` module provides advanced validation with automatic fix suggestions,
particularly useful for AI agents and automated pipelines.

.. automodule:: dartwork_mpl.validate_fixes
   :members: validate_with_fixes, get_fix_suggestions, check_agent_requirements, generate_validation_report
   :noindex:

Example with Auto-Fix
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import dartwork_mpl as dm
   from dartwork_mpl.validate_fixes import (
       generate_validation_report,
       get_fix_suggestions,
       validate_with_fixes,
   )

   # Validate and get fix suggestions
   issues, fixes = validate_with_fixes(fig)

   # `fixes` is a list[str] of auto-applied changes. To inspect
   # suggestions without mutating the figure, ask for each issue.
   for issue in issues:
       for suggestion in get_fix_suggestions(issue):
           print(suggestion)

   # Or ask validate_with_fixes to apply its safe layout fix once.
   issues_after, applied = validate_with_fixes(fig, auto_apply=True)
   print(applied)

   # Generate report for logging
   report = generate_validation_report(fig)
   print(report)
