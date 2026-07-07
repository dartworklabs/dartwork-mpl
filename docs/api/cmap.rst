Colormap Registry (``dm.cmap``)
===============================

Colormap registration has two public-facing layers.

The current v5 catalog lives in :mod:`dartwork_mpl.colors`: importing
``dartwork_mpl`` registers the 46 generated ``dc.*`` maps, their reversed
variants, and the two qualitative cycle maps (``dc.cycle`` /
``dc.cycle_print``). Most users should use those names directly through normal
matplotlib APIs such as ``plt.imshow(..., cmap="dc.aurora")`` or
``mpl.colormaps["dc.aurora"]``.

The ``dartwork_mpl.cmap`` module is the legacy text-file maps loader. It reads
``asset/cmap/*.txt`` and registers those backward-compatible maps on demand via
``dm.cmap.ensure_loaded()``. ``dm.list_colormaps()`` calls that loader before
listing names, so it reports the v5 catalog plus the legacy text-file maps
(excluding ``*_r`` variants unless requested).

To inspect the registered set, see :doc:`visualization` or call
``dm.list_colormaps()`` / ``dm.plot_colormaps()`` from
:mod:`dartwork_mpl.diagnostics`.

API
---

.. automodule:: dartwork_mpl.cmap
   :members:
   :undoc-members:
   :show-inheritance:
