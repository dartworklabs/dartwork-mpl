Diagnostics (``dm.diagnostics``)
================================

Asset visualization helpers.

The :mod:`dartwork_mpl.diagnostics` module bundles helpers
that let you inspect what colormaps, color libraries, and fonts are
registered in your current environment. They render
publication-quality preview figures without ever calling
``plt.show()``, so they compose with your normal save / display
pipeline.

Model B color previews live at ``dm.show_colors``. Diagnostic color-library and
colormap catalog renderers live under :mod:`dartwork_mpl.diagnostics`; font
preview remains available as ``dm.plot_fonts``. Upgrading from an older alias
path? See the :doc:`Migration Guide <../migration>`.

For richly-rendered swatch examples and the full narrative, see
:doc:`visualization`. The page below is a thin autodoc shadow that
matches the canonical module name.

API
---

.. automodule:: dartwork_mpl.diagnostics
   :members:
   :undoc-members:
   :show-inheritance:
