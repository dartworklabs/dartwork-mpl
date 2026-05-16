Figure Constants (deprecated)
=============================

.. deprecated:: 0.4.0
   All names exposed by ``dartwork_mpl.constant`` are deprecated and
   will be removed in 0.5.0. Use ``plt.subplots(figsize=dm.figsize(
   "...", "..."))`` instead, with ``dm.col1`` (= 9 cm) / ``dm.col2``
   (= 17 cm) as the academic-column sugar. See :doc:`../migration`
   for the per-token mapping table.

Predefined figure width constants commonly used in scientific
publications.  These are computed from :func:`~dartwork_mpl.cm2in` at
import time and match standard single- and double-column widths.

``SW`` (deprecated 0.4.0)
   Single-column figure width: ``cm2in(9)`` ≈ 3.543 inches.

``DW`` (deprecated 0.4.0)
   Double-column figure width: ``cm2in(17)`` ≈ 6.693 inches.

Example (legacy 0.3 idiom)
--------------------------

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   # REMOVED in 0.4.0 — `dm.SW` raises `AttributeError`. The block
   # below is shown only to document the migration shape.
   fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.75))

   # Modern replacement
   fig, ax = plt.subplots(figsize=dm.figsize(dm.col1, "standard"))
   fig, axes = plt.subplots(1, 2, figsize=dm.figsize(dm.col2, 0.4))

.. note::

   The ``dartwork_mpl.constant`` module itself has been removed; the
   names above are listed here only as a migration aid. Any access
   raises ``AttributeError`` at runtime.
