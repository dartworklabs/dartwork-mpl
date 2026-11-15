Style Management
================

Apply a packaged preset (scientific, report, minimal, presentation, poster,
web, dark, and Korean ``-kr`` variants) and size text and lines relative to
it with ``dm.fs`` / ``dm.lw`` / ``dm.fw``. A preset is a chain of
``.mplstyle`` layers under ``dartwork_mpl/style/assets``.

Typical usage
-------------

.. code-block:: python

   import dartwork_mpl as dm

   # Apply a preset (recommended)
   dm.style.use("scientific")       # papers
   dm.style.use("report")           # reports & dashboards
   dm.style.use("minimal")          # Tufte-style, data-ink focus
   dm.style.use("presentation")     # slides
   dm.style.use("poster")           # conference posters
   dm.style.use("web")              # web pages & documentation
   dm.style.use("dark")             # dark backgrounds
   dm.style.use("presentation-kr")  # Korean font variant

   # Several presets in order, or one for a single block
   dm.style.use(["report", "dark"])
   with dm.style.context("presentation"):
       ...

   # Inspect what a layer sets
   layers = dm.style.presets["report"]
   style_dict = dm.style.load_style_dict("font-presentation")

API
---

.. automodule:: dartwork_mpl.style
   :members:
   :undoc-members:
   :show-inheritance:
