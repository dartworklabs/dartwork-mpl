Style Management
================

Helpers for discovering and applying the packaged matplotlib styles. The
``Style`` manager reads ``asset/mplstyle``, provides preset combinations
(scientific, report, presentation, poster, web, minimal, dark, and Korean
variants), resets ``rcParams``, and stacks multiple style files when needed.

Typical usage
-------------

.. code-block:: python

   import dartwork_mpl as dm

   # Apply a preset (recommended)
   dm.style.use("scientific")       # papers
   dm.style.use("report")           # reports & dashboards
   dm.style.use("presentation")     # slides
   dm.style.use("poster")           # conference posters
   dm.style.use("web")              # web pages & documentation
   dm.style.use("minimal")          # Tufte-style, data-ink focus
   dm.style.use("dark")             # dark backgrounds
   dm.style.use("presentation-kr")  # Korean font variant

   # Stack multiple styles for advanced customization
   dm.style.stack(["base", "font-report", "theme-dark"])

   # Inspect what a style will set
   available = dm.list_styles()
   style_dict = dm.load_style_dict("font-presentation")

API
---

.. automodule:: dartwork_mpl.style
   :members:
   :undoc-members:
   :show-inheritance:
