Figure Creation
===============

.. note::

   The dartwork-mpl ``figure`` module was removed. ``dm.subplots`` and
   ``dm.figure`` are no longer part of the public API — they raise
   :class:`AttributeError` at access time. Construct figures with
   matplotlib's own constructors and pass the dartwork-mpl sizing
   helper into ``figsize=``::

      import matplotlib.pyplot as plt
      import dartwork_mpl as dm

      dm.style.use("scientific")
      fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))

   ``dm.figsize(width, aspect)`` is documented in :doc:`units`. See
   :doc:`../migration` for the full mapping from the 0.4-era
   ``dm.subplots`` / ``dm.figure`` surface.
