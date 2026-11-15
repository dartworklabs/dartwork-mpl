Save & Export
=============

Write one figure to several formats in one call. Saving only writes files;
run ``dm.validate_figure(fig)`` before it to check the figure.

Example
-------

.. snippet: no-run
.. code-block:: python

   import dartwork_mpl as dm

   dm.save_formats(fig, "report/figures/example",
                   formats=("png", "svg", "pdf"), dpi=300)

API
---

.. autofunction:: dartwork_mpl.save_formats
