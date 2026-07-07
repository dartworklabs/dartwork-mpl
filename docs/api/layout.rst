Layout Utilities
================

Utilities for tightening layouts without juggling ``plt.subplots_adjust``.
``simple_layout`` measures visible artists and arithmetically places GridSpec
edges so axes content lands at the requested distance from the figure bounds;
``make_offset`` nudges text/legends in point units; ``label_axes`` adds
standardized panel labels; ``arrow_axis`` draws annotated bidirectional arrows;
and ``set_decimal``/``get_bounding_box`` provide quick helpers when formatting axes.

Example
-------

.. code-block:: python

   import numpy as np
   import dartwork_mpl as dm

   fig, axes = plt.subplots(1, 3, figsize=dm.figsize(dm.col2, 0.35))
   for ax in axes:
       ax.plot(np.linspace(0, 1, 40), np.random.rand(40), color='dc.teal3')

   # Panel labels
   dm.label_axes(axes)  # adds a, b, c

   # Layout optimization
   dm.simple_layout(fig, ml=0.08, mr=0.05, mb=0.10, mt=0.08)

   # Decimal formatting
   dm.set_decimal(axes[0], xn=2, yn=1)

   # Arrow annotations
   dm.arrow_axis(axes[1], 'x', 'Installation cost')
   dm.arrow_axis(axes[2], 'y', 'Information richness')

.. figure:: images/layout_example.svg
   :alt: 3-panel layout with label_axes, arrow_axis, and set_decimal
   :width: 100%

API
---

Layout Functions
^^^^^^^^^^^^^^^^

.. note::

   ``cm2in`` / ``set_xmargin`` / ``set_ymargin`` were removed in the 0.4
   release. Use ``dm.cm(...)`` (which returns a ``Length``) and
   matplotlib's ``ax.margins(...)`` instead — see the migration table in
   :doc:`../migration`.

.. autofunction:: dartwork_mpl.simple_layout

Annotation Functions
^^^^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.make_offset
.. autofunction:: dartwork_mpl.label_axes
.. autofunction:: dartwork_mpl.arrow_axis

Utility Functions
^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.layout.get_bounding_box
.. autofunction:: dartwork_mpl.set_decimal
