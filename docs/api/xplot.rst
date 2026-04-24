Extended Plots (templates)
===========================

Ready-to-use specialized visualization templates that extend core
dartwork-mpl with opinionated, publication-ready plot functions.

.. warning::

   **Module Renamed**: The ``xplot`` module has been renamed to ``templates`` in v0.2.0.
   The old ``xplot`` name is available as a deprecated alias for backward compatibility.
   Please update your imports to use the new name:

   .. code-block:: python

      # Old (deprecated - will be removed in v1.0)
      from dartwork_mpl.xplot import plot_diverging_bar

      # New (recommended)
      from dartwork_mpl.templates import plot_diverging_bar
      # or
      import dartwork_mpl as dm
      dm.plot_diverging_bar(...)

Example
-------

.. code-block:: python

   import numpy as np
   from dartwork_mpl.templates import plot_diverging_bar  # New import path

   fig, ax = plot_diverging_bar(
       labels=['Category A', 'Category B', 'Category C'],
       neg_values=np.array([-30, -15, -25]),
       pos_values=np.array([40, 55, 35]),
       neg_label='Decrease',
       pos_label='Increase',
   )

.. figure:: images/xplot_example.svg
   :alt: Diverging bar chart from plot_diverging_bar
   :width: 100%

API
---

.. automodule:: dartwork_mpl.templates
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: dartwork_mpl.templates.diverging_bar
   :members:
   :undoc-members:
   :show-inheritance:

Legacy Compatibility
--------------------

For backward compatibility, the old ``xplot`` module name is still available:

.. automodule:: dartwork_mpl.xplot
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
