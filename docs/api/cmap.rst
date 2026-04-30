Colormap Registry (``dm.cmap``)
===============================

Custom colormap registry.

The ``dartwork_mpl.cmap`` module reads colormap text files from
``asset/cmap/`` at import time and registers them with matplotlib.
Most consumers never touch this module directly — once
``import dartwork_mpl as dm`` runs, the registered colormaps are
available through normal matplotlib APIs (``plt.imshow(..., cmap="...")``,
``mpl.colormaps[...]``).

To inspect the registered set, see :doc:`visualization` or call
``dm.list_colormaps()`` / ``dm.plot_colormaps()`` from
:mod:`dartwork_mpl.diagnostics`.

API
---

.. automodule:: dartwork_mpl.cmap
   :members:
   :undoc-members:
   :show-inheritance:
