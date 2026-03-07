Extended Plots (xplot)
======================

Ready-to-use specialized visualization templates that extend core
dartwork-mpl with opinionated, publication-ready plot functions.

``plot_diverging_bar(categories, negatives, positives, ...)``

   Create a horizontal diverging bar graph where negative values extend
   left and positive values extend right from a central axis.

   - Parameters:
     - ``categories``: list of category labels.
     - ``negatives``: list of negative values (will extend left).
     - ``positives``: list of positive values (will extend right).
     - ``neg_label``, ``pos_label``: legend labels for the two sides.
     - ``neg_color``, ``pos_color``: bar colors.
     - ``total_row``: whether to add a bolded "Total" row.
     - ``figsize``: figure dimensions.
     - See source for full parameter list.
   - Returns:
     - ``(fig, ax)`` tuple.

``get_source_code()``

   Return the module source code as a string — useful for providing
   context to AI coding agents.

   - Returns:
     - ``str`` — complete source code of the module.

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

.. automodule:: dartwork_mpl.xplot
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: dartwork_mpl.xplot.diverging_bar
   :members:
   :undoc-members:
   :show-inheritance:
