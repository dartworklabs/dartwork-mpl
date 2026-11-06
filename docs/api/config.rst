Configuration
=============

Process-wide defaults for dartwork-mpl behaviour toggles. Mutate the
:data:`~dartwork_mpl.config` singleton once near the top of your program
to flip the default of every call site that reads it — without having
to thread the keyword through each individual call.

Per-call keyword arguments always win over the global default.

Example
-------

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   dm.style.use("scientific")

   # Opt in to orphan-tick adoption globally.
   dm.config.adopt_orphan_tick_font = True

   fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
   ax.plot([1, 2, 3], [1, 4, 9])      # no axis label on x
   dm.simple_layout(fig)              # orphan tick fonts adopted
   dm.save_formats(fig, "out", formats=("png",))   # also adopted

   # Per-call opt-out still works.
   dm.simple_layout(fig, adopt_orphan_tick_font=False)

   # Or scope the change to a block.
   with dm.config.override(adopt_orphan_tick_font=True):
       dm.save_formats(fig, "out", formats=("png",))

Twin-axis colours
-----------------

``dm.simple_layout`` colours each side of a ``twinx`` / ``twiny`` pair like
the one series read on it (``twin_colors="series"``, the default). A colour
you set on any part of a side (spine, tick marks, tick labels, axis label;
on a ``twinx`` pair the left spine you see is the twin's copy,
``ax2.spines["left"]``) makes that whole side yours: its other parts keep
the preset's colours, and the other side keeps its series colour. The
exception is a colour set before the first ``dm.simple_layout`` that
equals the preset's default (``"black"`` under the light presets): it
cannot be told from the default and is painted with the rest of the side.
``"neutral"`` keeps the preset's axis colours, so it is the way to black
or neutral twin axes:

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   with dm.config.override(twin_colors="neutral"):
       fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
       ax.bar([1, 2, 3], [3, 4, 2])
       ax.twinx().plot([1, 2, 3], [10, 12, 9], color="dc.orange6")
       dm.simple_layout(fig)      # both sides keep the preset's colours

API
---

.. autoclass:: dartwork_mpl.Config
   :members:

.. autodata:: dartwork_mpl.config
   :no-value:
