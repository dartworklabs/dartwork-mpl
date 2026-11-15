Units and figure size (``dm.figsize`` / ``dm.cm`` / ``dm.Length``)
==================================================================

Physical units and figure size. A width is a unit string (``"13cm"``,
``"5in"``, ``"170mm"``, ``"24pt"``) or a :class:`~dartwork_mpl.size.Length`
from ``dm.cm`` / ``dm.inch`` / ``dm.mm`` / ``dm.pt`` (or ``dm.col1`` /
``dm.col2``); :func:`dartwork_mpl.figsize` turns it and an aspect or height
into the inch tuple matplotlib's ``figsize=`` expects.

.. code-block:: python

   import dartwork_mpl as dm

   dm.cm(13)            # Length(inch=5.118...)
   dm.cm(13).pt         # 368.5...

   # dm.figsize's second argument: pick whichever form reads naturally
   dm.figsize("13cm", "wide")        # aspect token
   dm.figsize("13cm", "16:9")        # "W:H" ratio
   dm.figsize("13cm", 0.6)           # numeric ratio (height/width)
   dm.figsize("13cm", "8cm")         # unit-string height
   dm.figsize("13cm", dm.cm(8))      # Length height

   # The active preset's canvas when the request names no size
   dm.figsize_for(n_points=12, n_series=2)
   dm.figsize_for(nrows=2, ncols=3)

API
---

.. automodule:: dartwork_mpl.size
   :members:
   :undoc-members:
   :show-inheritance:
