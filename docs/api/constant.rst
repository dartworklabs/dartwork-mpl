Figure Constants
================

Predefined figure width constants commonly used in scientific
publications.  These are computed from :func:`~dartwork_mpl.cm2in` at
import time and match standard single- and double-column widths.

``SW``
   Single-column figure width: ``cm2in(9)`` ≈ 3.543 inches.

``DW``
   Double-column figure width: ``cm2in(17)`` ≈ 6.693 inches.

Example
-------

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   # Single-column figure
   fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.75))

   # Double-column figure
   fig, axes = plt.subplots(1, 2, figsize=(dm.DW, dm.DW * 0.4))

.. automodule:: dartwork_mpl.constant
   :members:
   :undoc-members:
