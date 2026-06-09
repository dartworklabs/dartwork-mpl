Asset Diagnostics
=================

The :mod:`dartwork_mpl.diagnostics` module bundles four helpers that
let you inspect *exactly* what colormaps, color libraries, and fonts
are registered in your current environment. They render
publication-quality preview figures without ever calling
``plt.show()``, so they compose with your normal save / display
pipeline.

The four helpers are also re-exported at the top level
(``dm.classify_colormap``, ``dm.plot_colormaps``, ``dm.plot_colors``,
``dm.plot_fonts``) and from :mod:`dartwork_mpl.explore`. Upgrading
from an older alias path? See the :doc:`Migration Guide <../migration>`.

Quick examples
--------------

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib as mpl

   # Group colormaps by category and render one figure per group
   figs = dm.plot_colormaps(group_by_type=True, ncols=4)

   # Preview every named color, one figure per design system
   figs = dm.plot_colors(ncols=5, show_hex=True)

   # Audit registered font families with weight + italic spectrum
   fig = dm.plot_fonts(font_size=11, ncols=3)

   # Classify an arbitrary colormap
   dm.classify_colormap(mpl.colormaps["coolwarm"])  # → "Diverging"

.. figure:: images/viz_example.svg
   :alt: Color palette preview from plot_colors diagnostic tool
   :width: 100%

For a click-and-copy palette browser without leaving the docs, see
the :doc:`interactive palette explorer <../color_system/colors>`. For
a colormap browser, see the :doc:`colormap explorer
<../color_system/colormaps>`.

Choosing the right helper
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Goal
     - Helper
   * - "What named colors do I have available?"
     - :func:`~dartwork_mpl.plot_colors` — one figure per design system
   * - "Which colormaps come bundled, by category?"
     - :func:`~dartwork_mpl.plot_colormaps` — grouped or flat overview
   * - "Are my Korean / CJK fonts registered?"
     - :func:`~dartwork_mpl.plot_fonts` — pangram + weight spectrum
   * - "Is this colormap sequential, diverging, or cyclical?"
     - :func:`~dartwork_mpl.classify_colormap`
   * - "I just want a Python list, not a figure"
     - :func:`~dartwork_mpl.list_palettes`,
       :func:`~dartwork_mpl.list_colormaps`,
       :func:`~dartwork_mpl.show_palette`
       (see :doc:`explore module <../api/index>`)

API
---

.. autofunction:: dartwork_mpl.plot_colormaps
   :no-index:
.. autofunction:: dartwork_mpl.plot_colors
   :no-index:
.. autofunction:: dartwork_mpl.plot_fonts
   :no-index:
.. autofunction:: dartwork_mpl.classify_colormap
   :no-index:

Module Reference
----------------

.. automodule:: dartwork_mpl.diagnostics
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
