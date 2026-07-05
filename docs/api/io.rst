Save & Export
=============

Thin wrappers around ``matplotlib.Figure.savefig`` for common workflows:
export multiple formats in one call, or save-and-display SVGs sized for
notebooks/reports.

Example
-------

.. snippet: no-run
.. code-block:: python

   import dartwork_mpl as dm

   # Multi-format export with validation
   dm.save_formats(fig, "report/figures/example",
                   formats=("png", "svg", "pdf"), dpi=300)

   # Save and preview
   dm.save_and_show(fig, size=720)

   # Display an existing SVG
   dm.show("output/forecast.svg", size=540)

API
---

.. autofunction:: dartwork_mpl.save_formats
.. autofunction:: dartwork_mpl.save_and_show
.. autofunction:: dartwork_mpl.show
