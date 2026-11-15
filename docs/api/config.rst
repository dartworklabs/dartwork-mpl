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

API
---

.. autoclass:: dartwork_mpl.Config
   :members:

.. autodata:: dartwork_mpl.config
   :no-value:
