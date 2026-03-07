Extended Plots (xplot)
======================

Ready-to-use specialized visualization templates that extend core
dartwork-mpl with opinionated, publication-ready plot functions.

Example
-------

.. code-block:: python

   from dartwork_mpl.xplot import plot_diverging_bar

   fig, ax = plot_diverging_bar(
       categories=['Category A', 'Category B', 'Category C'],
       negatives=[-30, -15, -25],
       positives=[40, 55, 35],
       neg_label='Decrease',
       pos_label='Increase',
   )

API
---

.. automodule:: dartwork_mpl.xplot
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: dartwork_mpl.xplot.diverging_bar
   :members:
   :undoc-members:
   :show-inheritance:
