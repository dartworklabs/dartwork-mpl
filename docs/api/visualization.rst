Asset Diagnostics
=================

The :mod:`dartwork_mpl.diagnostics` module bundles helpers that
let you inspect *exactly* what colormaps, color libraries, and fonts
are registered in your current environment. They render
publication-quality preview figures without ever calling
``plt.show()``, so they compose with your normal save / display
pipeline.

The Model B color-family preview is available as ``dm.show_colors``. The
diagnostic color-library and colormap catalog renderers live under
``dartwork_mpl.diagnostics``. Upgrading from an older alias path? See the
:doc:`Migration Guide <../migration>`.

Quick examples
--------------

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib as mpl
   from dartwork_mpl import diagnostics

   # Group colormaps by category and render one figure per group
   figs = diagnostics.render_cmap_catalog(group_by_type=True, ncols=4)

   # Preview Model B color families
   fig = dm.show_colors(kind="qualitative")

   # Audit registered font families with weight + italic spectrum
   fig = dm.plot_fonts(font_size=11, ncols=3)

   # Classify an arbitrary colormap
   diagnostics.classify_cmap(mpl.colormaps["coolwarm"])  # → "Diverging"

``dm.show_colors`` previews the registered Model B families. Browse the full
token sheets in :doc:`Colors <../color_system/colors>`, choose series palettes
in :doc:`Palettes <../color_system/palettes>`, and inspect continuous maps in
the :doc:`Colormaps <../color_system/colormaps>` catalog.

Choosing the right helper
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Goal
     - Helper
   * - "What named colors do I have available?"
     - :func:`~dartwork_mpl.show_colors` for Model B families, or
       :func:`~dartwork_mpl.diagnostics.render_color_catalog` for all libraries
   * - "Which colormaps come bundled, by category?"
     - :func:`~dartwork_mpl.diagnostics.render_cmap_catalog` — grouped or flat overview
   * - "Are my Korean / CJK fonts registered?"
     - :func:`~dartwork_mpl.plot_fonts` — pangram + weight spectrum
   * - "Is this colormap sequential, diverging, or cyclical?"
     - :func:`~dartwork_mpl.diagnostics.classify_cmap`
   * - "I just want a Python list, not a figure"
     - ``dm.list_colors`` or ``dm.colors``

API
---

.. autofunction:: dartwork_mpl.show_colors
   :no-index:
.. autofunction:: dartwork_mpl.plot_fonts
   :no-index:
.. autofunction:: dartwork_mpl.diagnostics.classify_cmap
   :no-index:

Module Reference
----------------

.. automodule:: dartwork_mpl.diagnostics
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
