Diagnostics (``dm.diagnostics``)
================================

Asset visualization helpers.

The :mod:`dartwork_mpl.diagnostics` module bundles the four helpers
that let you inspect what colormaps, color libraries, and fonts are
registered in your current environment. They render
publication-quality preview figures without ever calling
``plt.show()``, so they compose with your normal save / display
pipeline.

The four helpers are also re-exported at the top level
(``dm.classify_colormap``, ``dm.plot_colormaps``, ``dm.plot_colors``,
``dm.plot_fonts``) and from :mod:`dartwork_mpl.explore`. They were
previously housed in :mod:`dartwork_mpl.asset_viz`, which still
works but emits a ``DeprecationWarning`` (see :doc:`../migration`).

For richly-rendered swatch examples and the full narrative, see
:doc:`visualization`. The page below is a thin autodoc shadow that
matches the canonical module name.

API
---

.. automodule:: dartwork_mpl.diagnostics
   :members:
   :undoc-members:
   :show-inheritance:
